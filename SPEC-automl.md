# Spec: Configured AutoML, Tuning, and Evaluation

Module id: `automl`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: core-contracts, processing

## Objective

For the user's explicit ML task, algorithm list, and metric, return the best successfully evaluated listed candidate within configured tuning limits. Supply sensible versioned parameter ranges without expanding the user's candidate list.

The [confirmed intent](docs/intent/generic-data-ml-library.md) requires classification, regression, forecasting, and clustering in the first release. None is a follow-up release.

Implemented subset: T014 temporal data validation and T015–T016 explicit local naive/ARIMA candidate evaluation; see docs/forecasting-fixture.md. Full bounded search, worker limits, assessment/refit, workflow integration and other requested algorithms remain pending.

## Tech Stack

Optional scikit-learn, XGBoost, PySpark ML, statsmodels ARIMA, and Prophet integrations.
Each requested family needs a concrete compatible first-release implementation, not a stub.
Prefer existing backend tuning facilities or a small bounded search over a custom optimizer framework.
Dependency versions, exact candidate variants, and default ranges require documented compatibility decisions.

## Provider Contract

```python
def train(
    dataset: DatasetRef, spec: MLSpec, context: RunContext
) -> TrainingResult: ...
```
Algorithm ids distinguish backend variants. Implementations declare task/engine/host compatibility, parameters, fit/predict behavior, persistence, and enforceable limits.
AutoML consumes processing contracts and returns core result types; it does not import lifecycle orchestration.

## Configuration and Search Requirements

- Require explicit task (`classification|regression|forecasting|clustering`), a nonempty unique list of algorithm ids, and a task-valid selection metric.
- Never infer task, discover all installed algorithms for search, switch processing engines, substitute algorithm variants, or add an unlisted baseline.
- For every listed algorithm, resolve omitted search ranges from its versioned library defaults. Validate overrides and merge only supported keys; explicit fixed parameters stay fixed. Record the final search specification and defaults version.
- Invalid task/algorithm/metric/domain combinations fail before data access/fitting where detectable. Unknown/missing installed providers produce actionable capability errors.
- Require positive finite trial/time limits. Search only resolved supported domains. Count each initiated candidate configuration once; report fold fits, final assessment refits, and optional full-data refits separately.
- Task config additionally defines features/target where applicable, split/assessment protocol, seeds, and time/group/horizon/frequency semantics when required.
- Processing stays with the configured engine. A candidate requiring a different engine is allowed only through an explicitly enabled supported transfer with enforced row/byte limits. Reject unsafe or unbounded collection.
- Learned imputation/encoding/scaling/selection fits inside each training fold. No test data or validation-fitted preprocessing may influence candidate selection.

## Task-Specific Evaluation

