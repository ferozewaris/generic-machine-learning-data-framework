"""Atomic single-file publication on a caller-provided local filesystem."""

import hashlib
import os
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from gmldf.core.errors import FrameworkError
from gmldf.core.types import WriteReceipt


class WriteFailure(FrameworkError):
    def __init__(self, receipt: WriteReceipt):
        self.receipt = receipt
        super().__init__(
            "OUTPUT_INCOMPLETE",
            path=f"outputs.{receipt.output_id}",
            retry_safety=receipt.retry_safety,
        )


def publish(
    destination: Path,
    *,
    output_id: str,
    writer: Callable[[Path], object],
    mode: Literal["error_if_exists", "overwrite", "append", "upsert"] = "error_if_exists",
    row_count: int | None = None,
) -> WriteReceipt:
    if mode not in {"error_if_exists", "overwrite"}:
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path=f"outputs.{output_id}.mode")
    destination = Path(os.path.abspath(destination))
    receipt = WriteReceipt(
        output_id=output_id,
        destination=destination.as_uri(),
        mode=mode,
        commit_status="not_committed",
        retry_safety="never",
        row_count=row_count,
    )
    attempted = False
    committed = False
    checksum = None
    try:
        with TemporaryDirectory(prefix=".gmldf-", dir=destination.parent) as temporary:
            staged = Path(temporary) / "output"
            staged.touch(mode=0o600, exist_ok=False)
            writer(staged)
            with staged.open("rb+") as stream:
                os.fsync(stream.fileno())
                checksum = "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()
            attempted = True
            if mode == "overwrite":
                os.replace(staged, destination)
            else:
                os.link(staged, destination)
            committed = True
    except Exception as cause:
        if committed:
            status, retry = "committed", "never"
        elif attempted and not (mode == "error_if_exists" and isinstance(cause, FileExistsError)):
            status, retry = "unknown", "unknown"
        else:
            status, retry = "not_committed", "never"
        failed = receipt.model_copy(
            update={
                "commit_status": status,
                "retry_safety": retry,
                "commit_id": checksum if committed else None,
                "row_count": receipt.row_count if committed else None,
            }
        )
        raise WriteFailure(failed) from cause
    return receipt.model_copy(update={"commit_status": "committed", "commit_id": checksum})
