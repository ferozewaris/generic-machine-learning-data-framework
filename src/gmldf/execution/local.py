"""Current-process local invocation and exclusive run metadata ownership."""

import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from pydantic import ValidationError

from gmldf.core.config import ConfigError, load_config, validate_config
from gmldf.core.errors import FrameworkError
from gmldf.core.secrets import redact
from gmldf.core.types import RunContext, RunIdentity, RunResult
from gmldf.data_io.local_publish import publish
from gmldf.workflow.providers import ProviderSet
from gmldf.workflow.runner import run


def _providers(config) -> ProviderSet:
    if config.engine != "pandas":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="engine")
    from gmldf.data_io.csv import PandasCSVReader, PandasCSVWriter
    from gmldf.processing.pandas import PandasEngine

    return ProviderSet(
        readers={"csv": PandasCSVReader()},
        writers={"csv": PandasCSVWriter()},
        processing=PandasEngine(),
    )


def run_local(
    config_path: Path, *, profile: str | None = None, run_id: str, output_dir: Path
) -> RunResult:
    config_path = Path(config_path).absolute()
    config = load_config(config_path).model_dump(exclude_unset=True)
    if profile is not None:
        config["execution"]["profile"] = profile
    for collection in ("sources", "outputs"):
        for index, spec in enumerate(config[collection]):
            location = spec.get("location")
            if location is not None:
                try:
                    uri = urlsplit(location)
                except ValueError as cause:
                    raise ConfigError(
                        f"{collection}.{index}.location", "invalid_location"
                    ) from cause
                if not uri.scheme:
                    spec["location"] = str((config_path.parent / location).absolute())
                elif (
                    uri.scheme == "file"
                    and uri.netloc in {"", "localhost"}
                    and not uri.query
                    and not uri.fragment
                ):
                    path = Path(unquote(uri.path))
                    if not path.is_absolute():
                        spec["location"] = (config_path.parent / path).absolute().as_uri()
    workflow = validate_config(config)
    if workflow.kind != "data":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="kind")
    providers = _providers(workflow)
    root = (config_path.parent / output_dir).absolute()
    digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(redact(config), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    try:
        identity = RunIdentity(
            run_id=run_id,
            attempt_id="attempt_" + uuid4().hex,
            config_digest=digest,
            code_version=version("gmldf"),
            environment={
                "python": platform.python_version(),
                "platform": platform.platform(),
                "pydantic": version("pydantic"),
                "PyYAML": version("PyYAML"),
            },
        )
    except ValidationError as cause:
        raise ConfigError("run_id", "invalid_run_id") from cause
    folder = root / identity.run_id
    context = RunContext(
        identity=identity,
        artifact_root=folder.as_uri(),
        allowed_capabilities=[
            c.id
            for p in (
                *providers.readers.values(),
                *providers.writers.values(),
                providers.processing,
            )
            for c in p.capabilities
        ],
    )
    providers.validate(workflow, context)
    environment = dict(identity.environment)
    for provider in (
        *providers.readers.values(),
        *providers.writers.values(),
        providers.processing,
    ):
        for capability in provider.capabilities:
            environment.update({package: version(package) for package in capability.dependencies})
    identity = identity.model_copy(update={"environment": environment})
    context = context.model_copy(update={"identity": identity})
    reserved = {(folder / name).resolve() for name in ("identity.json", "result.json")}
    for collection in ("sources", "outputs"):
        for index, spec in enumerate(getattr(workflow, collection)):
            if spec.location is not None:
                uri = urlsplit(spec.location)
                path = Path(unquote(uri.path)) if uri.scheme == "file" else Path(spec.location)
                if path.resolve() in reserved:
                    raise ConfigError(f"{collection}.{index}.location", "reserved_run_metadata")
    try:
        root.mkdir(parents=True, exist_ok=True)
        folder.mkdir()
    except FileExistsError as cause:
        raise ConfigError("run_id", "run_already_reserved") from cause
    except OSError as cause:
        raise FrameworkError("OUTPUT_INCOMPLETE", path="output_dir") from cause

    def persist(name, content):
        publish(
            folder / name,
            output_id="run_metadata",
            writer=lambda path: path.write_text(content, encoding="utf-8"),
        )

    persist("identity.json", identity.model_dump_json(indent=2) + "\n")
    result = run(workflow, context, providers)
    persist("result.json", result.model_dump_json(indent=2) + "\n")
    return result


def exit_code(result: RunResult) -> int:
    return {"succeeded": 0, "failed": 1, "cancelled": 130}.get(result.status, 1)
