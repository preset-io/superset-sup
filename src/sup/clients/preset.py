"""
Preset client wrapper for sup CLI.

Provides sup-specific functionality on top of the existing Preset client.
"""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from preset_cli.api.clients.preset import PresetClient
from sup.auth.preset import SupPresetAuth
from sup.config.settings import SupContext
from sup.output.styles import EMOJIS, RICH_STYLES

console = Console()


class SupPresetClient:
    """
    Preset client wrapper with sup-specific functionality.
    """

    def __init__(self, auth: SupPresetAuth):
        self.auth = auth
        self.client = PresetClient(auth.baseurl, auth)

    @classmethod
    def from_context(
        cls,
        ctx: SupContext,
        workspace_url: Optional[str] = None,
        silent: bool = False,
    ) -> "SupPresetClient":
        """Create client from sup configuration context."""
        auth = SupPresetAuth.from_sup_config(ctx, workspace_url, silent=silent)
        return cls(auth)

    def get_teams(self, silent: bool = False) -> List[Dict[str, Any]]:
        """Get all teams user has access to."""
        try:
            teams = self.client.get_teams()
            # Only show message when explicitly listing (not internal operations)
            if not silent:
                console.print(f"Found {len(teams)} teams", style=RICH_STYLES["dim"])
            return teams
        except Exception as e:
            console.print(
                f"{EMOJIS['error']} Failed to fetch teams: {e}",
                style=RICH_STYLES["error"],
            )
            return []

    def get_workspaces_for_team(self, team_name: str) -> List[Dict[str, Any]]:
        """Get all workspaces for a specific team."""
        try:
            workspaces = self.client.get_workspaces(team_name)
            return workspaces
        except Exception as e:
            console.print(
                f"{EMOJIS['error']} Failed to fetch workspaces for team {team_name}: {e}",
                style=RICH_STYLES["error"],
            )
            return []

    def get_all_workspaces(self, silent: bool = False) -> List[Dict[str, Any]]:
        """Get all workspaces across all teams user has access to."""
        all_workspaces = []
        teams = self.get_teams(silent=silent)

        for team in teams:
            team_name = team.get("name", "")
            if team_name:
                workspaces = self.get_workspaces_for_team(team_name)
                # Add team info to each workspace
                for workspace in workspaces:
                    workspace["team_name"] = team_name
                all_workspaces.extend(workspaces)

        return all_workspaces

    def display_workspaces_table(self, workspaces: List[Dict[str, Any]]) -> None:
        """Display workspaces in a beautiful Rich table."""
        if not workspaces:
            console.print(
                f"{EMOJIS['warning']} No workspaces found",
                style=RICH_STYLES["warning"],
            )
            return

        table = Table(
            title=f"{EMOJIS['workspace']} Available Workspaces",
            show_header=True,
            header_style=RICH_STYLES["header"],
            border_style="blue",
        )

        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bright_white", no_wrap=False)
        table.add_column("Team", style="yellow", no_wrap=True)
        table.add_column("URL", style="blue", no_wrap=False)
        table.add_column("Status", style="green", no_wrap=True)

        for workspace in workspaces:
            workspace_id = str(workspace.get("id", ""))
            # Use 'title' for human-readable name, fallback to 'name'
            display_name = workspace.get("title", workspace.get("name", "Unknown"))
            team_name = workspace.get("team_name", "Unknown")
            hostname = workspace.get("hostname", "")
            status = workspace.get("status", "unknown")

            # Create clickable URL if hostname exists
            url = f"https://{hostname}" if hostname else "N/A"

            table.add_row(workspace_id, display_name, team_name, url, status)

        console.print(table)
        console.print(
            "\n💡 Use [bold]sup workspace use <ID>[/] to set default workspace",
            style=RICH_STYLES["dim"],
        )
