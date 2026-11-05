import math
from pathlib import Path

import pandas as pd
import pytest

from gmldf.automl.forecasting import evaluate_naive
from gmldf.core.config import ConfigError, MLSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext, RunIdentity


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


@pytest.fixture
def dataset():
    frame = pd.read_csv(Path(__file__).parents[2] / "fixtures/automl/sales.csv")
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d", utc=True)
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
def context():
    return RunContext(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        allowed_capabilities=["pandas_naive_last"],
    )


def test_only_listed_naive_candidate_has_recomputable_causal_validation_result(
    dataset, spec, context
):
    result = evaluate_naive(dataset, spec, context)
    frame = dataset.handle
    last_training = frame.loc[frame["date"] <= pd.Timestamp(spec.split["train_end"]), "value"].iloc[
        -1
    ]
    actual = frame.loc[
        (frame["date"] > pd.Timestamp(spec.split["train_end"]))
        & (frame["date"] <= pd.Timestamp(spec.split["validation_end"])),
        "value",
    ]
    expected = math.fsum(abs(float(value) - float(last_training)) for value in actual) / 28
    assert result.record.algorithm == "naive.last"
    assert result.record.status == "succeeded"
    assert result.record.validation_score == pytest.approx(expected)
    assert result.record.fit_count == 1
    assert result.record.seed == 42
    assert result.record.duration_seconds >= 0
    assert result.record.split_id.startswith("sha256:")
    assert result.metric == "mae"
    assert result.greater_is_better is False
    assert result.fit.row_count == 675
    assert result.fit.cutoff == pd.Timestamp("2024-11-05T00:00:00Z")
    assert result.fit.dataset_ids == ["raw"]
    assert result.fit.source_versions == {}
    predictions = result.predictions.handle
    assert result.predictions.row_count == 28
    assert predictions["prediction"].tolist() == [last_training] * 28
    assert (
        predictions["timestamp"].tolist()
        == actual.index.map(lambda index: frame.loc[index, "date"]).tolist()
    )


def test_mutating_heldout_targets_never_changes_fitted_state_or_predictions(dataset, spec, context):
    original = evaluate_naive(dataset, spec, context)
    changed = dataset.handle.copy(deep=True)
    changed.loc[changed["date"] > pd.Timestamp(spec.split["train_end"]), "value"] += 1000.0
    result = evaluate_naive(dataset.with_handle(changed), spec, context)
    assert result.model == original.model
    assert result.record.split_id == original.record.split_id
    pd.testing.assert_frame_equal(result.predictions.handle, original.predictions.handle)
    assert result.record.validation_score != original.record.validation_score


@pytest.mark.parametrize(
    "change",
    [
        "unlisted",
        "extra_algorithm",
        "parameters",
        "search",
        "metric",
        "direction",
        "policy",
        "engine",
        "features",
    ],
)
def test_candidate_preflight_rejects_before_fitting_or_data_access(spec, context, change):
    raw = spec.model_dump()
    if change == "unlisted":
        raw["algorithms"] = [{"name": "installed.other"}]
    elif change == "extra_algorithm":
        raw["algorithms"].append({"name": "installed.other"})
    elif change in {"parameters", "search"}:
        raw["algorithms"][0]["parameters" if change == "parameters" else "search_space"] = {
            "guess": [1]
        }
    elif change == "metric":
        raw["evaluation"]["metric"] = "rmse"
    elif change == "direction":
        raw["evaluation"]["greater_is_better"] = True
    elif change == "policy":
        context = context.model_copy(update={"allowed_capabilities": []})
    elif change == "features":
        raw["features"] = ["other"]
    dataset = DatasetRef(
        id="raw",
        engine="spark" if change == "engine" else "pandas",
        materialization="memory",
        columns=[],
    )
    with pytest.raises((ConfigError, FrameworkError)):
        evaluate_naive(dataset, MLSpec.model_validate(raw), context)
    assert dataset.handle is None


def test_unrepresentable_integer_validation_targets_cannot_create_false_zero_mae(
    dataset, spec, context
):
    frame = dataset.handle.copy(deep=True)
    frame["value"] = pd.Series([2**60] * len(frame), dtype="Int64")
    frame.loc[675, "value"] = 2**60 + 1
    with pytest.raises(FrameworkError) as caught:
        evaluate_naive(dataset.with_handle(frame), spec, context)
    assert caught.value.error.code == "DATA_INVALID"


def test_validation_metric_is_computed_from_the_returned_predictions(
    dataset, spec, context, monkeypatch
):
    from gmldf.automl.candidates.naive import NaiveModel

    original = NaiveModel.forecast

    def forecast(model, horizon):
        result = original(model, horizon)
        result["prediction"] += 1.0
        return result

    monkeypatch.setattr(NaiveModel, "forecast", forecast)
    result = evaluate_naive(dataset, spec, context)
    actual = dataset.handle.loc[
        (dataset.handle["date"] > pd.Timestamp(spec.split["train_end"]))
        & (dataset.handle["date"] <= pd.Timestamp(spec.split["validation_end"])),
        "value",
    ].tolist()
    predictions = result.predictions.handle["prediction"].tolist()
    expected = math.fsum(
        abs(float(value) - prediction)
        for value, prediction in zip(actual, predictions, strict=True)
    ) / len(actual)
    assert result.record.validation_score == pytest.approx(expected)


def test_test_target_mutation_cannot_change_validation_score_or_fitted_state(
    dataset, spec, context
):
    original = evaluate_naive(dataset, spec, context)
    frame = dataset.handle.copy(deep=True)
    frame.loc[frame["date"] > pd.Timestamp(spec.split["validation_end"]), "value"] += 10000.0
    result = evaluate_naive(dataset.with_handle(frame), spec, context)
    assert result.record.validation_score == original.record.validation_score
    assert result.record.split_id == original.record.split_id
    assert result.model == original.model


def test_known_source_version_is_preserved_in_fit_and_split_identity(dataset, spec, context):
    original = evaluate_naive(dataset, spec, context)
    versioned = evaluate_naive(
        dataset.model_copy(update={"source_version": "version1"}), spec, context
    )
    assert versioned.fit.source_versions == {"raw": "version1"}
    assert versioned.record.split_id != original.record.split_id
    assert versioned.predictions.source_version == "version1"
