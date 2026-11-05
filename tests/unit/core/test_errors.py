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
