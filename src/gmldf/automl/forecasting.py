"""Explicit single-candidate validation evaluation, before bounded search."""

import hashlib
import json
import math
from dataclasses import dataclass
from time import perf_counter

from pydantic import ValidationError

from gmldf.automl.candidates.naive import NaiveModel, fit_naive
from gmldf.automl.forecast_data import split_forecast_data
from gmldf.core.capabilities import Capability, CapabilityRegistry, CapabilityRequest
from gmldf.core.config import ConfigError, MLSpec, Spec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import CandidateRecord, ColumnSpec, DatasetRef, FitData, RunContext

NAIVE_LAST = Capability(
    id="pandas_naive_last",
    operation="fit",
    engine="pandas",
    profile="local",
    task="forecasting",
    algorithm="naive.last",
    status="verified",
    install_extra="pandas",
    dependencies={
        "pandas": "3.1.1",
        "numpy": "2.4.6",
        "python-dateutil": "4.0.0",
        "tzdata": "2026.6",
    },
)


@dataclass(frozen=True)
class ForecastEvaluation:
    record: CandidateRecord
    fit: FitData
    predictions: DatasetRef
    model: NaiveModel
    metric: str
    greater_is_better: bool


def evaluate_naive(dataset: DatasetRef, spec: MLSpec, context: RunContext) -> ForecastEvaluation:
    try:
        spec = MLSpec.model_validate(spec.model_dump())
    except ValidationError as cause:
        raise ConfigError("ml", "invalid_ml_spec") from cause
    registry = CapabilityRegistry([NAIVE_LAST])
    for index, algorithm in enumerate(spec.algorithms):
        registry.require(
            CapabilityRequest(
                operation="fit",
                engine=dataset.engine,
                profile="local",
                task=spec.task,
                algorithm=algorithm.name,
            ),
            allowed=context.allowed_capabilities,
            path=f"ml.algorithms.{index}.name",
        )
    if len(spec.algorithms) != 1:
        raise ConfigError("ml.algorithms", "single_unique_naive_candidate_required")
    algorithm = spec.algorithms[0]
    try:
        Spec.model_validate(algorithm.parameters)
        if algorithm.search_space is not None:
            Spec.model_validate(algorithm.search_space)
    except ValidationError as cause:
        raise ConfigError("ml.algorithms.0", "naive_has_no_tunable_parameters") from cause
    if spec.features:
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="ml.features")
    if spec.evaluation.metric != "mae":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="ml.evaluation.metric")
    if spec.evaluation.greater_is_better not in {None, False}:
        raise ConfigError("ml.evaluation.greater_is_better", "mae_must_be_minimized")
    return _evaluate_forecast(dataset, spec, fit_naive, {})


def _evaluate_forecast(dataset, spec, fit_candidate, parameters) -> ForecastEvaluation:
    algorithm = spec.algorithms[0]
    split = split_forecast_data(dataset, spec)
    actual = split.validation[split.target]
    if not actual.map(lambda value: not isinstance(value, int) or int(float(value)) == value).all():
        raise FrameworkError("DATA_INVALID", path="ml.target")
    split_metadata = {
        "source_id": dataset.id,
        "source_uri": dataset.source_uri,
        "source_version": dataset.source_version,
        "time_column": spec.time_column,
        "target": spec.target,
        "frequency": spec.frequency,
        "horizon": spec.horizon,
        "split": spec.split,
        "first_timestamp": split.train[split.time_column].iloc[0].isoformat(),
        "partition_rows": [len(split.train), len(split.validation), len(split.test)],
    }
    split_id = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(split_metadata, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    started = perf_counter()
    model = fit_candidate(
        split.train, time_column=split.time_column, target=split.target, frequency=split.frequency
    )
    predictions = model.forecast(split.horizon)
    expected_times = split.validation[split.time_column].reset_index(drop=True)
    if not predictions["timestamp"].eq(expected_times).all():
        raise FrameworkError("EXECUTION_FAILED", path="ml.horizon")
    try:
        score = math.fsum(
            abs(float(value) - float(prediction))
            for value, prediction in zip(actual, predictions["prediction"], strict=True)
        ) / len(actual)
        if not math.isfinite(score):
            raise ValueError("finite_score_required")
    except (ValueError, OverflowError) as cause:
        raise FrameworkError("EXECUTION_FAILED", path="ml.evaluation.metric") from cause
    record = CandidateRecord(
        trial_id="trial_0",
        algorithm=algorithm.name,
        status="succeeded",
        parameters=parameters,
        validation_score=score,
        seed=spec.tuning.seed,
        fit_count=1,
        duration_seconds=perf_counter() - started,
        split_id=split_id,
    )
    fit = FitData(
        dataset_ids=[dataset.id],
        row_count=len(split.train),
        cutoff=model.cutoff,
        source_versions={dataset.id: dataset.source_version}
        if dataset.source_version is not None
        else {},
    )
    reference = DatasetRef(
        id="validation_predictions",
        engine="pandas",
        materialization="memory",
        row_count=len(predictions),
        columns=[
            ColumnSpec(name="timestamp", dtype="timestamp", nullable=False),
            ColumnSpec(name="prediction", dtype="float64", nullable=False),
        ],
        source_uri=dataset.source_uri,
        source_version=dataset.source_version,
    ).with_handle(predictions)
    return ForecastEvaluation(
        record=record,
        fit=fit,
        predictions=reference,
        model=model,
        metric="mae",
        greater_is_better=False,
    )
