from decimal import Decimal

import pytest

from gmldf.core.config import ConfigError, SourceSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import RunContext, RunIdentity
from gmldf.data_io.csv import PandasCSVReader


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
        allowed_capabilities=["pandas_csv_read"],
    )


def source(path, columns, **options):
    return SourceSpec(
        id="raw",
        connector="csv",
        location=str(path),
        columns=columns,
        options={
            "encoding": "utf-8",
            "delimiter": ",",
            "null_values": ["NULL"],
            **options,
        },
    )


def test_read_declared_unicode_decimal_date_null_and_integer_values(tmp_path, context):
    path = tmp_path / "input.csv"
    path.write_text(
        "name;amount;day;count\n東京;12,50;2026-01-02;2\nNULL;NULL;NULL;NULL\n", encoding="utf-8"
    )
    dataset = PandasCSVReader().read(
        source(
            path,
            {"name": "string", "amount": "decimal", "day": "date", "count": "int64"},
            delimiter=";",
            decimal=",",
            date_formats={"day": "%Y-%m-%d"},
        ),
        context,
    )
    assert dataset.engine == "pandas"
    assert dataset.row_count == 2
    assert dataset.source_uri == path.as_uri()
    assert dataset.source_version is None
    frame = dataset.handle
    assert frame.iloc[0]["name"] == "東京"
    assert frame.iloc[0]["amount"] == Decimal("12.50")
    assert str(frame.iloc[0]["day"].date()) == "2026-01-02"
    assert frame.iloc[0]["count"] == 2
    assert frame.iloc[1].isna().all()
    assert [column.dtype for column in dataset.columns] == ["string", "decimal", "date", "int64"]
    assert "handle" not in dataset.model_dump_json()


def test_header_only_empty_data_retains_declared_types(tmp_path, context):
    path = tmp_path / "empty.csv"
    path.write_text("x,day\n")
    dataset = PandasCSVReader().read(
        source(path, {"x": "float64", "day": "timestamp"}, date_formats={"day": "%Y-%m-%d"}),
        context,
    )
    assert dataset.row_count == 0
    assert list(dataset.handle.columns) == ["x", "day"]
    assert str(dataset.handle["x"].dtype) == "Float64"


@pytest.mark.parametrize(
    ("content", "error_path"),
    [
        ("x,y\n1\n", "sources.raw.rows"),
        ("x,y\n1,2,3\n", "sources.raw.rows"),
        ("x,x\n1,2\n", "sources.raw.columns"),
        ("different\n1\n", "sources.raw.columns"),
        ("x,y\nnot-an-integer,2\n", "sources.raw.columns"),
    ],
)
def test_malformed_rows_and_schema_failures_have_safe_distinct_errors(
    tmp_path, context, content, error_path
):
    path = tmp_path / "SENTINEL.csv"
    path.write_text(content)
    with pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(source(path, {"x": "int64", "y": "int64"}), context)
    assert caught.value.error.code == "DATA_INVALID"
    assert caught.value.error.path == error_path
    assert "SENTINEL" not in caught.value.error.model_dump_json()


def test_missing_file_is_distinct_from_schema_failure(tmp_path, context):
    with pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(source(tmp_path / "missing.csv", {"x": "string"}), context)
    assert caught.value.error.path == "sources.raw.location"
    assert isinstance(caught.value.__cause__, FileNotFoundError)


def test_csv_requires_explicit_parse_settings_and_schema(tmp_path, context):
    with pytest.raises(ConfigError):
        PandasCSVReader().read(
            SourceSpec(id="raw", connector="csv", location=str(tmp_path / "missing.csv")), context
        )


def test_denied_read_performs_no_file_access(tmp_path, context, monkeypatch):
    from pathlib import Path

    def forbidden(*args, **kwargs):
        raise AssertionError("file access before authorization")

    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(
            source(tmp_path / "input.csv", {"x": "string"}),
            context.model_copy(update={"allowed_capabilities": []}),
        )
    assert caught.value.error.code == "POLICY_DENIED"


@pytest.mark.parametrize(
    "location", ["https://host/input.csv", "https://[bad", "file://user:password@host/input.csv"]
)
def test_local_reader_rejects_remote_or_malformed_locations(context, location):
    with pytest.raises(ConfigError):
        PandasCSVReader().read(source(location, {"x": "string"}), context)


