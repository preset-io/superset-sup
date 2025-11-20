"""
Database management commands for sup CLI.

Handles database listing, selection, and connection management.
"""

from typing import Optional

import typer
# Removed: from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES
from sup.output.console import console

app = typer.Typer(help="Manage databases", no_args_is_help=True)


@app.command("list")
def list_databases(
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    List all databases in the current or specified workspace.

    Shows database ID, name, type, backend, and status.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.formatters import display_porcelain_list
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("databases", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)
            databases = client.get_databases(
                silent=True,
            )  # Always silent - spinner handles messages

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(databases)} databases"

        if porcelain:
            # Tab-separated: ID, Name, Backend, Status
            display_porcelain_list(
                databases,
                ["id", "database_name", "backend", "expose_in_sqllab"],
            )
        elif json_output:
            import json

            console.print(json.dumps(databases, indent=2))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(databases, default_flow_style=False, indent=2))
        else:
            client.display_databases_table(databases)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list databases: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("use")
def use_database(
    database_id: Annotated[int, typer.Argument(help="Database ID to use as default")],
    persist: Annotated[
        bool,
        typer.Option("--persist", "-p", help="Save to global config"),
    ] = False,
):
    """
    Set the default database for SQL queries.

    This database will be used for all SQL commands unless overridden.
    """
    from sup.config.settings import SupContext

    console.print(
        f"{EMOJIS['database']} Setting database {database_id} as default...",
        style=RICH_STYLES["info"],
    )

    try:
        ctx = SupContext()
        ctx.set_database_context(database_id, persist=persist)

        if persist:
            console.print(
                f"{EMOJIS['success']} Database {database_id} saved globally",
                style=RICH_STYLES["success"],
            )
        else:
            console.print(
                f"{EMOJIS['success']} Using database {database_id} for this project",
                style=RICH_STYLES["success"],
            )
            console.print(
                f"💡 Add --persist to save globally, or export SUP_DATABASE_ID={database_id}",
                style=RICH_STYLES["dim"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to set database: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


@app.command("info")
def database_info(
    database_id: Annotated[int, typer.Argument(help="Database ID to inspect")],
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Show detailed information about a database.

    Displays connection details, backend type, and configuration.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner(f"database {database_id}", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Get database info
            database = client.get_database(database_id)

        if porcelain:
            # Simple key-value output
            print(
                f"{database_id}\t{database.get('database_name', '')}\t{database.get('backend', '')}",
            )
        elif json_output:
            import json

            console.print(json.dumps(database, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(database, default_flow_style=False, indent=2))
        else:
            display_database_details(database)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get database info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_database_details(database: dict) -> None:
    """Display detailed database information."""
    from rich.panel import Panel

    database_id = database.get("id", "")
    name = database.get("database_name", "Unknown")
    backend = database.get("backend", "Unknown")

    # Basic info
    info_lines = [
        f"ID: {database_id}",
        f"Name: {name}",
        f"Backend: {backend}",
        f"Expose in SQL Lab: {database.get('expose_in_sqllab', False)}",
    ]

    # Add capabilities
    capabilities = []
    if database.get("allow_ctas"):
        capabilities.append("CTAS")
    if database.get("allow_cvas"):
        capabilities.append("CVAS")
    if database.get("allow_dml"):
        capabilities.append("DML")
    if database.get("allow_file_upload"):
        capabilities.append("File Upload")
    if database.get("allow_run_async"):
        capabilities.append("Async Queries")

    if capabilities:
        info_lines.append(f"Capabilities: {', '.join(capabilities)}")

    # Add UUID if available
    if database.get("uuid"):
        info_lines.append(f"UUID: {database['uuid']}")

    panel_content = "\n".join(info_lines)
    console.print(Panel(panel_content, title=f"Database: {name}", border_style=RICH_STYLES["brand"]))
