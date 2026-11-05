import subprocess
import sys
from pathlib import Path

import pytest

from gmldf.core.config import ConfigError, validate_config
from gmldf.core.errors import FrameworkError
from gmldf.core.policy import Policy
from gmldf.core.types import RunContext, RunIdentity
from gmldf.data_io.csv import PandasCSVReader, PandasCSVWriter
from gmldf.processing.pandas import PandasEngine
from gmldf.workflow.providers import ProviderSet
from gmldf.workflow.runner import run


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
            "pandas_csv_read",
            "pandas_select",
            "pandas_sort",
            "pandas_csv_write_new",
        ],
    )


def providers(**kwargs):
    return ProviderSet(
        readers={"csv": PandasCSVReader()},
        writers={"csv": PandasCSVWriter()},
        processing=PandasEngine(),
        **kwargs,
    )


def config(tmp_path):
    return validate_config(
        {
            "schema_version": 1,
            "name": "data",
            "kind": "data",
            "engine": "pandas",
            "execution": {"profile": "local"},
            "sources": [
                {
                    "id": "raw",
                    "connector": "csv",
                    "location": str(tmp_path / "in.csv"),
                    "columns": {"x": "int64", "unused": "string"},
                    "options": {"encoding": "utf-8", "delimiter": ",", "null_values": ["NULL"]},
                }
            ],
            "steps": [
                {
                    "id": "ordered",
                    "operation": "sort",
                    "inputs": ["selected"],
                    "params": {"by": ["x"]},
                },
                {
                    "id": "selected",
                    "operation": "select",
                    "inputs": ["raw"],
                    "params": {"columns": ["x"]},
                },
            ],
            "outputs": [
                {
                    "id": "out",
                    "dataset": "ordered",
                    "connector": "csv",
                    "location": str(tmp_path / "out.csv"),
                    "options": {"encoding": "utf-8", "delimiter": ",", "null_value": "NULL"},
                }
            ],
        }
    )


def test_real_csv_graph_runs_in_dependency_order_with_truthful_result(tmp_path, context):
    (tmp_path / "in.csv").write_text("x,unused\n2,a\n1,b\n")
    result = run(config(tmp_path), context, providers())
    assert result.status == "succeeded"
    assert result.identity == context.identity
    assert result.errors == []
    assert [s.stage_id for s in result.stages] == ["source_0", "step_1", "step_0", "output_0"]
    assert all(s.status == "succeeded" for s in result.stages)
    assert result.writes[0].commit_status == "committed"
    assert result.writes[0].row_count == 2
    assert (tmp_path / "out.csv").read_text() == "x\n1\n2\n"
    assert '"status":"succeeded"' in result.model_dump_json()


@pytest.mark.parametrize("invalid", ["sink", "step", "capability", "policy", "mapping"])
def test_full_preflight_rejects_before_source_access(tmp_path, context, invalid):
    workflow = config(tmp_path)
    supplied = providers(policy=Policy(sources=[])) if invalid == "policy" else providers()
    if invalid == "sink":
        workflow.outputs[0].options.clear()
    elif invalid == "step":
        workflow.steps[0].params["ascending"] = []
    elif invalid == "capability":
        context = context.model_copy(update={"allowed_capabilities": []})
    elif invalid == "mapping":
        supplied = ProviderSet(
            readers={}, writers={"csv": PandasCSVWriter()}, processing=PandasEngine()
        )
    with pytest.raises((ConfigError, FrameworkError)):
        run(workflow, context, supplied)
    assert not (tmp_path / "out.csv").exists()


def test_failed_source_skips_consumers_but_independent_source_and_sink_complete(tmp_path, context):
    workflow = config(tmp_path).model_dump()
    independent = dict(
        workflow["sources"][0], id="independent", location=str(tmp_path / "good.csv")
    )
    workflow["sources"].append(independent)
    workflow["outputs"].append(
        dict(
            workflow["outputs"][0],
            id="good",
            dataset="independent",
            location=str(tmp_path / "good-out.csv"),
        )
    )
    (tmp_path / "good.csv").write_text("x,unused\n3,a\n")
    result = run(validate_config(workflow), context, providers())
    assert result.status == "failed"
    assert [s.status for s in result.stages] == [
        "failed",
        "succeeded",
        "skipped",
        "skipped",
        "skipped",
        "succeeded",
    ]
    assert len(result.errors) == 1
    assert result.errors[0].stage_id == "source_0"
    assert [r.output_id for r in result.writes] == ["good"]
    assert (tmp_path / "good-out.csv").read_text() == "x,unused\n3,a\n"
    assert not (tmp_path / "out.csv").exists()


def test_failed_required_sink_preserves_prior_commit_without_retry(tmp_path, context):
    workflow = config(tmp_path).model_dump()
    workflow["outputs"].append(
        dict(workflow["outputs"][0], id="collision", location=str(tmp_path / "exists.csv"))
    )
    (tmp_path / "in.csv").write_text("x,unused\n2,a\n1,b\n")
    (tmp_path / "exists.csv").write_text("old")
    result = run(validate_config(workflow), context, providers())
    assert result.status == "failed"
    assert [r.commit_status for r in result.writes] == ["committed", "not_committed"]
    assert [r.output_id for r in result.writes] == ["out", "collision"]
    assert result.errors[0].code == "OUTPUT_INCOMPLETE"
    assert (tmp_path / "exists.csv").read_text() == "old"
    assert (tmp_path / "out.csv").read_text() == "x\n1\n2\n"


