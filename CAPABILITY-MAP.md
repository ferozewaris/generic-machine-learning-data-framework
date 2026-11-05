# Capability Map: Generic Data and Machine Learning Library

Status: eight module ids retained from the approved map; responsibilities revised to the [confirmed intent](docs/intent/generic-data-ml-library.md) on 2026-11-05.
Module specs describe that intent; remaining technical defaults are proposals, not implementation approval.

| Module id | Responsibility | Depends on | Specification |
|---|---|---|---|
| core-contracts | Config validation, dataset/artifact references, capability declarations, errors, run records, policy hooks | — | [Spec](SPEC-core-contracts.md) |
| data-io | All requested ingestion sources/result destinations, schema, credential references, safe writes | core-contracts | [Spec](SPEC-data-io.md) |
| processing | User-selected Spark/pandas/Polars/DuckDB, transformations, fitted preprocessing, explicit bounded transfers | core-contracts | [Spec](SPEC-processing.md) |
| automl | Explicit task/candidates/metric, default overridable search ranges, bounded tuning, evaluation, optional full-data refit | core-contracts, processing | [Spec](SPEC-automl.md) |
| model-lifecycle | Evaluated/refitted pipeline artifacts, optional MLflow, immutable identities, prediction loading | core-contracts | [Spec](SPEC-model-lifecycle.md) |
| workflow | Generic data-only/train/infer composition, lineage, failures, results | data-io, processing, automl, model-lifecycle | [Spec](SPEC-workflow.md) |
| execution | Pip installation, public Python/CLI invocation, optional extras, host-session/context compatibility | workflow | [Spec](SPEC-execution.md) |
| recipes | Equal-status generic task examples, connector/engine/runtime acceptance and supported-combination evidence | execution | [Spec](SPEC-recipes.md) |

Build order: core-contracts → data-io, processing, model-lifecycle → automl → workflow → execution → recipes.
These are provider boundaries in one distribution, not services. Interfaces belong to their provider module.

## First-Release Contract

- Every originally listed connector, all four processing engines, and all four ML tasks are first-release requirements.
- All requested model families (PySpark ML, scikit-learn, XGBoost, ARIMA, Prophet) and file/table/database/Delta outputs remain in scope.
- Task-specific examples validate a generic library. Incremental implementation milestones are not smaller first releases.
- User config chooses engine, task, algorithms, metric, tuning bounds, and outputs. Only listed algorithms run; optional baselines must also be listed.
- Search ranges have library defaults plus validated overrides. Resolved ranges and versions appear in run evidence.
- Explicit bounded cross-engine transfers are supported; unrequested or unsafe transfers fail.
- The evaluated model/report are the default result. Config may request a separately identified full-data refit without replacing the evaluation evidence.
- A minimal base and optional extras support compatible host environments. Databricks/Snowflake connectors and running inside those hosts have separate acceptance evidence.
- Users/platforms launch their own processes/jobs/containers. Library APIs do not provision infrastructure or submit/manage remote jobs.
- Basic policy hooks and redacted run records complement platform permissions; no hosted governance/account system is assumed.

## Technical Conventions

Proposed package/CLI: `gmldf`; proposed initial local target: Python 3.11. These names/versions are not confirmed product choices.
Layout: `src/gmldf/`, `tests/unit/`, `tests/contract/`, `tests/integration/`, `tests/e2e/`, `examples/`, `docs/`.
A base package and offline validator are implemented; the remaining capabilities are tracked in the backlog. Optional user-owned container/Kubernetes examples may live under `examples/environments/`.

After implementation, proposed development commands:
```sh
python3 -m pip install -e '.[dev]'
python3 -m build
python3 -m ruff check src tests
python3 -m ruff format --check src tests
python3 -m pytest -m 'not integration' -q
```

Use typed public boundaries, snake_case Python/config keys, kebab-case step ids, UTC run timestamps, and explicit business-time semantics.
Pin compatible optional environments after testing rather than requiring every dependency in one environment.
No arbitrary global accuracy/coverage/performance threshold is assumed. Each spec acceptance criterion and advertised combination needs meaningful evidence.

Always validate untrusted inputs, redact credentials, preserve failures, and fail clearly for unsupported combinations.
Never evaluate config as code, silently switch engines/collect data, add unlisted candidates, relabel untested support, or weaken tests.
Routine implementation choices can be recorded in decision notes; changes to the confirmed product contract require review.
Paid/destructive integration actions, publishing, merging, or deploying remain outside this documentation change.

## Review Boundary

The confirmed intent supersedes the earlier forecasting-first release and remote-job-management design.
Implementation follows the [plan](tasks/plan.md); current completed scope and acceptance evidence are recorded in the [backlog](tasks/todo.md). The base package and offline validator are available; remaining provider and workflow contracts are still to be implemented.
