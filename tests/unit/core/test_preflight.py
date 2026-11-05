from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

from gmldf.core.capabilities import Capability, CapabilityRegistry, CapabilityRequest, preflight
from gmldf.core.config import load_config
from gmldf.core.errors import FrameworkError
from gmldf.core.policy import Policy
from gmldf.core.types import RunContext, RunIdentity


def declaration(id, operation, **values):
    if values.get("connector") in {"csv", "parquet", "delta"}:
        values.setdefault("format", values["connector"])
    return Capability(id=id, operation=operation, engine="pandas", profile="local", **values)


@pytest.fixture
def workflow():
    return load_config(Path(__file__).parents[3] / "examples/validation/workflow.yaml")


@pytest.fixture
def context():
    def forbidden(*args):
        raise AssertionError("credential or provider access during preflight")

    return RunContext(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        credential_resolver=forbidden,
        allowed_capabilities=["read_csv", "select", "write_csv"],
    )


def declarations():
    return [
        declaration("read_csv", "read", connector="csv", status="verified"),
        declaration("select", "select", status="verified"),
        declaration(
            "write_csv", "write", connector="csv", mode="error_if_exists", status="verified"
        ),
    ]


def test_preflight_matches_exact_declarations_without_data_or_credentials(workflow, context):
    registry = CapabilityRegistry(declarations())
    result = preflight(workflow, context, registry, Policy())
    assert [capability.id for capability in result] == ["read_csv", "select", "write_csv"]


@pytest.mark.parametrize("status", ["planned", "unsupported"])
def test_unverified_missing_and_wrong_combinations_reject(status):
    capability = declaration("read_csv", "read", connector="csv", status=status)
    registry = CapabilityRegistry([capability])
    request = CapabilityRequest(
        operation="read", engine="pandas", profile="local", connector="csv", format="csv"
    )
    with pytest.raises(FrameworkError) as caught:
        registry.require(request, allowed=["read_csv"])
    assert caught.value.error.code == "CAPABILITY_UNSUPPORTED"
    with pytest.raises(FrameworkError):
        CapabilityRegistry([]).require(request, allowed=["read_csv"])
    with pytest.raises(FrameworkError):
        CapabilityRegistry(declarations()).require(
            request.model_copy(update={"engine": "spark"}), allowed=["read_csv"]
        )


@pytest.mark.parametrize(
    "policy",
    [
        Policy(sources=[]),
        Policy(operations=[]),
        Policy(outputs=[]),
        Policy(profiles=[]),
        Policy(artifact_roots=[]),
    ],
)
def test_policy_denial_precedes_dependency_or_provider_access(workflow, context, policy):
    calls = []
    registry = CapabilityRegistry(
        declarations(), version_reader=lambda name: calls.append(name) or "1"
    )
    with pytest.raises(FrameworkError) as caught:
        preflight(workflow, context, registry, policy)
    assert caught.value.error.code == "POLICY_DENIED"
    assert calls == []


def test_empty_context_allowlist_denies_before_dependencies(workflow, context):
    registry = CapabilityRegistry(declarations())
    with pytest.raises(FrameworkError) as caught:
        preflight(
            workflow, context.model_copy(update={"allowed_capabilities": []}), registry, Policy()
        )
    assert caught.value.error.code == "POLICY_DENIED"


@pytest.mark.parametrize("installed", [None, "0.0"])
def test_missing_or_mismatched_dependencies_produce_install_guidance(installed):
    def version_reader(name):
        if installed is None:
            raise PackageNotFoundError(name)
        return installed

    registry = CapabilityRegistry(
        [
            declaration(
                "read_csv",
                "read",
                connector="csv",
                status="verified",
                dependencies={"pandas": "3.0.0"},
                install_extra="pandas",
            )
        ],
        version_reader=version_reader,
    )
    with pytest.raises(FrameworkError) as caught:
        registry.require(
            CapabilityRequest(
                operation="read", engine="pandas", profile="local", connector="csv", format="csv"
            ),
            allowed=["read_csv"],
        )
    hint = caught.value.error.dependency
    assert hint.package == "pandas"
    assert hint.expected_version == "3.0.0"
    assert hint.install_extra == "pandas"
    assert hint.reason == ("missing" if installed is None else "version_mismatch")


def test_duplicate_keys_do_not_silently_replace_a_capability():
    with pytest.raises(ValueError, match="duplicate_capability"):
        CapabilityRegistry([declarations()[0], declarations()[0]])


