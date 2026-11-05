# Compatibility evidence

## Current status

This table distinguishes profiles to test from verified behavior. Only an executed check can change a row to verified.

| Capability/profile | Status | Evidence |
|---|---|---|
| CPython 3.11.18 / macOS arm64 / base install and offline config validation | Verified | T003–T004: editable install, clean standard-pip wheel install, 86 passing tests, Ruff, sdist/wheel build |
| CSV/Parquet and data-only workflows | Planned | T007–T013 |
| Spark/pandas/Polars/DuckDB processing | Planned | T008, T034–T045 |
| All four tasks and requested ML integrations | Planned | T014–T024, T046–T056 |
| Cloud/database/catalog connectors and Delta outputs | Planned | T059–T072 |
| MLflow lifecycle | Planned | T057–T058 |
| User-launched container/Kubernetes invocation | Planned | T028, T032 |
| Existing Databricks/Snowflake/AWS hosts | Planned | T073–T077 |

Unknown combinations are unsupported. The package must fail explicitly rather than infer another engine, add algorithms, or collect data without explicit bounds.

See [host-profile requirements](decisions/host-compatibility.md) and the [complete task inventory](../tasks/todo.md). First-release scope still requires every named capability in at least one actually verified supported combination.

Tested core dependency versions: Pydantic 2.14.3, pydantic-core 2.50.4, PyYAML 6.0.3. This evidence does not verify any processing engine, connector, model, external host, or public PyPI installation.
