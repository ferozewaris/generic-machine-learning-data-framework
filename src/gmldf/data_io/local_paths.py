"""Format-independent validation of local file locations."""

from pathlib import Path
from urllib.parse import unquote, urlsplit

from gmldf.core.config import ConfigError


def local_path(location: str | None, path_prefix: str) -> Path:
    if location is None:
        raise ConfigError(f"{path_prefix}.location", "local_file_required")
    try:
        parsed = urlsplit(location)
    except ValueError as cause:
        raise ConfigError(f"{path_prefix}.location", "local_file_required") from cause
    if (
        parsed.scheme == "file"
        and parsed.netloc in {"", "localhost"}
        and not parsed.query
        and not parsed.fragment
    ):
        path = Path(unquote(parsed.path))
    elif parsed.scheme and not Path(location).drive:
        raise ConfigError(f"{path_prefix}.location", "local_file_required")
    else:
        path = Path(location)
    return path
