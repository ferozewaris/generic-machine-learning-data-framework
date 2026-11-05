import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gmldf.execution.local import run_local


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "configs" / "workflow.yaml"
    path.parent.mkdir()
    (path.parent / "input.csv").write_text("x\n2\n1\n")
    path.write_text(
        yaml.safe_dump(
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
                        "location": "input.csv",
                        "columns": {"x": "int64"},
                        "options": {"encoding": "utf-8", "delimiter": ",", "null_values": ["NULL"]},
                    }
                ],
                "steps": [
                    {
                        "id": "ordered",
                        "operation": "sort",
                        "inputs": ["raw"],
                        "params": {"by": ["x"]},
                    }
                ],
                "outputs": [
                    {
                        "id": "out",
                        "dataset": "ordered",
                        "connector": "csv",
                        "location": "output.csv",
                        "options": {"encoding": "utf-8", "delimiter": ",", "null_value": "NULL"},
                    }
                ],
            }
        )
    )
    return path


def invoke(path, *args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "gmldf",
            "run",
            "--config",
            str(path),
            "--run-id",
            "demo",
            "--output-dir",
            "runs",
            *args,
        ],
        cwd=path.parent.parent,
        capture_output=True,
        text=True,
    )


def test_cli_resolves_paths_and_emits_exact_persisted_library_result(config_path):
    response = invoke(config_path, "--profile", "local")
    assert response.returncode == 0, response.stderr
    report = json.loads(response.stdout)
    folder = config_path.parent / "runs" / "demo"
    assert json.loads((folder / "result.json").read_text()) == report
    assert json.loads((folder / "identity.json").read_text()) == report["identity"]
    assert report["status"] == "succeeded"
    assert report["identity"]["config_digest"].startswith("sha256:")
    assert "python" in report["identity"]["environment"]
    assert report["writes"][0]["destination"] == (config_path.parent / "output.csv").as_uri()
    assert (config_path.parent / "output.csv").read_text() == "x\n1\n2\n"
    assert not (config_path.parent.parent / "output.csv").exists()
    progress = [json.loads(line) for line in response.stderr.splitlines()]
    assert [item["event"] for item in progress] == ["started", "succeeded"]


def test_python_local_helper_returns_the_workflow_result(config_path):
    result = run_local(config_path, profile="local", run_id="python", output_dir=Path("runs"))
    assert result.status == "succeeded"
    assert json.loads(
        (config_path.parent / "runs/python/result.json").read_text()
    ) == result.model_dump(mode="json")
    assert result.identity.run_id == "python"


@pytest.mark.parametrize("changed", [False, True])
def test_completed_run_reuse_rejects_before_mutating_any_output(config_path, changed):
    assert invoke(config_path).returncode == 0
    if changed:
        config = yaml.safe_load(config_path.read_text())
        config["outputs"][0]["mode"] = "overwrite"
        config_path.write_text(yaml.safe_dump(config))
    before = {p: p.read_bytes() for p in config_path.parent.rglob("*") if p.is_file()}
    response = invoke(config_path)
    assert response.returncode == 2
    assert json.loads(response.stderr.splitlines()[-1])["error"]["code"] == "CONFIG_INVALID"
    assert response.stdout == ""
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("change", ["engine", "profile", "options", "run_id"])
def test_rejection_has_no_business_or_run_output(config_path, change):
    config = yaml.safe_load(config_path.read_text())
    args = []
    if change == "engine":
        config["engine"] = "duckdb"
    elif change == "profile":
        args = ["--profile", "snowflake"]
    elif change == "run_id":
        args = ["--run-id", "../escape"]
    else:
        config["outputs"][0]["options"] = {}
    config_path.write_text(yaml.safe_dump(config))
    response = invoke(config_path, *args)
    assert response.returncode == 2
    assert response.stdout == ""
    assert json.loads(response.stderr.splitlines()[-1])["error"]["code"] in {
        "CONFIG_INVALID",
        "CAPABILITY_UNSUPPORTED",
    }
    assert not (config_path.parent / "output.csv").exists()
    assert not (config_path.parent / "runs").exists()
    assert "Traceback" not in response.stderr


def test_execution_failure_is_persisted_and_uses_exit_one(config_path):
    (config_path.parent / "input.csv").unlink()
    response = invoke(config_path)
    assert response.returncode == 1
    result = json.loads(response.stdout)
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "DATA_INVALID"
    assert json.loads((config_path.parent / "runs/demo/result.json").read_text()) == result
    assert "Traceback" not in response.stderr


def test_generated_attempt_id_accepts_numeric_uuid_prefix(config_path, monkeypatch):
    from types import SimpleNamespace

    from gmldf.execution import local

    monkeypatch.setattr(local, "uuid4", lambda: SimpleNamespace(hex="0" * 32))
    result = run_local(config_path, run_id="demo", output_dir=Path("runs"))
    assert result.identity.attempt_id == "attempt_" + "0" * 32


@pytest.mark.parametrize("name", ["identity.json", "result.json"])
def test_business_output_cannot_overwrite_reserved_run_metadata(config_path, name):
    config = yaml.safe_load(config_path.read_text())
    config["outputs"][0].update(location=f"runs/demo/{name}", mode="overwrite")
    config_path.write_text(yaml.safe_dump(config))
    response = invoke(config_path)
    assert response.returncode == 2
    assert json.loads(response.stderr.splitlines()[-1])["error"]["code"] == "CONFIG_INVALID"
    assert not (config_path.parent / "runs").exists()


def test_local_identity_records_the_selected_provider_versions(config_path):
    from importlib.metadata import version

    result = run_local(config_path, run_id="demo", output_dir=Path("runs"))
    assert result.identity.environment["pandas"] == version("pandas")
    assert result.identity.environment["numpy"] == version("numpy")


def test_cli_exit_mapping_reserves_130_for_confirmed_cancelled_results():
    from datetime import datetime, timezone

    from gmldf.core.types import RunIdentity, RunResult
    from gmldf.execution.local import exit_code

    now = datetime.now(timezone.utc)
    result = RunResult(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        status="cancelled",
        reason="cancelled",
        started_at=now,
        finished_at=now,
    )
    assert exit_code(result) == 130


def test_malformed_location_is_a_config_rejection_before_metadata(config_path):
    config = yaml.safe_load(config_path.read_text())
    config["sources"][0]["location"] = "https://[bad"
    config_path.write_text(yaml.safe_dump(config))
    response = invoke(config_path)
    assert response.returncode == 2
    error = json.loads(response.stderr.splitlines()[-1])["error"]
    assert error["code"] == "CONFIG_INVALID"
    assert error["path"] == "sources.0.location"
    assert not (config_path.parent / "runs").exists()


def test_relative_file_uris_resolve_against_config_directory(config_path):
    config = yaml.safe_load(config_path.read_text())
    config["sources"][0]["location"] = "file:input.csv"
    config["outputs"][0]["location"] = "file:output.csv"
    config_path.write_text(yaml.safe_dump(config))
    response = invoke(config_path)
    assert response.returncode == 0, response.stderr
    assert (config_path.parent / "output.csv").read_text() == "x\n1\n2\n"
    assert not (config_path.parent.parent / "output.csv").exists()
