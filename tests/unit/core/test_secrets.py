import json

import pytest

from gmldf.core.config import ConnectionSpec
from gmldf.core.errors import FrameworkError
from gmldf.core.secrets import Credentials, public_error, redact


def test_credential_values_resolve_only_at_explicit_access_and_hide_representations():
    calls = []
    credentials = Credentials(
        ConnectionSpec(credential_refs={"password": "warehouse_password"}),
        lambda ref: calls.append(ref) or "SENTINEL",
    )
    assert calls == []
    assert "warehouse_password" not in repr(credentials)
    values = credentials.resolve()
    assert calls == ["warehouse_password"]
    assert values["password"].reveal() == "SENTINEL"
    assert "SENTINEL" not in repr(values)
    assert "SENTINEL" not in str(values["password"])


@pytest.mark.parametrize("resolver", [None, lambda ref: "", lambda ref: 12])
def test_missing_or_invalid_credentials_fail_safely(resolver):
    credentials = Credentials(ConnectionSpec(credential_refs={"password": "pwd"}), resolver)
    with pytest.raises(FrameworkError) as caught:
        credentials.resolve()
    assert caught.value.error.code == "AUTH_FAILED"
    assert caught.value.error.retry_safety == "never"


def test_resolver_failure_retains_internal_cause_without_public_exception_chain():
    def fail(reference):
        raise RuntimeError("https://user:SENTINEL@host?token=SENTINEL")

    credentials = Credentials(ConnectionSpec(credential_refs={"token": "service_token"}), fail)
    with pytest.raises(FrameworkError) as caught:
        credentials.resolve()
    assert "SENTINEL" in str(caught.value.__cause__)
    payload = public_error(caught.value).model_dump_json()
    assert "SENTINEL" not in payload
    assert "SENTINEL" not in public_error(caught.value.__cause__).model_dump_json()


def test_public_diagnostics_redact_keys_urls_known_values_and_opaque_objects():
    value = {
        "password": "SENTINEL",
        "nested": [{"access_token": "SENTINEL"}],
        "source": "https://user:SENTINEL@host/file?sig=SENTINEL",
        "context": "SENTINEL",
        "opaque": object(),
        "version": "3.11",
        "count": 2,
    }
    payload = json.dumps(redact(value, secret_values=["SENTINEL"]))
    assert "SENTINEL" not in payload
    assert "3.11" in payload
    assert json.loads(payload)["count"] == 2
    assert value["password"] == "SENTINEL"


@pytest.mark.parametrize("key", ["apiKey", "Authorization", "Cookie", "aws_access_key_id"])
def test_sensitive_key_spelling_does_not_bypass_redaction(key):
    assert "SENTINEL" not in json.dumps(redact({key: "SENTINEL"}))


def test_recursive_and_nonfinite_diagnostics_are_bounded_and_json_safe():
    value = [float("nan")]
    value.append(value)
    result = redact(value)
    json.dumps(result, allow_nan=False)
    assert result == ["[REDACTED]", "[REDACTED]"]


@pytest.mark.parametrize(
    "uri",
    ["//user:SENTINEL@host/file", "file:/path?token=SENTINEL", "https:////user:SENTINEL@host/file"],
)
def test_non_authority_and_protocol_relative_uri_credentials_are_redacted(uri):
    assert "SENTINEL" not in json.dumps(redact({"source": uri}))


def test_diagnostic_aggregate_size_is_bounded():
    from gmldf.core.config import MAX_CONFIG_BYTES

    values = ["x" * (MAX_CONFIG_BYTES // 2)] * 10
    assert len(json.dumps(redact(values)).encode()) <= MAX_CONFIG_BYTES
