from pathlib import Path

import pandas as pd
import pytest

from gmldf.automl.forecast_data import split_forecast_data
from gmldf.core.config import ConfigError, MLSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef


@pytest.fixture
def spec():
    return MLSpec(
        task="forecasting",
        algorithms=[{"name": "naive.last"}],
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


def ref(frame):
    return DatasetRef(
        id="raw",
        engine="pandas",
        materialization="memory",
        columns=[
            ColumnSpec(name="date", dtype="timestamp"),
            ColumnSpec(name="value", dtype="float64"),
        ],
    ).with_handle(frame)


@pytest.fixture
def frame():
    path = Path(__file__).parents[2] / "fixtures/automl/sales.csv"
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d", utc=True)
    return frame


def test_deterministic_fixture_and_exact_temporal_windows(frame, spec):
    original = frame.copy(deep=True)
    assert len(frame) == 731
    assert frame["date"].iloc[0] == pd.Timestamp("2023-01-01T00:00:00Z")
    assert frame["date"].iloc[-1] == pd.Timestamp("2024-12-31T00:00:00Z")
    assert frame["value"].tolist() == [(500 + index + 50 * (index % 7)) / 5 for index in range(731)]
    split = split_forecast_data(ref(frame), spec)
    assert len(split.train) == 675
    assert len(split.validation) == len(split.test) == 28
    assert split.train["date"].iloc[-1] == pd.Timestamp("2024-11-05T00:00:00Z")
    assert split.validation["date"].iloc[0] == pd.Timestamp("2024-11-06T00:00:00Z")
    assert split.validation["date"].iloc[-1] == pd.Timestamp("2024-12-03T00:00:00Z")
    assert split.test["date"].iloc[0] == pd.Timestamp("2024-12-04T00:00:00Z")
    assert split.test["date"].iloc[-1] == pd.Timestamp("2024-12-31T00:00:00Z")
    split.train.loc[0, "value"] = -1
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate",
        "missing",
        "unordered",
        "null_date",
        "inf",
        "nan",
        "text",
        "naive",
        "extra_after_test",
    ],
)
def test_invalid_timeline_or_targets_reject_explicitly(frame, spec, problem):
    if problem == "duplicate":
        frame.loc[1, "date"] = frame.loc[0, "date"]
    elif problem == "missing":
        frame = frame.drop(index=1)
    elif problem == "unordered":
        frame = frame.iloc[::-1]
    elif problem == "null_date":
        frame.loc[1, "date"] = pd.NaT
    elif problem in {"inf", "nan"}:
        frame.loc[1, "value"] = float(problem)
    elif problem == "text":
        frame["value"] = frame["value"].astype("string")
    elif problem == "naive":
        frame["date"] = frame["date"].dt.tz_localize(None)
    else:
        frame = pd.concat(
            [frame, pd.DataFrame({"date": [pd.Timestamp("2025-01-01T00:00:00Z")], "value": [1.0]})],
            ignore_index=True,
        )
    with pytest.raises(FrameworkError) as caught:
        split_forecast_data(ref(frame), spec)
    assert caught.value.error.code == "DATA_INVALID"


@pytest.mark.parametrize(
    "field,value",
    [
        ("frequency", "invalid"),
        ("frequency", "0D"),
        ("frequency", "-1D"),
        ("horizon", 0),
        ("horizon", -1),
        ("horizon", None),
        ("time_column", None),
        ("target", None),
    ],
)
def test_invalid_forecasting_configuration_rejects_before_data_access(spec, field, value):
    invalid = spec.model_copy(update={field: value})
    with pytest.raises(ConfigError):
        split_forecast_data(ref(pd.DataFrame()), invalid)


@pytest.mark.parametrize(
    "change", ["missing_cutoff", "unordered_cutoff", "short_window", "unknown_key", "nonutc_cutoff"]
)
def test_explicit_split_rejects_invalid_or_ambiguous_cutoffs(frame, spec, change):
    split = dict(spec.split)
    if change == "missing_cutoff":
        split.pop("test_end")
    elif change == "unordered_cutoff":
        split["train_end"] = split["validation_end"]
    elif change == "short_window":
        split["train_end"] = "2024-11-06T00:00:00Z"
    elif change == "unknown_key":
        split["guess"] = True
    else:
        split["train_end"] = "2024-11-05"
    with pytest.raises(ConfigError):
        split_forecast_data(ref(frame), spec.model_copy(update={"split": split}))


@pytest.mark.parametrize("frequency", ["999999999999999999999D", "100000000D"])
def test_frequency_overflow_is_a_safe_configuration_rejection(frame, spec, frequency):
    with pytest.raises(ConfigError) as caught:
        split_forecast_data(ref(frame), spec.model_copy(update={"frequency": frequency}))
    assert caught.value.path == "ml.frequency"


def test_complex_target_is_rejected_as_unsupported_numeric_data(frame, spec):
    frame["value"] = frame["value"].astype(complex)
    with pytest.raises(FrameworkError) as caught:
        split_forecast_data(ref(frame), spec)
    assert caught.value.error.code == "DATA_INVALID"


def test_split_uses_configured_columns_frequency_horizon_and_cutoffs(spec):
    frame = pd.DataFrame(
        {
            "event_time": pd.date_range("2025-02-01", periods=10, freq="2h", tz="UTC"),
            "measurement": range(10),
        }
    )
    configured = spec.model_copy(
        update={
            "time_column": "event_time",
            "target": "measurement",
            "frequency": "2h",
            "horizon": 2,
            "split": {
                "method": "temporal_holdout",
                "train_end": frame["event_time"].iloc[5].isoformat(),
                "validation_end": frame["event_time"].iloc[7].isoformat(),
                "test_end": frame["event_time"].iloc[9].isoformat(),
            },
        }
    )
    data = DatasetRef(
        id="other",
        engine="pandas",
        materialization="memory",
        columns=[
            ColumnSpec(name="event_time", dtype="timestamp"),
            ColumnSpec(name="measurement", dtype="int64"),
        ],
    ).with_handle(frame)
    result = split_forecast_data(data, configured)
    assert result.train["measurement"].tolist() == list(range(6))
    assert result.validation["measurement"].tolist() == [6, 7]
    assert result.test["measurement"].tolist() == [8, 9]
    assert result.frequency == "2h"
    assert result.horizon == 2
