"""Provider composition; execution adapters select concrete implementations."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from gmldf.core.capabilities import CapabilityRegistry, preflight
from gmldf.core.config import Connector, WorkflowSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.policy import Policy
from gmldf.core.types import RunContext
from gmldf.data_io.base import Reader, Writer
from gmldf.processing.base import ProcessingEngine


@dataclass(frozen=True)
class ProviderSet:
    readers: Mapping[Connector, Reader]
    writers: Mapping[Connector, Writer]
    processing: ProcessingEngine
    policy: Policy = field(default_factory=Policy)

    def __post_init__(self):
        object.__setattr__(self, "readers", MappingProxyType(dict(self.readers)))
        object.__setattr__(self, "writers", MappingProxyType(dict(self.writers)))

    def validate(self, config: WorkflowSpec, context: RunContext) -> None:
        for collection, mapping in (("sources", self.readers), ("outputs", self.writers)):
            for index, spec in enumerate(getattr(config, collection)):
                if spec.connector not in mapping:
                    raise FrameworkError(
                        "CAPABILITY_UNSUPPORTED", path=f"{collection}.{index}.connector"
                    )
        providers = {
            id(provider): provider
            for provider in (*self.readers.values(), *self.writers.values(), self.processing)
        }
        try:
            registry = CapabilityRegistry(
                capability
                for provider in providers.values()
                for capability in provider.capabilities
            )
        except ValueError as cause:
            raise FrameworkError("CONFIG_INVALID", path="providers") from cause
        preflight(config, context, registry, self.policy)
        for source in config.sources:
            self.readers[source.connector].validate(source, context)
        for step in config.steps:
            self.processing.validate_step(step, context)
        for output in config.outputs:
            self.writers[output.connector].validate(output, context)
