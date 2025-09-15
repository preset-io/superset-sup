"""
Dashboard management commands for sup CLI.

Working version without decorators - follows dataset.py pattern.
"""

from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from sup.output.formatters import display_porcelain_list
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES
from sup.output.tables import display_dashboards_table

app = typer.Typer(help="Manage dashboards", no_args_is_help=True)
console = Console()


@app.command("list")
def list_dashboards(
    # Universal filters - same pattern as dataset.py/chart.py
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Filter by specific ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Filter by multiple IDs (comma-separated)"),
    ] = None,
    search_filter: Annotated[
        Optional[str],
        typer.Option("--search", help="Search dashboards by title or slug (server-side)"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", "-m", help="Show only dashboards you own"),
    ] = False,
    limit_filter: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of results"),
    ] = None,
    # Dashboard-specific filters
    published: Annotated[
        Optional[bool],
        typer.Option("--published", help="Show only published dashboards"),
    ] = None,
    draft: Annotated[
        Optional[bool],
        typer.Option("--draft", help="Show only draft dashboards"),
    ] = None,
    folder: Annotated[
        Optional[str],
        typer.Option("--folder", help="Filter by folder path pattern"),
    ] = None,
    # Output options - same pattern as other commands
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    List dashboards in the current or specified workspace.

    Examples:
        sup dashboard list                                    # All dashboards
        sup dashboard list --mine                            # My dashboards only
        sup dashboard list --published --porcelain          # Published only, machine-readable
        sup dashboard list --search="sales" --json          # Server search in title/slug, JSON
        sup dashboard list --folder="*marketing*"           # Marketing folder dashboards
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        # No complex filtering - just use simple server-side search

        # Get dashboards with spinner
        with data_spinner("dashboards", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Fetch dashboards with server-side search only
            dashboards = client.get_dashboards(
                silent=True,
                limit=limit_filter,
                text_search=search_filter,  # Server-side title/slug search
            )

            # Update spinner
            if sp:
                sp.text = f"Found {len(dashboards)} dashboards"

        # Display results - same pattern as dataset.py/chart.py
        if porcelain:
            display_porcelain_list(
                dashboards,
                ["id", "dashboard_title", "published", "created_on"],
            )
        elif json_output:
            import json

            console.print(json.dumps(dashboards, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(dashboards, default_flow_style=False, indent=2),
            )
        else:
            # Beautiful Rich table with clickable links
            workspace_hostname = ctx.get_workspace_hostname()
            display_dashboards_table(dashboards, workspace_hostname)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list dashboards: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
def dashboard_info(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID to inspect")],
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
    Show detailed information about a dashboard.

    Displays metadata, charts, permissions, and other dashboard details.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner(f"dashboard {dashboard_id}", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)
            dashboard = client.get_dashboard(dashboard_id, silent=True)

        if porcelain:
            # Simple key-value output
            print(
                f"{dashboard_id}\t{dashboard.get('dashboard_title', '')}\t{dashboard.get('published', False)}",  # noqa: E501
            )
        elif json_output:
            import json

            console.print(json.dumps(dashboard, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(dashboard, default_flow_style=False, indent=2))
        else:
            display_dashboard_details(dashboard)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get dashboard info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_dashboard_details(dashboard: Dict[str, Any]) -> None:
    """Display detailed dashboard information in Rich format."""
    dashboard_id = dashboard.get("id", "")
    title = dashboard.get("dashboard_title", "Unknown")
    published = dashboard.get("published", False)

    # Basic info
    info_lines = [
        f"ID: {dashboard_id}",
        f"Title: {title}",
        f"Status: {'Published' if published else 'Draft'}",
        f"URL Slug: {dashboard.get('slug', 'N/A')}",
    ]

    if dashboard.get("description"):
        info_lines.append(f"Description: {dashboard['description']}")

    if dashboard.get("created_on"):
        info_lines.append(f"Created: {dashboard['created_on'].split('T')[0]}")

    if dashboard.get("changed_on"):
        info_lines.append(f"Modified: {dashboard['changed_on'].split('T')[0]}")

    panel_content = "\n".join(info_lines)
    console.print(
        Panel(panel_content, title=f"Dashboard: {title}", border_style=RICH_STYLES["brand"]),
    )

    # Show owners if available
    owners = dashboard.get("owners", [])
    if owners:
        console.print(
            f"\n{EMOJIS['user']} Owners ({len(owners)}):",
            style=RICH_STYLES["header"],
        )
        for owner in owners[:5]:  # Show first 5 owners
            name = f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip()
            email = owner.get("email", "")
            if name and email:
                console.print(f"  • {name} ({email})", style=RICH_STYLES["dim"])
            elif email:
                console.print(f"  • {email}", style=RICH_STYLES["dim"])

        if len(owners) > 5:
            console.print(f"  ... and {len(owners) - 5} more", style=RICH_STYLES["dim"])

    # Extract chart data from position_json (has more info than charts array)
    chart_data = []
    position_json_str = dashboard.get("position_json", "{}")

    try:
        import json

        position_data = json.loads(position_json_str)

        # Extract chart information from position data
        for key, item in position_data.items():
            if key.startswith("CHART-") and "meta" in item:
                meta = item["meta"]
                chart_info = {
                    "id": meta.get("chartId", ""),
                    "name": meta.get("sliceName", "Unknown"),
                    "uuid": meta.get("uuid", ""),
                    "override_name": meta.get("sliceNameOverride"),
                }
                chart_data.append(chart_info)
    except Exception:
        # Fallback to simple chart names if position_json parsing fails
        chart_names = dashboard.get("charts", [])
        chart_data = [{"id": "", "name": name, "uuid": ""} for name in chart_names]

    if chart_data:
        console.print(
            f"\n{EMOJIS['chart']} Charts ({len(chart_data)}):",
            style=RICH_STYLES["header"],
        )

        # Show table with available data (ID, Name)
        chart_table = Table(
            show_header=True,
            header_style=RICH_STYLES["header"],
            border_style="dim",
        )
        chart_table.add_column("ID", style=COLORS.secondary, no_wrap=True)
        chart_table.add_column("Name", style="bright_white", no_wrap=False)

        # Sort by ID for consistent display
        sorted_charts = sorted([c for c in chart_data if c["id"]], key=lambda x: x["id"])

        for chart in sorted_charts:
            display_name = chart["override_name"] or chart["name"]
            chart_table.add_row(str(chart["id"]), display_name)

        console.print(chart_table)

        console.print(
            "\n💡 Use [bold]sup chart info <ID>[/] for detailed chart information",
            style=RICH_STYLES["dim"],
        )


if __name__ == "__main__":
    app()
