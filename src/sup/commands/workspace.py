"""
Workspace management commands for sup CLI.

Handles workspace listing, selection, and context management.
"""

from typing import Optional
from urllib.parse import urlparse

import typer

# Removed: from rich.console import Console
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage workspaces", no_args_is_help=True)


def parse_workspace_identifier(value: str, client=None) -> int:
    """
    Parse workspace identifier from either numeric ID or URL.

    Accepts formats:
    - Numeric ID: "123" or 123
    - Full URL: "https://myworkspace.app.preset.io/"
    - Hostname: "myworkspace.app.preset.io"
    - URL with path: "https://myworkspace.app.preset.io/superset/dashboard/5/"

    Args:
        value: Workspace ID or URL string
        client: Optional SupPresetClient instance for hostname lookup

    Returns:
        Workspace ID as integer

    Raises:
        ValueError: If value cannot be parsed as valid workspace identifier
    """
    # Try parsing as integer first
    try:
        return int(value)
    except ValueError:
        pass

    # Try parsing as URL or hostname
    hostname = None

    # Add scheme if missing for urlparse to work correctly
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"

    parsed = urlparse(value)
    hostname = parsed.hostname or parsed.netloc

    if not hostname:
        raise ValueError(
            f"Could not parse '{value}' as workspace ID or URL.\n"
            "Expected formats:\n"
            "  - Workspace ID: 123\n"
            "  - Full URL: https://myworkspace.app.preset.io/\n"
            "  - Hostname: myworkspace.app.preset.io"
        )

    # If we have a hostname, we need to look up the workspace ID
    if not client:
        raise ValueError(
            f"Cannot lookup workspace by URL '{value}' without active client.\n"
            "Please use workspace ID instead, or ensure you're authenticated."
        )

    # Get all workspaces and find matching hostname
    workspaces = client.get_all_workspaces(silent=True)
    for workspace in workspaces:
        if workspace.get("hostname") == hostname:
            return workspace["id"]

    raise ValueError(
        f"No workspace found with hostname '{hostname}'.\n"
        "Please check the URL or use 'sup workspace list' to see available workspaces."
    )


def safe_parse_workspace(value: str, client, porcelain: bool = False) -> int:
    """
    Safely parse workspace identifier with error handling.

    Args:
        value: Workspace ID or URL string
        client: SupPresetClient instance
        porcelain: Whether to suppress error output

    Returns:
        Workspace ID as integer

    Raises:
        typer.Exit: If parsing fails
    """
    try:
        return parse_workspace_identifier(value, client)
    except ValueError as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} {str(e)}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


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
    workspace: Annotated[str, typer.Argument(help="Workspace ID or URL to use as default")],
    persist: Annotated[
        bool,
        typer.Option("--persist", "-p", help="Save to global config"),
    ] = False,
):
    """
    Set the default workspace for current session.

    This workspace will be used for all subsequent commands unless overridden.

    Examples:
      sup workspace use 123
      sup workspace use https://myworkspace.app.preset.io/
      sup workspace use myworkspace.app.preset.io
    """
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext

    try:
        ctx = SupContext()
        client = SupPresetClient.from_context(
            ctx,
            silent=True,
        )  # Silent for internal operation

        # Parse workspace identifier
        workspace_id = safe_parse_workspace(workspace, client)

        console.print(
            f"{EMOJIS['workspace']} Setting workspace {workspace_id} as default...",
            style=RICH_STYLES["info"],
        )

        # Get workspace details to cache hostname
        workspaces = client.get_all_workspaces(silent=True)
        workspace_obj = None
        for ws in workspaces:
            if ws.get("id") == workspace_id:
                workspace_obj = ws
                break

        if not workspace_obj:
            console.print(
                f"{EMOJIS['error']} Workspace {workspace_id} not found",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        hostname = workspace_obj.get("hostname")
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
    workspace: Annotated[
        Optional[str],
        typer.Argument(help="Workspace ID or URL (uses current if not specified)"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Show detailed information about a workspace.

    Displays workspace name, status, region, team, and metadata.

    Examples:
      sup workspace info
      sup workspace info 123
      sup workspace info https://myworkspace.app.preset.io/
    """
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        ctx = SupContext()
        client = SupPresetClient.from_context(ctx, silent=True)

        # Use provided workspace or get from context
        if workspace is None:
            workspace_id = ctx.get_workspace_id()
            if not workspace_id:
                if not porcelain:
                    console.print(
                        f"{EMOJIS['error']} No workspace configured",
                        style=RICH_STYLES["error"],
                    )
                    console.print(
                        "💡 Run [bold]sup workspace list[/] and [bold]sup workspace use <ID>[/]",
                        style=RICH_STYLES["info"],
                    )
                raise typer.Exit(1)
        else:
            # Parse workspace identifier
            workspace_id = safe_parse_workspace(workspace, client, porcelain)

        with data_spinner(f"workspace {workspace_id}", silent=porcelain):
            # Get all workspaces and find the specific one
            workspaces = client.get_all_workspaces(silent=True)
            workspace_obj = None
            for ws in workspaces:
                if ws.get("id") == workspace_id:
                    workspace_obj = ws
                    break

            if not workspace_obj:
                if not porcelain:
                    console.print(
                        f"{EMOJIS['error']} Workspace {workspace_id} not found",
                        style=RICH_STYLES["error"],
                    )
                raise typer.Exit(1)

        if porcelain:
            # Simple key-value output
            title = workspace_obj.get("title", "")
            status = workspace_obj.get("status", "")
            hostname = workspace_obj.get("hostname", "")
            print(f"{workspace_id}\t{title}\t{status}\t{hostname}")
        elif json_output:
            import json

            console.print(json.dumps(workspace_obj, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(workspace_obj, default_flow_style=False, indent=2))
        else:
            display_workspace_details(workspace_obj)

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get workspace info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_workspace_details(workspace: dict) -> None:
    """Display detailed workspace information."""
    from rich.panel import Panel

    workspace_id = workspace.get("id", "")
    title = workspace.get("title", "Unknown")
    hostname = workspace.get("hostname", "")
    status = workspace.get("status", "Unknown")
    team_name = workspace.get("team_name", "Unknown")
    region = workspace.get("region", "Unknown")

    # Format URL
    url = f"https://{hostname}/" if hostname else "N/A"

    # Basic info
    info_lines = [
        f"ID: {workspace_id}",
        f"Title: {title}",
        f"Team: {team_name}",
        f"Status: {status}",
        f"Region: {region}",
        f"URL: {url}",
    ]

    # Add optional fields
    if workspace.get("descr"):
        info_lines.append(f"Description: {workspace['descr']}")

    # Add feature flags
    features = []
    if workspace.get("ai_assist_activated"):
        features.append("AI Assist")
    if workspace.get("allow_public_dashboards"):
        features.append("Public Dashboards")
    if workspace.get("enable_iframe_embedding"):
        features.append("iFrame Embedding")

    if features:
        info_lines.append(f"Features: {', '.join(features)}")

    panel_content = "\n".join(info_lines)
    console.print(
        Panel(panel_content, title=f"Workspace: {title}", border_style=RICH_STYLES["brand"])
    )


@app.command("set-target")
def set_import_target(
    workspace: Annotated[str, typer.Argument(help="Workspace ID or URL to use as import target")],
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
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext

    try:
        ctx = SupContext()
        client = SupPresetClient.from_context(ctx, silent=True)

        # Parse workspace identifier
        workspace_id = safe_parse_workspace(workspace, client)

        console.print(
            f"{EMOJIS['import']} Setting import target workspace {workspace_id}...",
            style=RICH_STYLES["info"],
        )

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
