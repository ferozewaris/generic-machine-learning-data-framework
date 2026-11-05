from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from gmldf.core.config import ConfigError, OutputSpec, SourceSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext, RunIdentity
from gmldf.data_io.parquet import PandasParquetReader, PandasParquetWriter


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


def sink(path, **kwargs):
    return OutputSpec(id="out", dataset="raw", connector="parquet", location=str(path), **kwargs)


def dataset(frame, columns):
    return DatasetRef(
        id="raw",
        engine="pandas",
        materialization="memory",
        columns=[ColumnSpec(name=name, dtype=dtype) for name, dtype in columns.items()],
    ).with_handle(frame)


def test_writer_roundtrips_values_types_and_receipts_without_index(tmp_path, context):
    columns = {
        "s": "string",
        "i": "int64",
        "f": "float64",
        "b": "boolean",
        "d": "decimal",
        "day": "date",
        "stamp": "timestamp",
    }
    frame = pd.DataFrame(
        {
            "s": pd.Series(["東京", None], dtype="string"),
            "i": pd.Series([2**60 + 1, None], dtype="Int64"),
            "f": pd.Series([1.25, None], dtype="Float64"),
            "b": pd.Series([True, None], dtype="boolean"),
            "d": [Decimal("12.50"), None],
            "day": pd.to_datetime(["2026-01-02", None]),
            "stamp": pd.to_datetime(["2026-01-02T03:00:00Z", None]),
        }
    )
    original = frame.copy(deep=True)
    path = tmp_path / "out.parquet"
    receipt = PandasParquetWriter().write(dataset(frame, columns), sink(path), context)
    assert receipt.commit_status == "committed"
    assert receipt.row_count == 2
    assert receipt.commit_id.startswith("sha256:")
    result = PandasParquetReader().read(source(path, columns), context)
    assert [c.dtype for c in result.columns] == list(columns.values())
    assert list(result.handle.columns) == list(columns)
    for name in columns:
        assert result.handle[name].isna().tolist() == frame[name].isna().tolist()
        assert result.handle[name].dropna().tolist() == frame[name].dropna().tolist()
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("values", [[], [None, None]])
def test_writer_preserves_empty_and_allnull_declared_columns(tmp_path, context, values):
    path = tmp_path / "out.parquet"
    frame = pd.DataFrame(
        {"i": pd.Series(values, dtype="Int64"), "d": pd.Series(values, dtype=object)}
    )
    columns = {"i": "int64", "d": "decimal"}
    PandasParquetWriter().write(dataset(frame, columns), sink(path), context)
    result = PandasParquetReader().read(source(path, columns), context)
    assert result.row_count == len(values)
    assert result.columns == dataset(frame, columns).columns
    assert result.handle.isna().all().all()


@pytest.mark.parametrize(
    "dtype,value",
    [
        ("date", pd.Timestamp("2026-01-02T12:00")),
        ("decimal", 1.25),
        ("int64", 1.5),
        ("float64", float("inf")),
        ("boolean", "maybe"),
        ("timestamp", "2026-01-02"),
    ],
)
def test_writer_rejects_lossy_or_incompatible_native_values_before_publication(
    tmp_path, context, dtype, value
):
    path = tmp_path / "out.parquet"
    with pytest.raises(FrameworkError) as caught:
        PandasParquetWriter().write(
            dataset(pd.DataFrame({"x": [value]}), {"x": dtype}), sink(path), context
        )
    assert caught.value.error.code == "DATA_INVALID"
    assert list(tmp_path.iterdir()) == []


def test_writer_preserves_no_clobber_and_explicit_overwrite_receipts(tmp_path, context):
    from gmldf.data_io.base import WriteFailure

    path = tmp_path / "out.parquet"
    path.write_bytes(b"old")
    ref = dataset(pd.DataFrame({"x": [1]}), {"x": "int64"})
    with pytest.raises(WriteFailure) as caught:
        PandasParquetWriter().write(ref, sink(path), context)
    assert caught.value.receipt.commit_status == "not_committed"
    assert path.read_bytes() == b"old"
    receipt = PandasParquetWriter().write(ref, sink(path, mode="overwrite"), context)
    assert receipt.commit_status == "committed"
    assert PandasParquetReader().read(source(path, {"x": "int64"}), context).handle[
        "x"
    ].tolist() == [1]


def test_writer_rejects_nullability_violations_and_unknown_options(tmp_path, context):
    path = tmp_path / "out.parquet"
    with pytest.raises(ConfigError):
        PandasParquetWriter().validate(sink(path, options={"compression": "unknown"}), context)
    ref = dataset(pd.DataFrame({"x": pd.Series([None], dtype="Int64")}), {"x": "int64"})
    ref = ref.model_copy(
        update={"columns": [ref.columns[0].model_copy(update={"nullable": False})]}
    )
    with pytest.raises(FrameworkError):
        PandasParquetWriter().write(ref, sink(path), context)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("storage", ["python", "pyarrow"])
def test_writer_rejects_nan_text_without_masking_it(tmp_path, context, storage):
    frame = pd.DataFrame({"x": pd.Series(["NaN"], dtype=pd.StringDtype(storage=storage))})
    with pytest.raises(FrameworkError) as caught:
        PandasParquetWriter().write(
            dataset(frame, {"x": "float64"}), sink(tmp_path / "out.parquet"), context
        )
    assert caught.value.error.code == "DATA_INVALID"
    assert list(tmp_path.iterdir()) == []


def test_nanosecond_timestamp_survives_without_truncation(tmp_path, context):
    path = tmp_path / "out.parquet"
    value = pd.Timestamp("2026-01-02T03:04:05.000000001Z")
    frame = pd.DataFrame({"stamp": pd.Series([value], dtype="datetime64[ns, UTC]")})
    PandasParquetWriter().write(dataset(frame, {"stamp": "timestamp"}), sink(path), context)
    result = PandasParquetReader().read(source(path, {"stamp": "timestamp"}), context)
    assert result.handle["stamp"].iloc[0] == value
    assert result.handle["stamp"].iloc[0].nanosecond == 1


@pytest.mark.parametrize("offset", ["+14:00", "-12:00"])
def test_date_conversion_preserves_explicit_local_calendar_date(tmp_path, context, offset):
    frame = pd.DataFrame({"day": pd.to_datetime([f"2026-01-02T00:00:00{offset}", None])})
    original = frame.copy(deep=True)
    path = tmp_path / "out.parquet"
    PandasParquetWriter().write(dataset(frame, {"day": "date"}), sink(path), context)
    result = PandasParquetReader().read(source(path, {"day": "date"}), context)
    assert result.handle["day"].iloc[0] == pd.Timestamp("2026-01-02")
    assert pd.isna(result.handle["day"].iloc[1])
    pd.testing.assert_frame_equal(frame, original)


def test_nonnullable_column_schema_survives_parquet_roundtrip(tmp_path, context):
    path = tmp_path / "out.parquet"
    ref = dataset(pd.DataFrame({"x": [1]}), {"x": "int64"})
    ref = ref.model_copy(
        update={"columns": [ref.columns[0].model_copy(update={"nullable": False})]}
    )
    PandasParquetWriter().write(ref, sink(path), context)
    assert pq.read_schema(path).field("x").nullable is False
    restored = PandasParquetReader().read(source(path, {"x": "int64"}), context)
    assert restored.columns == ref.columns
