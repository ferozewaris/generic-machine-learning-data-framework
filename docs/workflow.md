# Data workflow coordination

`gmldf.workflow.runner.run(config, context, providers)` executes a validated `WorkflowSpec` with a caller-owned `RunContext` and `ProviderSet`. The current runner supports `kind: data`; train/infer coordination remains pending.

Construct providers explicitly in the execution environment:

```python
from gmldf.data_io.csv import PandasCSVReader, PandasCSVWriter
from gmldf.processing.pandas import PandasEngine
from gmldf.workflow.providers import ProviderSet
from gmldf.workflow.runner import run

providers = ProviderSet(
    readers={"csv": PandasCSVReader()},
    writers={"csv": PandasCSVWriter()},
    processing=PandasEngine(),
)
result = run(config, context, providers)
print(result.model_dump_json(indent=2))
```

Install `.[pandas]` for this provider combination. Context capability IDs must authorize the exact configured operations; an empty list denies work. `ProviderSet` snapshots reader/writer mappings and accepts an optional core `Policy`.

The runner revalidates configuration and checks all capabilities, policy, and provider-specific options before source reads. Provider `validate` / `validate_step` methods perform configuration checks without opening business paths. Dataset-dependent column/value checks occur during execution. Preflight rejection raises a safe core error; execution failures return a failed `RunResult` with safe errors.

Sources execute in configuration order, steps in dependency order, then outputs in configuration order. Failed dependencies skip their consumers; independent branches continue. Stage IDs use collection indices (`source_0`, `step_0`, `output_0`) even when execution order differs from configuration order. Provider results must preserve the requested dataset identity and engine. No engine conversion or model-library import is performed by coordination.

Every output is mandatory. Success requires every stage and output to succeed. Completed receipts remain recorded when another output fails; outputs are independent commits. Both successful returns and `gmldf.data_io.base.WriteFailure` receipts must match the requested output ID and mode. An uncertain or uncommitted receipt makes the run fail. No automatic retry or resume occurs.

Direct workflow callers supply absolute paths, run identity, configuration digest and runtime metadata. [Local execution](local-execution.md) supplies config-relative path resolution, identity and exclusive run metadata. Stage progress events, cancellation/deadlines and recovery remain separate backlog tasks. Do not treat this runner as implementing those pending contracts.
