from pathlib import Path

import pytest

from gmldf.core.config import ConfigError, OutputSpec, SourceSpec
from gmldf.core.types import RunContext, RunIdentity
from gmldf.data_io.csv import PandasCSVReader, PandasCSVWriter


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
        allowed_capabilities=["pandas_csv_read", "pandas_csv_write_new"],
    )


def test_provider_validation_checks_specs_without_opening_data_or_output(
    tmp_path, context, monkeypatch
):
    source_path, sink_path = tmp_path / "missing.csv", tmp_path / "out.csv"
    original = Path.open

    def checked(path, *args, **kwargs):
        if path in {source_path, sink_path}:
            raise AssertionError("business data touched during provider validation")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    reader, writer = PandasCSVReader(), PandasCSVWriter()
    assert [capability.id for capability in reader.capabilities] == ["pandas_csv_read"]
    source = SourceSpec(
        id="raw",
        connector="csv",
        location=str(source_path),
        columns={"x": "int64"},
        options={"encoding": "utf-8", "delimiter": ",", "null_values": ["NULL"]},
    )
    sink = OutputSpec(
        id="out",
        dataset="raw",
        connector="csv",
        location=str(sink_path),
        options={"encoding": "utf-8", "delimiter": ",", "null_value": "NULL"},
    )
    assert reader.validate(source, context) is None
    assert writer.validate(sink, context) is None
    assert list(tmp_path.iterdir()) == []


def test_invalid_reader_and_writer_options_reject_without_data_access(tmp_path, context):
    source = SourceSpec(
        id="raw", connector="csv", location=str(tmp_path / "missing.csv"), columns={"x": "int64"}
    )
    sink = OutputSpec(id="out", dataset="raw", connector="csv", location=str(tmp_path / "out.csv"))
    with pytest.raises(ConfigError):
        PandasCSVReader().validate(source, context)
    with pytest.raises(ConfigError):
        PandasCSVWriter().validate(sink, context)
    assert list(tmp_path.iterdir()) == []
