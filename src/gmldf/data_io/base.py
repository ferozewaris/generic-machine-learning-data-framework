"""Provider-owned I/O contracts; native dataset handles remain process-local."""

from typing import Protocol

from gmldf.core.capabilities import Capability
from gmldf.core.config import OutputSpec, SourceSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import DatasetRef, RunContext, WriteReceipt


class Reader(Protocol):
    capabilities: tuple[Capability, ...]

    def validate(self, source: SourceSpec, context: RunContext) -> None: ...

    def read(self, source: SourceSpec, context: RunContext) -> DatasetRef: ...


class Writer(Protocol):
    capabilities: tuple[Capability, ...]

    def validate(self, sink: OutputSpec, context: RunContext) -> None: ...

    def write(self, dataset: DatasetRef, sink: OutputSpec, context: RunContext) -> WriteReceipt: ...


class WriteFailure(FrameworkError):
    def __init__(self, receipt: WriteReceipt):
        self.receipt = receipt
        super().__init__(
            "OUTPUT_INCOMPLETE",
            path=f"outputs.{receipt.output_id}",
            retry_safety=receipt.retry_safety,
        )
