# Generic Machine Learning and Data Framework

A planned pip-installable, configuration-driven Python library for data processing and AutoML. Users invoke it through Python or CLI in their own supported environment.

- Config-selected Spark, pandas, Polars, or DuckDB processing.
- Classification, regression, forecasting, and clustering.
- Only user-listed algorithms and an explicit selection metric; default overridable search ranges and bounded tuning.
- All requested ingestion connectors and file/table/database/Delta outputs, through optional compatible providers.
- Explicit size-limited cross-engine transfers and optional full-data refit with preserved evaluation evidence.
- Lightweight base installation plus optional backend dependencies. No infrastructure provisioning or remote-job management.

This repository currently contains design documents only. There is no published package or implemented compatibility claim.

Start with the [confirmed intent](docs/intent/generic-data-ml-library.md), [capability map](CAPABILITY-MAP.md), [implementation plan](tasks/plan.md), and [task backlog](tasks/todo.md).
The capability map links the eight module specs. All requested capabilities belong to the first release; implementation examples are not smaller releases.
