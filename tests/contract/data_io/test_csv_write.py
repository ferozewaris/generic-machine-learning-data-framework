from decimal import Decimal

import pandas as pd
import pytest

from gmldf.core.config import ConfigError, OutputSpec, SourceSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext, RunIdentity
from gmldf.data_io.csv import PandasCSVReader, PandasCSVWriter
from gmldf.data_io.local_publish import WriteFailure


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
            "pandas_csv_write_new",
            "pandas_csv_write_overwrite",
            "pandas_csv_read",
        ],
    )


def dataset(frame, types=None):
    types = types or {name: "string" for name in frame.columns}
    return DatasetRef(
        id="data",
        engine="pandas",
        materialization="memory",
        row_count=len(frame),
        columns=[ColumnSpec(name=name, dtype=types[name]) for name in frame.columns],
    ).with_handle(frame)


def sink(path, mode="error_if_exists", **options):
    return OutputSpec(
        id="out",
        dataset="data",
        connector="csv",
        location=str(path),
        mode=mode,
        options={"encoding": "utf-8", "delimiter": ";", "null_value": "NULL", **options},
    )


def test_csv_publish_roundtrips_declared_values_and_leaves_input_untouched(tmp_path, context):
    path = tmp_path / "out.csv"
    frame = pd.DataFrame(
        {
            "name": ["東京", None],
            "amount": [Decimal("12.50"), None],
            "flag": pd.Series([True, None], dtype="boolean"),
            "day": pd.to_datetime(["2026-01-02", None]),
        }
    )
    before = frame.copy(deep=True)
    types = {"name": "string", "amount": "decimal", "flag": "boolean", "day": "date"}
    receipt = PandasCSVWriter().write(
        dataset(frame, types), sink(path, decimal=",", date_formats={"day": "%Y-%m-%d"}), context
    )
    assert receipt.commit_status == "committed"
    assert receipt.row_count == 2
    assert receipt.destination == path.as_uri()
    assert path.read_text().splitlines()[0] == "name;amount;flag;day"
    restored = (
        PandasCSVReader()
        .read(
            SourceSpec(
                id="restored",
                connector="csv",
                location=str(path),
                columns=types,
                options={
                    "encoding": "utf-8",
                    "delimiter": ";",
                    "null_values": ["NULL"],
                    "decimal": ",",
                    "date_formats": {"day": "%Y-%m-%d"},
                },
            ),
            context,
        )
        .handle
    )
    assert restored["name"].iloc[0] == "東京"
    assert restored["amount"].iloc[0] == Decimal("12.50")
    assert restored["flag"].dtype == pd.BooleanDtype()
    assert bool(restored["flag"].iloc[0])
    assert str(restored["day"].iloc[0].date()) == "2026-01-02"
    assert restored.iloc[1].isna().all()
    pd.testing.assert_frame_equal(frame, before)


def test_default_preserves_existing_and_explicit_overwrite_is_opt_in(tmp_path, context):
    path = tmp_path / "out.csv"
    path.write_bytes(b"old")
    ref = dataset(pd.DataFrame({"x": ["new"]}))
    with pytest.raises(WriteFailure) as caught:
        PandasCSVWriter().write(ref, sink(path), context)
    assert caught.value.receipt.commit_status == "not_committed"
    assert path.read_bytes() == b"old"
    receipt = PandasCSVWriter().write(ref, sink(path, mode="overwrite"), context)
    assert receipt.commit_status == "committed"
    assert "new" in path.read_text()


@pytest.mark.parametrize("mode", ["append", "upsert"])
def test_unsupported_modes_cannot_modify_a_destination(tmp_path, context, mode):
    path = tmp_path / "out.csv"
    with pytest.raises(FrameworkError) as caught:
        PandasCSVWriter().write(
            dataset(pd.DataFrame({"x": ["new"]})), sink(path, mode=mode), context
        )
    assert caught.value.error.code == "CAPABILITY_UNSUPPORTED"
    assert list(tmp_path.iterdir()) == []


def test_serialization_failure_preserves_previous_file_and_truthful_receipt(
    tmp_path, context, monkeypatch
):
    def fail(self, path, **kwargs):
        path.write_bytes(b"partial")
        raise RuntimeError("SENTINEL")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail)
    path = tmp_path / "out.csv"
    path.write_bytes(b"old")
    with pytest.raises(WriteFailure) as caught:
        PandasCSVWriter().write(
            dataset(pd.DataFrame({"x": ["new"]})), sink(path, mode="overwrite"), context
        )
    assert path.read_bytes() == b"old"
    assert caught.value.receipt.row_count is None
    assert "SENTINEL" not in caught.value.error.model_dump_json()


def test_output_null_token_collision_is_rejected_before_publication(tmp_path, context):
    path = tmp_path / "out.csv"
    with pytest.raises(FrameworkError) as caught:
        PandasCSVWriter().write(dataset(pd.DataFrame({"x": ["NULL"]})), sink(path), context)
    assert caught.value.error.code == "DATA_INVALID"
    assert not path.exists()


def test_temporal_output_requires_explicit_formats(tmp_path, context):
    path = tmp_path / "out.csv"
    with pytest.raises(ConfigError):
        PandasCSVWriter().write(
            dataset(pd.DataFrame({"day": pd.to_datetime(["2026-01-01"])}), {"day": "date"}),
            sink(path),
            context,
        )
    assert not path.exists()