def test_provider_mappings_are_snapshots():
    readers = {"csv": PandasCSVReader()}
    supplied = ProviderSet(readers=readers, writers={}, processing=PandasEngine())
    readers.clear()
    assert "csv" in supplied.readers
    with pytest.raises(TypeError):
        supplied.readers["csv"] = object()


def test_workflow_import_does_not_import_backends_or_execution():
    code = """
import sys
from gmldf.workflow.runner import run
assert not any(m.split('.')[0] in {'pandas','numpy','sklearn','xgboost','statsmodels','prophet','mlflow','pyspark'} for m in sys.modules)
assert not any(m.startswith('gmldf.execution') for m in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_failed_step_skips_its_consumers_but_direct_source_output_commits(tmp_path, context):
    workflow = config(tmp_path).model_dump()
    workflow["steps"][1]["params"]["columns"] = ["absent"]
    workflow["outputs"].append(
        dict(
            workflow["outputs"][0], id="raw_out", dataset="raw", location=str(tmp_path / "raw.csv")
        )
    )
    (tmp_path / "in.csv").write_text("x,unused\n1,a\n")
    result = run(validate_config(workflow), context, providers())
    assert result.status == "failed"
    assert [s.status for s in result.stages] == [
        "succeeded",
        "failed",
        "skipped",
        "skipped",
        "succeeded",
    ]
    assert result.errors[0].code == "DATA_INVALID"
    assert result.writes[0].output_id == "raw_out"


@pytest.mark.parametrize("bad", ["engine", "id", "type"])
def test_invalid_provider_dataset_cannot_silently_change_engine_or_lineage(tmp_path, context, bad):
    class Reader(PandasCSVReader):
        def read(self, source, context):
            result = super().read(source, context)
            if bad == "type":
                return object()
            return result.model_copy(
                update={"engine": "spark"} if bad == "engine" else {"id": "different"}
            )

    supplied = ProviderSet(
        readers={"csv": Reader()}, writers={"csv": PandasCSVWriter()}, processing=PandasEngine()
    )
    (tmp_path / "in.csv").write_text("x,unused\n1,a\n")
    result = run(config(tmp_path), context, supplied)
    assert result.status == "failed"
    assert result.errors[0].code == "DATA_INVALID"
    assert result.writes == []
    assert not (tmp_path / "out.csv").exists()


@pytest.mark.parametrize("status", ["not_committed", "unknown", "committed_failure"])
def test_incomplete_receipts_and_postcommit_failures_are_preserved(tmp_path, context, status):
    from gmldf.core.types import WriteReceipt
    from gmldf.data_io.base import WriteFailure

    class Writer(PandasCSVWriter):
        def write(self, dataset, sink, context):
            receipt = WriteReceipt(
                output_id=sink.id,
                destination=Path(sink.location).as_uri(),
                mode=sink.mode,
                commit_status="committed" if status == "committed_failure" else status,
            )
            if status == "committed_failure":
                raise WriteFailure(receipt)
            return receipt

    supplied = ProviderSet(
        readers={"csv": PandasCSVReader()}, writers={"csv": Writer()}, processing=PandasEngine()
    )
    (tmp_path / "in.csv").write_text("x,unused\n1,a\n")
    result = run(config(tmp_path), context, supplied)
    assert result.status == "failed"
    assert result.errors[0].code == "OUTPUT_INCOMPLETE"
    assert len(result.writes) == 1
    assert result.writes[0].commit_status == (
        "committed" if status == "committed_failure" else status
    )


def test_duplicate_provider_declarations_reject_before_source_access(tmp_path, context):
    class Reader(PandasCSVReader):
        capabilities = PandasCSVReader.capabilities * 2

    supplied = ProviderSet(
        readers={"csv": Reader()}, writers={"csv": PandasCSVWriter()}, processing=PandasEngine()
    )
    with pytest.raises(FrameworkError) as caught:
        run(config(tmp_path), context, supplied)
    assert caught.value.error.code == "CONFIG_INVALID"
    assert caught.value.error.path == "providers"


@pytest.mark.parametrize("field,value", [("output_id", "foreign"), ("mode", "overwrite")])
def test_failed_provider_cannot_attach_foreign_receipts(tmp_path, context, field, value):
    from gmldf.core.types import WriteReceipt
    from gmldf.data_io.base import WriteFailure

    class Writer(PandasCSVWriter):
        def write(self, dataset, sink, context):
            receipt = WriteReceipt(
                output_id=sink.id,
                destination=Path(sink.location).as_uri(),
                mode=sink.mode,
                commit_status="committed",
            )
            raise WriteFailure(receipt.model_copy(update={field: value}))

    supplied = ProviderSet(
        readers={"csv": PandasCSVReader()}, writers={"csv": Writer()}, processing=PandasEngine()
    )
    (tmp_path / "in.csv").write_text("x,unused\n1,a\n")
    result = run(config(tmp_path), context, supplied)
    assert result.status == "failed"
    assert result.errors[0].code == "OUTPUT_INCOMPLETE"
    assert result.writes == []
