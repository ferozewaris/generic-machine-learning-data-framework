"""Shared fitted origin metadata and exact future timestamps for forecast candidates."""

from datetime import datetime

from pydantic import field_validator

from gmldf.core.config import ConfigError, Text
from gmldf.core.errors import FrameworkError
from gmldf.core.types import Manifest, UTCTime


class ForecastOrigin(Manifest):
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

    def future_dates(self, horizon: int):
        if type(horizon) is not int or horizon <= 0:
            raise ConfigError("ml.horizon", "positive_integer_required")
        import pandas as pd

        try:
            offset = pd.tseries.frequencies.to_offset(self.frequency)
            return pd.date_range(self.cutoff + offset, periods=horizon, freq=offset)
        except (ValueError, OverflowError, MemoryError) as cause:
            raise FrameworkError("RESOURCE_LIMIT", path="ml.horizon") from cause
