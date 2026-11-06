import math
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError
from statsmodels.tsa.arima.model import ARIMA

from gmldf.automl.candidates.arima import ArimaModel, ArimaParams, fit_arima
from gmldf.core.config import ConfigError
from gmldf.core.errors import FrameworkError


@pytest.fixture
def training():
    frame = pd.read_csv(Path(__file__).parents[2] / "fixtures/automl/sales.csv").iloc[:675]
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame


def fit(frame, **parameters):
    return fit_arima(
        frame,
        time_column="date",
        target="value",
        frequency="D",
        parameters={"order": [1, 1, 0], "trend": "t", **parameters},
    )


def test_real_arima_matches_native_forecast_and_keeps_private_persistence_handle(training):
    original = training.copy(deep=True)
    model = fit(training)
    expected = ARIMA(
        pd.Series(
            original["value"].to_numpy(dtype=float),
            index=pd.DatetimeIndex(original["date"], freq="D"),
        ),
        order=(1, 1, 0),
        trend="t",
        missing="raise",
    ).fit(method="statespace", method_kwargs={"maxiter": 100, "disp": False}, cov_type="none")
    predictions = model.forecast(28)
    assert model.results.nobs == 675
    assert model.results.mle_retvals["converged"]
    assert model.warning_count == 0
    assert predictions["prediction"].tolist() == pytest.approx(expected.forecast(28).tolist())
    assert (
        predictions["timestamp"].tolist()
        == pd.date_range("2024-11-06", periods=28, tz="UTC").tolist()
    )
    assert predictions["prediction"].map(math.isfinite).all()
    pd.testing.assert_frame_equal(training, original)
    training.loc[674, "value"] = -9999.0
    pd.testing.assert_frame_equal(model.forecast(28), predictions)
    assert "results" not in model.model_dump_json()
    assert "ARIMAResults" not in repr(model)
    restored = ArimaModel.model_validate_json(model.model_dump_json())
    assert restored.results is None
    with pytest.raises(FrameworkError) as caught:
        restored.forecast(28)
    assert caught.value.error.code == "EXECUTION_FAILED"


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"order": [1, 1]},
        {"order": [True, 1, 0]},
        {"order": [1.0, 1, 0]},
        {"order": [-1, 1, 0]},
        {"order": [25, 1, 0]},
        {"order": [1, 3, 0]},
        {"order": [1, 1, 0], "trend": "c"},
        {"order": [1, 2, 0], "trend": "t"},
        {"order": [1, 1, 0], "trend": "ct"},
        {"order": [1, 0, 0], "trend": "guess"},
        {"order": [1, 1, 0], "maxiter": 0},
        {"order": [1, 1, 0], "maxiter": True},
        {"order": [1, 1, 0], "enforce_stationarity": 1},
        {"order": [1, 1, 0], "unknown": 5},
    ],
)
def test_invalid_parameters_reject_before_data_access(parameters):
    with pytest.raises(ValidationError):
        ArimaParams.model_validate(parameters)
    with pytest.raises(ConfigError):
        fit_arima(None, time_column="date", target="value", frequency="D", parameters=parameters)


def test_nonconvergence_is_candidate_failure_not_success(training):
    with pytest.raises(FrameworkError) as caught:
        fit(training, order=[2, 1, 2], maxiter=1)
    assert caught.value.error.code == "EXECUTION_FAILED"


def test_native_fit_error_is_safe_and_does_not_echo_training_data(training, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("secret-training-value")

    monkeypatch.setattr(ARIMA, "fit", fail)
    with pytest.raises(FrameworkError) as caught:
        fit(training)
    assert caught.value.error.code == "EXECUTION_FAILED"
    assert "secret-training-value" not in str(caught.value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "bad", 2**60 + 1])
