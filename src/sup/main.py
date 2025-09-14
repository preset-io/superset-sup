#!/usr/bin/env python3
"""
sup - The Ultimate Superset CLI 🚀

Main entry point for the sup command-line interface.
"""

import typer
from rich.console import Console
from rich.theme import Theme
from typing_extensions import Annotated

from sup.commands import (
    chart,
    dashboard,
    database,
    dataset,
    query,
    sql,
    theme,
    workspace,
)
from sup.commands import config as config_cmd
from sup.output.styles import RICH_STYLES

# Custom Rich theme to eliminate purple/magenta colors
PRESET_THEME = Theme(
    {
        # Override default purple/magenta with emerald green
        "panel.border": "#10B981",  # Emerald green borders
        "panel.title": "bold #10B981",  # Emerald green panel titles
        "rule.line": "#10B981",  # Emerald green lines
        "table.header": "bold #10B981",  # Emerald green table headers
        "table.border": "#10B981",  # Emerald green table borders
        "table.title": "bold #10B981",  # Emerald green table titles
        "progress.bar": "#10B981",  # Emerald green progress bars
        "progress.complete": "#10B981",  # Emerald green completion
    },
)

# Initialize Rich console with custom theme
console = Console(theme=PRESET_THEME)

# ASCII Art Banner
BANNER = """\
██ ███████╗██╗   ██╗██████╗ ██╗
██ ██╔════╝██║   ██║██╔══██╗██║
   ███████╗██║   ██║██████╔╝██║
   ╚════██║██║   ██║██╔═══╝ ╚═╝
   ███████║╚██████╔╝██║     ██╗
   ╚══════╝ ╚═════╝ ╚═╝     ╚═╝"""

# Use cases for consistent display
USE_CASES = [
    "Access all/any of your data from the command line",
    "Manage & sync data assets across Superset instances",
    "Export/import dashboards and charts to/from filesystem",
    "Automate workflows and integrate with CI/CD pipelines",
    "Perfect for scripting and AI-assisted data exploration",
]

# Help text template - will be formatted with actual colors
HELP_TEMPLATE = """🚀 [bold {primary}]The Ultimate Superset/Preset CLI[/bold {primary}] 📊
   [bold {primary}]Brought to you and fully compatible with Preset[/bold {primary}]
   [dim]For power users and AI agents[/dim]

[bold {primary}]Key capabilities:[/bold {primary}]
{capabilities}"""


def format_help():
    """Create help text with beautiful emerald green Preset branding."""
    from sup.output.styles import COLORS

    capabilities = "\n".join(f"• [bright_white]{use_case}[/bright_white]" for use_case in USE_CASES)

    return HELP_TEMPLATE.format(primary=COLORS.primary, capabilities=capabilities)


# Initialize the main Typer app with -h support
app = typer.Typer(
    name="sup",
    help=format_help(),
    rich_markup_mode="rich",
    no_args_is_help=False,  # We'll handle this ourselves
    context_settings={"help_option_names": ["-h", "--help"]},
)


def show_banner():
    """Display the sup banner with beautiful Preset emerald green branding."""
    from sup.output.styles import COLORS

    console.print(BANNER, style=f"bold {COLORS.primary}")  # Beautiful emerald green
    console.print("🚀 The Ultimate Superset/Preset CLI 📊", style=RICH_STYLES["info"])
    console.print(
        "   Brought to you and fully compatible with Preset",
        style=f"bold {COLORS.primary}",
    )
    console.print("   For power users and AI agents\n", style=RICH_STYLES["dim"])

    # High-level use cases
    console.print("[bold]Key capabilities:[/]", style=RICH_STYLES["header"])
    for use_case in USE_CASES:
        console.print(f"• {use_case}", style=RICH_STYLES["accent"])
    console.print()


# Add command modules
app.command(name="sql", help="Execute SQL queries")(sql.sql_command)
app.add_typer(workspace.app, name="workspace", help="Manage workspaces")
app.add_typer(database.app, name="database", help="Manage databases")
app.add_typer(dataset.app, name="dataset", help="Manage datasets")
app.add_typer(chart.app, name="chart", help="Manage charts")
app.add_typer(dashboard.app, name="dashboard", help="Manage dashboards")
app.add_typer(query.app, name="query", help="Manage saved queries")
app.add_typer(theme.app, name="theme", help="Test themes and colors", hidden=True)
app.add_typer(config_cmd.app, name="config", help="Manage configuration")


def version_callback(value: bool):
    if value:
        from sup import __version__

        console.print(f"sup version {__version__}", style=RICH_STYLES["success"])
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version", callback=version_callback),
    ] = False,
):
    """
    🚀 The Ultimate Superset/Preset CLI 📊

    For power users and AI agents. Access data, manage assets, automate workflows.
    """
    if ctx.invoked_subcommand is None:
        show_banner()
        console.print(
            "Use [bold]sup --help[/] for available commands",
            style=RICH_STYLES["dim"],
        )


def cli():
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    cli()
