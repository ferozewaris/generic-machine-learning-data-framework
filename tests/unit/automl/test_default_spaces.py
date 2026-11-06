import copy
import json

import pytest

from gmldf.automl.default_spaces import resolve_search
from gmldf.core.config import ConfigError, MLSpec
from gmldf.core.errors import FrameworkError


def spec(algorithms=None, **updates):
    return MLSpec(
        task="forecasting",
        algorithms=algorithms or [{"name": "statsmodels.arima"}],
        evaluation={"metric": "mae"},
        tuning={"max_trials": 8, "timeout_seconds": 30.0, "seed": 42},
        **updates,
    )


def test_defaults_are_versioned_and_only_explicit_algorithms_resolve():
    result = resolve_search(spec())
    assert len(result) == 1
    assert result[0].algorithm == "statsmodels.arima"
    assert result[0].defaults_version == "statsmodels.arima.v1"
    assert result[0].domain == {
        "order": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 1]],
        "trend": ["n"],
        "enforce_stationarity": [True],
        "enforce_invertibility": [True],
        "maxiter": [100],
    }
    baseline = resolve_search(spec([{"name": "naive.last"}]))
    assert [(item.algorithm, item.domain) for item in baseline] == [("naive.last", {})]
    assert baseline[0].defaults_version == "naive.last.v1"
    both = resolve_search(spec([{"name": "naive.last"}, {"name": "statsmodels.arima"}]))
    assert [item.algorithm for item in both] == ["naive.last", "statsmodels.arima"]


def test_fixed_values_and_valid_per_key_overrides_keep_other_defaults_and_input():
    config = spec(
        [
            {
                "name": "statsmodels.arima",
                "parameters": {"trend": "t", "maxiter": 25},
                "search_space": {
                    "order": [[1, 1, 0], [0, 1, 1]],
                    "enforce_stationarity": [True, False],
                },
            }
        ]
    )
    before = copy.deepcopy(config.model_dump())
    result = resolve_search(config)[0]
    assert result.domain["order"] == [[1, 1, 0], [0, 1, 1]]
    assert result.domain["trend"] == ["t"]
    assert result.domain["maxiter"] == [25]
    assert result.domain["enforce_stationarity"] == [True, False]
    assert result.domain["enforce_invertibility"] == [True]
    assert config.model_dump() == before
    restored = type(result).model_validate_json(result.model_dump_json())
    assert restored == result


@pytest.mark.parametrize(
    "algorithm",
    [
        {"name": "unknown.installed"},
        {"name": "statsmodels.arima", "parameters": {"unknown": 1}},
        {"name": "statsmodels.arima", "search_space": {"unknown": [1]}},
        {"name": "statsmodels.arima", "search_space": {"order": []}},
        {"name": "statsmodels.arima", "search_space": {"order": [[True, 1, 0]]}},
        {"name": "statsmodels.arima", "search_space": {"order": [[1, 3, 0]]}},
        {"name": "statsmodels.arima", "search_space": {"order": [1, 2, 3]}},
        {"name": "statsmodels.arima", "search_space": {"order": [[1, 1, 0], [1, 1, 0]]}},
        {"name": "statsmodels.arima", "search_space": {"order": {"min": 0, "max": 3}}},
        {"name": "statsmodels.arima", "search_space": {"trend": ["c"]}},
        {"name": "statsmodels.arima", "parameters": {"maxiter": True}},
        {"name": "statsmodels.arima", "parameters": {"maxiter": 0}},
        {
            "name": "statsmodels.arima",
            "parameters": {"order": [1, 1, 0]},
            "search_space": {"order": [[0, 0, 0]]},
        },
        {"name": "statsmodels.arima", "search_space": {"maxiter": list(range(1, 130))}},
        {"name": "naive.last", "parameters": {"order": [0, 0, 0]}},
        {"name": "naive.last", "search_space": {"value": [1]}},
    ],
)
def test_unsupported_or_invalid_domains_fail_without_fitting(algorithm):
    with pytest.raises((ConfigError, FrameworkError)):
        resolve_search(spec([algorithm]))


@pytest.mark.parametrize(
    "change", ["task", "metric", "direction", "trials", "time", "infinite_time"]
)
def test_mutated_config_cannot_bypass_intent_or_bounded_search_validation(change):
    config = spec()
    if change == "task":
        config.task = "regression"
    elif change == "metric":
        config.evaluation.metric = "rmse"
    elif change == "direction":
        config.evaluation.greater_is_better = True
    elif change == "trials":
        config.tuning.max_trials = 0
    elif change == "time":
        config.tuning.timeout_seconds = 0.0
    else:
        config.tuning.timeout_seconds = float("inf")
    with pytest.raises((ConfigError, FrameworkError)):
        resolve_search(config)


def test_resolved_domain_mutation_cannot_change_library_defaults():
    first = resolve_search(spec())[0]
    original = json.loads(first.model_dump_json())
    first.domain["order"][0][0] = 24
    assert json.loads(resolve_search(spec())[0].model_dump_json()) == original


def test_total_domain_limit_rejects_before_cartesian_expansion():
    orders = [[p, 0, q] for p in range(10) for q in range(10)]
    config = spec(
        [
            {
                "name": "statsmodels.arima",
                "search_space": {
                    "order": orders,
                    "trend": ["n", "c", "t", "ct"],
                    "maxiter": list(range(1, 101)),
                },
            }
        ]
    )
    with pytest.raises(ConfigError):
        resolve_search(config)


def test_duplicate_algorithm_ids_reject_at_the_second_candidate_field():
    config = spec([{"name": "naive.last"}, {"name": "naive.last"}])
    with pytest.raises(ConfigError) as caught:
        resolve_search(config)
    assert caught.value.path == "ml.algorithms.1.name"
