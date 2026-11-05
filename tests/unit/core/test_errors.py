import json

import pytest
from pydantic import ValidationError

from gmldf.core.errors import ErrorInfo, FrameworkError


def test_public_error_omits_internal_cause_and_uses_stable_message():
    try:
        try:
            raise ValueError("password=SENTINEL")
        except ValueError as cause:
            raise FrameworkError(
                "AUTH_FAILED", path="connections.warehouse", stage_id="source", retry_safety="never"
            ) from cause
    except FrameworkError as error:
        assert str(error.__cause__) == "password=SENTINEL"
        assert "SENTINEL" not in str(error)
        public = json.loads(error.error.model_dump_json())
        assert public == {
            "code": "AUTH_FAILED",
            "message": "Authentication failed.",
            "path": "connections.warehouse",
            "stage_id": "source",
            "retry_safety": "never",
        }
        assert ErrorInfo.model_validate_json(error.error.model_dump_json()) == error.error


@pytest.mark.parametrize(
    "values",
    [
        {"code": "arbitrary secret"},
        {"code": ["DATA_INVALID"]},
        {"code": "DATA_INVALID", "message": "secret"},
        {"code": "DATA_INVALID", "path": "https://user:password@host"},
        {"code": "DATA_INVALID", "retry_safety": "yes"},
    ],
)
def test_error_boundary_rejects_uncontrolled_public_fields(values):
    with pytest.raises(ValidationError):
        ErrorInfo(**values)


def test_optional_dependency_failure_has_safe_actionable_install_details():
    error = FrameworkError(
        "CAPABILITY_UNSUPPORTED",
        dependency={
            "package": "pandas",
            "expected_version": "3.0.0",
            "install_extra": "pandas",
            "reason": "missing",
        },
    )
    public = error.error.model_dump(mode="json")
    assert public["dependency"]["install_extra"] == "pandas"
    assert public["dependency"]["package"] == "pandas"
    assert ErrorInfo.model_validate_json(error.error.model_dump_json()) == error.error
    with pytest.raises(ValidationError):
        FrameworkError(
            "CAPABILITY_UNSUPPORTED",
            dependency={
                "package": "https://user:password@host",
                "expected_version": "3.0.0",
                "install_extra": "pandas",
                "reason": "missing",
            },
        )
