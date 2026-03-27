"""
Role management commands for sup CLI.

Handles export, import, and sync of Superset roles and permissions.
"""

import logging
from pathlib import Path
from typing import List, Optional

import typer
import yaml
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

_logger = logging.getLogger(__name__)

app = typer.Typer(help="Manage roles and permissions", no_args_is_help=True)


@app.command("export")
def export_roles(
    path: Annotated[
        Path,
        typer.Argument(help="Output file path"),
    ] = Path("roles.yaml"),
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Override workspace"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML to stdout")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Export roles and permissions to a YAML file.

    Exports all Superset roles with their permission sets from the workspace.

    Example:
        sup role export
        sup role export roles.yaml
        sup role export --json
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("roles", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)
            roles = list(client.client.export_roles())

        if json_output:
            import json

            console.print(json.dumps(roles, indent=2))
        elif yaml_output:
            console.print(yaml.safe_dump(roles, default_flow_style=False))
        elif porcelain:
            for role in roles:
                name = role.get("name", "")
                perm_count = len(role.get("permissions", []))
                print(f"{name}\t{perm_count}")
        else:
            with open(path, "w", encoding="utf-8") as output:
                yaml.dump(roles, output)

            console.print(
                f"{EMOJIS['success']} Exported {len(roles)} roles to {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to export roles: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("import")
def import_roles(
    path: Annotated[
        Path,
        typer.Argument(help="Input YAML file path"),
    ] = Path("roles.yaml"),
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Override workspace"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Import roles and permissions from a YAML file.

    Reads roles from a YAML file and imports them into the workspace.

    Example:
        sup role import
        sup role import roles.yaml
        sup role import --dry-run
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        if not path.exists():
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} File not found: {path}",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(1)

        with open(path, encoding="utf-8") as input_:
            roles = yaml.load(input_, Loader=yaml.SafeLoader)

        if not roles:
            if not porcelain:
                console.print("No roles found in file.", style=RICH_STYLES["dim"])
            return

        if dry_run:
            if not porcelain:
                console.print(
                    f"{EMOJIS['info']} Dry run: would import {len(roles)} roles",
                    style=RICH_STYLES["info"],
                )
                for role in roles:
                    name = role.get("name", "unnamed")
                    perm_count = len(role.get("permissions", []))
                    console.print(
                        f"  - {name} ({perm_count} permissions)",
                        style=RICH_STYLES["dim"],
                    )
            else:
                for role in roles:
                    print(f"import\t{role.get('name', 'unnamed')}")
            return

        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)

        with spinner(f"Importing {len(roles)} roles", silent=porcelain):
            for role in roles:
                client.client.import_role(role)

        if porcelain:
            print(f"imported:{len(roles)}")
        else:
            console.print(
                f"{EMOJIS['success']} Imported {len(roles)} roles from {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to import roles: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("sync")
def sync_roles(
    path: Annotated[
        Path,
        typer.Argument(help="YAML file with user role definitions"),
    ] = Path("user_roles.yaml"),
    teams: Annotated[
        Optional[List[str]],
        typer.Option("--team", "-t", help="Target team (repeatable)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Sync team, workspace, and data access roles from a YAML file.

    Reads a YAML file defining user roles across teams and workspaces,
    and applies the role assignments. Handles team roles, workspace roles,
    and Superset data access roles.

    YAML format:
        - email: user@example.com
          team_role: admin
          workspaces:
            Workspace Title:
              workspace_role: primary creator
              data_access_roles:
                - "Role Name"

    Example:
        sup role sync user_roles.yaml
        sup role sync user_roles.yaml --team "My Team"
        sup role sync --dry-run
    """
    from preset_cli.api.clients.preset import PresetClient
    from preset_cli.cli.main import sync_all_user_roles_to_team

    from sup.auth.preset import get_preset_auth
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        if not path.exists():
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} File not found: {path}",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(1)

        with open(path, encoding="utf-8") as input_:
            user_roles = yaml.load(input_, Loader=yaml.SafeLoader)

        if not user_roles:
            if not porcelain:
                console.print("No role definitions found in file.", style=RICH_STYLES["dim"])
            return

        if dry_run:
            if not porcelain:
                console.print(
                    f"{EMOJIS['info']} Dry run: would sync roles for {len(user_roles)} users",
                    style=RICH_STYLES["info"],
                )
                for user in user_roles:
                    email = user.get("email", "unknown")
                    team_role = user.get("team_role", "unknown")
                    ws_count = len(user.get("workspaces", {}))
                    console.print(
                        f"  - {email} (team: {team_role}, {ws_count} workspaces)",
                        style=RICH_STYLES["dim"],
                    )
            else:
                for user in user_roles:
                    print(f"sync\t{user.get('email', 'unknown')}")
            return

        ctx = SupContext()
        auth = get_preset_auth(ctx)
        client = PresetClient("https://api.app.preset.io/", auth)

        # Resolve teams
        team_names = _resolve_teams(client, teams, porcelain)
        if not team_names:
            return

        with spinner(
            f"Syncing roles for {len(user_roles)} users", silent=porcelain
        ) as sp:
            for team_name in team_names:
                if sp:
                    sp.text = f"Syncing roles in team: {team_name}"
                workspaces = client.get_workspaces(team_name)
                sync_all_user_roles_to_team(client, team_name, user_roles, workspaces)

        if porcelain:
            print(f"synced:{len(user_roles)}")
        else:
            console.print(
                f"{EMOJIS['success']} Synced roles for {len(user_roles)} users",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to sync roles: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def _resolve_teams(
    client,
    teams: Optional[List[str]],
    porcelain: bool,
) -> List[str]:
    """Resolve team names from user input or prompt for selection."""
    if teams:
        all_teams = client.get_teams()
        team_name_map = {t["title"]: t["name"] for t in all_teams}
        team_name_map.update({t["name"]: t["name"] for t in all_teams})
        resolved = []
        for t in teams:
            if t in team_name_map:
                resolved.append(team_name_map[t])
            else:
                _logger.warning("Team '%s' not found, skipping", t)
        return resolved

    all_teams = client.get_teams()
    if not all_teams:
        if not porcelain:
            console.print("No teams found.", style=RICH_STYLES["dim"])
        return []

    if len(all_teams) == 1:
        return [all_teams[0]["name"]]

    if not porcelain:
        console.print("\nAvailable teams:", style=RICH_STYLES["dim"])
        for t in all_teams:
            console.print(f"  - {t['title']} ({t['name']})")
        selected = typer.prompt("Select team name")
        return [selected]

    return [t["name"] for t in all_teams]
