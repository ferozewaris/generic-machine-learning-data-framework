# Development

Initial tested interpreter: CPython 3.11.18 on macOS arm64. Use an isolated virtual environment; the system Python may be too old.

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[dev,pandas]'
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m ruff format --check src tests
.venv/bin/python -m build
```

An equivalent Python 3.11+ virtual environment and pip installation also work; uv is a development convenience, not a runtime dependency.

The base currently depends on Pydantic and PyYAML only. `dev` adds pytest, Ruff, and build tooling. The `pandas` extra pins the tested local CSV backend profile. Other engine/connector/ML extras will be introduced with real implementations; unimplemented extras are not advertised.

For base-only core checks, install `.[dev]` and run `.venv/bin/python -m pytest tests/unit/core tests/contract/core tests/unit/test_install.py -q`. The full current suite additionally requires `.[pandas]`; unavailable optional profiles are not treated as skipped passes.

For the initial package check, run `.venv/bin/python -m pytest tests/unit/test_install.py -q`. It imports the installed package in an isolated subprocess and checks metadata and optional-backend isolation.

Build artifacts stay under ignored `dist/`; nothing is published automatically. Public package-name availability, other Python versions, Linux images, and cloud/platform integrations require separate verification.
