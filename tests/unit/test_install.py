import json
import subprocess
import sys
from importlib.metadata import version


def test_installed_package_has_version_without_importing_backends():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import gmldf, json, sys; "
            "print(json.dumps({'version': gmldf.__version__, "
            "'modules': list(sys.modules)}))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    installed = json.loads(result.stdout)
    assert installed["version"] == version("gmldf")
    roots = {name.split(".")[0] for name in installed["modules"]}
    assert roots.isdisjoint(
        {"pandas", "polars", "duckdb", "pyspark", "sklearn", "xgboost", "mlflow", "boto3"}
    )
