"""
Group management commands for sup CLI.

Handles SCIM group listing and synchronization for Preset workspaces.
Enables group management for customers not using Okta/SCIM sync.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage SCIM groups", no_args_is_help=True)


@app.command("list")
def list_groups(
    team: Annotated[
        Optional[str],
        typer.Option("--team", "-t", help="Team name to list groups from"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML")] = False,
    csv_output: Annotated[bool, typer.Option("--csv", help="Output as CSV")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of groups to display"),
    ] = None,
    save_file: Annotated[
        Optional[Path],
        typer.Option("--save", "-s", help="Save output to file"),
    ] = None,
):
    """
    List all SCIM groups in a Preset team.

    Shows group ID, name, and member count. Supports pagination for large teams.
    If no team is specified, lists teams for selection.
    """
    from preset_cli.api.clients.preset import PresetClient
    from sup.auth.preset import get_preset_auth
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("groups", silent=porcelain) as sp:
            ctx = SupContext()
            auth = get_preset_auth(ctx)

            # Use the Preset client directly for SCIM operations
            client = PresetClient("https://api.app.preset.io/", auth)

            # Get team if not specified
            if not team:
                teams = client.get_teams()
                if len(teams) == 1:
                    team = teams[0]["name"]
                else:
                    if not porcelain:
                        console.print("\nAvailable teams:", style=RICH_STYLES["dim"])
                        for t in teams:
                            console.print(f"  • {t['title']} ({t['name']})")
                        team = typer.prompt("Select team name")

            # Collect all groups with pagination
            all_groups = []
            start_at = 1
            total_count = 100  # Default to ensure at least one iteration

            while start_at <= total_count:
                response = client.get_group_membership(team, start_at)  # type: ignore[arg-type]
                total_count = response.get("totalResults", 0)

                if response.get("Resources"):
                    all_groups.extend(response["Resources"])

                start_at += 100

            # Apply limit if specified
            if limit and limit > 0:
                all_groups = all_groups[:limit]

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(all_groups)} groups in team {team}"

        # Handle different output formats
        if save_file:
            save_groups_to_file(all_groups, save_file, team)  # type: ignore[arg-type]
            if not porcelain:
                console.print(
                    f"{EMOJIS['success']} Saved groups to {save_file}",
                    style=RICH_STYLES["success"],
                )
        elif porcelain:
            # Tab-separated: ID, Name, Member Count
            for group in all_groups:
                member_count = len(group.get("members", []))
                print(f"{group['id']}\t{group['displayName']}\t{member_count}")
        elif json_output:
            import json

            console.print(json.dumps(all_groups, indent=2))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(all_groups, default_flow_style=False, indent=2))
        elif csv_output:
            display_groups_csv(all_groups)
        else:
            display_groups_table(all_groups, team)  # type: ignore[arg-type]

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list groups: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("sync")
def sync_groups(
    config_file: Annotated[
        Path,
        typer.Argument(help="Path to YAML configuration file with group definitions"),
    ],
    team: Annotated[
        Optional[str],
        typer.Option("--team", "-t", help="Target team for group sync"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying them"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompts"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Synchronize SCIM groups from a YAML configuration file.

    This creates and manages groups for customers not using Okta/SCIM sync.
    The configuration file should define groups and their members.

    Example YAML format:

    groups:
      - name: "Data Engineers"
        members:
          - email: engineer1@company.com
          - email: engineer2@company.com
      - name: "Analysts"
        members:
          - email: analyst1@company.com
    """
    import yaml

    from preset_cli.api.clients.preset import PresetClient
    from sup.auth.preset import get_preset_auth
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        # Load configuration
        if not config_file.exists():
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} Configuration file not found: {config_file}",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(1)

        with open(config_file) as f:
            config = yaml.safe_load(f)

        if "groups" not in config:
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} Invalid configuration: 'groups' key not found",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(1)

        groups_to_sync = config["groups"]

        # Get authentication and client
        ctx = SupContext()
        auth = get_preset_auth(ctx)
        client = PresetClient("https://api.app.preset.io/", auth)

        # Get team if not specified
        if not team:
            teams = client.get_teams()
            if len(teams) == 1:
                team = teams[0]
            else:
                if not porcelain:
                    console.print("\nAvailable teams:", style=RICH_STYLES["dim"])
                    for t in teams:
                        console.print(f"  • {t}")
                    team = typer.prompt("Select team")

        # Get existing groups
        existing_groups = get_all_groups(client, team)  # type: ignore[arg-type]
        existing_by_name = {g["displayName"]: g for g in existing_groups}

        # Plan sync operations
        operations = plan_group_sync(groups_to_sync, existing_by_name)

        if not operations["create"] and not operations["update"] and not operations["delete"]:
            if not porcelain:
                console.print(
                    f"{EMOJIS['success']} All groups are already in sync",
                    style=RICH_STYLES["success"],
                )
            return

        # Display sync plan
        if not porcelain:
            display_sync_plan(operations, dry_run)

        if dry_run:
            if not porcelain:
                console.print("\n[dim]Dry run complete. No changes made.[/dim]")
            return

        # Confirm changes
        if not force and not porcelain:
            if not typer.confirm("\nProceed with sync?"):
                console.print("Sync cancelled.", style=RICH_STYLES["dim"])
                raise typer.Exit(0)

        # Execute sync
        with spinner("Synchronizing groups", silent=porcelain) as sp:
            results = execute_group_sync(client, team, operations)  # type: ignore[arg-type]

            if sp:
                sp.text = f"Synchronized {results['total']} groups"

        # Display results
        if not porcelain:
            display_sync_results(results)
        else:
            print(f"created:{results['created']}")
            print(f"updated:{results['updated']}")
            print(f"deleted:{results['deleted']}")
            print(f"errors:{results['errors']}")

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to sync groups: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("create")
def create_group(
    name: Annotated[str, typer.Argument(help="Name of the group to create")],
    team: Annotated[
        Optional[str],
        typer.Option("--team", "-t", help="Team to create the group in"),
    ] = None,
    members: Annotated[
        Optional[List[str]],
        typer.Option("--member", "-m", help="Email addresses of members to add"),
    ] = None,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Create a new SCIM group in a Preset team.

    Example:
        sup group create "Data Engineers" -m user1@company.com -m user2@company.com
    """
    from preset_cli.api.clients.preset import PresetClient
    from sup.auth.preset import get_preset_auth
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        with spinner(f"Creating group '{name}'", silent=porcelain):
            ctx = SupContext()
            auth = get_preset_auth(ctx)
            client = PresetClient("https://api.app.preset.io/", auth)

            # Get team if not specified
            if not team:
                teams = client.get_teams()
                if len(teams) == 1:
                    team = teams[0]["name"]
                else:
                    if not porcelain:
                        console.print("\nAvailable teams:", style=RICH_STYLES["dim"])
                        for t in teams:
                            console.print(f"  • {t['title']} ({t['name']})")
                        team = typer.prompt("Select team name")

            # Create the group via SCIM API
            group_data = {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                "displayName": name,
                "members": [],
            }

            # Add members if specified
            if members:
                # Note: This would require user lookup to get SCIM IDs
                # For now, we'll create the group empty and note this limitation
                if not porcelain:
                    console.print(
                        f"{EMOJIS['warning']} Member addition during creation not yet implemented. "
                        "Please use 'sup group add-members' after creation.",
                        style=RICH_STYLES["warning"],
                    )

            # Create the group
            response = create_scim_group(client, team, group_data)  # type: ignore[arg-type]
            group_id = response.get("id")

        if porcelain:
            print(f"{group_id}\t{name}")
        else:
            console.print(
                f"{EMOJIS['success']} Created group '{name}' with ID: {group_id}",
                style=RICH_STYLES["success"],
            )

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to create group: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


# Helper functions


def get_all_groups(client, team: str) -> List[Dict[str, Any]]:
    """Fetch all groups for a team with pagination."""
    all_groups = []
    start_at = 1
    total_count = 100  # Default to ensure at least one iteration

    while start_at <= total_count:
        response = client.get_group_membership(team, start_at)
        total_count = response.get("totalResults", 0)

        if response.get("Resources"):
            all_groups.extend(response["Resources"])

        start_at += 100

    return all_groups


def display_groups_table(groups: List[Dict[str, Any]], team: str) -> None:
    """Display groups in a Rich table."""
    from rich.table import Table

    table = Table(title=f"SCIM Groups in {team}", show_lines=True)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bright_white")
    table.add_column("Members", style="yellow")
    table.add_column("Member List", style="dim")

    for group in groups:
        group_id = group.get("id", "")
        name = group.get("displayName", "")
        members = group.get("members", [])
        member_count = str(len(members))

        # Format member list (first 3 members)
        member_list = ""
        if members:
            member_names = [m.get("display", m.get("value", "")) for m in members[:3]]
            member_list = ", ".join(member_names)
            if len(members) > 3:
                member_list += f" (+{len(members) - 3} more)"
        else:
            member_list = "No members"

        table.add_row(group_id, name, member_count, member_list)

    console.print(table)


def display_groups_csv(groups: List[Dict[str, Any]]) -> None:
    """Display groups in CSV format."""
    import csv
    import sys

    writer = csv.writer(sys.stdout)
    writer.writerow(["ID", "Name", "Member Count", "Members"])

    for group in groups:
        members = group.get("members", [])
        member_emails = [m.get("value", "") for m in members]
        writer.writerow(
            [
                group.get("id", ""),
                group.get("displayName", ""),
                len(members),
                ";".join(member_emails),
            ]
        )


def save_groups_to_file(groups: List[Dict[str, Any]], filepath: Path, team: str) -> None:
    """Save groups to a file in YAML or CSV format."""
    import csv

    import yaml

    if filepath.suffix.lower() == ".csv":
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Member Count", "Members"])

            for group in groups:
                members = group.get("members", [])
                member_emails = [m.get("value", "") for m in members]
                writer.writerow(
                    [
                        group.get("id", ""),
                        group.get("displayName", ""),
                        len(members),
                        ";".join(member_emails),
                    ]
                )
    else:
        # Default to YAML
        output = {
            "team": team,
            "groups": groups,
        }
        with open(filepath, "w") as f:
            yaml.safe_dump(output, f, default_flow_style=False, indent=2)


def plan_group_sync(
    desired_groups: List[Dict[str, Any]], existing_groups: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Plan sync operations for groups."""
    operations: Dict[str, List[Dict[str, Any]]] = {
        "create": [],
        "update": [],
        "delete": [],
    }

    desired_names = set()

    for group in desired_groups:
        name = group["name"]
        desired_names.add(name)

        if name in existing_groups:
            # Check if update is needed
            existing = existing_groups[name]
            if needs_update(group, existing):
                operations["update"].append(
                    {
                        "id": existing["id"],
                        "name": name,
                        "desired": group,
                        "existing": existing,
                    }
                )
        else:
            # Need to create
            operations["create"].append(group)

    # Check for groups to delete (exist but not in desired state)
    # Note: Be careful with deletion - maybe make this optional
    # For now, we won't auto-delete groups

    return operations


def needs_update(desired: Dict[str, Any], existing: Dict[str, Any]) -> bool:
    """Check if a group needs updating."""
    # Compare members
    desired_members = set(m["email"] for m in desired.get("members", []))
    existing_members = set(m.get("value", "") for m in existing.get("members", []))

    return desired_members != existing_members


def display_sync_plan(operations: Dict[str, List[Dict[str, Any]]], dry_run: bool) -> None:
    """Display the planned sync operations."""
    from rich.panel import Panel
    from rich.text import Text

    lines = []

    if operations["create"]:
        lines.append(Text(f"\n{EMOJIS['plus']} Groups to create:", style="green"))
        for group in operations["create"]:
            member_count = len(group.get("members", []))
            lines.append(Text(f"  • {group['name']} ({member_count} members)", style="dim"))

    if operations["update"]:
        lines.append(Text(f"\n{EMOJIS['refresh']} Groups to update:", style="yellow"))
        for op in operations["update"]:
            lines.append(Text(f"  • {op['name']}", style="dim"))

    if operations["delete"]:
        lines.append(Text(f"\n{EMOJIS['trash']} Groups to delete:", style="red"))
        for op in operations["delete"]:
            lines.append(Text(f"  • {op['name']}", style="dim"))

    if not lines:
        lines.append(Text("No changes required", style="green"))

    title = "Sync Plan (DRY RUN)" if dry_run else "Sync Plan"
    panel = Panel(
        Text.from_markup("\n".join(str(line) for line in lines)),
        title=title,
        border_style=RICH_STYLES["brand"],
    )
    console.print(panel)


def execute_group_sync(
    client, team: str, operations: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Execute the group sync operations."""
    results = {
        "created": 0,
        "updated": 0,
        "deleted": 0,
        "errors": 0,
        "total": 0,
    }

    # Create new groups
    for group in operations["create"]:
        try:
            group_data = {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                "displayName": group["name"],
                "members": [],  # Will need to add members in a separate step
            }
            create_scim_group(client, team, group_data)
            results["created"] += 1
        except Exception as e:
            console.print(f"Failed to create group {group['name']}: {e}", style="red")
            results["errors"] += 1

    # Update existing groups
    for op in operations["update"]:
        try:
            # Prepare update data using SCIM PATCH format
            group_data = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {
                        "op": "replace",
                        "path": "members",
                        "value": [
                            {"value": m["email"], "display": m["email"]}
                            for m in op["desired"].get("members", [])
                        ],
                    }
                ],
            }
            update_scim_group(client, team, op["id"], group_data)
            results["updated"] += 1
        except Exception as e:
            console.print(f"Failed to update group {op['name']}: {e}", style="red")
            results["errors"] += 1

    # Delete groups (if explicitly requested - not auto-deleting for safety)
    for op in operations["delete"]:
        try:
            delete_scim_group(client, team, op["id"])
            results["deleted"] += 1
        except Exception as e:
            console.print(f"Failed to delete group {op['name']}: {e}", style="red")
            results["errors"] += 1

    results["total"] = results["created"] + results["updated"] + results["deleted"]
    return results


def display_sync_results(results: Dict[str, Any]) -> None:
    """Display the results of sync operations."""
    from rich.panel import Panel

    lines = []

    if results["created"] > 0:
        lines.append(f"{EMOJIS['success']} Created: {results['created']} groups")

    if results["updated"] > 0:
        lines.append(f"{EMOJIS['refresh']} Updated: {results['updated']} groups")

    if results["deleted"] > 0:
        lines.append(f"{EMOJIS['trash']} Deleted: {results['deleted']} groups")

    if results["errors"] > 0:
        lines.append(f"{EMOJIS['error']} Errors: {results['errors']}")

    summary = f"\nTotal: {results['total']} operations completed"
    if results["errors"] > 0:
        summary += f" with {results['errors']} errors"

    lines.append(summary)

    panel = Panel(
        "\n".join(lines),
        title="Sync Results",
        border_style="green" if results["errors"] == 0 else "yellow",
    )
    console.print(panel)


def create_scim_group(client, team: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a SCIM group via the Preset API."""
    import json

    url = client.get_base_url() / "teams" / team / "scim/v2/Groups"
    client.session.headers["Accept"] = "application/scim+json"
    client.session.headers["Content-Type"] = "application/scim+json"
    response = client.session.post(url, data=json.dumps(group_data))
    response.raise_for_status()
    return response.json()


def update_scim_group(
    client, team: str, group_id: str, group_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Update an existing SCIM group in a team."""
    import json

    url = client.get_base_url() / "teams" / team / "scim/v2/Groups" / group_id
    client.session.headers["Accept"] = "application/scim+json"
    client.session.headers["Content-Type"] = "application/scim+json"
    response = client.session.patch(url, data=json.dumps(group_data))
    response.raise_for_status()
    return response.json()


def delete_scim_group(client, team: str, group_id: str) -> None:
    """Delete a SCIM group from a team."""
    url = client.get_base_url() / "teams" / team / "scim/v2/Groups" / group_id
    response = client.session.delete(url)
    response.raise_for_status()
