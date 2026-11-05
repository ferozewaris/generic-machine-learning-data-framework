"""Provider-owned I/O contracts; native dataset handles remain process-local."""

from typing import Protocol

from gmldf.core.config import SourceSpec
from gmldf.core.types import DatasetRef, RunContext


class Reader(Protocol):
    def read(self, source: SourceSpec, context: RunContext) -> DatasetRef: ...