def test_invalid_targets_reject_before_native_fit(training, value):
    if isinstance(value, str):
        training["value"] = training["value"].astype(object)
    elif isinstance(value, int):
        training["value"] = pd.Series([value] * len(training), dtype="Int64")
    training.loc[0, "value"] = value
    with pytest.raises(FrameworkError) as caught:
        fit(training)
    assert caught.value.error.code == "DATA_INVALID"


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5])
def test_invalid_forecast_horizon_is_rejected(training, horizon):
    model = fit(training)
    with pytest.raises(ConfigError):
        model.forecast(horizon)


def test_non_daily_microsecond_origin_uses_explicit_frequency(training):
    training["date"] = pd.date_range("2024-01-01T01:00:00.123456Z", periods=675, freq="2h")
    model = fit_arima(
        training,
        time_column="date",
        target="value",
        frequency="2h",
        parameters={"order": [1, 1, 0], "trend": "t"},
    )
    predictions = model.forecast(2)
    assert predictions["timestamp"].tolist() == [
        training["date"].iloc[-1] + pd.Timedelta(hours=i) for i in (2, 4)
    ]


@pytest.mark.parametrize("corruption", ["time", "length", "nan"])
def test_malformed_native_forecasts_are_safe_failures(training, monkeypatch, corruption):
    model = fit(training)
    predictions = model.results.forecast(2)
    if corruption == "time":
        predictions.index += pd.Timedelta(days=1)
    elif corruption == "length":
        predictions = predictions.iloc[:1]
    else:
        predictions.iloc[0] = float("nan")
    monkeypatch.setattr(model.results, "forecast", lambda **kwargs: predictions)
    with pytest.raises(FrameworkError) as caught:
        model.forecast(2)
    assert caught.value.error.code == "EXECUTION_FAILED"


@pytest.mark.parametrize("corruption", ["timezone", "gap", "nanoseconds"])
def test_invalid_training_origin_or_grid_is_rejected(training, corruption):
    if corruption == "timezone":
        training["date"] = training["date"].dt.tz_localize(None)
    elif corruption == "gap":
        training = training.drop(index=1)
    else:
        training["date"] = training["date"].astype("datetime64[ns, UTC]") + pd.Timedelta(
            nanoseconds=1
        )
    with pytest.raises(FrameworkError) as caught:
        fit(training)
    assert caught.value.error.code == "DATA_INVALID"


def test_fitted_parameters_are_immutable_provenance(training):
    model = fit(training)
    metadata = model.model_dump_json()
    predictions = model.forecast(2)
    with pytest.raises(ValidationError):
        model.parameters.order = (24, 2, 24)
    assert model.model_dump_json() == metadata
    pd.testing.assert_frame_equal(model.forecast(2), predictions)


def evaluation_inputs():
    from gmldf.core.config import MLSpec
    from gmldf.core.types import ColumnSpec, DatasetRef, RunContext, RunIdentity

    frame = pd.read_csv(Path(__file__).parents[2] / "fixtures/automl/sales.csv")
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    dataset = DatasetRef(
        id="raw",
        engine="pandas",
        materialization="memory",
        columns=[
            ColumnSpec(name="date", dtype="timestamp"),
            ColumnSpec(name="value", dtype="float64"),
        ],
    ).with_handle(frame)
    spec = MLSpec(
        task="forecasting",
        algorithms=[
            {"name": "statsmodels.arima", "parameters": {"order": [1, 1, 0], "trend": "t"}}
        ],
        evaluation={"metric": "mae"},
        tuning={"max_trials": 1, "timeout_seconds": 30.0, "seed": 42},
        time_column="date",
        target="value",
        frequency="D",
        horizon=28,
        split={
            "method": "temporal_holdout",
            "train_end": "2024-11-05T00:00:00Z",
            "validation_end": "2024-12-03T00:00:00Z",
            "test_end": "2024-12-31T00:00:00Z",
        },
    )
    context = RunContext(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        allowed_capabilities=["pandas_arima"],
    )
    return dataset, spec, context


