"""
Shared utilities for sup CLI.
"""

import re
from pathlib import Path

import yaml

# Jinja2 escaping markers — centralized so changes propagate everywhere
JINJA2_OPEN_MARKER = "__JINJA2_OPEN__"
JINJA2_CLOSE_MARKER = "__JINJA2_CLOSE__"
JINJA2_OPEN_PATTERN = r"\{\{"
JINJA2_CLOSE_PATTERN = r"\}\}"


def remove_root(file_name: str) -> str:
    """Strip the first path component from a ZIP entry name.

    Superset export ZIPs wrap everything under a ``bundle/`` root directory.
    This helper removes that prefix so files land in the desired output
    directory without the extra nesting.

    Raises ``ValueError`` for absolute paths, which should never appear in a
    well-formed Superset export ZIP and would otherwise silently produce
    unexpected output paths.
    """
    p = Path(file_name)
    if p.is_absolute():
        raise ValueError(f"Absolute path in ZIP entry is not allowed: {file_name!r}")
    parts = p.parts
    return str(Path(*parts[1:])) if len(parts) > 1 else file_name


def safe_extract_path(base: Path, relative: str) -> Path:
    """Resolve *relative* under *base* and verify it stays within *base*.

    Raises ``ValueError`` if the resolved path escapes the base directory
    (e.g. via ``../`` components), preventing path-traversal attacks when
    extracting ZIP archives.
    """
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError(f"Path traversal detected: {relative!r} escapes {base}")
    return target


def escape_jinja(content: str) -> str:
    """Escape Jinja2 templates in YAML content.

    Replaces {{ and }} with safe markers so templates don't interfere
    with Jinja2 processing during import/push operations.
    """
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            data = _traverse_escape(data)
            return yaml.dump(data, sort_keys=False)
    except yaml.YAMLError:
        pass
    return content


def _traverse_escape(value):
    """Recursively escape Jinja2 markers in data structures."""
    if isinstance(value, dict):
        return {k: _traverse_escape(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_traverse_escape(item) for item in value]
    elif isinstance(value, str):
        value = re.sub(JINJA2_OPEN_PATTERN, JINJA2_OPEN_MARKER, value)
        value = re.sub(JINJA2_CLOSE_PATTERN, JINJA2_CLOSE_MARKER, value)
        return value
    return value
