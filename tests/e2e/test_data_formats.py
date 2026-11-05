from pathlib import Path

import pandas as pd
import pytest
import yaml

from gmldf.core.config import OutputSpec, SourceSpec
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext, RunIdentity
from gmldf.data_io.parquet import PandasParquetReader, PandasParquetWriter
from gmldf.execution.local import run_local


@pytest.fixture
def context():
    return RunContext(
        identity=RunIdentity(
            run_id="setup",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        allowed_capabilities=["pandas_parquet_read", "pandas_parquet_write_new"],
    )


@pytest.mark.parametrize("input_format", ["csv", "parquet"])
@pytest.mark.parametrize("output_format", ["csv", "parquet"])
def test_config_only_format_changes_produce_equivalent_values_and_schema(
    tmp_path, context, input_format, output_format
):
    config = yaml.safe_load(
        (Path(__file__).parents[2] / "examples/data-only/workflow.yaml").read_text()
    )
    (tmp_path / "input.csv").write_text(
        "record_id,amount,category\nb,2.5,beta\na,1.25,alpha\nc,NULL,beta\n"
    )
    if input_format == "parquet":
        frame = pd.DataFrame(
            {
                "record_id": ["b", "a", "c"],
                "amount": ["2.5", "1.25", None],
                "category": ["beta", "alpha", "beta"],
            }
        )
        ref = DatasetRef(
            id="raw",
            engine="pandas",
            materialization="memory",
            columns=[ColumnSpec(name=name, dtype="string") for name in frame.columns],
        ).with_handle(frame)
        PandasParquetWriter().write(
            ref,
            OutputSpec(
                id="input",
                dataset="raw",
                connector="parquet",
                location=str(tmp_path / "input.parquet"),
            ),
            context,
        )
        config["sources"][0].update(connector="parquet", location="input.parquet", options={})
    if output_format == "parquet":
        config["outputs"][0].update(connector="parquet", location="runs/result.parquet", options={})
    path = tmp_path / "workflow.yaml"
    path.write_text(yaml.safe_dump(config))
    result = run_local(path, run_id="formats", output_dir=Path("runs"))
    assert result.status == "succeeded"
    assert result.writes[0].commit_status == "committed"
    assert result.writes[0].row_count == 3
    if output_format == "parquet":
        output = PandasParquetReader().read(
            SourceSpec(
                id="result",
                connector="parquet",
                location=str(tmp_path / "runs/result.parquet"),
                columns={"record_id": "string", "amount": "float64"},
            ),
            context,
        )
        assert [(c.name, c.dtype) for c in output.columns] == [
            ("record_id", "string"),
            ("amount", "float64"),
        ]
        assert output.handle["record_id"].tolist() == ["a", "b", "c"]
        assert output.handle["amount"].dropna().tolist() == [1.25, 2.5]
        assert output.handle["amount"].isna().tolist() == [False, False, True]
        assert result.identity.environment["pyarrow"] == "26.0.1"
    else:
        assert (
            tmp_path / "runs/result.csv"
        ).read_text() == "record_id,amount\na,1.25\nb,2.5\nc,NULL\n"
