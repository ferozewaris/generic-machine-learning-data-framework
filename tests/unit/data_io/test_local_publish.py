import os

import pytest

from gmldf.core.errors import FrameworkError
from gmldf.data_io.local_publish import WriteFailure, publish


def test_default_publication_preserves_existing_destination_and_cleans_temporary_files(tmp_path):
    destination = tmp_path / "output.csv"
    destination.write_bytes(b"old")
    with pytest.raises(WriteFailure) as caught:
        publish(destination, output_id="result", writer=lambda path: path.write_bytes(b"new"))
    assert destination.read_bytes() == b"old"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["output.csv"]
    assert caught.value.receipt.commit_status == "not_committed"
    assert caught.value.receipt.retry_safety == "never"


def test_explicit_overwrite_publishes_only_selected_destination_and_returns_commit_id(tmp_path):
    destination = tmp_path / "output.csv"
    other = tmp_path / "other.csv"
    destination.write_bytes(b"old")
    other.write_bytes(b"untouched")
    receipt = publish(
        destination,
        output_id="result",
        mode="overwrite",
        row_count=2,
        writer=lambda path: path.write_bytes(b"new"),
    )
    assert receipt.commit_status == "committed"
    assert receipt.retry_safety == "never"
    assert receipt.row_count == 2
    assert receipt.commit_id.startswith("sha256:")
    assert destination.read_bytes() == b"new"
    assert other.read_bytes() == b"untouched"


def test_failure_before_commit_keeps_old_destination_and_returns_safe_receipt(tmp_path):
    destination = tmp_path / "output.csv"
    destination.write_bytes(b"old")

    def fail(path):
        path.write_bytes(b"partial")
        raise RuntimeError("SENTINEL")

    with pytest.raises(WriteFailure) as caught:
        publish(destination, output_id="result", mode="overwrite", row_count=100, writer=fail)
    assert destination.read_bytes() == b"old"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["output.csv"]
    assert caught.value.receipt.commit_status == "not_committed"
    assert "SENTINEL" not in str(caught.value)
    assert "SENTINEL" not in caught.value.receipt.model_dump_json()
    assert str(caught.value.__cause__) == "SENTINEL"
    assert caught.value.receipt.row_count is None


def test_lost_commit_acknowledgement_is_unknown_and_never_retry_safe(tmp_path, monkeypatch):
    destination = tmp_path / "output.csv"
    original = os.replace

    def lose_ack(source, target):
        original(source, target)
        raise OSError("SENTINEL")

    monkeypatch.setattr(os, "replace", lose_ack)
    with pytest.raises(WriteFailure) as caught:
        publish(
            destination,
            output_id="result",
            mode="overwrite",
            row_count=100,
            writer=lambda path: path.write_bytes(b"new"),
        )
    assert destination.read_bytes() == b"new"
    assert caught.value.receipt.commit_status == "unknown"
    assert caught.value.receipt.retry_safety == "unknown"
    assert caught.value.receipt.row_count is None


@pytest.mark.parametrize("mode", ["append", "upsert"])
def test_unsupported_write_modes_make_no_output_or_temporary_files(tmp_path, mode):
    with pytest.raises(FrameworkError) as caught:
        publish(
            tmp_path / "out",
            output_id="result",
            mode=mode,
            writer=lambda path: path.write_bytes(b"bad"),
        )
    assert caught.value.error.code == "CAPABILITY_UNSUPPORTED"
    assert list(tmp_path.iterdir()) == []


def test_new_default_publication_has_private_permissions_and_exact_content_identity(tmp_path):
    import hashlib

    destination = tmp_path / "new.csv"
    receipt = publish(destination, output_id="result", writer=lambda path: path.write_bytes(b"new"))
    assert receipt.commit_status == "committed"
    assert receipt.commit_id == "sha256:" + hashlib.sha256(b"new").hexdigest()
    assert destination.read_bytes() == b"new"
    assert destination.stat().st_mode & 0o077 == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == ["new.csv"]


def test_default_publish_does_not_clobber_a_destination_created_during_staging(tmp_path):
    destination = tmp_path / "out.csv"

    def concurrent(path):
        path.write_bytes(b"ours")
        destination.write_bytes(b"concurrent")

    with pytest.raises(WriteFailure) as caught:
        publish(destination, output_id="result", writer=concurrent)
    assert destination.read_bytes() == b"concurrent"
    assert caught.value.receipt.commit_status == "not_committed"


def test_failure_after_known_commit_preserves_committed_receipt(tmp_path, monkeypatch):
    from contextlib import contextmanager

    from gmldf.data_io import local_publish

    original = local_publish.TemporaryDirectory

    @contextmanager
    def finalization_failure(**kwargs):
        with original(**kwargs) as temporary:
            yield temporary
        raise OSError("SENTINEL")

    monkeypatch.setattr(local_publish, "TemporaryDirectory", finalization_failure)
    destination = tmp_path / "out.csv"
    with pytest.raises(WriteFailure) as caught:
        publish(destination, output_id="result", writer=lambda path: path.write_bytes(b"new"))
    assert destination.read_bytes() == b"new"
    assert caught.value.receipt.commit_status == "committed"
    assert caught.value.receipt.commit_id.startswith("sha256:")
    assert caught.value.receipt.retry_safety == "never"
