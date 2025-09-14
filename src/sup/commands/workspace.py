"""
Workspace management commands for sup CLI.

Handles workspace listing, selection, and context management.
"""

from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage workspaces", no_args_is_help=True)
console = Console()


@app.command("list")
def list_workspaces(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
    team: Annotated[
        Optional[str],
        typer.Option("--team", "-t", help="Filter by team name"),
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of results"),
    ] = None,
):
    """
    List all available workspaces.

    Shows workspace ID, name, team, URL, and status for easy selection.
    """
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext
    from sup.output.formatters import display_porcelain_list
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("workspaces", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupPresetClient.from_context(
                ctx,
                silent=True,
            )  # Always silent - spinner handles messages

            if team:
                workspaces = client.get_workspaces_for_team(team)
                # Add team name for consistency
                for workspace in workspaces:
                    workspace["team_name"] = team
            else:
                workspaces = client.get_all_workspaces(silent=True)

            # Apply limit if specified
            if limit and limit > 0:
                workspaces = workspaces[:limit]

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(workspaces)} workspaces"

        if porcelain:
            # Tab-separated: ID, Name, Team, Hostname, Status
            display_porcelain_list(
                workspaces,
                ["id", "title", "team_name", "hostname", "status"],
            )
        elif json_output:
            import json

            console.print(json.dumps(workspaces, indent=2))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(workspaces, default_flow_style=False, indent=2),
            )
        else:
            client.display_workspaces_table(workspaces)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list workspaces: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("use")
def use_workspace(
    workspace_id: Annotated[int, typer.Argument(help="Workspace ID to use as default")],
    persist: Annotated[
        bool,
        typer.Option("--persist", "-p", help="Save to global config"),
    ] = False,
):
    """
    Set the default workspace for current session.

    This workspace will be used for all subsequent commands unless overridden.
    """
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext

    console.print(
        f"{EMOJIS['workspace']} Setting workspace {workspace_id} as default...",
        style=RICH_STYLES["info"],
    )

    try:
        ctx = SupContext()
        client = SupPresetClient.from_context(
            ctx,
            silent=True,
        )  # Silent for internal operation

        # Get workspace details to cache hostname
        workspaces = client.get_all_workspaces(silent=True)
        workspace = None
        for ws in workspaces:
            if ws.get("id") == workspace_id:
                workspace = ws
                break

        if not workspace:
            console.print(
                f"{EMOJIS['error']} Workspace {workspace_id} not found",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        hostname = workspace.get("hostname")
        ctx.set_workspace_context(workspace_id, hostname=hostname, persist=persist)

        if persist:
            console.print(
                f"{EMOJIS['success']} Workspace {workspace_id} saved globally",
                style=RICH_STYLES["success"],
            )
        else:
            console.print(
                f"{EMOJIS['success']} Using workspace {workspace_id} for this project",
                style=RICH_STYLES["success"],
            )
            console.print(
                f"💡 Add --persist to save globally, or export SUP_WORKSPACE_ID={workspace_id}",
                style=RICH_STYLES["dim"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to set workspace: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


@app.command("info")
def workspace_info(
    workspace_id: Annotated[
        Optional[int],
        typer.Argument(help="Workspace ID (uses current if not specified)"),
    ] = None,
):
    """
    Show detailed information about a workspace.

    Displays databases, datasets, dashboards, and other metadata.
    """
    if workspace_id:
        console.print(
            f"{EMOJIS['info']} Loading workspace {workspace_id} details...",
            style=RICH_STYLES["info"],
        )
    else:
        console.print(
            f"{EMOJIS['info']} Loading current workspace details...",
            style=RICH_STYLES["info"],
        )

    # TODO: Implement workspace details fetching
    console.print(
        f"{EMOJIS['warning']} Workspace info not yet implemented",
        style=RICH_STYLES["warning"],
    )


@app.command("set-target")
def set_import_target(
    workspace_id: Annotated[int, typer.Argument(help="Workspace ID to use as import target")],
    persist: Annotated[
        bool,
        typer.Option("--persist", "-p", help="Save to global config"),
    ] = False,
):
    """
    Set the import target workspace for cross-workspace operations.

    Only needed when you want imports to go to different workspace than exports.
    By default, imports use the same workspace as exports (source workspace).

    Use this for enterprise sync workflows:
    • Development → Staging migrations
    • Backup → Restore scenarios
    • Cross-workspace asset sharing
    """
    from sup.config.settings import SupContext

    console.print(
        f"{EMOJIS['import']} Setting import target workspace {workspace_id}...",
        style=RICH_STYLES["info"],
    )

    try:
        ctx = SupContext()
        ctx.set_target_workspace_id(workspace_id, persist=persist)

        if persist:
            console.print(
                f"{EMOJIS['success']} Import target workspace {workspace_id} saved globally",
                style=RICH_STYLES["success"],
            )
        else:
            console.print(
                f"{EMOJIS['success']} Using workspace {workspace_id} as import target for project",
                style=RICH_STYLES["success"],
            )
            console.print(
                "💡 Add --persist to save globally",
                style=RICH_STYLES["dim"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to set import target workspace: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


@app.command("show")
def show_workspace_context():
    """
    Show current workspace context including source and import target.

    Displays the configured workspaces for exports (source) and imports (target).
    """
    from sup.config.settings import SupContext

    try:
        ctx = SupContext()
        source_workspace_id = ctx.get_workspace_id()
        target_workspace_id = ctx.get_target_workspace_id()

        console.print(
            f"{EMOJIS['workspace']} Current Workspace Context",
            style=RICH_STYLES["header"],
        )

        if source_workspace_id:
            console.print(
                f"📤 Source (exports, queries): [cyan]{source_workspace_id}[/cyan]",
                style=RICH_STYLES["info"],
            )
        else:
            console.print(
                "📤 Source: [dim]Not configured[/dim]",
                style=RICH_STYLES["warning"],
            )
            console.print(
                "💡 Run [bold]sup workspace use <ID>[/] to set source workspace",
                style=RICH_STYLES["dim"],
            )

        if target_workspace_id and target_workspace_id != source_workspace_id:
            console.print(
                f"📥 Import Target: [cyan]{target_workspace_id}[/cyan] [dim](cross)[/dim]",
                style=RICH_STYLES["info"],
            )
        elif target_workspace_id == source_workspace_id:
            console.print(
                f"📥 Import Target: [cyan]{target_workspace_id}[/cyan] [dim](same as source)[/dim]",
                style=RICH_STYLES["info"],
            )
        else:
            console.print(
                "📥 Import Target: [dim]Same as source (default)[/dim]",
                style=RICH_STYLES["info"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to show workspace context: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)
