"""
User management commands for sup CLI.

Handles user listing, role management, and security operations.
"""

from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage users", no_args_is_help=True)
console = Console()


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
):
    """
    Show detailed information about a user.

    Displays user details, roles, permissions, and activity.
    """
    console.print(
        f"{EMOJIS['info']} Loading user {user_id} details...",
        style=RICH_STYLES["info"],
    )

    # TODO: Implement user details fetching
    console.print(
        f"{EMOJIS['warning']} User info not yet implemented",
        style=RICH_STYLES["warning"],
    )


@app.command("export")
def export_users(
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    folder: Annotated[
        Optional[str],
        typer.Option("--folder", "-f", help="Output folder for exported users"),
    ] = "./security/",
    format_type: Annotated[
        str,
        typer.Option("--format", help="Export format"),
    ] = "yaml",
):
    """
    Export users, roles, and permissions to files.

    Creates YAML files with user data suitable for version control and import.
    """
    console.print(
        f"{EMOJIS['export']} Exporting users to {folder}...",
        style=RICH_STYLES["info"],
    )

    # TODO: Implement user export functionality
    console.print(
        f"{EMOJIS['warning']} User export not yet implemented",
        style=RICH_STYLES["warning"],
    )


@app.command("import")
def import_users(
    path: Annotated[str, typer.Argument(help="Path to user data files")],
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing users"),
    ] = False,
):
    """
    Import users, roles, and permissions from files.

    Reads YAML files and creates/updates users and their roles.
    """
    console.print(
        f"{EMOJIS['import']} Importing users from {path}...",
        style=RICH_STYLES["info"],
    )

    # TODO: Implement user import functionality
    console.print(
        f"{EMOJIS['warning']} User import not yet implemented",
        style=RICH_STYLES["warning"],
    )