def test_explicit_arima_evaluation_has_recomputable_mae_and_causal_fit():
    from gmldf.automl.forecasting import evaluate_arima

    dataset, spec, context = evaluation_inputs()
    result = evaluate_arima(dataset, spec, context)
    actual = dataset.handle["value"].iloc[675:703].tolist()
    expected = (
        math.fsum(
            abs(value - prediction)
            for value, prediction in zip(
                actual, result.predictions.handle["prediction"], strict=True
            )
        )
        / 28
    )
    assert result.record.algorithm == "statsmodels.arima"
    assert result.record.validation_score == pytest.approx(expected)
    assert result.record.parameters["order"] == [1, 1, 0]
    assert result.record.parameters["trend"] == "t"
    assert result.record.parameters["maxiter"] == 100
    assert result.record.fit_count == 1
    assert result.record.seed == 42
    assert result.fit.row_count == result.model.results.nobs == 675
    assert result.fit.cutoff == pd.Timestamp(spec.split["train_end"])
    changed = dataset.handle.copy(deep=True)
    changed.loc[675:, "value"] += 1000.0
    changed_result = evaluate_arima(dataset.with_handle(changed), spec, context)
    pd.testing.assert_frame_equal(result.predictions.handle, changed_result.predictions.handle)
    assert changed_result.record.validation_score != result.record.validation_score
    assert changed_result.record.split_id == result.record.split_id


@pytest.mark.parametrize(
    "change",
    [
        "algorithm",
        "policy",
        "engine",
        "task",
        "metric",
        "features",
        "parameters",
        "search",
        "multiple",
    ],
)
def test_arima_preflight_rejects_before_data_access(change):
    from gmldf.automl.forecasting import evaluate_arima
    from gmldf.core.config import MLSpec

    dataset, spec, context = evaluation_inputs()
    raw = spec.model_dump()
    dataset = dataset.with_handle(None)
    if change == "algorithm":
        raw["algorithms"][0]["name"] = "installed.unlisted"
    elif change == "policy":
        context = context.model_copy(update={"allowed_capabilities": []})
    elif change == "engine":
        dataset = dataset.model_copy(update={"engine": "spark"})
    elif change == "task":
        raw["task"] = "regression"
    elif change == "metric":
        raw["evaluation"]["metric"] = "rmse"
    elif change == "features":
        raw["features"] = ["other"]
    elif change == "parameters":
        raw["algorithms"][0]["parameters"]["order"] = [1, 1]
    elif change == "search":
        raw["algorithms"][0]["search_space"] = {"order": [[1, 1, 0]]}
    else:
        raw["algorithms"].append({"name": "naive.last"})
    with pytest.raises((ConfigError, FrameworkError)) as caught:
        evaluate_arima(dataset, MLSpec.model_validate(raw), context)
    if isinstance(caught.value, FrameworkError):
        assert caught.value.error.code in {"CAPABILITY_UNSUPPORTED", "POLICY_DENIED"}


def test_arima_exact_dependency_preflight_provides_install_hint(monkeypatch):
    from functools import partial

    from gmldf.automl import forecasting
    from gmldf.automl.forecasting import evaluate_arima
    from gmldf.core import capabilities

    dataset, spec, context = evaluation_inputs()
    original = capabilities.version

    def missing_statsmodels(name):
        if name == "statsmodels":
            raise capabilities.PackageNotFoundError(name)
        return original(name)

    monkeypatch.setattr(
        forecasting,
        "CapabilityRegistry",
        partial(capabilities.CapabilityRegistry, version_reader=missing_statsmodels),
    )
    with pytest.raises(FrameworkError) as caught:
        evaluate_arima(dataset.with_handle(None), spec, context)
    assert caught.value.error.code == "CAPABILITY_UNSUPPORTED"
    assert caught.value.error.dependency.install_extra == "arima"
