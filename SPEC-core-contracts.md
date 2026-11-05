# Spec: Core Contracts

Module id: `core-contracts`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: none

## Objective

Give every module one versioned interpretation of configuration, references, capabilities, errors, and run outcomes. Users must discover invalid requests before data is read or destinations are modified.

The [confirmed intent](docs/intent/generic-data-ml-library.md) defines first-release scope; shared conventions are indexed in [CAPABILITY-MAP.md](CAPABILITY-MAP.md).
Implemented: offline structural config validation, bounded YAML parsing, and CLI reports (T004). Run/artifact contracts, policy/capability preflight, and full ML intent checks remain subsequent tasks.

## Tech Stack

Initial implementation: Python 3.11+, Pydantic 2 strict models, and a hardened PyYAML 6 SafeLoader. No compute or cloud dependencies. See the [recorded contract](docs/decisions/library-contract.md) for input limits and the tested initial profile.
Backend dependency versions and external runtime profiles remain separate compatibility checks.

## Requirements and Provider Contracts

- Config schema version starts at integer `1`. Reject unsupported versions, unknown keys, duplicate YAML keys, unsafe tags, and unresolved references. Arbitrary Jinja evaluation and Python expressions are excluded.
- Root fields: `schema_version`, `name`, `kind` (`data|train|infer`), `engine`, `execution`, `sources`, `steps`, `outputs`; `ml` required only for training; `model` required only for inference. Engine is explicitly user-selected. Training requires an explicit `ml.task`, nonempty unique `ml.algorithms` list, `ml.evaluation.metric`, and positive tuning trial/time bounds.
- Execution config identifies the current host context/profile and explicit resource/time limits; it contains no remote submission instructions. Connection values reference named connections; sensitive values are resolved through credential references, never embedded in saved configs.
- Named source ids and step ids share one unique dataset namespace. Reject missing inputs and cycles. Outputs reference a source/step dataset or a supported artifact from training/inference.
- Define engine-neutral `DatasetRef` metadata: id, engine, schema, materialization kind, optional source version/snapshot and row-count knowledge. Opaque in-process engine handles are not serialized or mistaken for portable datasets.
- Define `ArtifactRef`: immutable URI/version, kind, manifest schema version, checksum, producing run id. A checksum establishes integrity, not trust.
- Define `RunContext`: run id, attempt id, redacted config digest, credential resolver, artifact root, cancellation/deadline, allowed capabilities, event recorder. Different runtime implementations supply context without changing business config.
- Capability declarations identify operation, engine, task/model, runtime profile, dependency versions, and support status. Statuses: `planned`, `verified`, `unsupported`; missing combinations are unsupported. Offline checks use installed declarations; live permission/connectivity checks are separate.
- Core owns shared `TrainingResult` and `PredictionResult` shapes: candidate records, resolved search spaces/default versions, metric name/direction, validation score, test assessment, feature signature, artifact handles, and output dataset references. TrainingResult distinguishes `evaluated_model`, optional `refit_model`, returned `model`, fit-data cutoffs, and the artifact to which evaluation scores apply. ML backends return these without requiring lifecycle imports.
- Errors expose code, safe message, config path/stage id when known, retry safety, and chained internal cause. Codes include `CONFIG_INVALID`, `CAPABILITY_UNSUPPORTED`, `POLICY_DENIED`, `AUTH_FAILED`, `DATA_INVALID`, `RESOURCE_LIMIT`, `EXECUTION_FAILED`, `OUTPUT_INCOMPLETE`.
- Run states: pending → running → succeeded/failed/cancelled. Step/trial records distinguish skipped and failed work. UTC timestamps and config/code/environment identity are mandatory.
- Training transfer config defaults to disabled. An enabled transfer names source/target engine and positive row/byte bounds; no matching supported route means rejection. `ml.refit_on_all_data` defaults to false. Omitted per-algorithm search ranges resolve to versioned library defaults; invalid overrides fail before fitting.
- Policy hooks may reject connectors, operations, artifact locations, or runtime profiles before execution. They complement platform IAM; they are not a multi-tenant authorization system.

## Commands

Proposed, available after implementation:
```sh
python3 -m gmldf validate --config examples/forecasting/workflow.yaml --profile local --output validation.json
python3 -m pytest tests/unit/core tests/contract/core -q
python3 -m ruff check src/gmldf/core tests/unit/core tests/contract/core
```
Validation performs no connector calls, training, or destination writes. Saving the explicitly requested validation report is its only output effect.

## Project Structure

`src/gmldf/core/` owns schema, reference types, capability records, run/error contracts.
`tests/unit/core/` covers malformed inputs; `tests/contract/core/` verifies serialized forms and provider compatibility.
Schema documentation belongs in `docs/configuration.md`.

## Code Style

Illustrative provider contract:
```python
def validate_config(config: Mapping[str, object]) -> ValidatedWorkflow:
    """Return a validated workflow or raise ConfigError with a field path."""
```
Use explicit typed fields rather than arbitrary nested dictionaries at public boundaries. Configuration has no executable Python.

## Testing Strategy and Success Criteria

1. A valid data-only config needs no ML/backend imports. Unknown fields, duplicate keys, bad versions, duplicate ids, unresolved inputs, and cycles each fail with their exact field path.
2. Offline validation makes zero network calls and resolves no secret values.
3. Run and artifact manifests round-trip through JSON without opaque engine objects or secrets.
4. All terminal run states include timestamps and a safe reason; exception causes remain inspectable internally.
5. A denied policy or unsupported capability fails before source access and output mutation.
6. Sentinel secrets supplied through errors, URLs, credentials, and context never appear in serialized reports or logs.
7. Missing engine/task/algorithm list/metric, empty or duplicate algorithms, and unbounded transfer config fail at the relevant field path; omitted refit/transfer flags resolve to false without inferring intent.

Use pytest unit and contract tests with fake resolvers and import-isolation checks. No cloud accounts are needed.

## Boundaries

- Always: follow the shared boundaries in the capability map; validate inputs at trust boundaries; retain module-specific failure details without credentials or raw sensitive records.
- Ask first: change the approved provider contracts or scope; run paid or destructive integration checks; publish artifacts or deploy external resources.
- Never: import another module's private implementation, bypass capability checks, or advertise untested support.

## Open Questions

- Package name, Python target, schema dependencies, and input limits are recorded in [the implementation contract](docs/decisions/library-contract.md).
- Which enterprise policy restrictions are mandatory for the first adopters?
