# Initial library implementation contract

Recorded 2026-11-05 for T001. Product scope remains the [confirmed intent](../intent/generic-data-ml-library.md).

- Distribution/import/CLI name: `gmldf`. Version `0.1.0a1` is an unpublished development version; package-name availability has not been established.
- Python: require 3.11 or newer; initially test CPython 3.11.18 on macOS arm64. Other versions/hosts need their own evidence.
- Configuration: Pydantic 2 with strict values, forbidden extra fields, and hidden input values in validation errors; PyYAML 6 SafeLoader with duplicate-key and alias rejection. These are core dependencies, not compute backends.
- Input limits: 1 MiB UTF-8 configuration, 50 container nesting levels, and 20,000 values/keys. Reject aliases rather than expanding shared or recursive YAML structures. The same structural limits apply to Python mappings.
- Schemas are versioned from integer `1`. Engine, task, candidate list, selection metric, trial limit, and deadline are explicit. ML config is required only for training; immutable model reference is required only for inference.
- Configuration validation is offline. It validates structure and references, not installed backend compatibility, credentials, live data, or model quality.
- All originally named connectors, engines, tasks, model integrations, and outputs remain first-release scope. No example dataset/metric/horizon becomes a product default.
- Evaluated/refitted model separation, explicit bounded transfer, and only-listed algorithm search remain unchanged. They are subsequent implementation tasks.

Remaining technical choices include backend/driver versions, provider parameter schemas, default tuning ranges, and tested external host profiles. Do not mark any of those verified from core validation tests.

Sources: [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Pydantic model configuration](https://docs.pydantic.dev/latest/api/config/), [PyYAML safe loading](https://pyyaml.org/wiki/PyYAMLDocumentation), and [standard Python package metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
