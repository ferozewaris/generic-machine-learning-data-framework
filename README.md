# Generic Machine Learning and Data Framework

A planned pip-installable, configuration-driven Python library for data processing and AutoML. Users invoke it through Python or CLI in their own supported environment.

- Config-selected Spark, pandas, Polars, or DuckDB processing.
- Classification, regression, forecasting, and clustering.
- Only user-listed algorithms and an explicit selection metric; default overridable search ranges and bounded tuning.
- All requested ingestion connectors and file/table/database/Delta outputs, through optional compatible providers.
- Explicit size-limited cross-engine transfers and optional full-data refit with preserved evaluation evidence.
- Lightweight base installation plus optional backend dependencies. No infrastructure provisioning or remote-job management.

Implementation has started. Available now: an installable base package, offline configuration validation, shared metadata/preflight contracts, and an optional schema-checked [local CSV reader](docs/data-io.md). Data processing, AutoML, other connectors, and workflow execution remain in the backlog. No package has been published to PyPI.

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m gmldf validate --config examples/validation/workflow.yaml
```

You can also install with pip inside an existing Python 3.11+ environment: `python -m pip install -e .`. uv is a development convenience only.

The validation command does not read configured data, resolve secrets, train models, or certify backend compatibility. See [configuration](docs/configuration.md), [development commands](docs/development.md), and [actual compatibility evidence](docs/compatibility.md).

Start with the [confirmed intent](docs/intent/generic-data-ml-library.md), [capability map](CAPABILITY-MAP.md), [implementation plan](tasks/plan.md), and [task backlog](tasks/todo.md).
The capability map links the eight module specs. All requested capabilities belong to the first release; implementation examples are not smaller releases.
