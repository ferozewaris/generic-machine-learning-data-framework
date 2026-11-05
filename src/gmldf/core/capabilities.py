"""Exact declared capabilities and offline preflight; no backend imports or discovery."""

from collections.abc import Callable, Collection, Iterable
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from pydantic import Field, model_validator

from gmldf.core.config import ConfigError, Connector, Engine, Name, Text, WorkflowSpec
from gmldf.core.errors import DependencyHint, FrameworkError
from gmldf.core.policy import Policy
from gmldf.core.types import Manifest, RunContext


class CapabilityRequest(Manifest):
    operation: Name
    engine: Engine
    profile: Name
    connector: Connector | None = None
    format: Literal["csv", "parquet", "delta"] | None = None
    mode: Literal["error_if_exists", "overwrite", "append", "upsert"] | None = None
    task: Literal["classification", "regression", "forecasting", "clustering"] | None = None
    algorithm: Text | None = None
    target_engine: Engine | None = None

    def key(self) -> tuple:
        return tuple(getattr(self, name) for name in CapabilityRequest.model_fields)


class Capability(CapabilityRequest):
    id: Name
    status: Literal["planned", "verified", "unsupported"]
    dependencies: dict[Name, Text] = Field(default_factory=dict)
    install_extra: Name | None = None

    @model_validator(mode="after")
    def dependency_metadata(self):
        if self.dependencies and self.install_extra is None:
            raise ValueError("dependency_extra_required")
        for package, expected in self.dependencies.items():
            DependencyHint(
                package=package,
                expected_version=expected,
                install_extra=self.install_extra,
                reason="missing",
            )
        return self


class CapabilityRegistry:
    def __init__(
        self, declarations: Iterable[Capability], *, version_reader: Callable[[str], str] = version
    ):
        self._declarations = {}
        self._version_reader = version_reader
        ids = set()
        for declaration in declarations:
            if declaration.key() in self._declarations or declaration.id in ids:
                raise ValueError("duplicate_capability")
            self._declarations[declaration.key()] = declaration
            ids.add(declaration.id)

    def require(self, request: CapabilityRequest, *, allowed: Collection[str]) -> Capability:
        declaration = self._declarations.get(request.key())
        if declaration is None or declaration.status != "verified":
            raise FrameworkError("CAPABILITY_UNSUPPORTED", path="capabilities")
        if declaration.id not in allowed:
            raise FrameworkError("POLICY_DENIED", path="allowed_capabilities")
        for package, expected in declaration.dependencies.items():
            try:
                installed = self._version_reader(package)
            except PackageNotFoundError:
                reason = "missing"
            else:
                if installed == expected:
                    continue
                reason = "version_mismatch"
            hint = DependencyHint(
                package=package,
                expected_version=expected,
                install_extra=declaration.install_extra,
                reason=reason,
            )
            raise FrameworkError(
                "CAPABILITY_UNSUPPORTED", path=f"dependencies.{package}", dependency=hint
            )
        return declaration


def preflight(
    workflow: WorkflowSpec, context: RunContext, registry: CapabilityRegistry, policy: Policy
) -> tuple[Capability, ...]:
    transfer = workflow.ml.input_transfer if workflow.ml is not None else None
    training_engine = workflow.engine
    if transfer is not None and transfer.enabled:
        if transfer.source_engine != workflow.engine:
            raise ConfigError("ml.input_transfer.source_engine", "processing_engine_mismatch")
        training_engine = transfer.target_engine
    shared = {"engine": workflow.engine, "profile": workflow.execution.profile}
    requests = [
        CapabilityRequest(
            **shared,
            operation="read",
            connector=source.connector,
            format=source.format
            or (source.connector if source.connector in {"csv", "parquet", "delta"} else None),
        )
        for source in workflow.sources
    ]
    requests.extend(
        CapabilityRequest(**shared, operation=step.operation) for step in workflow.steps
    )
    requests.extend(
        CapabilityRequest(
            engine=training_engine if output.dataset == "ml.test_predictions" else workflow.engine,
            profile=workflow.execution.profile,
            operation="write",
            connector=output.connector,
            mode=output.mode,
            format=output.format
            or (output.connector if output.connector in {"csv", "parquet", "delta"} else None),
        )
        for output in workflow.outputs
    )
    if workflow.ml is not None:
        requests.extend(
            CapabilityRequest(
                engine=training_engine,
                profile=workflow.execution.profile,
                operation="fit",
                task=workflow.ml.task,
                algorithm=algorithm.name,
            )
            for algorithm in workflow.ml.algorithms
        )
        if transfer is not None and transfer.enabled:
            requests.append(
                CapabilityRequest(
                    operation="transfer",
                    engine=transfer.source_engine,
                    target_engine=transfer.target_engine,
                    profile=workflow.execution.profile,
                )
            )
    if workflow.model is not None:
        requests.append(CapabilityRequest(**shared, operation="predict"))
    policy.check(workflow, context, operations=[request.operation for request in requests])
    return tuple(
        registry.require(request, allowed=context.allowed_capabilities) for request in requests
    )
