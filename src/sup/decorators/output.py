"""
Output decorators for sup CLI commands.

Provides decorators to automatically add output format parameters and
handle output formatting logic consistently across all commands.
"""

import functools
from typing import Any, Callable, Optional

import typer
from typing_extensions import Annotated

from sup.config.settings import OutputOptions


def with_output_options(func: Callable) -> Callable:
    """
    Decorator that adds standard output format parameters to a command.

    This eliminates the need to manually specify --json, --yaml, --porcelain
    parameters in every command that produces output.

    The decorated function will receive an `output` parameter containing
    an OutputOptions object with all the parsed output settings.
    """

    @functools.wraps(func)
    def wrapper(
        # Standard output options - consistent across ALL commands
        json_output: Annotated[
            bool,
            typer.Option("--json", "-j", help="Output as JSON"),
        ] = False,
        yaml_output: Annotated[
            bool,
            typer.Option("--yaml", "-y", help="Output as YAML"),
        ] = False,
        porcelain: Annotated[
            bool,
            typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
        ] = False,
        # Workspace context (common to most commands)
        workspace_id: Annotated[
            Optional[int],
            typer.Option("--workspace-id", "-w", help="Workspace ID"),
        ] = None,
        **kwargs: Any,
    ) -> Any:
        # Create OutputOptions object
        output = OutputOptions(
            json_output=json_output,
            yaml_output=yaml_output,
            porcelain=porcelain,
            workspace_id=workspace_id,
        )

        # Call the original function with output object
        return func(output=output, **kwargs)

    return wrapper
