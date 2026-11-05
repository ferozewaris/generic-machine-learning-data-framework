"""Strict local CSV reads for the optional pandas backend."""

import csv
import io
import math
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field, ValidationError

from gmldf.core.capabilities import Capability, CapabilityRegistry, CapabilityRequest
from gmldf.core.config import ConfigError, SourceSpec, Spec, Text
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext

CSV_READ = Capability(
    id="pandas_csv_read",
    operation="read",
    engine="pandas",
    profile="local",
    connector="csv",
    format="csv",
    status="verified",
    install_extra="pandas",
    dependencies={
        "pandas": "3.1.1",
        "numpy": "2.4.6",
        "python-dateutil": "4.0.0",
        "tzdata": "2026.6",
    },
)
COLUMN_TYPES = {"string", "int64", "float64", "boolean", "decimal", "date", "timestamp"}


class CSVOptions(Spec):
    encoding: Text
    delimiter: Annotated[str, Field(min_length=1, max_length=1)]
    null_values: list[str]
    date_formats: dict[str, Text] = Field(default_factory=dict)
    decimal: Literal[".", ","] = "."
    utc: bool = False


def _cast(series, dtype, options):
    import pandas as pd

    if dtype == "string":
        return series
    if dtype in {"int64", "float64"}:
        result = series.str.replace(options.decimal, ".", regex=False).astype(
            "Int64" if dtype == "int64" else "Float64"
        )
        if not result.dropna().map(math.isfinite).all():
            raise ValueError("nonfinite_number")
        return result
    if dtype == "boolean":
        if not series.dropna().isin(["true", "false"]).all():
            raise ValueError("invalid_boolean")
        return series.map({"true": True, "false": False}).astype("boolean")
    if dtype == "decimal":

        def decimal(value):
            if pd.isna(value):
                return None
            number = Decimal(value.replace(options.decimal, "."))
            if not number.is_finite():
                raise ValueError("nonfinite_decimal")
            return number

        return series.map(decimal)
    result = pd.to_datetime(
        series,
        format=options.date_formats[series.name],
        errors="raise",
        exact=True,
        utc=options.utc,
    )
    if (result.isna() & series.notna()).any():
        raise ValueError("undeclared_null")
    if dtype == "date" and not result.dropna().eq(result.dropna().dt.normalize()).all():
        raise ValueError("non_midnight_date")
    return result


class PandasCSVReader:
    capability = CSV_READ

    def read(self, source: SourceSpec, context: RunContext) -> DatasetRef:
        path_prefix = f"sources.{source.id}"
        request = CapabilityRequest(
            operation="read",
            engine="pandas",
            profile="local",
            connector=source.connector,
            format=source.format or "csv",
        )
        CapabilityRegistry([self.capability]).require(
            request, allowed=context.allowed_capabilities, path=f"{path_prefix}.connector"
        )
        try:
            options = CSVOptions.model_validate(source.options)
        except ValidationError as cause:
            field = cause.errors(include_input=False, include_context=False)[0]["loc"][0]
            suffix = f".{field}" if field in CSVOptions.model_fields else ""
            raise ConfigError(f"{path_prefix}.options{suffix}", "invalid_csv_options") from cause
        try:
            io.TextIOWrapper(io.BytesIO(), encoding=options.encoding).close()
        except (LookupError, ValueError) as cause:
            raise ConfigError(f"{path_prefix}.options.encoding", "unsupported_encoding") from cause
        if options.delimiter in {"\n", "\r", "\0", '"'}:
            raise ConfigError(f"{path_prefix}.options.delimiter", "unsupported_delimiter")
        if not source.columns or any(
            not name or dtype not in COLUMN_TYPES for name, dtype in source.columns.items()
        ):
            raise ConfigError(f"{path_prefix}.columns", "explicit_supported_types_required")
        dates = {name for name, dtype in source.columns.items() if dtype in {"date", "timestamp"}}
        if set(options.date_formats) != dates:
            raise ConfigError(f"{path_prefix}.options.date_formats", "date_formats_required")
        if source.location is None:
            raise ConfigError(f"{path_prefix}.location", "local_file_required")
        try:
            parsed = urlsplit(source.location)
        except ValueError as cause:
            raise ConfigError(f"{path_prefix}.location", "local_file_required") from cause
        if (
            parsed.scheme == "file"
            and parsed.netloc in {"", "localhost"}
            and not parsed.query
            and not parsed.fragment
        ):
            path = Path(unquote(parsed.path))
        elif parsed.scheme and not Path(source.location).drive:
            raise ConfigError(f"{path_prefix}.location", "local_file_required")
        else:
            path = Path(source.location)
        import pandas as pd

        try:
            if not path.is_file():
                raise FileNotFoundError("regular_file_required")
            with path.open("r", encoding=options.encoding, newline="") as stream:
                rows = csv.reader(stream, delimiter=options.delimiter, strict=True)
                header = next(rows, [])
                if (
                    not header
                    or len(set(header)) != len(header)
                    or set(header) != set(source.columns)
                ):
                    raise FrameworkError("DATA_INVALID", path=f"{path_prefix}.columns")
                for row in rows:
                    if len(row) != len(header):
                        raise FrameworkError("DATA_INVALID", path=f"{path_prefix}.rows")
                stream.seek(0)
                frame = pd.read_csv(
                    stream,
                    sep=options.delimiter,
                    dtype="string",
                    keep_default_na=False,
                    na_values=options.null_values,
                    skip_blank_lines=False,
                    on_bad_lines="error",
                )
        except FrameworkError:
            raise
        except OSError as cause:
            raise FrameworkError("DATA_INVALID", path=f"{path_prefix}.location") from cause
        except (ValueError, csv.Error, UnicodeError) as cause:
            raise FrameworkError("DATA_INVALID", path=f"{path_prefix}.rows") from cause
        try:
            for column in frame.columns:
                frame[column] = _cast(frame[column], source.columns[column], options)
        except Exception as cause:
            raise FrameworkError("DATA_INVALID", path=f"{path_prefix}.columns") from cause
        return DatasetRef(
            id=source.id,
            engine="pandas",
            columns=[ColumnSpec(name=name, dtype=source.columns[name]) for name in frame.columns],
            materialization="memory",
            source_uri=path.resolve().as_uri(),
            source_version=None,
            row_count=len(frame),
        ).with_handle(frame)
