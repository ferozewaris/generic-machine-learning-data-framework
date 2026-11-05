import logging
import traceback
from copy import deepcopy
from io import StringIO

import pytest

from gmldf.core.config import ConfigError, validate_config


@pytest.fixture
def config():
    return {
        "schema_version": 1,
        "name": "data-example",
        "kind": "data",
        "engine": "pandas",
        "execution": {"profile": "local"},
        "sources": [{"id": "raw", "connector": "csv", "location": "input.csv"}],
        "steps": [],
        "outputs": [{"id": "result", "dataset": "raw", "connector": "csv", "location": "out.csv"}],
    }


def test_valid_data_config_preserves_explicit_values_without_mutating_input(config):
    original = deepcopy(config)
    validated = validate_config(config)
    assert validated.name == "data-example"
    assert validated.engine == "pandas"
    assert validated.outputs[0].mode == "error_if_exists"
    assert config == original


@pytest.mark.parametrize("engine", ["spark", "pandas", "polars", "duckdb"])
def test_all_config_selected_engines_are_representable(config, engine):
    config["engine"] = engine
    assert validate_config(config).engine == engine


@pytest.mark.parametrize("field", ["engine", "sources", "outputs", "steps"])
def test_missing_root_fields_have_exact_paths(config, field):
    del config[field]
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == field
    assert error.value.code == "CONFIG_INVALID"


@pytest.mark.parametrize("version", [True, "1", 0, 2])
def test_schema_version_requires_integer_one(config, version):
    config["schema_version"] = version
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == "schema_version"


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda c: c.update(engine="auto"), "engine"),
        (lambda c: c.update(kind="unknown"), "kind"),
        (lambda c: c.update(password="SENTINEL_SECRET"), "password"),
        (lambda c: c["execution"].update(submit=True), "execution.submit"),
        (lambda c: c["sources"][0].update(unexpected="SENTINEL_SECRET"), "sources.0.unexpected"),
        (lambda c: c["sources"][0].update(id="bad id"), "sources.0.id"),
        (lambda c: c["sources"][0].update(connector="unknown"), "sources.0.connector"),
        (lambda c: c["outputs"][0].update(mode="delete"), "outputs.0.mode"),
    ],
)
def test_invalid_fields_are_rejected_without_echoing_values(config, change, path):
    change(config)
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == path
    assert "SENTINEL_SECRET" not in str(error.value)


@pytest.mark.parametrize("kind, required", [("train", "ml"), ("infer", "model")])
def test_kind_specific_config_is_required(config, kind, required):
    config["kind"] = kind
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == required


@pytest.mark.parametrize("task", ["classification", "regression", "forecasting", "clustering"])
def test_training_requires_explicit_user_intent(config, task):
    config["kind"] = "train"
    config["ml"] = {
        "task": task,
        "algorithms": [{"name": "user-selected-algorithm"}],
        "evaluation": {"metric": "user-selected-metric"},
        "tuning": {"max_trials": 8, "timeout_seconds": 300},
    }
    ml = validate_config(config).ml
    assert ml.task == task
    assert [algorithm.name for algorithm in ml.algorithms] == ["user-selected-algorithm"]
    assert ml.refit_on_all_data is False
    assert ml.input_transfer is None
    assert ml.algorithms[0].search_space is None


def test_inference_accepts_an_explicit_model_reference(config):
    config.update(kind="infer", model={"uri": "models/immutable-version"})
    assert validate_config(config).model.uri == "models/immutable-version"


def test_data_only_rejects_model_or_ml_options(config):
    config["model"] = {"uri": "models/unexpected"}
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == "model"


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda c: c["sources"].append(dict(c["sources"][0])), "sources.1.id"),
        (lambda c: c["sources"][0].pop("location"), "sources.0"),
        (lambda c: c["sources"][0].update(table="also_a_table"), "sources.0"),
        (lambda c: c["sources"][0].update(connection="missing"), "sources.0.connection"),
        (lambda c: c["outputs"][0].update(dataset="missing"), "outputs.0.dataset"),
        (lambda c: c["outputs"][0].update(dataset="ml.test_predictions"), "outputs.0.dataset"),
        (lambda c: c["outputs"].append(dict(c["outputs"][0])), "outputs.1.id"),
        (lambda c: c["outputs"][0].update(connection="missing"), "outputs.0.connection"),
    ],
)
def test_invalid_references_and_endpoints_have_exact_paths(config, change, path):
    change(config)
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == path


def test_forward_references_in_an_acyclic_graph_are_valid(config):
    config["steps"] = [
        {"id": "final", "operation": "select", "inputs": ["prepared"]},
        {"id": "prepared", "operation": "cast", "inputs": ["raw"]},
    ]
    config["outputs"][0]["dataset"] = "final"
    assert len(validate_config(config).steps) == 2


@pytest.mark.parametrize(
    ("steps", "path"),
    [
        ([{"id": "raw", "operation": "select", "inputs": ["raw"]}], "steps.0.id"),
        ([{"id": "one", "operation": "select", "inputs": ["missing"]}], "steps.0.inputs.0"),
        ([{"id": "one", "operation": "select", "inputs": ["one"]}], "steps.0.inputs"),
        (
            [
                {"id": "one", "operation": "select", "inputs": ["two"]},
                {"id": "two", "operation": "select", "inputs": ["one"]},
            ],
            "steps.0.inputs",
        ),
    ],
)
def test_invalid_graphs_are_rejected(config, steps, path):
    config["steps"] = steps
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == path


