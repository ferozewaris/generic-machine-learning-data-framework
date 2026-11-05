import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def installed_python(tmp_path_factory):
    work = tmp_path_factory.mktemp("wheel-install")
    built = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(work / "dist"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    venv.EnvBuilder(with_pip=True).create(work / "venv")
    python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    wheelhouse = Path(os.environ.get("GMLDF_WHEELHOUSE", REPO / "build/wheelhouse"))
    assert wheelhouse.is_dir(), (
        "Prepare build/wheelhouse using the offline test setup in docs/development.md"
    )
    wheel = next((work / "dist").glob("*.whl"))
    install = subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            f"{wheel}[pandas]",
        ],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stderr
    check = subprocess.run(
        [str(python), "-I", "-c", "import gmldf; print(gmldf.__file__)"],
        cwd=work,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr
    assert str(work / "venv") in check.stdout
    assert str(REPO / "src") not in check.stdout
    return python


def example(tmp_path):
    target = tmp_path / "recipe"
    shutil.copytree(REPO / "examples/data-only", target, ignore=shutil.ignore_patterns("runs"))
    return target / "workflow.yaml"


def invoke(python, path):
    return subprocess.run(
        [
            str(python),
            "-I",
            "-m",
            "gmldf",
            "run",
            "--config",
            str(path),
            "--profile",
            "local",
            "--run-id",
            "data_demo",
            "--output-dir",
            "runs",
        ],
        cwd=path.parent.parent,
        capture_output=True,
        text=True,
    )


def test_fresh_wheel_install_runs_the_documented_data_recipe(installed_python, tmp_path):
    path = example(tmp_path)
    response = invoke(installed_python, path)
    assert response.returncode == 0, response.stderr
    result = json.loads(response.stdout)
    assert result["status"] == "succeeded"
    assert result["writes"][0]["row_count"] == 3
    assert (
        path.parent / "runs/result.csv"
    ).read_text() == "record_id,amount\na,1.25\nb,2.5\nc,NULL\n"
    assert json.loads((path.parent / "runs/data_demo/result.json").read_text()) == result


def test_changing_paths_requires_only_config_changes(installed_python, tmp_path):
    path = example(tmp_path)
    config = yaml.safe_load(path.read_text())
    (path.parent / "input.csv").rename(path.parent / "different.csv")
    config["sources"][0]["location"] = "different.csv"
    config["outputs"][0]["location"] = "runs/different-result.csv"
    path.write_text(yaml.safe_dump(config))
    response = invoke(installed_python, path)
    assert response.returncode == 0, response.stderr
    assert (
        path.parent / "runs/different-result.csv"
    ).read_text() == "record_id,amount\na,1.25\nb,2.5\nc,NULL\n"
    assert not (path.parent / "runs/result.csv").exists()


def test_invalid_recipe_has_no_business_outputs(installed_python, tmp_path):
    path = example(tmp_path)
    config = yaml.safe_load(path.read_text())
    config["steps"][0]["params"]["columns"] = []
    path.write_text(yaml.safe_dump(config))
    response = invoke(installed_python, path)
    assert response.returncode == 2
    assert response.stdout == ""
    assert not (path.parent / "runs").exists()


def test_documented_dev_extra_supports_offline_wheel_build(installed_python, tmp_path):
    wheelhouse = Path(os.environ.get("GMLDF_WHEELHOUSE", REPO / "build/wheelhouse"))
    install = subprocess.run(
        [
            str(installed_python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "gmldf[dev,pandas]",
        ],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stderr
    built = subprocess.run(
        [
            str(installed_python),
            "-I",
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path / "dist"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr


def test_missing_parquet_extra_rejects_before_source_or_output_access(installed_python, tmp_path):
    path = example(tmp_path)
    config = yaml.safe_load(path.read_text())
    config["sources"][0].update(connector="parquet", location="missing.parquet", options={})
    path.write_text(yaml.safe_dump(config))
    response = invoke(installed_python, path)
    assert response.returncode == 2
    error = json.loads(response.stderr.splitlines()[-1])["error"]
    assert error["code"] == "CAPABILITY_UNSUPPORTED"
    assert error["dependency"] == {
        "package": "pyarrow",
        "expected_version": "26.0.1",
        "install_extra": "parquet",
        "reason": "missing",
    }
    assert not (path.parent / "runs").exists()
