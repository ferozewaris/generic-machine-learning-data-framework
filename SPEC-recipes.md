# Spec: Generic Examples and First-Release Acceptance

Module id: `recipes`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: execution

## Objective

Prove that one pip-installable config-driven library supports data-only workflows and all four ML task families without use-case-specific source changes.
Examples are equal-status acceptance fixtures across all four task families.

The [confirmed intent](docs/intent/generic-data-ml-library.md) defines scope. First-release completion requires all named connectors/engines/tasks and requested ML integrations in documented supported combinations.

## Tech Stack

Uses the library and independently installed optional environments. Synthetic data is local and non-sensitive.
Concrete candidate examples and dependency pins are technical choices; no full backend compatibility is claimed today.

## Example Requirements

- Provide runnable data-only, classification, regression, forecasting, and clustering configs with synthetic fixtures and a documented generation method.
- Every training config explicitly names processing engine, task, algorithm list, selection metric, tuning bounds, and outputs. Baselines are included only by listing them.
- Include examples that omit search ranges to exercise versioned library defaults and examples with valid overrides.
- Keep split/feature/assessment logic task-specific but independent of customer/business naming.
- Classification demonstrates label checks, suitable metric/probabilities, fold-local preprocessing, save/load, and inference.
- Regression demonstrates numeric-target checks, declared metric, untouched assessment, save/load, and inference.
- Forecasting demonstrates causal temporal evaluation, explicit horizon/frequency, and artifact-specific forecast origin.
- Clustering demonstrates a valid explicit assessment metric/protocol, degeneracy rejection, and declared prediction capability.
- One example demonstrates a disabled-by-default, explicitly authorized, size-limited processing-to-model transfer. Negative examples reject oversized, unbounded, unknown-size, or unsupported routes.
- Demonstrate evaluated-model return by default and full-data refit only when configured; save both identities and retain the original evaluation report.
- Include equivalent file-format outputs and database/table/Delta scenarios in their compatible environments. All requested connectors/engines have integration evidence, not merely config examples.
- Users/platforms may launch examples inside containers/Kubernetes/AWS/Databricks/Snowflake. The library only installs and executes in the host; no launch/status/cancel SDK is part of acceptance.
- Do not copy BizInsights code/customer fixtures. Named datasets, ordered steps, explicit model spaces, and small semantic tests are selective inspiration.

## Illustrative Config Fragment

This classification fragment shows style, not a complete executable config:
```yaml
schema_version: 1
name: generic-classification
kind: train
engine: pandas
execution:
  profile: local
ml:
  task: classification
  target: label
  algorithms:
    - name: sklearn.dummy_classifier
    - name: sklearn.logistic_regression
      search_space:
        C: [0.1, 1.0, 10.0]
  evaluation:
    metric: roc_auc
  tuning:
    max_trials: 8
    timeout_seconds: 300
    seed: 42
  refit_on_all_data: false
```
Complete examples additionally define sources, steps, features, splits, and outputs.
Algorithm ids/values above are proposed examples; ROC AUC is explicit for this example, not a library-wide default.
The omitted first algorithm search range resolves from its defaults; no other installed algorithm is added.

## Forecasting Fixture

A possible synthetic daily fixture spans 2023-01-01 through 2024-12-31, with training through November 5, validation November 6–December 3, and test December 4–31.
Its explicit horizon is 28 days and explicit metric is MAE; a config may list naive and ARIMA candidates.
These values constrain only that test fixture. They do not become library defaults or the first-release product scope.
Default evaluated artifact fits through the validation cutoff; optional full-data refit fits through the test cutoff. Inference derives its origin from the selected immutable artifact.

## Commands

Proposed after implementation:
```sh
python3 -m gmldf run --config examples/data-only/workflow.yaml --profile local --run-id data-demo --output-dir runs/data-demo
python3 -m gmldf run --config examples/classification/workflow.yaml --profile local --run-id classification-demo --output-dir runs/classification-demo
python3 -m pytest tests/e2e/test_classification.py tests/e2e/test_regression.py tests/e2e/test_forecasting.py tests/e2e/test_clustering.py -q
python3 -m pytest tests/e2e/test_refit.py tests/e2e/test_transfer.py -q
python3 -m pytest tests/e2e/test_portability.py -m integration -q
```
Host integrations require an available authorized environment; commands do not provision it.

## Project Structure

`examples/data-only/`, `examples/classification/`, `examples/regression/`, `examples/forecasting/`, `examples/clustering/`: synthetic input/config/inference examples.
`examples/environments/`: optional user-managed invocation examples.
`tests/e2e/`: acceptance flows; `docs/compatibility.md`: versioned supported combinations and evidence.

## Code Style

Use descriptive dataset/step ids and paths relative to the config file.
No embedded Python or customer-specific logic is required by example configs. Backend differences are explicit.

## Testing Strategy and Success Criteria

1. Fresh base and optional pip installations run documented Python/CLI examples without library source edits.
2. All four ML tasks plus data-only flows complete generic config-driven preparation, training where applicable, output, persistence, and supported inference.
3. Only explicitly listed algorithms run; task/metric/engine omissions and incompatible candidates reject. Default/overridden search domains are observable.
4. Task-specific split/assessment evidence is independently recomputable; test/validation leakage and causal violations are caught.
5. All requested connectors, four processing engines, requested model integrations, and output types have a verified supported combination with actual integration evidence.
6. Explicit transfers honor row/byte limits and cannot silently collect or switch engines.
7. Default and optional-refit examples preserve distinct artifacts, original evaluation scores, and actual fit cutoffs; inference never refits.
8. User-hosted container/Kubernetes/AWS/Databricks/Snowflake invocation has supported-profile evidence; library calls perform no infrastructure or job-management actions.
9. Invalid schemas, missing extras/models, unsupported routes, auth failures, write interruptions, deadlines, and cancellation have truthful safe outcomes.
10. Inputs, candidate algorithms, metrics, and output locations change through config only. Synthetic correctness is not a universal business-accuracy claim.

## Boundaries

- Always: validate the complete first-release capability inventory, preserve unsupported-combination evidence, and keep examples generic.
- Ask first: use private data or paid/mutating external environments outside the existing authorized scope.
- Never: treat one example's completion as release completion, copy customer data/code, or mark mocked/absent live tests verified.

## Remaining Technical Choices

- Concrete small candidate sets per task/backend and pinned installation profiles.
- Representative synthetic fixture sizes and numerical tolerances per backend.
- Optional real-data business checks are user-specific supplements, not a prerequisite tied to one business use case for releasing the generic library.
