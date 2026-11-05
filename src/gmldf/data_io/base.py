"""Provider-owned I/O contracts; native dataset handles remain process-local."""

from typing import Protocol

from gmldf.core.config import OutputSpec, SourceSpec
from gmldf.core.types import DatasetRef, RunContext, WriteReceipt


class Reader(Protocol):
    def read(self, source: SourceSpec, context: RunContext) -> DatasetRef: ...


class Writer(Protocol):
    def write(self, dataset: DatasetRef, sink: OutputSpec, context: RunContext) -> WriteReceipt: ...
