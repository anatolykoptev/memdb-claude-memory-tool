"""Path validation and normalization for the MemDB memory tool adapter."""

from __future__ import annotations

_MEMORIES_PREFIX = "/memories"
_MAX_KEY_LEN = 512


class PathError(ValueError):
    """Raised for invalid memory paths."""


def validate_path(path: str) -> str:
    """Validate and normalize a memory path.

    Rules:
    - Must start with /memories
    - No ``..`` segments
    - No ``~``
    - No NUL bytes
    - Total length <= 512 chars

    Returns the normalized path (trailing slash preserved for dirs).
    Raises PathError on violation.
    """
    if not path.startswith(_MEMORIES_PREFIX):
        raise PathError(f"Path must start with /memories, got: {path!r}")
    if "~" in path:
        raise PathError(f"Path must not contain ~: {path!r}")
    if "\x00" in path:
        raise PathError("Path must not contain NUL bytes")
    # Reject traversal attempts
    parts = path.split("/")
    for part in parts:
        if part == "..":
            raise PathError(f"Path must not contain '..': {path!r}")
    if len(path) > _MAX_KEY_LEN:
        raise PathError(f"Path length {len(path)} exceeds maximum of {_MAX_KEY_LEN}")
    return path


def is_directory_path(path: str) -> bool:
    """Return True if path looks like a directory (trailing slash or no extension)."""
    if path.endswith("/"):
        return True
    # No dot in the last segment → treat as directory
    last_segment = path.rstrip("/").rsplit("/", 1)[-1]
    return "." not in last_segment