def test_python_mapping_size_and_container_cycles_are_bounded(config, monkeypatch):
    import gmldf.core.config as module

    config["sources"][0]["options"] = {"cycle": config}
    with pytest.raises(ConfigError, match="cyclic_structure"):
        validate_config(config)
    config["sources"][0]["options"] = {}
    monkeypatch.setattr(module, "MAX_CONFIG_BYTES", 100)
    with pytest.raises(ConfigError, match="size_limit"):
        validate_config(config)


def test_depth_and_node_limits_apply_to_python_values(config, monkeypatch):
    import gmldf.core.config as module

    monkeypatch.setattr(module, "MAX_DEPTH", 2)
    with pytest.raises(ConfigError, match="depth_limit"):
        validate_config(config)
    monkeypatch.setattr(module, "MAX_DEPTH", 50)
    monkeypatch.setattr(module, "MAX_NODES", 10)
    with pytest.raises(ConfigError, match="node_limit"):
        validate_config(config)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object()])
def test_parameters_must_be_finite_json_values(config, value):
    config["sources"][0]["options"] = {"value": value}
    with pytest.raises(ConfigError) as error:
        validate_config(config)
    assert error.value.path == "sources.0.options.value"


def test_validation_never_accesses_configured_data_or_network(config, monkeypatch):
    import socket
    from pathlib import Path

    def forbidden(*args, **kwargs):
        raise AssertionError("offline validation attempted I/O")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    config["sources"][0].update(connector="s3", location="s3://does-not-exist/data.csv")
    config["connections"] = {"unused": {"credential_refs": {"password": "absent-secret"}}}
    assert validate_config(config).sources[0].connector == "s3"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("name: one\nname: two\n", "duplicate_key"),
        ("!!python/object/apply:builtins.eval ['1 + 1']", "invalid_yaml"),
        ("name: [", "invalid_yaml"),
        ("shared: &a [1]\nalias: *a", "yaml_alias_not_allowed"),
        ("name: &a [*a]", "yaml_alias_not_allowed"),
        ("1: numeric_key", "string_keys_required"),
        ("[]", "mapping_required"),
        ("", "mapping_required"),
    ],
)
def test_unsafe_or_invalid_yaml_is_rejected(tmp_path, text, reason):
    from gmldf.core.config import load_config

    path = tmp_path / "workflow.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError) as error:
        load_config(path)
    assert error.value.reason == reason


def test_yaml_read_limit_is_enforced_before_parsing(tmp_path, monkeypatch):
    import gmldf.core.config as module

    monkeypatch.setattr(module, "MAX_CONFIG_BYTES", 20)
    path = tmp_path / "workflow.yaml"
    path.write_text("x" * 21)
    with pytest.raises(ConfigError, match="size_limit"):
        module.load_config(path)


def test_yaml_depth_and_node_limits_precede_construction(tmp_path, monkeypatch):
    import gmldf.core.config as module

    path = tmp_path / "workflow.yaml"
    monkeypatch.setattr(module, "MAX_DEPTH", 3)
    path.write_text("nested: " + "[" * 5 + "0" + "]" * 5)
    with pytest.raises(ConfigError, match="depth_limit"):
        module.load_config(path)
    monkeypatch.setattr(module, "MAX_DEPTH", 50)
    monkeypatch.setattr(module, "MAX_NODES", 5)
    path.write_text("values: [1, 2, 3, 4, 5]")
    with pytest.raises(ConfigError, match="node_limit"):
        module.load_config(path)


def test_yaml_loading_preserves_the_validated_config(tmp_path, config):
    import yaml

    from gmldf.core.config import load_config

    path = tmp_path / "workflow.yaml"
    path.write_text(yaml.safe_dump(config))
    assert load_config(path).model_dump() == validate_config(config).model_dump()


def test_read_and_encoding_errors_are_safe(tmp_path):
    from gmldf.core.config import load_config

    with pytest.raises(ConfigError, match="cannot_read_file"):
        load_config(tmp_path / "missing.yaml")
    path = tmp_path / "workflow.yaml"
    path.write_bytes(b"\xff")
    with pytest.raises(ConfigError, match="invalid_utf8"):
        load_config(path)


@pytest.mark.parametrize(
    "text",
    [
        "password: !!int ExamplePassword123\n",
        "password: !!bool ExamplePassword123\n",
        "password: !!float ExamplePassword123\n",
        "password: !!timestamp ExamplePassword123\n",
        "date: 2026-02-30\n",
        "value: !!int ''\n",
        "value: !!float ''\n",
        "password: [ExamplePassword123\n",
    ],
)
def test_yaml_failures_are_safe_in_python_tracebacks_and_logs(tmp_path, text):
    from gmldf.core.config import load_config

    path = tmp_path / "workflow.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError) as caught:
        load_config(path)
    error = caught.value
    assert error.code == "CONFIG_INVALID"
    assert error.reason == "invalid_yaml"
    assert error.path == "document" or error.path.startswith("line:")
    formatted = "".join(traceback.format_exception(error))
    assert "examplepassword123" not in formatted.casefold()
    assert "yaml.constructor" not in formatted

    output = StringIO()
    logger = logging.Logger("yaml-error-regression")
    logger.addHandler(logging.StreamHandler(output))
    logger.error("Invalid config", exc_info=(type(error), error, error.__traceback__))
    assert "examplepassword123" not in output.getvalue().casefold()
    assert "yaml.constructor" not in output.getvalue()
