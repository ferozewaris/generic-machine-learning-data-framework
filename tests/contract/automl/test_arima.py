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
