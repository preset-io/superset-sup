#!/usr/bin/env python3
"""
sup - The Ultimate Superset CLI 🚀

Main entry point for the sup command-line interface.
"""

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.commands import chart
from sup.commands import config as config_cmd
from sup.commands import database, dataset, sql, workspace
from sup.output.styles import RICH_STYLES

# Initialize Rich console for beautiful output
console = Console()

# ASCII Art Banner
BANNER = """██ ███████╗██╗   ██╗██████╗ ██╗
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


def format_help():
    """Create help text without ASCII art but with key messaging - DRY version."""
    help_text = "🚀 [bold cyan]The Ultimate Superset/Preset CLI[/bold cyan] 📊\n"
    help_text += "   [dim]For power users and AI agents[/dim]\n\n"
    help_text += "[bold magenta]Key capabilities:[/bold magenta]\n"

    for use_case in USE_CASES:
        help_text += f"• [bright_cyan]{use_case}[/bright_cyan]\n"

    return help_text


# Initialize the main Typer app
app = typer.Typer(
    name="sup",
    help=format_help(),
    rich_markup_mode="rich",
    no_args_is_help=False,  # We'll handle this ourselves
)


def show_banner():
    """Display the sup banner with branding."""
    console.print(BANNER, style=RICH_STYLES["brand"])
    console.print("🚀 The Ultimate Superset/Preset CLI 📊", style=RICH_STYLES["info"])
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
