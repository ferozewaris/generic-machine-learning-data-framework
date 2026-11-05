"""The small operation boundary; no dataframe facade or backend conversion."""

from collections.abc import Sequence
from typing import Protocol

from gmldf.core.capabilities import Capability
from gmldf.core.config import StepSpec
from gmldf.core.types import DatasetRef, RunContext


class ProcessingEngine(Protocol):
    capabilities: tuple[Capability, ...]

    def validate_step(self, step: StepSpec, context: RunContext) -> None: ...

    def transform(
        self, dataset: DatasetRef, steps: Sequence[StepSpec], context: RunContext
    ) -> DatasetRef: ...
