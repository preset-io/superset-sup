"""
Shared Jinja2 template parameters for sup commands.

Provides reusable CLI options for template processing across all entity types.
"""

from typing import List, Optional

import typer
from typing_extensions import Annotated


def template_options():
    """
    Returns a list of common Jinja2 template CLI options.

    Use with Typer's dependency system to keep template parameters DRY
    across all entity push/sync commands.
    """
    return [
        typer.Option(
            None,
            "--option",
            "-o",
            help="Template variables (key=value, can be used multiple times)",
            metavar="KEY=VALUE",
        ),
        typer.Option(
            False,
            "--load-env",
            "-e",
            help="Load environment variables for templates (access via env['VAR_NAME'])",
        ),
        typer.Option(
            False,
            "--disable-jinja-templating",
            help="Disable Jinja2 template processing in YAML files",
        ),
    ]


# Type annotations for template parameters
TemplateOptions = Annotated[
    Optional[List[str]],
    typer.Option(
        "--option",
        "-o",
        help="Template variables (key=value, can be used multiple times)",
        metavar="KEY=VALUE",
    ),
]

LoadEnvOption = Annotated[
    bool,
    typer.Option(
        "--load-env",
        "-e",
        help="Load environment variables for templates (access via env['VAR_NAME'])",
    ),
]

DisableJinjaOption = Annotated[
    bool,
    typer.Option(
        "--disable-jinja-templating",
        help="Disable Jinja2 template processing in YAML files",
    ),
]
