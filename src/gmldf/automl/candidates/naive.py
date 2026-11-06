"""Last-observation forecast state; fitting never receives holdout targets."""

import math

from gmldf.automl.candidates.origin import ForecastOrigin
from gmldf.core.errors import FrameworkError


class NaiveModel(ForecastOrigin):
    value: float

    def forecast(self, horizon: int):
        dates = self.future_dates(horizon)
        import pandas as pd

        try:
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