def test_capability_keys_distinguish_file_formats_and_match_exact_versions():
    registry = CapabilityRegistry(
        [
            Capability(
                id="s3_csv",
                operation="read",
                engine="pandas",
                profile="local",
                connector="s3",
                format="csv",
                status="verified",
                dependencies={"pandas": "3.0.0"},
                install_extra="pandas",
            )
        ],
        version_reader=lambda name: "3.0.0",
    )
    request = CapabilityRequest(
        operation="read", engine="pandas", profile="local", connector="s3", format="csv"
    )
    assert registry.require(request, allowed=["s3_csv"]).id == "s3_csv"
    with pytest.raises(FrameworkError):
        registry.require(request.model_copy(update={"format": "parquet"}), allowed=["s3_csv"])


def test_explicit_transfer_checks_training_on_target_engine_only(workflow, context):
    from gmldf.core.config import validate_config

    values = workflow.model_dump(exclude_unset=True)
    values.update(
        engine="spark",
        kind="train",
        ml={
            "task": "classification",
            "algorithms": [{"name": "random_forest"}],
            "evaluation": {"metric": "accuracy"},
            "tuning": {"max_trials": 1, "timeout_seconds": 1.0},
            "input_transfer": {
                "enabled": True,
                "source_engine": "spark",
                "target_engine": "pandas",
                "max_rows": 100,
                "max_bytes": 10000,
            },
        },
    )
    training = validate_config(values)
    capabilities = [item.model_copy(update={"engine": "spark"}) for item in declarations()]
    capabilities.extend(
        [
            declaration(
                "fit", "fit", task="classification", algorithm="random_forest", status="verified"
            ),
            Capability(
                id="transfer",
                operation="transfer",
                engine="spark",
                target_engine="pandas",
                profile="local",
                status="verified",
            ),
        ]
    )
    allowed = context.allowed_capabilities + ["fit", "transfer"]
    result = preflight(
        training,
        context.model_copy(update={"allowed_capabilities": allowed}),
        CapabilityRegistry(capabilities),
        Policy(),
    )
    assert next(item for item in result if item.id == "fit").engine == "pandas"


def test_operation_policy_covers_reads_and_writes_not_just_steps(workflow, context):
    with pytest.raises(FrameworkError) as caught:
        preflight(
            workflow, context, CapabilityRegistry(declarations()), Policy(operations=["select"])
        )
    assert caught.value.error.code == "POLICY_DENIED"


def test_transfer_source_must_match_processing_engine(workflow, context):
    from gmldf.core.config import ConfigError, validate_config

    values = workflow.model_dump(exclude_unset=True)
    values.update(
        kind="train",
        ml={
            "task": "classification",
            "algorithms": [{"name": "random_forest"}],
            "evaluation": {"metric": "accuracy"},
            "tuning": {"max_trials": 1, "timeout_seconds": 1.0},
            "input_transfer": {
                "enabled": True,
                "source_engine": "polars",
                "target_engine": "pandas",
                "max_rows": 100,
                "max_bytes": 10000,
            },
        },
    )
    with pytest.raises(ConfigError) as caught:
        preflight(validate_config(values), context, CapabilityRegistry([]), Policy())
    assert caught.value.path == "ml.input_transfer.source_engine"


def test_transferred_training_predictions_use_target_engine_writer(workflow, context):
    from gmldf.core.config import validate_config

    values = workflow.model_dump(exclude_unset=True)
    values.update(
        engine="spark",
        kind="train",
        ml={
            "task": "classification",
            "algorithms": [{"name": "random_forest"}],
            "evaluation": {"metric": "accuracy"},
            "tuning": {"max_trials": 1, "timeout_seconds": 1.0},
            "input_transfer": {
                "enabled": True,
                "source_engine": "spark",
                "target_engine": "pandas",
                "max_rows": 100,
                "max_bytes": 10000,
            },
        },
    )
    values["outputs"][0]["dataset"] = "ml.test_predictions"
    capabilities = [
        item.model_copy(update={"engine": "spark"})
        for item in declarations()
        if item.operation != "write"
    ]
    capabilities.extend(
        [
            declaration(
                "write_csv", "write", connector="csv", mode="error_if_exists", status="verified"
            ),
            declaration(
                "fit", "fit", task="classification", algorithm="random_forest", status="verified"
            ),
            Capability(
                id="transfer",
                operation="transfer",
                engine="spark",
                target_engine="pandas",
                profile="local",
                status="verified",
            ),
        ]
    )
    result = preflight(
        validate_config(values),
        context.model_copy(
            update={"allowed_capabilities": context.allowed_capabilities + ["fit", "transfer"]}
        ),
        CapabilityRegistry(capabilities),
        Policy(),
    )
    assert next(item for item in result if item.operation == "write").engine == "pandas"
