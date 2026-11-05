import pandas as pd
import pytest
from pydantic import ValidationError

from gmldf.automl.candidates.naive import NaiveModel, fit_naive
from gmldf.core.config import ConfigError
from gmldf.core.errors import FrameworkError


def train():
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-11-01", periods=5, freq="D", tz="UTC"),
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )


def test_fitted_state_forecasts_only_from_training_origin_and_roundtrips_json():
    frame = train()
    original = frame.copy(deep=True)
    model = fit_naive(frame, time_column="date", target="value", frequency="D")
    frame.loc[4, "value"] = 999.0
    predictions = model.forecast(28)
    assert predictions["prediction"].tolist() == [5.0] * 28
    assert (
        predictions["timestamp"].tolist()
        == pd.date_range("2024-11-06", periods=28, freq="D", tz="UTC").tolist()
    )
    assert model.cutoff == original["date"].iloc[-1]
    restored = NaiveModel.model_validate_json(model.model_dump_json())
    pd.testing.assert_frame_equal(restored.forecast(28), predictions)
    assert set(model.model_dump()) == {"value", "cutoff", "frequency", "time_column", "target"}


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5])
def test_invalid_prediction_horizon_is_rejected_without_silent_coercion(horizon):
    model = fit_naive(train(), time_column="date", target="value", frequency="D")
    with pytest.raises(ConfigError):
        model.forecast(horizon)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "five"])
def test_nonfinite_or_non_numeric_last_target_is_safe_data_failure(value):
    frame = train()
    if isinstance(value, str):
        frame["value"] = frame["value"].astype(object)
    frame.loc[4, "value"] = value
    with pytest.raises(FrameworkError) as caught:
        fit_naive(frame, time_column="date", target="value", frequency="D")
    assert caught.value.error.code == "DATA_INVALID"


def test_model_cutoff_cannot_lose_nanoseconds_during_metadata_serialization():
    with pytest.raises(ValidationError):
        NaiveModel(
            value=1.0,
            cutoff=pd.Timestamp("2024-11-05T00:00:00.000000001Z"),
            frequency="D",
            time_column="date",
            target="value",
        )


@pytest.mark.parametrize("frequency", ["invalid", "0D", "-1D"])
def test_native_model_rejects_invalid_frequencies(frequency):
    with pytest.raises(ValidationError):
        NaiveModel(
            value=1.0,
            cutoff=pd.Timestamp("2024-11-05T00:00:00Z"),
            frequency=frequency,
            time_column="date",
            target="value",
        )


def test_fit_rejects_implicit_integer_precision_loss():
    frame = train()
    frame["value"] = pd.Series([1, 2, 3, 4, 2**60 + 1], dtype="Int64")
    with pytest.raises(FrameworkError) as caught:
        fit_naive(frame, time_column="date", target="value", frequency="D")
    assert caught.value.error.code == "DATA_INVALID"


def test_prediction_range_overflow_is_a_safe_resource_failure():
    model = NaiveModel(
        value=1.0,
        cutoff=pd.Timestamp("2024-11-05T00:00:00Z"),
        frequency="100000000D",
        time_column="date",
        target="value",
    )
    with pytest.raises(FrameworkError) as caught:
        model.forecast(2)
    assert caught.value.error.code == "RESOURCE_LIMIT"


@pytest.mark.parametrize("cutoff", [0, True])
def test_native_model_does_not_coerce_scalar_cutoffs(cutoff):
    with pytest.raises(ValidationError):
        NaiveModel(value=1.0, cutoff=cutoff, frequency="D", time_column="date", target="value")


def test_microsecond_aligned_ns_input_has_identical_predictions_after_json_roundtrip():
    frame = train()
    frame["date"] = frame["date"].astype("datetime64[ns, UTC]")
    model = fit_naive(frame, time_column="date", target="value", frequency="D")
    restored = NaiveModel.model_validate_json(model.model_dump_json())
    pd.testing.assert_frame_equal(model.forecast(2), restored.forecast(2))
