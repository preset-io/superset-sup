"""
Shared utilities for sup CLI.
"""

import re

import yaml

# Jinja2 escaping markers — centralized so changes propagate everywhere
JINJA2_OPEN_MARKER = "__JINJA2_OPEN__"
JINJA2_CLOSE_MARKER = "__JINJA2_CLOSE__"
JINJA2_OPEN_PATTERN = r"\{\{"
JINJA2_CLOSE_PATTERN = r"\}\}"


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
