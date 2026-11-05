"""Schema-checked single-file Parquet for the pinned local pandas profile."""

import math
from pathlib import Path

from pydantic import ValidationError

from gmldf.core.capabilities import Capability, CapabilityRegistry, CapabilityRequest
from gmldf.core.config import ConfigError, SourceSpec, Spec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext
from gmldf.data_io.local_paths import local_path

PARQUET_READ = Capability(
    id="pandas_parquet_read",
    operation="read",
    engine="pandas",
    profile="local",
    connector="parquet",
    format="parquet",
    status="verified",
    install_extra="parquet",
    dependencies={
        "pandas": "3.1.1",
        "numpy": "2.4.6",
        "python-dateutil": "4.0.0",
        "tzdata": "2026.6",
        "pyarrow": "26.0.1",
    },
)
COLUMN_TYPES = {"string", "int64", "float64", "boolean", "decimal", "date", "timestamp"}


def _check_column(array, dtype):
    import pyarrow as pa

    checks = {
        "string": lambda t: pa.types.is_string(t) or pa.types.is_large_string(t),
        "int64": pa.types.is_int64,
        "float64": pa.types.is_float64,
        "boolean": pa.types.is_boolean,
        "decimal": pa.types.is_decimal,
        "date": pa.types.is_date,
        "timestamp": pa.types.is_timestamp,
    }
    if not pa.types.is_null(array.type) and not checks[dtype](array.type):
        raise ValueError("physical_type_mismatch")
    if dtype in {"float64", "decimal"}:
        for value in array.to_pylist():
            if value is not None and not (
                value.is_finite() if dtype == "decimal" else math.isfinite(value)
            ):
                raise ValueError("nonfinite_value")


def _pandas_type(dtype):
    import pandas as pd
    import pyarrow as pa

    return {
        pa.int64(): pd.Int64Dtype(),
        pa.float64(): pd.Float64Dtype(),
        pa.bool_(): pd.BooleanDtype(),
        pa.string(): pd.StringDtype(storage="python"),
        pa.large_string(): pd.StringDtype(storage="python"),
    }.get(dtype)


class PandasParquetReader:
    capabilities = (PARQUET_READ,)

    def _prepare(self, source: SourceSpec, context: RunContext) -> Path:
        prefix = f"sources.{source.id}"
        CapabilityRegistry(self.capabilities).require(
            CapabilityRequest(
                operation="read",
                engine="pandas",
                profile="local",
                connector=source.connector,
                format=source.format or "parquet",
            ),
            allowed=context.allowed_capabilities,
            path=f"{prefix}.connector",
        )
        try:
            Spec.model_validate(source.options)
        except ValidationError as cause:
            raise ConfigError(f"{prefix}.options", "invalid_parquet_options") from cause
        if not source.columns or any(
            not name or dtype not in COLUMN_TYPES for name, dtype in source.columns.items()
        ):
            raise ConfigError(f"{prefix}.columns", "explicit_supported_types_required")
        return local_path(source.location, prefix)

    def validate(self, source: SourceSpec, context: RunContext) -> None:
        self._prepare(source, context)

    def read(self, source: SourceSpec, context: RunContext) -> DatasetRef:
        path = self._prepare(source, context)
        import pandas as pd
        import pyarrow.parquet as pq

        try:
            if not path.is_file():
                raise FileNotFoundError("regular_file_required")
            with path.open("rb") as stream:
                table = pq.ParquetFile(stream).read(use_threads=False)
            if len(set(table.column_names)) != len(table.column_names) or set(
                table.column_names
            ) != set(source.columns):
                raise ValueError("schema_mismatch")
            for name, dtype in source.columns.items():
                _check_column(table[name], dtype)
            frame = table.to_pandas(
                ignore_metadata=True, date_as_object=False, types_mapper=_pandas_type
            )
            for name, dtype in source.columns.items():
                if dtype in {"string", "int64", "float64", "boolean"}:
                    frame[name] = frame[name].astype(
                        {
                            "string": pd.StringDtype(storage="python"),
                            "int64": "Int64",
                            "float64": "Float64",
                            "boolean": "boolean",
                        }[dtype]
                    )
                elif dtype in {"date", "timestamp"} and frame[name].dtype == object:
                    frame[name] = pd.to_datetime(frame[name], errors="raise")
        except Exception as cause:
            raise FrameworkError("DATA_INVALID", path=f"sources.{source.id}.columns") from cause
        return DatasetRef(
            id=source.id,
            engine="pandas",
            materialization="memory",
            columns=[ColumnSpec(name=name, dtype=source.columns[name]) for name in frame.columns],
            row_count=len(frame),
            source_uri=path.resolve().as_uri(),
            source_version=None,
        ).with_handle(frame)
