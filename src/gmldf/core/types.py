"""Versioned metadata contracts, independent of compute and model backends."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, ConfigDict, Field, JsonValue, PrivateAttr, model_validator

from gmldf.core.config import Engine, Name, Spec, Text
from gmldf.core.errors import ErrorInfo, RetrySafety


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
    _handle: object | None = PrivateAttr(default=None)

    @property
    def handle(self) -> object | None:
        return self._handle

    def with_handle(self, handle: object) -> "DatasetRef":
        bound = self.model_copy()
        bound._handle = handle
        return bound

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
    seed: int | None = None
    fit_count: Annotated[int, Field(ge=0)] | None = None
    duration_seconds: Annotated[float, Field(ge=0)] | None = None
    split_id: Checksum | None = None


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


class RunIdentity(Manifest):
    run_id: Name
    attempt_id: Name
    config_digest: Checksum
    code_version: Text
    environment: Annotated[dict[Text, Text], Field(min_length=1)]


class RunEvent(Manifest):
    stage_id: Name
    event: Literal["started", "succeeded", "failed", "skipped", "cancelled", "committed"]
    timestamp: UTCTime
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def outcome(self):
        if (self.event == "failed") != (self.error is not None):
            raise ValueError("event_error_mismatch")
        return self


class RunContext(Manifest):
    identity: RunIdentity
    artifact_root: SafeURI
    deadline: UTCTime | None = None
    allowed_capabilities: list[Name] = Field(default_factory=list)
    credential_resolver: Callable[[str], str] | None = Field(default=None, exclude=True, repr=False)
    cancelled: Callable[[], bool] | None = Field(default=None, exclude=True, repr=False)
    event_recorder: Callable[[RunEvent], None] | None = Field(
        default=None, exclude=True, repr=False
    )


class WriteReceipt(Manifest):
    output_id: Name
    destination: SafeURI
    mode: Literal["error_if_exists", "overwrite", "append", "upsert"]
    commit_status: Literal["committed", "not_committed", "unknown"]
    retry_safety: RetrySafety = "never"
    row_count: Annotated[int, Field(ge=0)] | None = None
    source_version: Text | None = None
    commit_id: Text | None = None

    @model_validator(mode="after")
    def retry_uncertainty(self):
        if self.commit_status == "unknown" and self.retry_safety == "safe":
            raise ValueError("unknown_commit_cannot_be_retry_safe")
        return self


class StageRecord(Manifest):
    stage_id: Name
    status: Literal["succeeded", "failed", "skipped", "cancelled"]
    started_at: UTCTime | None = None
    finished_at: UTCTime
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def outcome(self):
        if self.status != "skipped" and self.started_at is None:
            raise ValueError("stage_start_required")
        if self.started_at is not None and self.finished_at < self.started_at:
            raise ValueError("negative_duration")
        if (self.status == "failed") != (self.error is not None):
            raise ValueError("stage_error_mismatch")
        return self


class RunResult(Manifest):
    schema_version: SchemaVersion = 1
    identity: RunIdentity
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"]
    started_at: UTCTime | None = None
    finished_at: UTCTime | None = None
    reason: Literal["completed", "failed", "cancelled"] | None = None
    stages: list[StageRecord] = Field(default_factory=list)
    trials: list[CandidateRecord] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    writes: list[WriteReceipt] = Field(default_factory=list)
    errors: list[ErrorInfo] = Field(default_factory=list)

    @model_validator(mode="after")
    def outcome(self):
        terminal = self.status in {"succeeded", "failed", "cancelled"}
        if terminal:
            if self.started_at is None or self.finished_at is None or self.reason is None:
                raise ValueError("terminal_metadata_required")
            expected = "completed" if self.status == "succeeded" else self.status
            if self.reason != expected or self.finished_at < self.started_at:
                raise ValueError("invalid_terminal_metadata")
        elif self.finished_at is not None or self.reason is not None:
            raise ValueError("nonterminal_metadata_conflict")
        if self.status == "running" and self.started_at is None:
            raise ValueError("run_start_required")
        if (self.status == "failed") != bool(self.errors):
            raise ValueError("run_error_mismatch")
        if self.status == "succeeded" and (
            any(stage.status != "succeeded" for stage in self.stages)
            or any(write.commit_status != "committed" for write in self.writes)
        ):
            raise ValueError("incomplete_work_cannot_succeed")
        return self
