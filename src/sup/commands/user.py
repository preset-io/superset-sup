"""
User management commands for sup CLI.

Handles user listing, role management, and security operations.
"""

from typing import Optional

import typer
# Removed: from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES
from sup.output.console import console

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
            print(
                f"{user_id}\t{user.get('email', '')}\t{user.get('first_name', '')}\t{user.get('last_name', '')}",
            )
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
    console.print(Panel(panel_content, title=f"User: {full_name}", border_style=RICH_STYLES["brand"]))
