"""Sequential dependency coordination through provider-owned contracts."""

from datetime import datetime, timezone
from graphlib import TopologicalSorter

from gmldf.core.config import WorkflowSpec, validate_config
from gmldf.core.errors import FrameworkError
from gmldf.core.secrets import public_error
from gmldf.core.types import DatasetRef, RunContext, RunResult, StageRecord, WriteReceipt
from gmldf.data_io.base import WriteFailure
from gmldf.workflow.providers import ProviderSet


def run(config: WorkflowSpec, context: RunContext, providers: ProviderSet) -> RunResult:
    config = validate_config(config.model_dump(exclude_unset=True))
    if config.kind != "data":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="kind")
    providers.validate(config, context)
    started = datetime.now(timezone.utc)
    datasets, stages, writes, errors = {}, [], [], []

    def execute(stage_id, dependencies, action, accept):
        if any(name not in datasets for name in dependencies):
            stages.append(
                StageRecord(
                    stage_id=stage_id, status="skipped", finished_at=datetime.now(timezone.utc)
                )
            )
            return
        stage_start = datetime.now(timezone.utc)
        error = None
        try:
            value = action()
            accept(value)
        except Exception as cause:
            error = public_error(cause).model_copy(update={"stage_id": stage_id})
            errors.append(error)
        stages.append(
            StageRecord(
                stage_id=stage_id,
                status="failed" if error else "succeeded",
                started_at=stage_start,
                finished_at=datetime.now(timezone.utc),
                error=error,
            )
        )

    def store(value, name):
        if not isinstance(value, DatasetRef) or value.id != name or value.engine != config.engine:
            raise FrameworkError("DATA_INVALID", path="dataset")
        datasets[name] = value

    for index, source in enumerate(config.sources):
        execute(
            f"source_{index}",
            [],
            lambda: providers.readers[source.connector].read(source, context),
            lambda value: store(value, source.id),
        )
    steps = {step.id: (index, step) for index, step in enumerate(config.steps)}
    for name in TopologicalSorter({step.id: step.inputs for step in config.steps}).static_order():
        if name not in steps:
            continue
        index, step = steps[name]
        execute(
            f"step_{index}",
            step.inputs,
            lambda: providers.processing.transform(datasets[step.inputs[0]], [step], context),
            lambda value: store(value, step.id),
        )

    def record_receipt(value, output):
        if (
            not isinstance(value, WriteReceipt)
            or value.output_id != output.id
            or value.mode != output.mode
        ):
            raise FrameworkError("OUTPUT_INCOMPLETE", path="outputs")
        writes.append(value)

    def receipt(value, output):
        record_receipt(value, output)
        if value.commit_status != "committed":
            raise FrameworkError(
                "OUTPUT_INCOMPLETE", path="outputs", retry_safety=value.retry_safety
            )

    def write(output):
        try:
            return providers.writers[output.connector].write(
                datasets[output.dataset], output, context
            )
        except WriteFailure as cause:
            record_receipt(cause.receipt, output)
            raise

    for index, output in enumerate(config.outputs):
        execute(
            f"output_{index}",
            [output.dataset],
            lambda: write(output),
            lambda value: receipt(value, output),
        )
    return RunResult(
        identity=context.identity,
        status="failed" if errors else "succeeded",
        reason="failed" if errors else "completed",
        started_at=started,
        finished_at=datetime.now(timezone.utc),
        stages=stages,
        writes=writes,
        errors=errors,
    )
