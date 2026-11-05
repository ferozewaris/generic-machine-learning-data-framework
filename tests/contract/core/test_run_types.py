import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from gmldf.core.errors import ErrorInfo
from gmldf.core.types import RunContext, RunIdentity, RunResult, WriteReceipt


def identity():
    return RunIdentity(
        run_id="run-1",
        attempt_id="attempt-1",
        config_digest="sha256:" + "a" * 64,
        code_version="commit-1",
        environment={"python": "3.11.18"},
    )


def test_context_serializes_identity_but_not_runtime_callbacks():
    sentinel = "SENTINEL"
    context = RunContext(
        identity=identity(),
        artifact_root="file:///tmp/runs/run-1",
        credential_resolver=lambda reference: sentinel,
        cancelled=lambda: False,
        event_recorder=lambda event: None,
        allowed_capabilities=["csv_read"],
    )
    payload = context.model_dump_json()
    assert "credential_resolver" not in payload
    assert "cancelled" not in payload
    assert "event_recorder" not in payload
    assert sentinel not in payload
    assert sentinel not in repr(context)
    restored = RunContext.model_validate_json(payload)
    assert restored.identity == context.identity
    assert restored.credential_resolver is None
    assert restored.allowed_capabilities == ["csv_read"]


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled"])
def test_terminal_runs_require_utc_times_and_safe_reason(status):
    start = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2)))
    values = {
        "identity": identity(),
        "status": status,
        "started_at": start,
        "finished_at": start + timedelta(seconds=2),
        "reason": "completed" if status == "succeeded" else status,
    }
    if status == "failed":
        values["errors"] = [ErrorInfo(code="EXECUTION_FAILED")]
    result = RunResult(**values)
    encoded = json.loads(result.model_dump_json())
    assert encoded["started_at"] == "2025-12-31T22:00:00Z"
    assert encoded["finished_at"] == "2025-12-31T22:00:02Z"
    assert RunResult.model_validate_json(result.model_dump_json()) == result
    for change in (
        {"finished_at": None},
        {"reason": None},
        {"started_at": start.replace(tzinfo=None)},
        {"finished_at": start - timedelta(seconds=1)},
    ):
        with pytest.raises(ValidationError):
            RunResult(**{**values, **change})


@pytest.mark.parametrize(
    "change",
    [
        {"status": "succeeded", "errors": [ErrorInfo(code="EXECUTION_FAILED")]},
        {"status": "failed", "errors": []},
        {"status": "running", "finished_at": datetime.now(timezone.utc)},
        {"status": "pending", "finished_at": datetime.now(timezone.utc)},
    ],
)
def test_run_states_cannot_claim_conflicting_outcomes(change):
    with pytest.raises(ValidationError):
        RunResult(identity=identity(), **change)


def test_write_receipt_preserves_commit_and_retry_uncertainty():
    receipt = WriteReceipt(
        output_id="out",
        destination="file:///tmp/output.csv",
        mode="error_if_exists",
        commit_status="unknown",
        retry_safety="unknown",
        row_count=None,
    )
    assert WriteReceipt.model_validate_json(receipt.model_dump_json()) == receipt
    with pytest.raises(ValidationError):
        WriteReceipt(**{**receipt.model_dump(), "retry_safety": "safe"})


@pytest.mark.parametrize("status", ["pending", "running"])
def test_nonterminal_run_forms_roundtrip(status):
    values = {"identity": identity(), "status": status}
    if status == "running":
        values["started_at"] = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = RunResult(**values)
    assert RunResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "change",
    [
        {"status": "succeeded", "started_at": None},
        {"finished_at": datetime(2025, 1, 1, tzinfo=timezone.utc)},
        {"status": "failed"},
        {"error": ErrorInfo(code="EXECUTION_FAILED")},
    ],
)
def test_stage_outcomes_reject_missing_start_negative_duration_or_wrong_error(change):
    from gmldf.core.types import StageRecord

    with pytest.raises(ValidationError):
        StageRecord(
            **{
                "stage_id": "read",
                "status": "succeeded",
                "started_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "finished_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                **change,
            }
        )


def test_completed_receipts_and_skipped_stages_survive_a_failed_run_roundtrip():
    from gmldf.core.types import StageRecord

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = RunResult(
        identity=identity(),
        status="failed",
        reason="failed",
        started_at=now,
        finished_at=now,
        errors=[ErrorInfo(code="OUTPUT_INCOMPLETE")],
        stages=[StageRecord(stage_id="dependent", status="skipped", finished_at=now)],
        writes=[
            WriteReceipt(
                output_id="saved",
                destination="file:///tmp/saved.csv",
                mode="error_if_exists",
                commit_status="committed",
                row_count=3,
            )
        ],
    )
    assert RunResult.model_validate_json(result.model_dump_json()) == result
    assert result.writes[0].row_count == 3
    with pytest.raises(ValidationError):
        RunResult(
            **{**result.model_dump(), "status": "succeeded", "reason": "completed", "errors": []}
        )


def test_write_receipt_records_output_commit_independently_of_source_version():
    receipt = WriteReceipt(
        output_id="out",
        destination="s3://bucket/output",
        mode="overwrite",
        commit_status="committed",
        source_version="input-v1",
        commit_id="output-v2",
    )
    restored = WriteReceipt.model_validate_json(receipt.model_dump_json())
    assert restored.commit_id == "output-v2"
    assert restored.source_version == "input-v1"


@pytest.mark.parametrize(
    "change",
    [{"event": "failed"}, {"event": "succeeded", "error": ErrorInfo(code="EXECUTION_FAILED")}],
)
def test_event_error_matches_outcome(change):
    from gmldf.core.types import RunEvent

    with pytest.raises(ValidationError):
        RunEvent(stage_id="read", timestamp=datetime.now(timezone.utc), **change)
