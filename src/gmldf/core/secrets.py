"""Lazy credentials and controlled diagnostics for provider boundaries."""

import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from pydantic import JsonValue, ValidationError

from gmldf.core.config import MAX_CONFIG_BYTES, MAX_DEPTH, MAX_NODES, ConfigError, ConnectionSpec
from gmldf.core.errors import ErrorInfo, FrameworkError

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = (
    "password",
    "secret",
    "token",
    "credential",
    "privatekey",
    "apikey",
    "accesskey",
    "authorization",
    "cookie",
)


@dataclass(frozen=True)
class Secret:
    _value: str = field(repr=False)

    def reveal(self) -> str:
        return self._value


@dataclass(repr=False)
class Credentials:
    connection: ConnectionSpec
    resolver: Callable[[str], str] | None = None

    def resolve(self) -> dict[str, Secret]:
        resolved = {}
        for name, reference in self.connection.credential_refs.items():
            try:
                if self.resolver is None:
                    raise ValueError("credential_resolver_required")
                value = self.resolver(reference)
                if not isinstance(value, str) or not value:
                    raise ValueError("invalid_credential_value")
            except Exception as cause:
                raise FrameworkError("AUTH_FAILED", path="connections.credential_refs") from cause
            resolved[name] = Secret(value)
        return resolved


def public_error(error: BaseException) -> ErrorInfo:
    """Never stringify an external exception or follow its cause for public output."""
    if isinstance(error, FrameworkError):
        return error.error
    if isinstance(error, ConfigError):
        try:
            return ErrorInfo(code="CONFIG_INVALID", path=error.path)
        except ValidationError:
            return ErrorInfo(code="CONFIG_INVALID")
    return ErrorInfo(code="EXECUTION_FAILED")


def redact(value: object, *, secret_values: Iterable[str] = ()) -> JsonValue:
    """Bounded diagnostic copy; unknown objects are never stringified."""
    secrets = tuple(secret for secret in secret_values if secret)
    nodes = 0
    remaining = MAX_CONFIG_BYTES
    active = set()

    def text(value):
        nonlocal remaining
        if len(value) > MAX_CONFIG_BYTES:
            return REDACTED
        try:
            parsed = urlsplit(value)
        except ValueError:
            return REDACTED
        if (
            parsed.username is not None
            or parsed.query
            or parsed.fragment
            or (":/" in value and "@" in value)
        ):
            return REDACTED
        for secret in secrets:
            value = value.replace(secret, REDACTED)
        size = len(json.dumps(value).encode("utf-8"))
        if size > remaining:
            return REDACTED
        remaining -= size
        return value

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_NODES:
            return REDACTED
        if isinstance(item, (dict, list, tuple)):
            if id(item) in active:
                return REDACTED
            active.add(id(item))
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                if nodes >= MAX_NODES:
                    result[REDACTED] = REDACTED
                    break
                name = text(key) if isinstance(key, str) else REDACTED
                normalized = "".join(character for character in name.lower() if character.isalnum())
                sensitive = any(part in normalized for part in SENSITIVE_KEYS)
                result[name] = REDACTED if sensitive else visit(child, depth + 1)
                nodes += 1
            active.remove(id(item))
            return result
        if isinstance(item, (list, tuple)):
            result = []
            for child in item:
                if nodes >= MAX_NODES:
                    result.append(REDACTED)
                    break
                result.append(visit(child, depth + 1))
            active.remove(id(item))
            return result
        if isinstance(item, str):
            return text(item)
        if item is None or type(item) in (bool, int):
            return item
        if isinstance(item, float) and math.isfinite(item):
            return item
        return REDACTED

    result = visit(value, 0)
    try:
        return result if len(json.dumps(result).encode("utf-8")) <= MAX_CONFIG_BYTES else REDACTED
    except ValueError:
        return REDACTED