- Classification: validated labels and metric-compatible predictions/probabilities; stratified, group-aware, or temporal holdout/CV as explicitly configured.
- Regression: numeric target validation, metric-compatible holdout/CV, group/time separation where selected.
- Forecasting: causal features and origin-based forecasts; temporal holdout/backtesting with declared horizon/frequency. Predictions cannot observe held-out targets. Small one-series examples do not limit the generic library to that business use case.
- Clustering: explicitly declared assessment protocol and valid internal metric or external labels, degenerate-cluster checks, and documented inference support. Do not force supervised accuracy semantics onto clustering.
- Rank finite validation/CV/assessment scores using the declared metric direction; validate any user direction override against the metric definition. Ties follow configured candidate order.
- Baselines appear only when listed; examples may list one deliberately, and it may win.
- After supervised/time-series selection, refit the selected pipeline on train+validation, assess once on untouched test data, and preserve that evaluated pipeline. The test set cannot alter selection or parameters.
- Clustering follows its declared assessment contract; results identify which data the reported metric describes.
- Split-aware preprocessing and untouched evaluation follow the separation described in [scikit-learn's leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).

## Optional Full-Data Refit and Results

- `ml.refit_on_all_data` defaults to false. Default returned `model` is `evaluated_model`, with its exact fit data/cutoff and assessment evidence.
- If true, preserve the evaluated artifact/report, fit the selected configuration on all eligible data supplied to this training run, and return a separately identified `refit_model` as `model`.
- Do not search again, fetch unrequested future data, reuse test scores as refit-model scores, or mutate the evaluated artifact. Record refit dataset identity, cutoff, parameters, preprocessing, and operation duration.
- Forecast origin comes from the chosen artifact's actual fitted cutoff. Ordinary inference never refits.
- Refit is part of the declared overall deadline and output contract. If requested refit fails, report failure and preserve any completed evaluated artifacts; do not silently return success with a different model.
- Trial records include id, resolved parameters/default version, fold scores, seed, duration, status, and safe failure reason.
- Candidate-specific fit failure can fail a trial; auth/policy/shared-data errors and cancellation terminate the stage. No completed candidates means no winner.
- Stop starting fits at expiry and terminate supported library-owned workers. Unsupported limit-enforcement modes fail preflight.
- Results include selected model identity, feature signature, trial evidence, metric/direction, validation and test/assessment evidence, fitted cutoffs, resolved search domains, data/environment identity, and reproducibility limits.

## Commands

Proposed after implementation:
```sh
python3 -m pytest tests/unit/automl tests/contract/automl -q
python3 -m pytest tests/integration/automl -m integration -q
python3 -m gmldf run --config examples/classification/workflow.yaml --profile local --run-id classification-demo --output-dir runs/classification-demo
```

## Project Structure

`src/gmldf/automl/`: task protocols, candidate registry, default spaces, bounded search, selection and refit.
`tests/unit/automl/`: domain/ranking/budget/error checks.
`tests/contract/automl/`: task/candidate/refit contracts.
`tests/integration/automl/`: actual backend fits and persistence compatibility.

## Code Style

Use typed contracts; name metrics `validation_score`, `test_score`, or `assessment_score`, with direction and model identity.
Never label a prior evaluated score as a score measured on the optional full-data-refitted artifact.

## Testing Strategy and Success Criteria

1. Only listed algorithms are fitted, including an explicit test that installed/unlisted algorithms and baselines never run.
2. Defaults and valid overrides produce recorded versioned search spaces; invalid overrides and missing task/metric/candidates fail before fitting.
3. Validation-only oracle ranking, tie rules, failed/NaN trials, and all-candidates-failed behavior are deterministic. Test-target mutation cannot change selection.
4. Fold-local preprocessing and causal/group/time tests prove isolation; forecasts return the declared horizon from the correct origin.
5. Trial/time limits and in-process cancellation are enforced with controlled workers/clocks, including refits; unsupported enforcement is rejected.
6. All four task families and every requested model integration have real contract/integration evidence for declared combinations.
7. Default results preserve the evaluated pipeline; optional full-data refit returns a separate artifact, preserves the original report, updates fit cutoff, and never relabels scores or mutates selection.
8. Explicit bounded cross-engine transfer succeeds only for a declared supported route; disabled, oversized, unknown-size, and unsupported routes reject before collection.
9. An explicitly listed baseline can win; no universal accuracy improvement or global optimum is promised.

## Boundaries

- Always: honor the user-selected task/candidates/metric/engine, validate domains, retain complete evaluated evidence, enforce limits.
- Ask first: change the confirmed candidate-selection or refit semantics.
- Never: add unlisted algorithms, leak evaluation data, collect without bounds, or claim full-data-refit scores were measured.

## Remaining Technical Choices

- Exact supported candidate variants per task/backend and concrete versioned default search ranges.
- Provider-specific forecast/group/CV and clustering assessment limitations, documented in the support matrix.
- Hardware/dependency profiles and trust-approved persistence formats. Business thresholds are dataset-specific user config, not one fixed release criterion.
