# Development

Initial tested interpreter: CPython 3.11.18 on macOS arm64. Use an isolated virtual environment; the system Python may be too old.

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[dev,pandas,parquet,arima]'
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m ruff format --check src tests
.venv/bin/python -m build
```

An equivalent Python 3.11+ virtual environment and pip installation also work; uv is a development convenience, not a runtime dependency.

The base currently depends on Pydantic and PyYAML only. `dev` adds pytest, Ruff, build tooling and the pinned Hatchling backend for offline no-isolation builds. The `pandas` extra pins the tested local CSV backend profile. The `parquet` extra adds pinned PyArrow26.0.1; local Parquet providers are verified for this pinned profile. The `arima` extra pins the tested statsmodels0.15.0 profile and its runtime dependencies. Other engine/connector/ML extras will be introduced with real implementations; unimplemented extras are not advertised.

For base-only core checks, install `.[dev]` and run `.venv/bin/python -m pytest tests/unit/core tests/contract/core tests/unit/test_install.py -q`. The full current suite additionally requires `.[pandas,parquet,arima]` for native data paths and actual forecasting candidate fits; unavailable optional profiles are not treated as skipped passes.

For the initial package check, run `.venv/bin/python -m pytest tests/unit/test_install.py -q`. It imports the installed package in an isolated subprocess and checks metadata and optional-backend isolation.

Build artifacts stay under ignored `dist/`; nothing is published automatically. Public package-name availability, other Python versions, Linux images, and cloud/platform integrations require separate verification.

The data-recipe e2e test builds the current wheel and installs it with standard pip into a fresh environment without system site packages. Prepare an offline wheelhouse once for your Python/OS architecture (from an environment that has pip):

```sh
.venv/bin/python -m build --no-isolation
python -m pip download --only-binary=:all: --dest build/wheelhouse 'dist/gmldf-0.1.0a1-py3-none-any.whl[dev,pandas]'
.venv/bin/python -m pytest tests/e2e/test_data_only.py -q
```

Use `GMLDF_WHEELHOUSE=/absolute/path` for another prepared wheel directory. Missing dependency wheels fail the test with an installation error; they are never skipped or fetched by the test. Downloaded wheels stay under ignored `build/`. The test always rebuilds the package under test, so a previously downloaded package wheel cannot hide source changes. `venv`/`ensurepip` must be available in the selected Python installation.
