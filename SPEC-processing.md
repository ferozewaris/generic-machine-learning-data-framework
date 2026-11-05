# Spec: Processing Engines and Feature Preparation

Module id: `processing`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: core-contracts

## Objective

Apply configured data transformations with documented semantics, and expose trainable preprocessing that can be fitted within each training fold and reused for inference.

The [confirmed intent](docs/intent/generic-data-ml-library.md) defines first-release scope; shared conventions are indexed in [CAPABILITY-MAP.md](CAPABILITY-MAP.md).
Implemented subset: real local pandas select/cast/sort (T008), documented in docs/processing.md. Other operations, engines and learned preprocessing remain desired work.

## Tech Stack

Optional pandas, Polars, DuckDB, and PySpark backends. All four engines are required for the first release; examples may use a single declared engine. Core and the local backend must not require Spark or Databricks.
The initial local pandas profile is pinned and verified in docs/compatibility.md. Other dependency/host profiles remain unresolved until their own compatibility checks.

## Requirements and Provider Contracts

Provider-owned boundaries:
```python
def transform(
    dataset: DatasetRef, steps: Sequence[StepSpec], context: RunContext
) -> DatasetRef: ...

def fit_preprocessor(
    train: DatasetRef, spec: FeatureSpec, context: RunContext
) -> FittedPreprocessor: ...
```
A fitted preprocessor exposes transform, feature signature, and an artifact handle through core-owned reference types.

- Initial operations: select, rename, cast, filter, fill explicit constant values, sort, group/aggregate, and joins on named keys. Named inputs and outputs make dependencies visible.
- All listed initial operations have explicit supported-engine contracts for first-release acceptance. An example's small subset does not define release completion; no placeholder implementation counts as support.
- Distinguish stateless preparation from learned preprocessing. Imputation statistics, encoders, scaling, and feature selection fit only on a training fold.
- Each backend maps approved operation names to implementations. Unknown operations fail; no `eval`, arbitrary import paths, or embedded Python.
- Backend-specific SQL is an explicit escape hatch: mark the step nonportable and declare its dialect. No promise that Spark SQL runs unchanged in DuckDB or Snowflake.
- Publish operation semantics for null filtering/join keys, duplicate join keys, date/time zones, ordering, casts/overflow, decimals, and aggregations. Reject unsupported type/operation pairs.
- Row ordering is unspecified unless explicitly requested. Comparisons normalize ordering only where order is not semantic.
- The processing engine is always user-selected. Dataset handles stay with it until an explicitly enabled supported transfer. Cross-engine ML training is allowed only with source/target declaration, enforced row/byte bounds, and a recorded materialization event; missing/unknown bounds or a size that cannot be proven safe must reject before local collection. No automatic engine selection or fallback.
- Forecast features are causal: lag/rolling computations cannot use later target values. Group boundaries and forecast cutoffs must be honored.
- No universal dataframe wrapper that mimics every engine API; the shared surface is the small operation contract.

## Commands

Proposed after implementation:
```sh
python3 -m pytest tests/unit/processing tests/contract/processing -q
python3 -m pytest tests/integration/processing -m integration -q
python3 -m ruff check src/gmldf/processing tests/contract/processing
```

## Project Structure

`src/gmldf/processing/` owns operation contracts and backend implementations.
`tests/fixtures/processing/` contains small semantic fixtures.
`tests/contract/processing/` runs the same declared operation cases against each supported backend.

## Code Style

Use the typed boundary above and explicit operation dispatch. Keep engine-specific expressions inside that backend. A new backend must state unsupported operations rather than approximate them silently.

## Testing Strategy and Success Criteria

1. Proof transformations match explicit expected schemas and values.
2. Declared common operations pass equivalent fixtures on pandas, Polars, DuckDB, and Spark before parity is claimed.
3. Nulls, empty inputs, duplicate keys, time zones, precision/overflow, and stable sorting have documented expected cases.
4. Learned preprocessing observes training rows only; validation-only categories/extreme values do not affect fitted statistics.
5. Future target changes cannot alter earlier forecasting features.
6. Unknown operations, incompatible engines, and unbounded conversions fail before processing.
7. Fitted preprocessing can be serialized/reloaded without changing the inference feature signature.

Use unit tests for dispatch and semantic fixtures; backend integration tests for real engine behavior. No mock-only parity claims.

## Boundaries

- Always: follow the shared boundaries in the capability map; validate inputs at trust boundaries; retain module-specific failure details without credentials or raw sensitive records.
- Ask first: change the approved provider contracts or scope; run paid or destructive integration checks; publish artifacts or deploy external resources.
- Never: import another module's private implementation, bypass capability checks, or advertise untested support.

## Open Questions

- Which operation/type pairs can each engine guarantee under the common semantics? This does not defer any named engine beyond the first release.
- Confirm cast-failure, time-zone, and decimal semantics where engines differ.
- Should engine-specific SQL be allowed by default or require a policy permission?
