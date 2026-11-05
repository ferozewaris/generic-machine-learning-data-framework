from copy import deepcopy
from pathlib import Path

import pytest

from gmldf.core.config import ConfigError, load_config, validate_config


@pytest.fixture
def training():
    config = load_config(
        Path(__file__).parents[3] / "examples/validation/workflow.yaml"
    ).model_dump(exclude_unset=True)
    config.update(
        kind="train",
        ml={
            "task": "classification",
            "algorithms": [{"name": "sklearn.logistic_regression"}],
            "evaluation": {"metric": "accuracy"},
            "tuning": {"max_trials": 2, "timeout_seconds": 3.0},
        },
    )
    return config


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda c: c.pop("engine"), "engine"),
        (lambda c: c["ml"].pop("task"), "ml.task"),
        (lambda c: c["ml"]["evaluation"].pop("metric"), "ml.evaluation.metric"),
        (lambda c: c["ml"].update(algorithms=[]), "ml.algorithms"),
        (
            lambda c: c["ml"]["algorithms"].append({"name": "sklearn.logistic_regression"}),
            "ml.algorithms.1.name",
        ),
        (lambda c: c["ml"]["evaluation"].update(metric="silhouette"), "ml.evaluation.metric"),
        (
            lambda c: c["ml"]["evaluation"].update(greater_is_better=False),
            "ml.evaluation.greater_is_better",
        ),
        (
            lambda c: c["ml"].update(input_transfer={"enabled": True}),
            "ml.input_transfer.source_engine",
        ),
    ],
)
def test_explicit_intent_failures_have_exact_paths(training, change, path):
    change(training)
    with pytest.raises(ConfigError) as caught:
        validate_config(training)
    assert caught.value.path == path


def test_safe_defaults_preserve_only_explicit_candidates_and_do_not_mutate_input(training):
    original = deepcopy(training)
    ml = validate_config(training).ml
    assert ml.refit_on_all_data is False
    assert ml.input_transfer.enabled is False
    assert [candidate.name for candidate in ml.algorithms] == ["sklearn.logistic_regression"]
    assert training == original


@pytest.mark.parametrize(
    ("task", "metric", "direction"),
    [
        ("classification", "roc_auc", True),
        ("classification", "log_loss", False),
        ("regression", "r2", True),
        ("regression", "rmse", False),
        ("forecasting", "mae", False),
        ("clustering", "silhouette", True),
        ("clustering", "davies_bouldin", False),
    ],
)
def test_task_valid_metrics_preserve_explicit_direction(training, task, metric, direction):
    training["ml"].update(
        task=task,
        algorithms=[{"name": "explicit-provider-candidate"}],
        evaluation={"metric": metric, "greater_is_better": direction},
    )
    ml = validate_config(training).ml
    assert ml.task == task
    assert ml.evaluation.metric == metric
    assert ml.evaluation.greater_is_better == direction


def test_disabled_transfer_needs_no_route_or_bounds(training):
    training["ml"]["input_transfer"] = {"enabled": False}
    assert validate_config(training).ml.input_transfer.enabled is False


@pytest.mark.parametrize("field", ["target_engine", "max_rows", "max_bytes"])
def test_enabled_transfer_requires_every_bound_and_engine(training, field):
    transfer = {
        "enabled": True,
        "source_engine": "pandas",
        "target_engine": "spark",
        "max_rows": 2,
        "max_bytes": 100,
    }
    transfer.pop(field)
    training["ml"]["input_transfer"] = transfer
    with pytest.raises(ConfigError) as caught:
        validate_config(training)
    assert caught.value.path == f"ml.input_transfer.{field}"


def provider_context_and_declarations():
    from gmldf.core.capabilities import Capability
    from gmldf.core.types import RunContext, RunIdentity

    shared = {"engine": "pandas", "profile": "local", "status": "verified"}
    declarations = [
        Capability(**shared, id="input", operation="read", connector="csv", format="csv"),
        Capability(**shared, id="step", operation="select"),
        Capability(
            **shared,
            id="output",
            operation="write",
            connector="csv",
            format="csv",
            mode="error_if_exists",
        ),
        Capability(
            **shared,
            id="requested",
            operation="fit",
            task="classification",
            algorithm="sklearn.logistic_regression",
        ),
        Capability(
            **shared,
            id="unlisted",
            operation="fit",
            task="forecasting",
            algorithm="naive",
            dependencies={"unlisted-package": "1.0"},
            install_extra="forecasting",
        ),
    ]
    context = RunContext(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        allowed_capabilities=[item.id for item in declarations],
    )
    return context, declarations


@pytest.mark.parametrize(
    "changed_declaration",
    [
        {"algorithm": "different_algorithm"},
        {"task": "regression"},
        {"engine": "spark"},
    ],
)
def test_algorithm_task_engine_mismatch_rejects_at_candidate_path(training, changed_declaration):
    from gmldf.core.capabilities import CapabilityRegistry, preflight
    from gmldf.core.errors import FrameworkError
    from gmldf.core.policy import Policy

    context, declarations = provider_context_and_declarations()
    declarations[3] = declarations[3].model_copy(update=changed_declaration)
    with pytest.raises(FrameworkError) as caught:
        preflight(validate_config(training), context, CapabilityRegistry(declarations), Policy())
    assert caught.value.error.path == "ml.algorithms.0.name"
    assert caught.value.error.code == "CAPABILITY_UNSUPPORTED"


def test_registry_never_scans_or_adds_unlisted_candidates(training):
    from gmldf.core.capabilities import CapabilityRegistry, preflight
    from gmldf.core.policy import Policy

    context, declarations = provider_context_and_declarations()
    lookups = []
    registry = CapabilityRegistry(
        declarations, version_reader=lambda package: lookups.append(package) or "1.0"
    )
    result = preflight(validate_config(training), context, registry, Policy())
    assert [item.algorithm for item in result if item.operation == "fit"] == [
        "sklearn.logistic_regression"
    ]
    assert lookups == []
    assert training["ml"]["task"] == "classification"
    assert training["engine"] == "pandas"


def test_registry_does_not_substitute_algorithm_variants(training):
    from gmldf.core.capabilities import CapabilityRegistry, preflight
    from gmldf.core.errors import FrameworkError
    from gmldf.core.policy import Policy

    context, declarations = provider_context_and_declarations()
    declarations[3] = declarations[3].model_copy(update={"algorithm": "spark.logistic_regression"})
    with pytest.raises(FrameworkError) as caught:
        preflight(validate_config(training), context, CapabilityRegistry(declarations), Policy())
    assert caught.value.error.path == "ml.algorithms.0.name"


def test_enabled_transfer_requires_a_declared_route(training):
    from gmldf.core.capabilities import CapabilityRegistry, preflight
    from gmldf.core.errors import FrameworkError
    from gmldf.core.policy import Policy

    context, declarations = provider_context_and_declarations()
    declarations[3] = declarations[3].model_copy(update={"engine": "spark"})
    training["ml"]["input_transfer"] = {
        "enabled": True,
        "source_engine": "pandas",
        "target_engine": "spark",
        "max_rows": 2,
        "max_bytes": 100,
    }
    with pytest.raises(FrameworkError) as caught:
        preflight(validate_config(training), context, CapabilityRegistry(declarations), Policy())
    assert caught.value.error.path == "ml.input_transfer"
