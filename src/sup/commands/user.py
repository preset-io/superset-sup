"""
User management commands for sup CLI.

Handles user listing, role management, pull/push, and invitations.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

_logger = logging.getLogger(__name__)

app = typer.Typer(help="Manage users", no_args_is_help=True)


@app.command("list")
def list_users(
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
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of results"),
    ] = None,
):
    """
    List all users in the current or specified workspace.

    Shows user ID, email, first name, last name, roles, and status.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.formatters import display_porcelain_list
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("users", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Get users from the Superset API
            users_list = list(client.client.export_users())
            users = [dict(user) for user in users_list]  # Convert UserType to Dict[str, Any]

            # Apply limit if specified
            if limit and limit > 0:
                users = users[:limit]

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(users)} users"

        if porcelain:
            # Tab-separated: ID, Email, First Name, Last Name, Username, Roles
            display_porcelain_list(
                users,
                ["id", "email", "first_name", "last_name", "username", "role"],
            )
        elif json_output:
            import json

            console.print(json.dumps(users, indent=2))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(users, default_flow_style=False, indent=2))
        else:
            client.display_users_table(users)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list users: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
def user_info(
    user_id: Annotated[int, typer.Argument(help="User ID to inspect")],
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
    Show detailed information about a user.

    Displays user details, roles, and permissions.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner(f"user {user_id}", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Get all users and find the specific one
            users_list = list(client.client.export_users())
            user = None
            for u in users_list:
                if u.get("id") == user_id:
                    user = dict(u)
                    break

            if not user:
                if not porcelain:
                    console.print(
                        f"{EMOJIS['error']} User {user_id} not found",
                        style=RICH_STYLES["error"],
                    )
                raise typer.Exit(1)

        if porcelain:
            # Simple key-value output
            email = user.get("email", "")
            first = user.get("first_name", "")
            last = user.get("last_name", "")
            print(f"{user_id}\t{email}\t{first}\t{last}")
        elif json_output:
            import json

            console.print(json.dumps(user, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(user, default_flow_style=False, indent=2))
        else:
            display_user_details(user)

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get user info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_user_details(user: dict) -> None:
    """Display detailed user information."""
    from rich.panel import Panel

    user_id = user.get("id", "")
    email = user.get("email", "Unknown")
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    username = user.get("username", "Unknown")

    # Format full name
    full_name = f"{first_name} {last_name}".strip() or "Unknown"

    # Get roles
    roles = user.get("role", [])
    if isinstance(roles, list):
        roles_str = ", ".join(roles) if roles else "No roles"
    else:
        roles_str = str(roles)

    # Basic info
    info_lines = [
        f"ID: {user_id}",
        f"Name: {full_name}",
        f"Email: {email}",
        f"Username: {username}",
        f"Roles: {roles_str}",
    ]

    panel_content = "\n".join(info_lines)
    console.print(
        Panel(panel_content, title=f"User: {full_name}", border_style=RICH_STYLES["brand"])
    )


@app.command("pull")
def pull_users(
    path: Annotated[
        Path,
        typer.Argument(help="Output file path"),
    ] = Path("users_workspace_roles.yaml"),
    teams: Annotated[
        Optional[List[str]],
        typer.Option("--team", "-t", help="Filter by team (repeatable)"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML to stdout")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Pull users and their workspace roles to a YAML file.

    Pulls all users across teams with their team and workspace role assignments.
    The output format is compatible with 'sup user push'.

    Example:
        sup user pull
        sup user pull users.yaml
        sup user pull --team "My Team"
        sup user pull --json
    """
    from preset_cli.api.clients.preset import PresetClient
    from preset_cli.cli.export_users import (
        convert_user_data_to_list,
        get_filtered_teams,
        process_team_members,
        process_team_workspaces,
    )
    from sup.auth.preset import get_preset_auth
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        with spinner("Pulling users and workspace roles", silent=porcelain) as sp:
            ctx = SupContext()
            auth = get_preset_auth(ctx)
            client = PresetClient("https://api.app.preset.io/", auth)

            team_filter = set(teams) if teams else set()
            filtered_teams = get_filtered_teams(client, team_filter)

            if not filtered_teams:
                if not porcelain:
                    console.print("No teams found.", style=RICH_STYLES["dim"])
                return

            # Initialize user data storage
            from collections import defaultdict

            user_data: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "email": None,
                    "first_name": None,
                    "last_name": None,
                    "username": None,
                    "workspaces": {},
                },
            )

            # Role mappings
            workspace_role_map = {
                "Admin": "workspace admin",
                "PresetAlpha": "primary creator",
                "PresetBeta": "secondary creator",
                "PresetGamma": "limited creator",
                "PresetReportsOnly": "viewer",
                "PresetDashboardsOnly": "dashboard viewer",
                "PresetNoAccess": "no access",
                "Alpha": "primary creator",
                "Beta": "secondary creator",
                "Gamma": "limited creator",
                "ReportsOnly": "viewer",
                "DashboardsOnly": "dashboard viewer",
                "NoAccess": "no access",
            }
            team_role_map = {1: "admin", 2: "user"}

            for team in filtered_teams:
                team_name = team["name"]
                team_title = team["title"]

                if sp:
                    sp.text = f"Processing team: {team_title}"

                process_team_members(client, team_name, team_title, user_data, team_role_map)
                process_team_workspaces(
                    client, team_name, team_title, user_data, workspace_role_map
                )

            users_list = convert_user_data_to_list(user_data)

            if sp:
                sp.text = f"Found {len(users_list)} users"

        if json_output:
            import json

            console.print(json.dumps(users_list, indent=2))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(users_list, default_flow_style=False, sort_keys=False))
        elif porcelain:
            for user in users_list:
                email = user.get("email", "")
                first = user.get("first_name", "")
                last = user.get("last_name", "")
                print(f"{email}\t{first}\t{last}")
        else:
            import yaml

            with open(path, "w", encoding="utf-8") as output:
                yaml.dump(users_list, output, default_flow_style=False, sort_keys=False)

            console.print(
                f"{EMOJIS['success']} Pulled {len(users_list)} users to {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to pull users: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("push")
def push_users(
    path: Annotated[
        Path,
        typer.Argument(help="Input YAML file path"),
    ] = Path("users.yaml"),
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
    Push users via SCIM from a YAML file.

    Supports two file formats (auto-detected):
    - Simple format: basic user info (email, first_name, last_name)
    - Workspace roles format: user info + workspace role assignments

    Example:
        sup user push users.yaml
        sup user push users_workspace_roles.yaml --team "My Team"
        sup user push --dry-run
    """
    import yaml

    from preset_cli.api.clients.preset import PresetClient
    from preset_cli.cli.main import (
        UserFileFormat,
        detect_users_file_format,
        import_users_with_workspace_roles,
    )
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
            users = yaml.load(input_, Loader=yaml.SafeLoader)

        if not users:
            if not porcelain:
                console.print("No users found in file.", style=RICH_STYLES["dim"])
            return

        file_format = detect_users_file_format(users)

        if dry_run:
            if not porcelain:
                fmt_label = (
                    "with workspace roles"
                    if file_format == UserFileFormat.WORKSPACE_ROLES
                    else "simple"
                )
                console.print(
                    f"{EMOJIS['info']} Dry run: would push {len(users)} users ({fmt_label} format)",
                    style=RICH_STYLES["info"],
                )
                for user in users:
                    console.print(
                        f"  - {user.get('email', 'unknown')}",
                        style=RICH_STYLES["dim"],
                    )
            else:
                for user in users:
                    print(f"push\t{user.get('email', 'unknown')}")
            return

        ctx = SupContext()
        auth = get_preset_auth(ctx)
        client = PresetClient("https://api.app.preset.io/", auth)

        # Resolve teams
        team_names = _resolve_teams(client, teams, porcelain)
        if not team_names:
            return

        with spinner(f"Pushing {len(users)} users", silent=porcelain):
            if file_format == UserFileFormat.WORKSPACE_ROLES:
                import_users_with_workspace_roles(client, team_names, users)
            else:
                client.import_users(team_names, users)

        if porcelain:
            print(f"pushed:{len(users)}")
        else:
            console.print(
                f"{EMOJIS['success']} Pushed {len(users)} users from {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to push users: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("invite")
def invite_users(
    path: Annotated[
        Path,
        typer.Argument(help="YAML file with user emails"),
    ] = Path("users.yaml"),
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
    Invite users to join Preset teams.

    Reads a YAML file containing user emails and sends invitations.
    The YAML file should contain a list of objects with an 'email' field.

    Example:
        sup user invite users.yaml --team "My Team"
        sup user invite --dry-run
    """
    import yaml

    from preset_cli.api.clients.preset import PresetClient
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
            config = yaml.load(input_, Loader=yaml.SafeLoader)

        if not config:
            if not porcelain:
                console.print("No users found in file.", style=RICH_STYLES["dim"])
            return

        emails = [user["email"] for user in config]

        if dry_run:
            if not porcelain:
                console.print(
                    f"{EMOJIS['info']} Dry run: would invite {len(emails)} users",
                    style=RICH_STYLES["info"],
                )
                for email in emails:
                    console.print(f"  - {email}", style=RICH_STYLES["dim"])
            else:
                for email in emails:
                    print(f"invite\t{email}")
            return

        ctx = SupContext()
        auth = get_preset_auth(ctx)
        client = PresetClient("https://api.app.preset.io/", auth)

        # Resolve teams
        team_names = _resolve_teams(client, teams, porcelain)
        if not team_names:
            return

        with spinner(f"Inviting {len(emails)} users", silent=porcelain):
            client.invite_users(team_names, emails)

        if porcelain:
            print(f"invited:{len(emails)}")
        else:
            console.print(
                f"{EMOJIS['success']} Invited {len(emails)} users",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to invite users: {e}",
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
        # Convert team titles to internal names if needed
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

    # No teams specified — get all teams
    all_teams = client.get_teams()
    if not all_teams:
        if not porcelain:
            console.print("No teams found.", style=RICH_STYLES["dim"])
        return []

    if len(all_teams) == 1:
        return [all_teams[0]["name"]]

    # Prompt for team selection
    if not porcelain:
        console.print("\nAvailable teams:", style=RICH_STYLES["dim"])
        for team in all_teams:
            console.print(f"  - {team['title']} ({team['name']})")
        selected = typer.prompt("Select team name")
        return [selected]

    return [t["name"] for t in all_teams]
