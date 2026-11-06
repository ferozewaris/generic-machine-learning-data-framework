# Versioned tuning domains

`gmldf.automl.default_spaces.resolve_search(ml_spec)` resolves finite domains
offline and returns core `SearchDomain` records in configured algorithm order.
It accesses no dataset, fits no model, and discovers no installed algorithms.
The current profiles are forecasting with MAE: `naive.last` and
`statsmodels.arima`. Further first-release candidate profiles are pending their
implementations. Actual fitting additionally requires compatible engine, host,
policy and dependency declarations.

Each `domain` maps a parameter name to an ordered nonempty list of choices.
An order tuple is one choice, so ARIMA orders need a nested list:

```yaml
task: forecasting
algorithms:
  - name: statsmodels.arima
    parameters:
      trend: t
      maxiter: 100
    search_space:
      order: [[1, 1, 0], [0, 1, 1]]
evaluation:
  metric: mae
tuning:
  max_trials: 8
  timeout_seconds: 30
  seed: 42
```

This fragment describes ML intent; time/target columns, frequency, horizon and
split are additionally needed for a real forecast evaluation. CLI training and
multi-candidate search are still pending T017–T020.

`parameters` fixes values as singleton domains. `search_space` overrides only
named supported domains; omitted keys keep defaults. A key cannot occur in both
sections: contradictory fixed/search intent rejects rather than ignoring one.
Unknown keys, duplicate algorithms/choices, empty or non-list choices, invalid
types/ranges, incompatible trend/order combinations, invalid task/metric direction,
and nonpositive/nonfinite tuning limits reject before any fit. Every Cartesian
combination must be valid. There are at most 128 choices per key and 4096
combinations per algorithm; oversized domains reject before expansion. Continuous
range/distribution objects are not accepted by this finite categorical profile.

| Algorithm/defaults version | Default domains |
|---|---|
| `naive.last` / `naive.last.v1` | `{}`: one parameter-free configuration |
| `statsmodels.arima` / `statsmodels.arima.v1` | `order`: `[0,0,0]`, `[1,0,0]`, `[1,1,0]`, `[0,1,1]`; `trend`: `n`; stationarity and invertibility: true; `maxiter`:100 |

ARIMA bounds and native behavior are in [forecasting-fixture.md](forecasting-fixture.md).
These are library defaults, not a global optimum or convergence guarantee. A
baseline is resolved only when explicitly listed. Result records serialize exact
resolved domains and their defaults version; changing a returned domain cannot
mutate library defaults. Defaults changes require a version change. Full training
will retain these records in `TrainingResult.resolved_search` when integrated.

The resolver validates limits but does not enforce a running fit's deadline.
Supported worker enforcement remains T018; no timeout claim is made by this API.

```sh
.venv/bin/python -m pytest tests/unit/automl/test_default_spaces.py -q
```
