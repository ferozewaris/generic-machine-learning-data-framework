"""Last-observation forecast state; fitting never receives holdout targets."""

import math
from datetime import datetime

from pydantic import field_validator

from gmldf.core.config import ConfigError, Text
from gmldf.core.errors import FrameworkError
from gmldf.core.types import Manifest, UTCTime


class NaiveModel(Manifest):
    value: float
    cutoff: UTCTime
    frequency: Text
    time_column: Text
    target: Text

    @field_validator("cutoff", mode="before")
    @classmethod
    def metadata_precision(cls, value):
        import pandas as pd

        if not isinstance(value, (datetime, str)):
            raise ValueError("datetime_cutoff_required")
        try:
            parsed = pd.Timestamp(value)
            if parsed.nanosecond != 0:
                raise ValueError("microsecond_cutoff_required")
        except (TypeError, OverflowError) as cause:
            raise ValueError("invalid_cutoff") from cause
        return parsed.to_pydatetime()

    @field_validator("frequency")
    @classmethod
    def positive_frequency(cls, value):
        import pandas as pd

        try:
            if pd.tseries.frequencies.to_offset(value).n <= 0:
                raise ValueError("positive_frequency_required")
        except OverflowError as cause:
            raise ValueError("invalid_frequency") from cause
        return value

    def forecast(self, horizon: int):
        if type(horizon) is not int or horizon <= 0:
            raise ConfigError("ml.horizon", "positive_integer_required")
        import pandas as pd

        try:
            offset = pd.tseries.frequencies.to_offset(self.frequency)
            dates = pd.date_range(self.cutoff + offset, periods=horizon, freq=offset)
            return pd.DataFrame({"timestamp": dates, "prediction": [self.value] * horizon})
        except (ValueError, OverflowError, MemoryError) as cause:
            raise FrameworkError("RESOURCE_LIMIT", path="ml.horizon") from cause


def fit_naive(training, *, time_column: str, target: str, frequency: str) -> NaiveModel:
    import pandas as pd

    try:
        if not isinstance(training, pd.DataFrame) or training.empty:
            raise ValueError("training_frame_required")
        values = training[target]
        if (
            not (
                pd.api.types.is_integer_dtype(values.dtype)
                or pd.api.types.is_float_dtype(values.dtype)
            )
            or values.isna().any()
            or not values.map(math.isfinite).all()
        ):
            raise ValueError("finite_real_targets_required")
        last = values.iloc[-1]
        value = float(last)
        if pd.api.types.is_integer_dtype(values.dtype) and int(value) != int(last):
            raise ValueError("explicit_float_conversion_required")
        return NaiveModel(
            value=value,
            cutoff=training[time_column].iloc[-1],
            frequency=frequency,
            time_column=time_column,
            target=target,
        )
    except Exception as cause:
        raise FrameworkError("DATA_INVALID", path="ml.target") from cause
