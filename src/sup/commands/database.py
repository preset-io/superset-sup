"""
Database management commands for sup CLI.

Handles database listing, selection, and connection management.
"""

from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage databases", no_args_is_help=True)
console = Console()


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
):
    """
    Show detailed information about a database.

    Displays connection details, available schemas, tables, and metadata.
    """
    console.print(
        f"{EMOJIS['info']} Loading database {database_id} details...",
        style=RICH_STYLES["info"],
    )

    # TODO: Implement database details fetching
    console.print(
        f"{EMOJIS['warning']} Database info not yet implemented",
        style=RICH_STYLES["warning"],
    )
