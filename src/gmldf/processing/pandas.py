"""Stateless named pandas select/cast/sort operations."""

import math
from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import Field

from gmldf.core.capabilities import Capability, CapabilityRegistry, CapabilityRequest
from gmldf.core.config import ConfigError, Spec, StepSpec, Text
from gmldf.core.errors import FrameworkError
from gmldf.core.types import DatasetRef, RunContext

DEPENDENCIES = {"pandas": "3.1.1", "numpy": "2.4.6", "python-dateutil": "4.0.0", "tzdata": "2026.6"}


class SelectParams(Spec):
    columns: Annotated[list[Text], Field(min_length=1)]


class CastParams(Spec):
    columns: Annotated[
        dict[str, Literal["string", "int64", "float64", "date", "timestamp"]], Field(min_length=1)
    ]
    date_formats: dict[str, Text] = Field(default_factory=dict)
    utc: bool = False


class SortParams(Spec):
    by: Annotated[list[Text], Field(min_length=1)]
    ascending: bool | list[bool] = True
    nulls: Literal["first", "last"] = "last"


def _select(frame, params):
    return frame.loc[:, params.columns].copy()


def _cast(frame, params):
    import pandas as pd

    result = frame.copy()
    for name, dtype in params.columns.items():
        series = result[name]
        if dtype == "string":
            result[name] = series.astype("string")
        elif dtype in {"int64", "float64"}:
            numeric = series.astype("Int64" if dtype == "int64" else "Float64")
            if not numeric.dropna().map(math.isfinite).all():
                raise ValueError("nonfinite_numeric_cast")
            result[name] = numeric
        else:
            converted = pd.to_datetime(
                series, format=params.date_formats[name], errors="raise", exact=True, utc=params.utc
            )
            if (converted.isna() & series.notna()).any():
                raise ValueError("undeclared_null")
            if (
                dtype == "date"
                and not converted.dropna().eq(converted.dropna().dt.normalize()).all()
            ):
                raise ValueError("non_midnight_date")
            result[name] = converted
    return result


def _sort(frame, params):
    return frame.sort_values(
        by=params.by, ascending=params.ascending, na_position=params.nulls, kind="stable"
    )


OPERATIONS = {
    "select": (SelectParams, _select),
    "cast": (CastParams, _cast),
    "sort": (SortParams, _sort),
}


class PandasEngine:
    capabilities = tuple(
        Capability(
            id=f"pandas_{name}",
            operation=name,
            engine="pandas",
            profile="local",
            status="verified",
            dependencies=DEPENDENCIES,
            install_extra="pandas",
        )
        for name in OPERATIONS
    )

    def _prepare_step(self, step: StepSpec, context: RunContext):
        CapabilityRegistry(self.capabilities).require(
            CapabilityRequest(operation=step.operation, engine="pandas", profile="local"),
            allowed=context.allowed_capabilities,
            path=f"steps.{step.id}.operation",
        )
        if len(step.inputs) != 1:
            raise ConfigError(f"steps.{step.id}.inputs", "single_named_input_required")
        params_model, operation = OPERATIONS[step.operation]
        try:
            params = params_model.model_validate(step.params)
            if isinstance(params, SelectParams) and len(params.columns) != len(set(params.columns)):
                raise ValueError("duplicate_columns")
            if isinstance(params, SortParams):
                if len(params.by) != len(set(params.by)):
                    raise ValueError("duplicate_sort_columns")
                if isinstance(params.ascending, list) and len(params.ascending) != len(params.by):
                    raise ValueError("sort_direction_count_mismatch")
            if isinstance(params, CastParams):
                dates = {
                    name for name, dtype in params.columns.items() if dtype in {"date", "timestamp"}
                }
                if set(params.date_formats) != dates:
                    raise ValueError("explicit_date_formats_required")
        except ValueError as cause:
            raise ConfigError(f"steps.{step.id}.params", "invalid_parameters") from cause
        return params, operation

    def validate_step(self, step: StepSpec, context: RunContext) -> None:
        self._prepare_step(step, context)

    def transform(
        self, dataset: DatasetRef, steps: Sequence[StepSpec], context: RunContext
    ) -> DatasetRef:
        if dataset.engine != "pandas":
            raise FrameworkError("CAPABILITY_UNSUPPORTED", path="dataset.engine")
        prepared = []
        current_id = dataset.id
        for step in steps:
            params, operation = self._prepare_step(step, context)
            if step.inputs != [current_id]:
                raise ConfigError(f"steps.{step.id}.inputs", "single_named_input_required")
            prepared.append((step, params, operation))
            current_id = step.id
        if not prepared:
            return dataset
        import pandas as pd

        if not isinstance(dataset.handle, pd.DataFrame):
            raise FrameworkError("DATA_INVALID", path="dataset.handle")
        frame = dataset.handle
        types = {column.name: column for column in dataset.columns}
        if list(frame.columns) != list(types):
            raise FrameworkError("DATA_INVALID", path="dataset.columns")
        for step, params, operation in prepared:
            try:
                frame = operation(frame, params)
            except Exception as cause:
                raise FrameworkError("DATA_INVALID", path=f"steps.{step.id}.params") from cause
            if step.operation == "cast":
                types.update(
                    {
                        name: types[name].model_copy(update={"dtype": dtype})
                        for name, dtype in params.columns.items()
                    }
                )
        return DatasetRef(
            id=current_id,
            engine="pandas",
            materialization="memory",
            columns=[types[name] for name in frame.columns],
            row_count=len(frame),
            source_uri=dataset.source_uri,
            source_version=dataset.source_version,
        ).with_handle(frame)
