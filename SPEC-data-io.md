# Spec: Data Ingestion and Result I/O

Module id: `data-io`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: core-contracts

## Objective

Read configured datasets and write results through explicit source/sink contracts while preserving schemas and preventing accidental destructive or duplicate writes.

The [confirmed intent](docs/intent/generic-data-ml-library.md) defines first-release scope; shared conventions are indexed in [CAPABILITY-MAP.md](CAPABILITY-MAP.md).
Implemented subset: schema-checked local pandas CSV reads (T007) and atomic CSV writes (T009), documented in docs/data-io.md. Parquet, remote sources and table/database/Delta outputs remain desired work.

## Tech Stack

Core contracts plus optional provider drivers. CSV and Parquet are formats; S3, ADLS, and Google Cloud Storage are storage locations; SQL Server, Oracle, Databricks, and Snowflake provide table/query access. All requested connectors are first-release scope, delivered as optional compatible providers rather than one mandatory dependency bundle.
Exact dependency versions and supported runtime profiles remain unresolved until compatibility validation; no new packages are installed by this specification.

## Requirements and Provider Contracts

Provider-owned boundary:
```python
def read(source: SourceSpec, context: RunContext) -> DatasetRef: ...
def write(dataset: DatasetRef, sink: SinkSpec, context: RunContext) -> WriteReceipt: ...
```
Each implementation declares its engine/format/location/runtime support. Supply engine-specific implementations through this boundary; do not make the generic I/O layer import processing or execution modules.

- Source spec: named id, connector, location/table/query, format where applicable, schema, parse options, and connection reference. SQL values use parameters; qualified identifiers are validated and quoted according to the driver.
- First-release file formats: local CSV and Parquet reads/writes. CSV must declare encoding, delimiter, null representation, and date parsing where inference would be ambiguous. Configurable schema inference must be explicit and recorded.
- First-release sources: S3, ADLS, GCS; SQL Server and Oracle; Databricks and Snowflake tables/queries. Access can be external or platform-native depending on declared capability.
- First-release results: CSV, Parquet, database/catalog tables, and Delta. Delta is a transactional table format, not a filename option usable by every engine.
- Database connections support encrypted transport and provider/workload identity where available. Secret references resolve only at access time and are redacted.
- A read records schema and source snapshot/version when available. If repeatable snapshots cannot be obtained, flag reproducibility as limited.
- Fail on malformed rows/schema mismatches by default. An explicit quarantine policy may be added as product scope with rejected-row counts and a protected destination.
- Write modes: `error_if_exists` default; `append` and `overwrite` explicit; `upsert` only where supported and with declared keys. Capability preflight rejects unsupported semantics.
- Receipt: destination, mode, commit identifier/version when available, rows written if known, completion state, and retry safety.
- Use atomic publish/transactions when supported. Otherwise report the partial-write limitation; do not advertise atomicity or exactly-once behavior.
- Retries of append/upsert require a proven idempotency mechanism for the same logical run/output key. Reject changed payload/config reuse of that key; never blindly repeat an ambiguous write.
- First-release workflows are batch. Streaming, change-data capture, checkpoints, and cross-sink transactions are not implied by the confirmed intent.
- No automatic full-table extraction, driver collection, or local materialization without an explicit supported transfer and configured bounds.

## Commands

Proposed after implementation:
```sh
python3 -m pytest tests/unit/data_io tests/contract/data_io -q
python3 -m pytest tests/integration/data_io -m integration -q
python3 -m gmldf run --config examples/data-only/workflow.yaml --profile local --run-id data-demo --output-dir runs/data-demo
```
Live integration tests require separately supplied credentials and isolated test destinations; the command alone does not authorize paid or destructive tests.

## Project Structure

`src/gmldf/data_io/` owns connector contracts and providers.
`tests/contract/data_io/` contains shared reader/writer cases.
`tests/integration/data_io/` contains provider-specific live cases.
Synthetic fixtures live in `tests/fixtures/data_io/`.

## Code Style

Use the read/write signatures above; provider names and write modes are explicit strings validated by core schemas. Keep credential values out of dataclass representations and exception messages.

## Testing Strategy and Success Criteria

1. CSV/Parquet round trips preserve declared values, nulls, types, and schema for the shared acceptance fixtures.
2. The default write cannot replace an existing destination. Explicit overwrite affects only the selected destination.
3. Auth failures and invalid schemas produce distinct core errors without exposing credentials.
4. Injected write failures preserve the old destination when atomic publish is promised; otherwise return an incomplete output with safe recovery guidance.
5. Retrying a non-idempotent append is blocked after an ambiguous commit.
6. Every product connector passes shared contract tests and a live integration case before its exact combination becomes verified.
7. Tests cover SQL parameter handling, identifiers, empty datasets, Unicode, decimals, timestamps, and unavailable source versions.

Unit mocks verify dispatch and failures; they do not establish provider compatibility.

## Boundaries

- Always: follow the shared boundaries in the capability map; validate inputs at trust boundaries; retain module-specific failure details without credentials or raw sensitive records.
- Ask first: change the approved provider contracts or scope; run paid or destructive integration checks; publish artifacts or deploy external resources.
- Never: import another module's private implementation, bypass capability checks, or advertise untested support.

## Open Questions

- Which authentication methods and database versions are required first?
- What source snapshot guarantees and write atomicity does each environment need?
- Which exact engine/provider/version combinations and write modes establish each first-release connector's supported profile? All named connectors remain mandatory; this is a compatibility question.
