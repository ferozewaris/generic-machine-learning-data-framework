# Generic Data and AutoML Library

Status: refined to the [confirmed intent](../intent/generic-data-ml-library.md) on 2026-11-05.

## Problem Statement

How might enterprise teams and external developers define reusable data and ML workflows through configuration, install the library with pip, and run compatible backends in their own environments?

## Recommended Direction

A generic Python library with Python and CLI entry points, a lightweight base, and optional dependencies.
Users choose the processing engine, ML task, candidate algorithms, selection metric, limits, and outputs.
AutoML tunes only listed algorithms using overridable versioned search ranges; cross-engine training requires explicit bounded transfer.
Return the evaluated winning pipeline by default and optionally a distinct full-data-refitted model while preserving evaluation evidence.

First-release scope includes all requested connectors, Spark/pandas/Polars/DuckDB, classification/regression/forecasting/clustering, requested model integrations, result formats, and optional MLflow integration.
Examples demonstrate these generic capabilities; no single use case defines the release.

## Key Assumptions to Validate

- [ ] Pip-installed optional environments are compatible and independently testable.
- [ ] Users adapt workflows through config without source edits.
- [ ] Each advertised combination passes real integration checks.
- [ ] Selected algorithms/metrics, safe transfers, and evaluated/refitted identity remain explicit across hosts.

## First-Release Capability Inventory

- Ingestion: CSV, Parquet, S3, SQL Server, Oracle, Databricks, Snowflake, ADLS, Google Cloud Storage.
- Processing: Spark, pandas, Polars, DuckDB selected by config.
- Tasks: classification, regression, forecasting, clustering, each with supported model comparison/tuning.
- Model integrations: scikit-learn, XGBoost, PySpark ML, ARIMA, Prophet.
- Results/lifecycle: CSV/Parquet, tables/databases/Delta, evaluated/refitted artifacts, optional MLflow.
- Hosts: user-owned local processes, containers/Kubernetes, AWS, Databricks, and compatible Snowflake Python/container facilities; support is combination-specific.
- Enterprise integration: declared credential references, safe writes, policy hooks, and redacted run records.

## Reference Framework: Selective Inspiration

Reference reviewed: `/Users/feroze/Documents/bizinsights-databricks-generic-framework`. Use it as an example of configuration-driven workflows, not as a codebase to copy or a mandatory architecture. The observations below come from selected source files and configurations, not a runtime audit.

| Observed pattern | Source in the reference | Lesson for this framework |
|---|---|---|
| Named datasets and ordered processing actions | `generic_framework/pipeline/data_processing.py`, `application_config/silver/payment.yaml` | Let configuration describe dataset inputs, transformation steps, joins, and outputs explicitly. |
| Separate feature engineering, training, and inference configurations | `application_config/ml/feature_engineering.yaml`, `training.yaml`, `inference.yaml` | Support independently runnable stages while keeping their feature definitions and model artifacts consistent. |
| Candidate models, parameter search spaces, trial limits, and metric direction in configuration | `application_config/ml/training.yaml`, `notebooks/ml/train.py` | Make AutoML choices and budgets inspectable; validate them for the selected task and backend. |
| Experiment tracking and model registry integration | `notebooks/ml/tarining_drivers/late_payment_next_3_months/generic_driver.py` | Record model comparisons and artifacts, with environment-specific registry settings outside business logic. |
| Small transformation tests with expected datasets | `tests/data_processing/test_type_caster.py` | Verify transformation behavior with small input/output examples; use equivalent cases when comparing engines. |

Adapt these patterns deliberately:

- Keep Spark sessions, Unity Catalog access, `dbutils`, and Databricks registry settings in their relevant backend or runtime implementation. The reference's pipeline and I/O modules depend directly on these technologies; the portable core must not require them.
- Resolve configured operation names through an explicit approved mapping and validate parameters before execution. Do not carry over the `eval(step["transformer"])` dispatch in `generic_framework/data_processing/actions.py`.
- Select candidates using validation results or cross-validation, then assess the selected pipeline on an untouched test set. The reference's `ModelSelector.evaluate_models` chooses a winner using test-set scores; do not inherit that evaluation design.
- Keep customer-specific feature logic and bronze/silver/gold conventions in optional recipes. Do not make them requirements for all workflows.
- Keep batch, incremental, and streaming behavior explicit. The reference illustrates all three; batch is the first-release workflow style, upsert is supported only where verified, and streaming/checkpoints are outside this release.
- Provide reusable library entry points for the workflow; platform notebooks may call them without owning the core training logic.


## Not Doing

- Infrastructure provisioning or remote-job submission/status/cancellation management: users/platforms own launching and orchestration.
- Automatic task/engine selection or scanning installed algorithms: explicit configuration controls behavior.
- Universal backend combinations: declare tested combinations and reject unsupported ones.
- Automatic model promotion, hosted UI/accounts, custom scheduler, or online serving: not required by the confirmed library intent.
- A business-specific release: examples provide acceptance evidence without defining the product.

## Remaining Technical Choices

Package name, Python/dependency versions, schema library, tested host/provider profiles, default search ranges, and backend-specific semantics.
Business metrics are user-configured; there is no mandatory sales dataset, fixed horizon, or universal accuracy threshold.

## Main Risk

Pip installability does not guarantee a backend can execute in every host. Versioned supported-combination evidence is required before claiming compatibility.
