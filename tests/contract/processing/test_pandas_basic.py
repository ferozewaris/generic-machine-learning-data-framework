import pandas as pd
import pytest

from gmldf.core.config import ConfigError, StepSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.types import ColumnSpec, DatasetRef, RunContext, RunIdentity
from gmldf.processing.pandas import PandasEngine


@pytest.fixture
def context():
    return RunContext(
        identity=RunIdentity(
            run_id="run",
            attempt_id="attempt",
            config_digest="sha256:" + "a" * 64,
            code_version="test",
            environment={"python": "3.11"},
        ),
        artifact_root="file:///tmp/run",
        allowed_capabilities=["pandas_select", "pandas_cast", "pandas_sort"],
    )


def dataset(frame):
    return DatasetRef(
        id="raw",
        engine="pandas",
        materialization="memory",
        row_count=len(frame),
        columns=[ColumnSpec(name=name, dtype="string") for name in frame.columns],
    ).with_handle(frame)


def test_named_select_cast_sort_produces_expected_values_without_mutating_input(context):
    frame = pd.DataFrame(
        {
            "x": ["2", None, "1", "2"],
            "name": ["first", "missing", "low", "second"],
            "unused": [1, 2, 3, 4],
        }
    )
    original = frame.copy(deep=True)
    steps = [
        StepSpec(
            id="selected", operation="select", inputs=["raw"], params={"columns": ["x", "name"]}
        ),
        StepSpec(
            id="typed", operation="cast", inputs=["selected"], params={"columns": {"x": "int64"}}
        ),
        StepSpec(
            id="sorted", operation="sort", inputs=["typed"], params={"by": ["x"], "nulls": "last"}
        ),
    ]
    result = PandasEngine().transform(dataset(frame), steps, context)
    assert result.id == "sorted"
    assert result.row_count == 4
    assert list(result.handle.columns) == ["x", "name"]
    assert result.handle["name"].tolist() == ["low", "first", "second", "missing"]
    assert str(result.handle["x"].dtype) == "Int64"
    assert [column.dtype for column in result.columns] == ["int64", "string"]
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    "operation,params",
    [
        ("select", {"columns": ["x"]}),
        ("cast", {"columns": {"x": "float64"}}),
        ("sort", {"by": ["x"]}),
    ],
)
def test_empty_frames_preserve_declared_operations(context, operation, params):
    step = StepSpec(id="out", operation=operation, inputs=["raw"], params=params)
    result = PandasEngine().transform(
        dataset(pd.DataFrame({"x": pd.Series([], dtype="string")})), [step], context
    )
    assert result.row_count == 0
    assert list(result.handle.columns) == ["x"]


@pytest.mark.parametrize("params", [{"columns": {"x": "int64"}}, {"columns": {"x": "float64"}}])
def test_invalid_numeric_casts_fail_without_silent_coercion(context, params):
    step = StepSpec(id="out", operation="cast", inputs=["raw"], params=params)
    with pytest.raises(FrameworkError) as caught:
        PandasEngine().transform(dataset(pd.DataFrame({"x": ["not-a-number"]})), [step], context)
    assert caught.value.error.code == "DATA_INVALID"


def test_explicit_datetime_cast_and_sort_null_first(context):
    frame = pd.DataFrame({"when": ["2026-02-01", None, "2026-01-01"]})
    steps = [
        StepSpec(
            id="typed",
            operation="cast",
            inputs=["raw"],
            params={"columns": {"when": "timestamp"}, "date_formats": {"when": "%Y-%m-%d"}},
        ),
        StepSpec(
            id="ordered",
            operation="sort",
            inputs=["typed"],
            params={"by": ["when"], "nulls": "first"},
        ),
    ]
    result = PandasEngine().transform(dataset(frame), steps, context)
    assert result.handle["when"].isna().tolist() == [True, False, False]
    assert result.handle["when"].dt.strftime("%Y-%m-%d").dropna().tolist() == [
        "2026-01-01",
        "2026-02-01",
    ]


@pytest.mark.parametrize(
    "engine,handle", [("spark", object()), ("pandas", object()), ("pandas", None)]
)
def test_incompatible_engine_handles_are_rejected_without_conversion(context, engine, handle):
    ref = DatasetRef(id="raw", engine=engine, materialization="memory", columns=[]).with_handle(
        handle
    )
    step = StepSpec(id="out", operation="select", inputs=["raw"], params={"columns": ["x"]})
    with pytest.raises(FrameworkError):
        PandasEngine().transform(ref, [step], context)