def test_unknown_encoding_is_a_config_error_before_source_access(tmp_path, context):
    with pytest.raises(ConfigError):
        PandasCSVReader().read(
            source(tmp_path / "missing.csv", {"x": "string"}, encoding="unknown-encoding"), context
        )


def test_nonregular_path_is_rejected_before_open(tmp_path, context, monkeypatch):
    from pathlib import Path

    original = Path.open

    def checked(path, *args, **kwargs):
        if path == tmp_path:
            raise AssertionError("opened a nonregular source")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    with pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(source(tmp_path, {"x": "string"}), context)
    assert caught.value.error.path == "sources.raw.location"


@pytest.mark.parametrize(
    ("dtype", "value"),
    [
        ("float64", "inf"),
        ("float64", "NaN"),
        ("float64", "nan"),
        ("decimal", "Infinity"),
        ("boolean", "maybe"),
        ("int64", "1.5"),
    ],
)
def test_invalid_or_nonfinite_declared_values_never_silently_coerce(
    tmp_path, context, dtype, value
):
    path = tmp_path / "values.csv"
    path.write_text(f"x\n{value}\n")
    with pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(source(path, {"x": dtype}), context)
    assert caught.value.error.path == "sources.raw.columns"


@pytest.mark.parametrize(
    "options",
    [{"encoding": "base64_codec"}, {"delimiter": "\n"}, {"delimiter": "\r"}, {"delimiter": '"'}],
)
def test_unsupported_text_framing_is_rejected_before_read(tmp_path, context, options):
    with pytest.raises(ConfigError):
        PandasCSVReader().read(
            source(tmp_path / "missing.csv", {"x": "string"}, **options), context
        )


@pytest.mark.parametrize("value", ["NaT", ""])
def test_date_parser_cannot_add_undeclared_null_representations(tmp_path, context, value):
    path = tmp_path / "date.csv"
    path.write_text(f'day\n"{value}"\n')
    with pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(
            source(path, {"day": "date"}, date_formats={"day": "%Y-%m-%d"}), context
        )
    assert caught.value.error.path == "sources.raw.columns"


@pytest.mark.parametrize("encoding", ["utf8\0", "\ud800"])
def test_malformed_encoding_errors_are_safe_config_failures(tmp_path, context, encoding):
    with pytest.raises(ConfigError) as caught:
        PandasCSVReader().read(
            source(tmp_path / "missing.csv", {"x": "string"}, encoding=encoding), context
        )
    assert caught.value.path == "sources.raw.options.encoding"


def test_declared_non_utf8_encoding_delimiter_boolean_and_decimal_float(tmp_path, context):
    path = tmp_path / "encoded.csv"
    path.write_bytes("flag\tvalue\ntrue\t1,25\nfalse\tNULL\n".encode("utf-16"))
    dataset = PandasCSVReader().read(
        source(
            path,
            {"flag": "boolean", "value": "float64"},
            encoding="utf-16",
            delimiter="\t",
            decimal=",",
        ),
        context,
    )
    assert dataset.handle["flag"].tolist() == [True, False]
    assert dataset.handle["value"].iloc[0] == 1.25
    assert dataset.handle["value"].isna().tolist() == [False, True]


def test_timestamp_parsing_uses_explicit_format_and_utc_policy(tmp_path, context):
    path = tmp_path / "time.csv"
    path.write_text("when\n2026-01-02T03:04:05+0200\n")
    dataset = PandasCSVReader().read(
        source(path, {"when": "timestamp"}, date_formats={"when": "%Y-%m-%dT%H:%M:%S%z"}, utc=True),
        context,
    )
    assert str(dataset.handle["when"].iloc[0]) == "2026-01-02 01:04:05+00:00"


def test_importing_reader_does_not_import_optional_dataframe_backend():
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; import gmldf.data_io.csv; assert 'pandas' not in sys.modules; assert 'numpy' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("storage", ["python", "pyarrow"])
def test_csv_numeric_nan_rejection_is_independent_of_string_storage(tmp_path, context, storage):
    import pandas as pd

    path = tmp_path / "nan.csv"
    path.write_text("x\nNaN\n")
    with pd.option_context("mode.string_storage", storage), pytest.raises(FrameworkError) as caught:
        PandasCSVReader().read(source(path, {"x": "float64"}), context)
    assert caught.value.error.code == "DATA_INVALID"
