"""The small operation boundary; no dataframe facade or backend conversion."""

from collections.abc import Sequence
from typing import Protocol

from gmldf.core.config import StepSpec
from gmldf.core.types import DatasetRef, RunContext


class ProcessingEngine(Protocol):
    def transform(
        self, dataset: DatasetRef, steps: Sequence[StepSpec], context: RunContext
    ) -> DatasetRef: ...
