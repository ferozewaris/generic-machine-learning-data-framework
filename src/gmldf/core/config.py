"""Offline, strict workflow configuration validation."""

import json
import math
from collections.abc import Mapping
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

MAX_CONFIG_BYTES = 1024 * 1024
MAX_DEPTH = 50
MAX_NODES = 20_000

Name = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=128)]
Text = Annotated[str, Field(min_length=1)]
Engine = Literal["spark", "pandas", "polars", "duckdb"]
Connector = Literal[
    "csv", "parquet", "s3", "sqlserver", "oracle", "databricks", "snowflake", "adls", "gcs", "delta"
]


class ConfigError(ValueError):
    """A config error that never includes the rejected input value."""

    code = "CONFIG_INVALID"

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


def _check_input(value: object) -> None:
    active = set()
    nodes = 0

    def visit(item, path, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES:
            raise ConfigError(path, "node_limit")
        if depth > MAX_DEPTH:
            raise ConfigError(path, "depth_limit")
        if isinstance(item, (dict, list)):
            if id(item) in active:
                raise ConfigError(path, "cyclic_structure")
            active.add(id(item))
            if isinstance(item, dict):
                for key, child in item.items():
                    if not isinstance(key, str):
                        raise ConfigError(path, "string_keys_required")
                    visit(key, path, depth + 1)
                    visit(child, f"{path}.{key}" if path else key, depth + 1)
            else:
                for index, child in enumerate(item):
                    visit(child, f"{path}.{index}", depth + 1)
            active.remove(id(item))
        elif isinstance(item, str):
            if len(item) > MAX_CONFIG_BYTES:
                raise ConfigError(path, "size_limit")
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise ConfigError(path, "finite_value_required")
        elif item is not None and type(item) not in (bool, int):
            raise ConfigError(path, "json_value_required")

    visit(value, "", 0)
    try:
        size = 0
        for chunk in json.JSONEncoder(ensure_ascii=False).iterencode(value):
            size += len(chunk.encode("utf-8"))
            if size > MAX_CONFIG_BYTES:
                raise ConfigError("document", "size_limit")
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, ConfigError):
            raise
        raise ConfigError("document", "invalid_json_value") from exc


