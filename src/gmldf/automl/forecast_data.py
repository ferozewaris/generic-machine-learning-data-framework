"""Explicit UTC-lattice temporal holdout validation; no candidate fitting."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from gmldf.core.config import ConfigError, MLSpec, Spec, Text
from gmldf.core.errors import FrameworkError
from gmldf.core.types import DatasetRef

if TYPE_CHECKING:
    import pandas as pd


class TemporalSplitSpec(Spec):
    method: Literal["temporal_holdout"]
    train_end: Text
    validation_end: Text
    test_end: Text


@dataclass(frozen=True)
class ForecastData:
    train: "pd.DataFrame"
    validation: "pd.DataFrame"
    test: "pd.DataFrame"
    time_column: str
    target: str
    frequency: str
    horizon: int


def split_forecast_data(dataset: DatasetRef, spec: MLSpec) -> ForecastData:
    import pandas as pd

    try:
        spec = MLSpec.model_validate(spec.model_dump())
        split = TemporalSplitSpec.model_validate(spec.split)
    except ValidationError as cause:
        raise ConfigError("ml", "invalid_forecast_configuration") from cause
    for name in ("time_column", "target", "frequency", "horizon"):
        if getattr(spec, name) is None:
            raise ConfigError(f"ml.{name}", "required_for_forecasting")
    if spec.task != "forecasting":
        raise ConfigError("ml.task", "forecasting_required")
    if spec.group_columns:
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="ml.group_columns")
    try:
        offset = pd.tseries.frequencies.to_offset(spec.frequency)
        if offset.n <= 0:
            raise ValueError("positive_frequency_required")
    except (ValueError, OverflowError) as cause:
        raise ConfigError("ml.frequency", "invalid_frequency") from cause
    cutoffs = []
    for name in ("train_end", "validation_end", "test_end"):
        try:
            value = pd.Timestamp(getattr(split, name))
            if pd.isna(value) or value.tzinfo is None or value.utcoffset().total_seconds() != 0:
                raise ValueError("explicit_utc_cutoff_required")
            cutoffs.append(value.tz_convert("UTC"))
        except (ValueError, TypeError) as cause:
            raise ConfigError(f"ml.split.{name}", "invalid_utc_cutoff") from cause
    train_end, validation_end, test_end = cutoffs
    if not train_end < validation_end < test_end:
        raise ConfigError("ml.split", "strictly_ordered_cutoffs_required")
    if dataset.engine != "pandas":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="dataset.engine")
    frame = dataset.handle
    if (
        not isinstance(frame, pd.DataFrame)
        or frame.empty
        or list(frame.columns) != [c.name for c in dataset.columns]
    ):
        raise FrameworkError("DATA_INVALID", path="dataset")
    if spec.time_column not in frame or spec.target not in frame or spec.time_column == spec.target:
        raise ConfigError("ml", "distinct_existing_time_and_target_required")
    times, target = frame[spec.time_column], frame[spec.target]
    if (
        not pd.api.types.is_datetime64_any_dtype(times.dtype)
        or times.dt.tz is None
        or times.isna().any()
    ):
        raise FrameworkError("DATA_INVALID", path="ml.time_column")
    times = pd.DatetimeIndex(times).tz_convert("UTC")
    if not times.is_unique or not times.is_monotonic_increasing:
        raise FrameworkError("DATA_INVALID", path="ml.time_column")
    try:
        expected = pd.date_range(times[0], periods=len(times), freq=offset)
    except (ValueError, OverflowError) as cause:
        raise ConfigError("ml.frequency", "invalid_frequency_range") from cause
    if not times.equals(expected):
        raise FrameworkError("DATA_INVALID", path="ml.time_column")
    if (
        not (
            pd.api.types.is_integer_dtype(target.dtype) or pd.api.types.is_float_dtype(target.dtype)
        )
        or target.isna().any()
        or not target.map(math.isfinite).all()
    ):
        raise FrameworkError("DATA_INVALID", path="ml.target")
    if times[-1] != test_end:
        raise FrameworkError("DATA_INVALID", path="ml.split.test_end")
    if any(cutoff not in times for cutoff in cutoffs):
        raise ConfigError("ml.split", "cutoff_must_match_timestamp")
    train = frame.loc[times <= train_end].copy(deep=True)
    validation = frame.loc[(times > train_end) & (times <= validation_end)].copy(deep=True)
    test = frame.loc[times > validation_end].copy(deep=True)
    if len(validation) != spec.horizon or len(test) != spec.horizon:
        raise ConfigError("ml.split", "each_holdout_must_match_horizon")
    return ForecastData(
        train=train,
        validation=validation,
        test=test,
        time_column=spec.time_column,
        target=spec.target,
        frequency=spec.frequency,
        horizon=spec.horizon,
    )
