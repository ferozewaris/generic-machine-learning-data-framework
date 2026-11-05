"""Versioned metadata contracts, independent of compute and model backends."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, ConfigDict, Field, JsonValue, model_validator

from gmldf.core.config import Engine, Name, Spec, Text
from gmldf.core.errors import ErrorInfo


def _safe_uri(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("credential_free_uri_required")
    if parsed.scheme in {"file", "models"}:
        valid = parsed.path.startswith("/") and not parsed.path.startswith("//")
        valid = valid and parsed.netloc in {"", "localhost"}
    else:
        valid = bool(parsed.scheme and parsed.hostname)
    if not valid or any(character.isspace() for character in value):
        raise ValueError("absolute_uri_required")
    return value


SafeURI = Annotated[Text, AfterValidator(_safe_uri)]
SchemaVersion = Annotated[int, Field(ge=1, le=1)]
Checksum = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class Manifest(Spec):
    model_config = ConfigDict(frozen=True)


class ColumnSpec(Manifest):
    name: Text
    dtype: Text
    nullable: bool = True


class DatasetRef(Manifest):
    id: Name
    engine: Engine
    columns: list[ColumnSpec]
    materialization: Literal["memory", "file", "table"]
    source_uri: SafeURI | None = None
    source_version: Text | None = None
    row_count: Annotated[int, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def unique_columns(self):
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("duplicate_column")
        return self


class ArtifactRef(Manifest):
    uri: SafeURI
    version: Text
    kind: Literal["model", "preprocessing", "report", "manifest", "predictions"]
    manifest_schema_version: SchemaVersion = 1
    checksum: Checksum
    producing_run_id: Name


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone_required")
    return value.astimezone(timezone.utc)


UTCTime = Annotated[datetime, AfterValidator(_utc)]


class FitData(Manifest):
    dataset_ids: Annotated[list[Name], Field(min_length=1)]
    row_count: Annotated[int, Field(ge=0)]
    source_versions: dict[str, Text] = Field(default_factory=dict)
    cutoff: UTCTime | None = None


class SearchDomain(Manifest):
    algorithm: Text
    defaults_version: Text
    domain: dict[str, JsonValue]


class CandidateRecord(Manifest):
    trial_id: Name
    algorithm: Text
    status: Literal["succeeded", "failed", "skipped"]
    parameters: dict[str, JsonValue]
    validation_score: float | None = None
    error: ErrorInfo | None = None


class Assessment(Manifest):
    model: ArtifactRef
    metric: Text
    greater_is_better: bool
    validation_score: float
    test_score: float | None = None


class TrainingResult(Manifest):
    schema_version: SchemaVersion = 1
    evaluated_model: ArtifactRef
    refit_model: ArtifactRef | None = None
    model: ArtifactRef
    assessment: Assessment
    candidates: Annotated[list[CandidateRecord], Field(min_length=1)]
    resolved_search: Annotated[list[SearchDomain], Field(min_length=1)]
    feature_signature: list[ColumnSpec]
    evaluated_fit: FitData
    refit_fit: FitData | None = None
    predictions: DatasetRef

    @model_validator(mode="after")
    def model_evidence(self):
        if self.assessment.model != self.evaluated_model:
            raise ValueError("assessment_model_mismatch")
        if (self.refit_model is None) != (self.refit_fit is None):
            raise ValueError("refit_provenance_required")
        if self.refit_model is not None and self.refit_model.uri == self.evaluated_model.uri:
            raise ValueError("distinct_refit_identity_required")
        expected = self.refit_model if self.refit_model is not None else self.evaluated_model
        if self.model != expected:
            raise ValueError("returned_model_mismatch")
        return self


class PredictionResult(Manifest):
    schema_version: SchemaVersion = 1
    model: ArtifactRef
    predictions: DatasetRef