def test_unknown_operation_and_wrong_named_input_fail(context):
    ref = dataset(pd.DataFrame({"x": [1]}))
    with pytest.raises(FrameworkError) as caught:
        PandasEngine().transform(
            ref,
            [
                StepSpec(
                    id="out",
                    operation="eval",
                    inputs=["raw"],
                    params={"code": "raise RuntimeError()"},
                )
            ],
            context,
        )
    assert caught.value.error.code == "CAPABILITY_UNSUPPORTED"
    with pytest.raises(ConfigError):
        PandasEngine().transform(
            ref,
            [
                StepSpec(
                    id="out", operation="select", inputs=["different"], params={"columns": ["x"]}
                )
            ],
            context,
        )


def test_multikey_stable_sort_has_explicit_directions_and_null_order(context):
    frame = pd.DataFrame(
        {
            "a": ["x", "x", "x", None, "x"],
            "b": ["2", "1", "2", "1", "2"],
            "id": ["first", "low", "second", "null", "third"],
        }
    )
    step = StepSpec(
        id="ordered",
        operation="sort",
        inputs=["raw"],
        params={"by": ["a", "b"], "ascending": [True, False], "nulls": "first"},
    )
    result = PandasEngine().transform(dataset(frame), [step], context)
    assert result.handle["id"].tolist() == ["null", "first", "second", "third", "low"]


@pytest.mark.parametrize(
    "params,error",
    [
        ({"by": ["x"], "ascending": [True, False]}, ConfigError),
        ({"by": ["x", "x"]}, ConfigError),
        ({"by": ["missing"]}, FrameworkError),
    ],
)
def test_invalid_sort_keys_and_direction_shapes_fail_safely(context, params, error):
    step = StepSpec(id="ordered", operation="sort", inputs=["raw"], params=params)
    with pytest.raises(error):
        PandasEngine().transform(dataset(pd.DataFrame({"x": ["a"]})), [step], context)


@pytest.mark.parametrize("value", ["1.5", "inf", "NaN", "nan"])
def test_numeric_cast_never_truncates_or_admits_nonfinite_values(context, value):
    dtype = "int64" if value == "1.5" else "float64"
    step = StepSpec(id="typed", operation="cast", inputs=["raw"], params={"columns": {"x": dtype}})
    with pytest.raises(FrameworkError):
        PandasEngine().transform(dataset(pd.DataFrame({"x": [value]})), [step], context)


@pytest.mark.parametrize("value", ["NaT", "", "2026-01-02 12:00"])
def test_temporal_cast_cannot_insert_nulls_or_truncate_time(context, value):
    step = StepSpec(
        id="typed",
        operation="cast",
        inputs=["raw"],
        params={"columns": {"x": "date"}, "date_formats": {"x": "%Y-%m-%d %H:%M"}},
    )
    with pytest.raises(FrameworkError):
        PandasEngine().transform(dataset(pd.DataFrame({"x": [value]})), [step], context)


def test_all_steps_are_authorized_before_any_step_runs(context):
    ref = dataset(pd.DataFrame({"x": ["a"]}))
    steps = [
        StepSpec(id="one", operation="cast", inputs=["raw"], params={"columns": {"x": "int64"}}),
        StepSpec(id="two", operation="sort", inputs=["one"], params={"by": ["x"]}),
    ]
    denied = context.model_copy(update={"allowed_capabilities": ["pandas_cast"]})
    with pytest.raises(FrameworkError) as caught:
        PandasEngine().transform(ref, steps, denied)
    assert caught.value.error.code == "POLICY_DENIED"


@pytest.mark.parametrize(
    "operation,params,inputs",
    [
        ("select", {"columns": ["x", "x"]}, ["raw"]),
        ("sort", {"by": ["x", "x"]}, ["raw"]),
        ("sort", {"by": ["x"], "ascending": []}, ["raw"]),
        ("cast", {"columns": {"x": "date"}}, ["raw"]),
        ("cast", {"columns": {"x": "string"}, "date_formats": {"x": "%Y"}}, ["raw"]),
        ("select", {"columns": ["x"]}, ["raw", "other"]),
    ],
)
def test_step_validation_rejects_intrinsic_errors_without_a_dataset(
    context, operation, params, inputs
):
    step = StepSpec(id="out", operation=operation, inputs=inputs, params=params)
    with pytest.raises(ConfigError) as caught:
        PandasEngine().validate_step(step, context)
    assert caught.value.path in {"steps.out.params", "steps.out.inputs"}


def test_step_validation_accepts_data_dependent_columns_and_enforces_policy(context):
    step = StepSpec(id="out", operation="select", inputs=["raw"], params={"columns": ["unknown"]})
    assert PandasEngine().validate_step(step, context) is None
    with pytest.raises(FrameworkError) as caught:
        PandasEngine().validate_step(step, context.model_copy(update={"allowed_capabilities": []}))
    assert caught.value.error.code == "POLICY_DENIED"