def test_header_only_output_preserves_schema(tmp_path, context):
    path = tmp_path / "empty.csv"
    receipt = PandasCSVWriter().write(
        dataset(pd.DataFrame({"x": pd.Series([], dtype="string")})), sink(path), context
    )
    assert receipt.row_count == 0
    assert path.read_text() == "x\n"


def test_unicode_delimiter_roundtrips_without_changing_values(tmp_path, context):
    path = tmp_path / "unicode.csv"
    PandasCSVWriter().write(
        dataset(pd.DataFrame({"x": ["東京"], "y": ["two"]})), sink(path, delimiter="§"), context
    )
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", pd.errors.ParserWarning)
        restored = PandasCSVReader().read(
            SourceSpec(
                id="restored",
                connector="csv",
                location=str(path),
                columns={"x": "string", "y": "string"},
                options={"encoding": "utf-8", "delimiter": "§", "null_values": ["NULL"]},
            ),
            context,
        )
    assert restored.handle.iloc[0].tolist() == ["東京", "two"]


def test_denied_writer_cannot_start_publication(tmp_path, context, monkeypatch):
    from gmldf.data_io import csv

    def forbidden(*args, **kwargs):
        raise AssertionError("publication attempted before authorization")

    monkeypatch.setattr(csv, "publish", forbidden)
    with pytest.raises(FrameworkError) as caught:
        PandasCSVWriter().write(
            dataset(pd.DataFrame({"x": ["new"]})),
            sink(tmp_path / "out.csv"),
            context.model_copy(update={"allowed_capabilities": []}),
        )
    assert caught.value.error.code == "POLICY_DENIED"


def test_decimal_separator_null_collision_cannot_erase_a_number(tmp_path, context):
    path = tmp_path / "out.csv"
    with pytest.raises(FrameworkError) as caught:
        PandasCSVWriter().write(
            dataset(pd.DataFrame({"x": pd.Series([1.5], dtype="Float64")}), {"x": "float64"}),
            sink(path, decimal=",", null_value="1,5"),
            context,
        )
    assert caught.value.error.code == "DATA_INVALID"
    assert not path.exists()


def test_date_output_cannot_discard_non_midnight_time_or_replace_existing_file(tmp_path, context):
    path = tmp_path / "out.csv"
    path.write_bytes(b"old")
    frame = pd.DataFrame({"day": pd.to_datetime(["2026-01-02T12:34:56"])})
    with pytest.raises(FrameworkError) as caught:
        PandasCSVWriter().write(
            dataset(frame, {"day": "date"}),
            sink(path, mode="overwrite", date_formats={"day": "%Y-%m-%d"}),
            context,
        )
    assert caught.value.error.code == "DATA_INVALID"
    assert path.read_bytes() == b"old"


def test_numeric_and_utc_timestamp_values_roundtrip_with_explicit_formats(tmp_path, context):
    path = tmp_path / "typed.csv"
    frame = pd.DataFrame(
        {
            "i": pd.Series([2, None], dtype="Int64"),
            "f": pd.Series([1.25, None], dtype="Float64"),
            "when": pd.to_datetime(["2026-01-02T01:02:03+00:00", None]),
        }
    )
    types = {"i": "int64", "f": "float64", "when": "timestamp"}
    formats = {"when": "%Y-%m-%dT%H:%M:%S%z"}
    PandasCSVWriter().write(
        dataset(frame, types),
        sink(path, encoding="utf-16", decimal=",", date_formats=formats),
        context,
    )
    restored = (
        PandasCSVReader()
        .read(
            SourceSpec(
                id="restored",
                connector="csv",
                location=str(path),
                columns=types,
                options={
                    "encoding": "utf-16",
                    "delimiter": ";",
                    "null_values": ["NULL"],
                    "decimal": ",",
                    "date_formats": formats,
                    "utc": True,
                },
            ),
            context,
        )
        .handle
    )
    assert restored["i"].iloc[0] == 2
    assert restored["f"].iloc[0] == 1.25
    assert restored["when"].iloc[0] == frame["when"].iloc[0]
    assert restored.iloc[1].isna().all()


@pytest.mark.parametrize("storage", ["python", "pyarrow"])
def test_writer_does_not_convert_nan_text_into_null(tmp_path, context, storage):
    from gmldf.core.types import ColumnSpec, DatasetRef

    frame = pd.DataFrame({"x": pd.Series(["NaN"], dtype=pd.StringDtype(storage=storage))})
    dataset = DatasetRef(
        id="data",
        engine="pandas",
        materialization="memory",
        columns=[ColumnSpec(name="x", dtype="float64")],
    ).with_handle(frame)
    output = OutputSpec(
        id="out",
        dataset="data",
        connector="csv",
        location=str(tmp_path / "out.csv"),
        options={"encoding": "utf-8", "delimiter": ",", "null_value": "NULL"},
    )
    with pytest.raises(FrameworkError) as caught:
        PandasCSVWriter().write(dataset, output, context)
    assert caught.value.error.code == "DATA_INVALID"
    assert not (tmp_path / "out.csv").exists()
