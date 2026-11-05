import json
import subprocess
import sys

import pytest
import yaml


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "workflow.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "offline-example",
                "kind": "data",
                "engine": "duckdb",
                "execution": {"profile": "local"},
                "sources": [{"id": "raw", "connector": "csv", "location": "does-not-exist.csv"}],
                "steps": [],
                "outputs": [
                    {
                        "id": "result",
                        "dataset": "raw",
                        "connector": "csv",
                        "location": "must-not-be-created.csv",
                    }
                ],
            }
        )
    )
    return path


def invoke(config_path, *arguments):
    return subprocess.run(
        [sys.executable, "-m", "gmldf", "validate", "--config", str(config_path), *arguments],
        capture_output=True,
        text=True,
        cwd=config_path.parent,
    )


def test_cli_validates_offline_and_creates_no_business_output(config_path):
    before = set(config_path.parent.iterdir())
    result = invoke(config_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report == {
        "valid": True,
        "scope": "configuration",
        "name": "offline-example",
        "kind": "data",
        "engine": "duckdb",
        "profile": "local",
        "capabilities_checked": False,
    }
    assert result.stderr == ""
    assert set(config_path.parent.iterdir()) == before


def test_explicit_report_is_the_only_written_file(config_path):
    report_path = config_path.parent / "report.json"
    result = invoke(config_path, "--profile", "user-host", "--output", str(report_path))
    assert result.returncode == 0, result.stderr
    assert json.loads(report_path.read_text()) == json.loads(result.stdout)
    assert json.loads(result.stdout)["profile"] == "user-host"
    assert set(config_path.parent.iterdir()) == {config_path, report_path}


@pytest.mark.parametrize("target", ["report.json", "workflow.yaml"])
def test_reports_never_overwrite_existing_files(config_path, target):
    path = config_path.parent / target
    if path != config_path:
        path.write_text("original contents")
    original = path.read_bytes()
    result = invoke(config_path, "--output", str(path))
    assert result.returncode == 1
    assert result.stdout == ""
    assert path.read_bytes() == original
    assert json.loads(result.stderr)["error"]["code"] == "OUTPUT_INCOMPLETE"


def test_config_failure_is_structured_and_does_not_echo_values(config_path):
    config_path.write_text(config_path.read_text() + "password: SENTINEL_SECRET\n")
    result = invoke(config_path)
    assert result.returncode == 2
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert error["code"] == "CONFIG_INVALID"
    assert error["path"] == "password"
    assert "SENTINEL_SECRET" not in result.stderr
    assert "Traceback" not in result.stderr


def test_duplicate_yaml_keys_do_not_echo_secret_values(config_path):
    config_path.write_text("name: SENTINEL_SECRET\nname: other\n")
    result = invoke(config_path)
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"]["reason"] == "duplicate_key"
    assert "SENTINEL_SECRET" not in result.stderr


def test_invalid_profile_uses_the_same_structured_error(config_path):
    result = invoke(config_path, "--profile", "bad profile")
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"]["path"] == "execution.profile"


def test_cli_has_no_remote_job_commands(config_path):
    for command in ("submit", "status", "cancel"):
        result = subprocess.run(
            [sys.executable, "-m", "gmldf", command], capture_output=True, text=True
        )
        assert result.returncode == 2
        assert "invalid choice" in result.stderr


def test_missing_config_is_a_safe_error(config_path):
    config_path.unlink()
    result = invoke(config_path)
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"]["reason"] == "cannot_read_file"


def test_profile_override_does_not_inflate_a_valid_near_limit_config(config_path):
    from gmldf.core.config import MAX_CONFIG_BYTES

    config = yaml.safe_load(config_path.read_text())
    config["sources"][0]["options"] = {"padding": ""}
    overhead = len(json.dumps(config).encode("utf-8"))
    config["sources"][0]["options"]["padding"] = "x" * (MAX_CONFIG_BYTES - overhead - 1)
    config_path.write_text(json.dumps(config))
    result = invoke(config_path, "--profile", "local")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["profile"] == "local"
