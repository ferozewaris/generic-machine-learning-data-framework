"""Native, explicitly parameterized ARIMA fitting on training observations only."""

import math
import warnings
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from gmldf.automl.candidates.origin import ForecastOrigin
from gmldf.core.config import ConfigError, Spec
from gmldf.core.errors import FrameworkError

Order = Annotated[int, Field(strict=True, ge=0, le=24)]
Difference = Annotated[int, Field(strict=True, ge=0, le=2)]


class ArimaParams(Spec):
    model_config = ConfigDict(frozen=True)

    order: Annotated[tuple[Order, Difference, Order], Field(strict=False)]
    trend: Literal["n", "c", "t", "ct"] = "n"
    enforce_stationarity: bool = True
    enforce_invertibility: bool = True
    maxiter: Annotated[int, Field(strict=True, ge=1, le=10000)] = 100

    @model_validator(mode="after")
    def compatible_trend(self):
        difference = self.order[1]
        if (difference > 0 and "c" in self.trend) or (difference > 1 and "t" in self.trend):
            raise ValueError("trend_must_survive_differencing")
        return self


class ArimaModel(ForecastOrigin):
    parameters: ArimaParams
    warning_count: Annotated[int, Field(strict=True, ge=0)]
    _results: Any = PrivateAttr(default=None)

    @property
    def results(self):
        return self._results

    def forecast(self, horizon: int):
        dates = self.future_dates(horizon)
        if self.results is None:
            raise FrameworkError("EXECUTION_FAILED", path="ml.model")
        import pandas as pd

        try:
            native = self.results.forecast(steps=horizon)
            if (
                len(native) != horizon
                or not (native.index == dates).all()
                or not all(math.isfinite(value) for value in native)
            ):
                raise ValueError("invalid_native_forecast")
            return pd.DataFrame({"timestamp": dates, "prediction": native.to_numpy(copy=True)})
        except Exception as cause:
            raise FrameworkError("EXECUTION_FAILED", path="ml.horizon") from cause


def fit_arima(
    training, *, time_column: str, target: str, frequency: str, parameters: dict
) -> ArimaModel:
    try:
        parameters = ArimaParams.model_validate(parameters)
    except ValidationError as cause:
        raise ConfigError("ml.algorithms.parameters", "invalid_arima_parameters") from cause
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
            or (
                pd.api.types.is_integer_dtype(values.dtype)
                and not values.map(lambda value: int(float(value)) == int(value)).all()
            )
        ):
            raise ValueError("finite_exact_real_targets_required")
        model = ArimaModel(
            cutoff=training[time_column].iloc[-1],
            frequency=frequency,
            time_column=time_column,
            target=target,
            parameters=parameters,
            warning_count=0,
        )
        index = pd.DatetimeIndex(training[time_column], freq=frequency)
        series = pd.Series(values.to_numpy(dtype=float, copy=True), index=index)
    except Exception as cause:
        raise FrameworkError("DATA_INVALID", path="ml.target") from cause

    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.arima.model import ARIMA

    try:
        with warnings.catch_warnings(record=True) as recorded:
            results = ARIMA(
                series,
                order=parameters.order,
                trend=parameters.trend,
                missing="raise",
                enforce_stationarity=parameters.enforce_stationarity,
                enforce_invertibility=parameters.enforce_invertibility,
            ).fit(
                method="statespace",
                method_kwargs={"maxiter": parameters.maxiter, "disp": False},
                cov_type="none",
            )
        if not results.mle_retvals.get("converged", False) or any(
            issubclass(warning.category, ConvergenceWarning) for warning in recorded
        ):
            raise ValueError("arima_did_not_converge")
        model = model.model_copy(update={"warning_count": len(recorded)})
        model._results = results
        return model
    except Exception as cause:
        raise FrameworkError("EXECUTION_FAILED", path="ml.algorithms") from cause
