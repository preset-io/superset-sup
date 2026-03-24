"""Tests for sup.commands.template_params module."""

import typer

from sup.commands.template_params import (
    DisableJinjaOption,
    LoadEnvOption,
    TemplateOptions,
    template_options,
)


def test_template_options_returns_list_of_three():
    """template_options() returns exactly 3 typer.Option objects."""
    result = template_options()
    assert isinstance(result, list)
    assert len(result) == 3


def test_template_options_types():
    """Each element returned by template_options() is a typer.models.OptionInfo."""
    result = template_options()
    for opt in result:
        assert isinstance(opt, typer.models.OptionInfo)


def test_annotated_types_importable():
    """TemplateOptions, LoadEnvOption, DisableJinjaOption are importable."""
    assert TemplateOptions is not None
    assert LoadEnvOption is not None
    assert DisableJinjaOption is not None
