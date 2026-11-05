"""Stable public errors; exception causes are internal diagnostics only."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ErrorCode = Literal[
    "CONFIG_INVALID",
    "CAPABILITY_UNSUPPORTED",
    "POLICY_DENIED",
    "AUTH_FAILED",
    "DATA_INVALID",
    "RESOURCE_LIMIT",
    "EXECUTION_FAILED",
    "OUTPUT_INCOMPLETE",
]
RetrySafety = Literal["never", "safe", "unknown"]
MESSAGES = {
    "CONFIG_INVALID": "Configuration is invalid.",
    "CAPABILITY_UNSUPPORTED": "Requested capability is unavailable.",
    "POLICY_DENIED": "Policy denied the requested operation.",
    "AUTH_FAILED": "Authentication failed.",
    "DATA_INVALID": "Data does not match the declared contract.",
    "RESOURCE_LIMIT": "A configured resource limit was reached.",
    "EXECUTION_FAILED": "Execution failed.",
    "OUTPUT_INCOMPLETE": "Output publication did not complete.",
}


class ErrorInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, hide_input_in_errors=True)

    code: ErrorCode
    message: str
    path: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]+$", max_length=512)] | None = None
    stage_id: Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=128)] | None = (
        None
    )
    retry_safety: RetrySafety = "never"

    @model_validator(mode="before")
    @classmethod
    def safe_message(cls, values):
        if (
            isinstance(values, dict)
            and isinstance(values.get("code"), str)
            and values["code"] in MESSAGES
        ):
            expected = MESSAGES[values["code"]]
            if values.get("message", expected) != expected:
                raise ValueError("invalid_error_message")
            return {**values, "message": expected}
        return values


class FrameworkError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        *,
        path: str | None = None,
        stage_id: str | None = None,
        retry_safety: RetrySafety = "never",
    ):
        self.error = ErrorInfo(code=code, path=path, stage_id=stage_id, retry_safety=retry_safety)
        super().__init__(f"{self.error.code}: {self.error.message}")
