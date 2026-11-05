# Synthetic forecasting acceptance fixture

`tests/fixtures/automl/sales.csv` contains731 daily records from2023-01-01 through2024-12-31, including leap day. It is synthetic and contains no copied/customer data. Its two columns are `date` and `value`; the file name has no meaning to library code.

Generation method: for zero-based day index `i`, the value is `(500 + i + 50 * (i % 7)) / 5`, written to one decimal place. Construct dates by adding `i` days to2023-01-01. Integer arithmetic in fifths makes the generation deterministic. The tests independently verify every value and the exact date range.

The fixture's explicit split is675 training records through2024-11-05,28 validation records from2024-11-06 through2024-12-03, and28 test records from2024-12-04 through2024-12-31. These cutoffs and horizon are fixture choices. They are not library defaults or a narrower release definition.

The data validator `gmldf.automl.forecast_data.split_forecast_data(dataset, spec)` consumes a native pandas `DatasetRef` and an explicit forecasting `MLSpec`. Its current temporal-holdout configuration uses:

```yaml
time_column: date
target: value
frequency: D
horizon: 28
split:
  method: temporal_holdout
  train_end: '2024-11-05T00:00:00Z'
  validation_end: '2024-12-03T00:00:00Z'
  test_end: '2024-12-31T00:00:00Z'
```

Parse fixture dates using an exact `%Y-%m-%d` format with `utc: true` in the CSV reader. The target must be a native real integer/float column with finite, nonnull values; textual numbers need an explicit processing cast. Times must be native timezone-aware datetimes, unique, strictly increasing and complete on the configured frequency grid after conversion to UTC. Naive times, missing/duplicate dates, complex/boolean/text targets and frequency overflows reject explicitly. No automatic sorting, gap filling or target imputation occurs.

Cutoffs must explicitly specify UTC, lie on actual records and be strictly ordered. Validation and test must each contain exactly the declared horizon. The last supplied record must match the test cutoff, so later data is never silently discarded or made available for selection. The returned `ForecastData` contains independent copied train/validation/test frames plus configured column names, frequency and horizon.

A separate two-hourly fixture test uses different column names, cutoffs and a two-step horizon. Other positive pandas frequencies can work when they match the UTC timeline; frequency interpretation across local daylight-saving transitions is not inferred. Grouped forecasting rejects in this current validator; grouped/backtesting support remains a later task.

The data-validator slice validates partitions only. The candidate primitive below fits an explicitly listed naive model; selection, untouched assessment and optional refit remain subsequent tasks. For this fixture, a future evaluated model fits through the validation cutoff and an explicitly requested full-data refit fits through the test cutoff; their forecast origins must remain distinct. These data-validator checks make no model-quality claim; the candidate-level validation result below is separate from final test assessment.

## Explicit naive validation candidate

T015 adds `gmldf.automl.forecasting.evaluate_naive(dataset, spec, context)` as a candidate-level primitive. Its current local pandas profile accepts exactly the user-listed `naive.last` algorithm, explicit MAE (minimized), empty fixed/search parameters, and no exogenous features. An unlisted baseline, additional unsupported algorithm, denied capability or unsupported engine rejects before fitting. Context must allow `pandas_naive_last`.

The model fits the training partition only and repeats the last observed target for the configured future horizon. Prediction receives fitted scalar state and horizon, with no validation/test targets. Returned columns are `timestamp` and `prediction`. MAE is recomputable from these exact validation predictions. Changing heldout targets cannot alter fitted state/predictions; changing test targets cannot alter validation score.

The internal `ForecastEvaluation` contains core `CandidateRecord`, `FitData`, and prediction `DatasetRef` contracts plus the native `NaiveModel`. It records one initiated fit, seed, elapsed trial duration, split metadata digest, actual fitted cutoff and available source versions. The split digest contains partition/source metadata, not target values; unknown source versions remain unknown and do not establish snapshots. There is no fabricated durable model artifact or test assessment.

Naive state roundtrips through strict JSON. Its datetime metadata requires a microsecond-aligned fitted cutoff; finer origins reject rather than truncate. Integer targets requiring implicit precision loss in float64 fitting/scoring reject; users may choose an explicit processing cast. Horizon/frequency validation and range errors are controlled. Whole-run training deadlines/worker cancellation, bounded multi-candidate search, final train+validation refit/test assessment, artifact publication and ordinary inference remain subsequent tasks. The CLI still rejects `kind: train` until workflow integration is implemented.