class _ConfigLoader(yaml.SafeLoader):
    def __init__(self, stream):
        super().__init__(stream)
        self.depth = 0
        self.nodes = 0

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ConfigError("document", "yaml_alias_not_allowed")
        self.depth += 1
        self.nodes += 1
        if self.depth > MAX_DEPTH:
            raise ConfigError("document", "depth_limit")
        if self.nodes > MAX_NODES:
            raise ConfigError("document", "node_limit")
        try:
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            path = f"line:{key_node.start_mark.line + 1}"
            if not isinstance(key, str):
                raise ConfigError(path, "string_keys_required")
            if key in result:
                raise ConfigError(path, "duplicate_key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def load_config(path: str | Path) -> "WorkflowSpec":
    """Read a bounded UTF-8 YAML file and validate it without provider access."""
    try:
        with Path(path).open("rb") as stream:
            content = stream.read(MAX_CONFIG_BYTES + 1)
    except OSError as exc:
        raise ConfigError("document", "cannot_read_file") from exc
    if len(content) > MAX_CONFIG_BYTES:
        raise ConfigError("document", "size_limit")
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        raise ConfigError("document", "invalid_utf8") from exc
    try:
        config = yaml.load(text, Loader=_ConfigLoader)
    except ConfigError:
        raise
    except (yaml.YAMLError, ValueError, LookupError, AttributeError) as exc:
        # Scalar constructors can raise builtin errors containing raw input.
        mark = getattr(exc, "problem_mark", None)
        path = f"line:{mark.line + 1}" if mark is not None else "document"
        raise ConfigError(path, "invalid_yaml") from None
    return validate_config(config)


class Spec(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", hide_input_in_errors=True, allow_inf_nan=False
    )


class ExecutionSpec(Spec):
    profile: Name
    timeout_seconds: Annotated[float, Field(gt=0)] | None = None
    memory_bytes: Annotated[int, Field(gt=0)] | None = None


class ConnectionSpec(Spec):
    options: dict[str, JsonValue] = Field(default_factory=dict)
    credential_refs: dict[str, Name] = Field(default_factory=dict)


class SourceSpec(Spec):
    id: Name
    connector: Connector
    location: Text | None = None
    table: Text | None = None
    query: Text | None = None
    connection: Name | None = None
    format: Literal["csv", "parquet", "delta"] | None = None
    columns: dict[str, Text] = Field(default_factory=dict)
    options: dict[str, JsonValue] = Field(default_factory=dict)


class StepSpec(Spec):
    id: Name
    operation: Name
    inputs: Annotated[list[Name], Field(min_length=1)]
    params: dict[str, JsonValue] = Field(default_factory=dict)


class OutputSpec(Spec):
    id: Name
    dataset: Text
    connector: Connector
    location: Text | None = None
    table: Text | None = None
    connection: Name | None = None
    format: Literal["csv", "parquet", "delta"] | None = None
    mode: Literal["error_if_exists", "append", "overwrite", "upsert"] = "error_if_exists"
    options: dict[str, JsonValue] = Field(default_factory=dict)


class AlgorithmSpec(Spec):
    name: Text
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    search_space: dict[str, JsonValue] | None = None


class EvaluationSpec(Spec):
    metric: Text
    greater_is_better: bool | None = None


class TuningSpec(Spec):
    max_trials: Annotated[int, Field(gt=0)]
    timeout_seconds: Annotated[float, Field(gt=0)]
    seed: int | None = None


class TransferSpec(Spec):
    enabled: bool = False
    source_engine: Engine
    target_engine: Engine
    max_rows: Annotated[int, Field(gt=0)]
    max_bytes: Annotated[int, Field(gt=0)]


class MLSpec(Spec):
    task: Literal["classification", "regression", "forecasting", "clustering"]
    algorithms: Annotated[list[AlgorithmSpec], Field(min_length=1)]
    evaluation: EvaluationSpec
    tuning: TuningSpec
    target: Text | None = None
    features: list[Text] = Field(default_factory=list)
    time_column: Text | None = None
    group_columns: list[Text] = Field(default_factory=list)
    frequency: Text | None = None
    horizon: Annotated[int, Field(gt=0)] | None = None
    split: dict[str, JsonValue] = Field(default_factory=dict)
    refit_on_all_data: bool = False
    input_transfer: TransferSpec | None = None


class ModelSpec(Spec):
    uri: Text


class WorkflowSpec(Spec):
    schema_version: Literal[1]
    name: Text
    kind: Literal["data", "train", "infer"]
    engine: Engine
    execution: ExecutionSpec
    sources: Annotated[list[SourceSpec], Field(min_length=1)]
    steps: list[StepSpec]
    outputs: Annotated[list[OutputSpec], Field(min_length=1)]
    connections: dict[Name, ConnectionSpec] = Field(default_factory=dict)
    ml: MLSpec | None = None
    model: ModelSpec | None = None


def _validate_references(workflow: WorkflowSpec) -> None:
    ids = set()
    for collection in ("sources", "steps"):
        for index, item in enumerate(getattr(workflow, collection)):
            if item.id in ids:
                raise ConfigError(f"{collection}.{index}.id", "duplicate_id")
            ids.add(item.id)
    for index, step in enumerate(workflow.steps):
        for offset, name in enumerate(step.inputs):
            if name not in ids:
                raise ConfigError(f"steps.{index}.inputs.{offset}", "unknown_dataset")
    try:
        tuple(TopologicalSorter({step.id: step.inputs for step in workflow.steps}).static_order())
    except CycleError as exc:
        index = next(i for i, step in enumerate(workflow.steps) if step.id in exc.args[1])
        raise ConfigError(f"steps.{index}.inputs", "dependency_cycle") from exc

    artifact = {"train": "ml.test_predictions", "infer": "ml.predictions"}.get(workflow.kind)
    output_ids = set()
    for index, output in enumerate(workflow.outputs):
        if output.id in output_ids:
            raise ConfigError(f"outputs.{index}.id", "duplicate_id")
        output_ids.add(output.id)
        if output.dataset not in ids and output.dataset != artifact:
            raise ConfigError(f"outputs.{index}.dataset", "unknown_dataset")
    for collection in ("sources", "outputs"):
        for index, item in enumerate(getattr(workflow, collection)):
            targets = (item.location, item.table, getattr(item, "query", None))
            if sum(target is not None for target in targets) != 1:
                raise ConfigError(f"{collection}.{index}", "one_destination_required")
            if item.connection is not None and item.connection not in workflow.connections:
                raise ConfigError(f"{collection}.{index}.connection", "unknown_connection")


def validate_config(config: Mapping[str, object]) -> WorkflowSpec:
    """Validate config structure offline, without loading a data/ML provider."""
    if not isinstance(config, Mapping):
        raise ConfigError("document", "mapping_required")
    config = dict(config)
    _check_input(config)
    if "schema_version" in config and type(config["schema_version"]) is not int:
        raise ConfigError("schema_version", "integer_required")
    try:
        workflow = WorkflowSpec.model_validate(config)
    except ValidationError as exc:
        issue = exc.errors(include_input=False, include_context=False)[0]
        path = ".".join(str(part) for part in issue["loc"]) or "document"
        raise ConfigError(path, issue["type"]) from exc
    for kind, field in [("train", "ml"), ("infer", "model")]:
        if workflow.kind == kind and getattr(workflow, field) is None:
            raise ConfigError(field, "required_for_kind")
        if workflow.kind != kind and getattr(workflow, field) is not None:
            raise ConfigError(field, "not_allowed_for_kind")
    _validate_references(workflow)
    return workflow
