import json

import pytest
from pydantic import ValidationError

from gmldf.core.types import ArtifactRef, DatasetRef


def test_dataset_json_has_metadata_and_never_an_engine_handle():
    dataset = DatasetRef(
        id="raw",
        engine="pandas",
        columns=[{"name": "amount", "dtype": "decimal", "nullable": True}],
        materialization="memory",
        source_uri="file:///tmp/input.csv",
        source_version="sha256:abc",
        row_count=0,
    )
    payload = dataset.model_dump_json()
    assert json.loads(payload)["row_count"] == 0
    assert json.loads(payload)["columns"] == [
        {"name": "amount", "dtype": "decimal", "nullable": True}
    ]
    assert DatasetRef.model_validate_json(payload) == dataset
    with pytest.raises(ValidationError):
        DatasetRef(**{**dataset.model_dump(), "handle": object()})


def test_artifact_reference_preserves_immutable_identity():
    artifact = ArtifactRef(
        uri="file:///tmp/models/run-1/pipeline",
        version="1",
        kind="model",
        checksum="sha256:" + "a" * 64,
        producing_run_id="run-1",
    )
    assert artifact.manifest_schema_version == 1
    assert ArtifactRef.model_validate_json(artifact.model_dump_json()) == artifact
    for change in ({"checksum": "untrusted"}, {"version": ""}, {"manifest_schema_version": 2}):
        with pytest.raises(ValidationError):
            ArtifactRef(**{**artifact.model_dump(), **change})


@pytest.mark.parametrize(
    "uri",
    [
        "https://user:password@host/file",
        "s3://bucket/file?token=SENTINEL",
        "https://host/file#password",
        "https://[invalid",
        "",
    ],
)
def test_references_reject_locations_that_could_leak_credentials(uri):
    with pytest.raises(ValidationError):
        DatasetRef(id="raw", engine="pandas", columns=[], materialization="file", source_uri=uri)


def test_dataset_rejects_duplicate_columns_and_unknown_row_counts_are_explicit():
    dataset = DatasetRef(id="raw", engine="pandas", columns=[], materialization="memory")
    assert dataset.row_count is None
    with pytest.raises(ValidationError):
        DatasetRef(id="raw", engine="pandas", columns=[], materialization="memory", row_count=-1)
    with pytest.raises(ValidationError):
        DatasetRef(
            id="raw",
            engine="pandas",
            materialization="memory",
            columns=[{"name": "x", "dtype": "int64"}, {"name": "x", "dtype": "string"}],
        )


def artifact(version="evaluated"):
    return ArtifactRef(
        uri=f"file:///tmp/models/{version}",
        version=version,
        kind="model",
        checksum="sha256:" + "a" * 64,
        producing_run_id="train-1",
    )


def training_values():
    evaluated = artifact()
    return {
        "evaluated_model": evaluated,
        "model": evaluated,
        "assessment": {
            "model": evaluated,
            "metric": "mae",
            "greater_is_better": False,
            "validation_score": 0.2,
            "test_score": 0.3,
        },
        "candidates": [
            {
                "trial_id": "trial-1",
                "algorithm": "arima",
                "status": "succeeded",
                "parameters": {"p": 1},
                "validation_score": 0.2,
            }
        ],
        "resolved_search": [
            {
                "algorithm": "arima",
                "defaults_version": "1",
                "domain": {"p": [0, 1]},
            }
        ],
        "feature_signature": [{"name": "y", "dtype": "float64"}],
        "evaluated_fit": {
            "dataset_ids": ["train"],
            "row_count": 100,
            "cutoff": "2026-01-01T00:00:00Z",
        },
        "predictions": {
            "id": "predictions",
            "engine": "pandas",
            "columns": [],
            "materialization": "memory",
        },
    }


def test_training_json_preserves_evaluation_and_distinct_refit_provenance():
    from gmldf.core.types import TrainingResult

    values = training_values()
    evaluated = TrainingResult.model_validate_json(
        json.dumps(values, default=lambda x: x.model_dump(mode="json"))
    )
    assert evaluated.model == evaluated.evaluated_model
    assert evaluated.refit_model is None
    assert evaluated.assessment.greater_is_better is False
    assert evaluated.resolved_search[0].defaults_version == "1"
    assert TrainingResult.model_validate_json(evaluated.model_dump_json()) == evaluated
    values.update(
        refit_model=artifact("refit"),
        model=artifact("refit"),
        refit_fit={"dataset_ids": ["all"], "row_count": 140},
    )
    refitted = TrainingResult.model_validate_json(
        json.dumps(values, default=lambda x: x.model_dump(mode="json"))
    )
    assert refitted.assessment.model == refitted.evaluated_model
    assert refitted.model == refitted.refit_model
    assert refitted.refit_fit.row_count == 140
    assert refitted.evaluated_fit.row_count == 100


@pytest.mark.parametrize(
    "change",
    [
        {"model": artifact("other")},
        {"refit_model": artifact()},
        {"refit_model": artifact("refit")},
        {"refit_fit": {"dataset_ids": ["all"], "row_count": 140}},
        {
            "assessment": {
                "model": artifact("other"),
                "metric": "mae",
                "greater_is_better": False,
                "validation_score": 0.2,
            }
        },
    ],
)
def test_training_rejects_misattributed_model_evidence(change):
    from gmldf.core.types import TrainingResult

    with pytest.raises(ValidationError):
        TrainingResult.model_validate_json(
            json.dumps({**training_values(), **change}, default=lambda x: x.model_dump(mode="json"))
        )


def test_prediction_json_links_exact_model_and_output_without_model_handle():
    from gmldf.core.types import PredictionResult

    result = PredictionResult(
        model=artifact(),
        predictions=DatasetRef(id="p", engine="pandas", columns=[], materialization="memory"),
    )
    assert PredictionResult.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        PredictionResult(**{**result.model_dump(), "model_handle": object()})


@pytest.mark.parametrize(
    "uri", ["password=SENTINEL", "https:////user:password@host/file", "file:relative"]
)
def test_manifest_uris_require_a_valid_absolute_uri(uri):
    with pytest.raises(ValidationError):
        DatasetRef(id="raw", engine="pandas", columns=[], materialization="file", source_uri=uri)


@pytest.mark.parametrize("version", [True, 1.0, "1", 2])
def test_manifest_versions_require_integer_one(version):
    from gmldf.core.types import PredictionResult, TrainingResult

    with pytest.raises(ValidationError):
        ArtifactRef(**{**artifact().model_dump(), "manifest_schema_version": version})
    with pytest.raises(ValidationError):
        PredictionResult(
            model=artifact(),
            predictions=DatasetRef(id="p", engine="pandas", columns=[], materialization="memory"),
            schema_version=version,
        )
    with pytest.raises(ValidationError):
        TrainingResult.model_validate_json(
            json.dumps(
                {**training_values(), "schema_version": version},
                default=lambda x: x.model_dump(mode="json"),
            )
        )
