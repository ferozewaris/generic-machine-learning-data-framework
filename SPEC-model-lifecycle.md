# Spec: Model Artifacts, Tracking, and Prediction Loading

Module id: `model-lifecycle`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: core-contracts

## Objective

Preserve a complete evaluated model pipeline and its provenance, track comparisons, and load a specific trusted model version for repeatable batch inference.

The [confirmed intent](docs/intent/generic-data-ml-library.md) defines first-release scope; shared conventions are indexed in [CAPABILITY-MAP.md](CAPABILITY-MAP.md).
This document defines desired behavior, not currently implemented functionality.

## Tech Stack

Core references, compatible artifact stores and backend-native serializers. MLflow is an optional-install first-release tracking/registry integration; users not selecting it need no MLflow server.
Exact dependency versions and supported runtime profiles remain unresolved until compatibility validation; no new packages are installed by this specification.

## Requirements and Provider Contracts

```python
def save(result: TrainingResult, context: RunContext) -> ArtifactRef: ...
def load(model: ArtifactRef, context: RunContext) -> Predictor: ...
```
Predictor accepts a DatasetRef and returns the core PredictionResult, validating its feature signature. It need not import the AutoML selection implementation.

- Bundle manifest contains schema version, immutable model identity, preprocessing identity/order, input/output signatures, task, model format, parameters, validation/test evidence, run/config/code identity, dependency/runtime versions, and source/split provenance.
- Save model and learned preprocessing together or as immutable linked artifacts. A weights-only file is not a complete model result.
- Artifact bundles include manifest, metrics, trial records, fitted pipeline, and checksums. Publish the complete bundle atomically where supported; incomplete bundles cannot load.
- Loading verifies approved source/trust policy, format/version compatibility, integrity, and required dependencies before deserialization. Never treat a checksum as proof that pickle or other executable serialization is safe.
- Resolve aliases to immutable versions once at run start and record that resolution. Concurrent alias changes cannot change an in-progress inference run.
- Record one parent training run and distinguish candidate/trial records. MLflow integration maps these to its tracking concepts; cloud-specific registry settings stay in runtime profiles.
- MLflow tracks parameters, metrics, code versions, and artifacts; it is separate from Kubernetes/container execution. See [official tracking documentation](https://mlflow.org/docs/latest/ml/tracking/).
- Runs not selecting MLflow work without an MLflow server. If tracking is explicitly required and unavailable, fail visibly. Best-effort tracking must be explicitly requested and record degraded status.
- Batch inference never refits preprocessing. Missing required features fail; extra-feature policy and category/missing-value behavior come from the stored signature.
- Store the evaluated model and optional full-data-refitted model under distinct immutable identities. Evaluation records point to the evaluated model; refit manifests link to it and record their own fit data/cutoff, without copying scores as measured refit performance.
- TrainingResult.model selects the evaluated artifact by default or the requested refit artifact. Loading either for inference preserves that artifact's preprocessing and fit cutoff; never silently refit.
- No automatic champion alias changes, deployment, promotion, retention deletion, or online serving in the first release.

## Commands

Proposed after implementation:
```sh
python3 -m pytest tests/unit/model_lifecycle tests/contract/model_lifecycle -q
python3 -m pytest tests/integration/model_lifecycle -m integration -q
python3 -m gmldf run --config examples/forecasting/inference.yaml --profile local --run-id inference-demo --output-dir runs/inference-demo
```

## Project Structure

`src/gmldf/model_lifecycle/` owns bundle validation, stores, tracking, and loading.
`tests/fixtures/model_lifecycle/` contains safe synthetic manifests.
`tests/integration/model_lifecycle/` verifies supported serializers and an isolated MLflow deployment.

## Code Style

Use immutable ArtifactRef inputs and typed Predictor outputs. Avoid a mutable global registry client; context supplies environment-specific tracking settings.

## Testing Strategy and Success Criteria

1. Save/load round-trip predictions match within backend-declared numerical tolerance for the same evaluation rows.
2. Missing preprocessing, corrupt checksums, incompatible signatures/versions, untrusted origins, and incomplete bundles all fail before prediction.
3. Alias resolution remains pinned throughout one run.
4. A local run not selecting cloud/MLflow needs no cloud SDK or MLflow import.
5. MLflow integration records selected parameters, metric direction, trial outcomes, model identity, and artifacts without credentials.
6. Required-tracking failure cannot be reported as an entirely successful run.
7. Inference input failures do not trigger a hidden model refit.
8. Evaluated/refitted bundles remain independently immutable; the original report identifies only the evaluated artifact and the returned model follows the explicit refit flag.

Use fake stores for failure injection plus real serializer round trips and an opt-in MLflow integration test. Mocks alone do not establish registry compatibility.

## Boundaries

- Always: follow the shared boundaries in the capability map; validate inputs at trust boundaries; retain module-specific failure details without credentials or raw sensitive records.
- Ask first: change the approved provider contracts or scope; run paid or destructive integration checks; publish artifacts or deploy external resources.
- Never: import another module's private implementation, bypass capability checks, or advertise untested support.

## Open Questions

- Which serializers and artifact stores are approved for enterprise use?
- Which MLflow server/registry variants are required first?
- Are signatures or artifact approval records required beyond trusted storage and checksums?
