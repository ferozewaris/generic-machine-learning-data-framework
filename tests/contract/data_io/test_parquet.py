from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from gmldf.core.config import ConfigError, SourceSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import RunContext, RunIdentity
from gmldf.data_io.parquet import PandasParquetReader


@pytest.fixture
def context():
    return RunContext(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        allowed_capabilities=[
            "pandas_parquet_read",
            "pandas_parquet_write_new",
            "pandas_parquet_write_overwrite",
        ],
    )


def source(path, columns, **kwargs):
    return SourceSpec(id="raw", connector="parquet", location=str(path), columns=columns, **kwargs)


def test_read_native_values_nulls_unicode_decimal_and_utc(tmp_path, context):
    path = tmp_path / "in.parquet"
    table = pa.table(
        {
            "s": ["東京", None],
            "i": pa.array([2**60 + 1, None], type=pa.int64()),
            "f": [1.25, None],
            "b": [True, None],
            "d": [Decimal("12.50"), None],
            "day": [date(2026, 1, 2), None],
            "stamp": [datetime(2026, 1, 2, 3, tzinfo=timezone.utc), None],
        }
    )
    pq.write_table(table, path)
    columns = dict(
        zip(
            table.column_names,
            ["string", "int64", "float64", "boolean", "decimal", "date", "timestamp"],
            strict=True,
        )
    )
    ref = PandasParquetReader().read(source(path, columns), context)
    assert ref.row_count == 2
    assert ref.source_uri == path.as_uri()
    assert ref.source_version is None
    assert [c.dtype for c in ref.columns] == list(columns.values())
    frame = ref.handle
    assert frame.iloc[0]["s"] == "東京"
    assert frame.iloc[0]["i"] == 2**60 + 1
    assert frame.iloc[0]["d"] == Decimal("12.50")
    assert frame.iloc[0]["stamp"] == pd.Timestamp("2026-01-02T03:00:00Z")
    assert frame.iloc[0]["day"] == pd.Timestamp("2026-01-02")
    assert frame.iloc[1].isna().all()


@pytest.mark.parametrize(
    "values,dtype",
    [([float("nan")], "float64"), ([float("inf")], "float64"), (["2"], "int64"), ([1.25], "int64")],
)
def test_invalid_physical_types_and_nonfinite_values_reject(tmp_path, context, values, dtype):
    path = tmp_path / "in.parquet"
    pq.write_table(pa.table({"x": values}), path)
    with pytest.raises(FrameworkError) as caught:
        PandasParquetReader().read(source(path, {"x": dtype}), context)
    assert caught.value.error.code == "DATA_INVALID"


@pytest.mark.parametrize("values", [[], [None, None]])
def test_empty_or_allnull_native_columns_preserve_declared_types(tmp_path, context, values):
    path = tmp_path / "in.parquet"
    pq.write_table(pa.table({"x": pa.array(values, type=pa.int64())}), path)
    ref = PandasParquetReader().read(source(path, {"x": "int64"}), context)
    assert ref.row_count == len(values)
    assert str(ref.handle["x"].dtype) == "Int64"


def test_preflight_requires_explicit_schema_and_rejects_unknown_options(tmp_path, context):
    reader = PandasParquetReader()
    with pytest.raises(ConfigError):
        reader.validate(source(tmp_path / "missing", {}), context)
    with pytest.raises(ConfigError):
        reader.validate(
            source(tmp_path / "missing", {"x": "int64"}, options={"filters": []}), context
        )
    assert list(tmp_path.iterdir()) == []


def test_corrupt_missing_or_schema_mismatched_parquet_is_safe(tmp_path, context):
    path = tmp_path / "in.parquet"
    for content in (None, b"not parquet"):
        if content is not None:
            path.write_bytes(content)
        with pytest.raises(FrameworkError) as caught:
            PandasParquetReader().read(source(path, {"x": "int64"}), context)
        assert caught.value.error.code == "DATA_INVALID"
    pq.write_table(pa.table({"other": [1]}), path)
    with pytest.raises(FrameworkError):
        PandasParquetReader().read(source(path, {"x": "int64"}), context)
