"""Explicit allowlists checked before provider access; platform IAM remains authoritative."""

from collections.abc import Iterable

from gmldf.core.config import Name, WorkflowSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import Manifest, RunContext, SafeURI


class Policy(Manifest):
    sources: list[Name] | None = None
    operations: list[Name] | None = None
    outputs: list[Name] | None = None
    profiles: list[Name] | None = None
    artifact_roots: list[SafeURI] | None = None
    output_ids: list[Name] | None = None

    def check(
        self, workflow: WorkflowSpec, context: RunContext, *, operations: Iterable[str]
    ) -> None:
        checks = [
            (self.profiles, workflow.execution.profile, "execution.profile"),
            (self.artifact_roots, context.artifact_root, "artifact_root"),
        ]
        checks.extend(
            (self.sources, source.connector, f"sources.{index}.connector")
            for index, source in enumerate(workflow.sources)
        )
        checks.extend((self.operations, operation, "operations") for operation in operations)
        checks.extend(
            (self.outputs, output.connector, f"outputs.{index}.connector")
            for index, output in enumerate(workflow.outputs)
        )
        checks.extend(
            (self.output_ids, output.id, f"outputs.{index}.id")
            for index, output in enumerate(workflow.outputs)
        )
        for allowed, value, path in checks:
            if allowed is not None and value not in allowed:
                raise FrameworkError("POLICY_DENIED", path=path)
