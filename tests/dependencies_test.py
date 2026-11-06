"""
Tests for the dependency declarations in ``pyproject.toml``.
"""

import sys
from pathlib import Path

from packaging.requirements import Requirement

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def get_requirement(name: str) -> Requirement:
    """
    Return the requirement declared in ``pyproject.toml`` for a given package.
    """
    with open(PYPROJECT, "rb") as input_:
        dependencies = tomllib.load(input_)["project"]["dependencies"]

    requirements = [Requirement(dependency) for dependency in dependencies]
    return next(requirement for requirement in requirements if requirement.name == name)


def test_sqlglot_is_bounded_below_30() -> None:
    """
    Test that ``sqlglot`` is capped below 30.

    ``sqlglot`` 30 no longer exports ``Expression`` from the top-level package, which breaks
    ``from sqlglot import Expression`` in ``preset_cli.cli.superset.sync.dbt.metrics`` (and
    therefore ``sup dbt core`` and ``sup dbt cloud``).
    """
    specifier = get_requirement("sqlglot").specifier

    assert "26.0" in specifier
    assert "29.0.1" in specifier
    assert "30.0.0" not in specifier
    assert "30.29.0" not in specifier
