"""
Chart management commands for sup CLI.

Handles chart listing, details, export, import, and sync operations.
"""

from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from sup.filters.chart import apply_chart_filters, parse_chart_filters
from sup.output.formatters import display_porcelain_list
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage charts", no_args_is_help=True)
console = Console()


@app.command("list")
def list_charts(
    # Universal filters
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Filter by specific ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Filter by multiple IDs (comma-separated)"),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name", help="Filter by name pattern (supports wildcards)"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", help="Show only charts you own"),
    ] = False,
    team_filter: Annotated[
        Optional[int],
        typer.Option("--team", help="Filter by team ID"),
    ] = None,
    created_after: Annotated[
        Optional[str],
        typer.Option(
            "--created-after",
            help="Show charts created after date (YYYY-MM-DD)",
        ),
    ] = None,
    modified_after: Annotated[
        Optional[str],
        typer.Option(
            "--modified-after",
            help="Show charts modified after date (YYYY-MM-DD)",
        ),
    ] = None,
    limit_filter: Annotated[
        Optional[int],
        typer.Option("--limit", help="Maximum number of results"),
    ] = None,
    offset_filter: Annotated[
        Optional[int],
        typer.Option("--offset", help="Skip first n results"),
    ] = None,
    page_filter: Annotated[
        Optional[int],
        typer.Option("--page", help="Page number (alternative to offset)"),
    ] = None,
    page_size_filter: Annotated[
        Optional[int],
        typer.Option("--page-size", help="Results per page (default: 100)"),
    ] = None,
    order_filter: Annotated[
        Optional[str],
        typer.Option("--order", help="Sort by field (name, created, modified, id)"),
    ] = None,
    desc_filter: Annotated[
        bool,
        typer.Option("--desc", help="Sort descending (default: ascending)"),
    ] = False,
    # Chart-specific filters
    dashboard_id: Annotated[
        Optional[int],
        typer.Option("--dashboard-id", help="Filter by dashboard ID"),
    ] = None,
    viz_type: Annotated[
        Optional[str],
        typer.Option(
            "--viz-type",
            help="Filter by visualization type (bar, line, etc.)",
        ),
    ] = None,
    dataset_id: Annotated[
        Optional[int],
        typer.Option("--dataset-id", help="Filter by dataset ID"),
    ] = None,
    # Output options
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
    List charts in the current or specified workspace.

    Examples:
        sup chart list                                    # All charts
        sup chart list --mine                            # My charts only
        sup chart list --dashboard-id=45 --porcelain    # Charts in dashboard, machine-readable
        sup chart list --viz-type="bar*" --json         # Bar charts, JSON
        sup chart list --modified-after=2024-01-01      # Recent modifications
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        # Parse filters
        filters = parse_chart_filters(
            id_filter,
            ids_filter,
            name_filter,
            mine_filter,
            team_filter,
            created_after,
            modified_after,
            limit_filter,
            offset_filter,
            page_filter,
            page_size_filter,
            order_filter,
            desc_filter,
            dashboard_id,
            viz_type,
            dataset_id,
        )

        # Get charts from API with spinner (using server-side filtering for performance)
        with data_spinner("charts", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Fetch charts with fast pagination - only one page
            page = (filters.page - 1) if filters.page else 0
            charts = client.get_charts(silent=True, limit=filters.limit, page=page)

            # Apply complex client-side filters only if needed
            from sup.filters.api_params import needs_client_side_filtering

            if (
                needs_client_side_filtering(filters)
                or filters.dashboard_id
                or filters.viz_type
                or filters.dataset_id
            ):
                filtered_charts = apply_chart_filters(charts, filters)
            else:
                filtered_charts = charts

            # Update spinner with results
            if sp:
                if filtered_charts != charts:
                    sp.text = f"Found {len(charts)} charts, showing {len(filtered_charts)} after filtering"
                else:
                    sp.text = f"Found {len(charts)} charts"

        # Display results
        if porcelain:
            # Tab-separated: ID, Name, VizType, Dataset, Dashboard
            display_porcelain_list(
                filtered_charts,
                ["id", "slice_name", "viz_type", "datasource_name", "dashboards"],
            )
        elif json_output:
            import json

            console.print(json.dumps(filtered_charts, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(filtered_charts, default_flow_style=False, indent=2),
            )
        else:
            # Get hostname for clickable links
            workspace_hostname = ctx.get_workspace_hostname()
            display_charts_table(filtered_charts, workspace_hostname)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list charts: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
def chart_info(
    chart_id: Annotated[int, typer.Argument(help="Chart ID to inspect")],
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Show detailed information about a chart.

    Displays visualization type, query, dataset, and metadata.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    if not porcelain:
        console.print(
            f"{EMOJIS['info']} Loading chart {chart_id} details...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)
        chart = client.get_chart(chart_id, silent=porcelain)

        if porcelain:
            # Simple key-value output
            print(
                f"{chart_id}\t{chart.get('slice_name', '')}\t{chart.get('viz_type', '')}",
            )
        elif json_output:
            import json

            console.print(json.dumps(chart, indent=2, default=str))
        else:
            display_chart_details(chart)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get chart info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_charts_table(
    charts: List[Dict[str, Any]],
    workspace_hostname: Optional[str] = None,
) -> None:
    """Display charts in a beautiful Rich table with clickable links."""
    if not charts:
        console.print(
            f"{EMOJIS['warning']} No charts found",
            style=RICH_STYLES["warning"],
        )
        return

    table = Table(
        title=f"{EMOJIS['chart']} Available Charts",
        show_header=True,
        header_style=RICH_STYLES["header"],
        border_style="magenta",
    )

    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bright_white", no_wrap=False)
    table.add_column("Type", style="yellow", no_wrap=True)
    table.add_column("Dataset", style="blue", no_wrap=True)
    table.add_column("Dashboards", style="green", no_wrap=True)

    for chart in charts:
        chart_id = chart.get("id", "")
        name = chart.get("slice_name", "Unknown")
        viz_type = chart.get("viz_type", "Unknown")
        dataset_name = chart.get("datasource_name", "Unknown")

        # Handle dashboards (can be multiple)
        dashboards = chart.get("dashboards", [])
        dashboard_names = ", ".join(
            [str(d.get("dashboard_title", d.get("id", ""))) for d in dashboards[:2]],
        )
        if len(dashboards) > 2:
            dashboard_names += f" (+{len(dashboards) - 2} more)"

        # Create clickable links if hostname available
        if workspace_hostname:
            # ID links to API endpoint
            id_link = f"https://{workspace_hostname}/api/v1/chart/{chart_id}"
            id_display = f"[link={id_link}]{chart_id}[/link]"

            # Name links to chart editor
            name_link = (
                f"https://{workspace_hostname}/superset/explore/?slice_id={chart_id}"
            )
            name_display = f"[link={name_link}]{name}[/link]"
        else:
            # No clickable links if no hostname
            id_display = str(chart_id)
            name_display = name

        table.add_row(
            id_display,
            name_display,
            viz_type,
            dataset_name,
            dashboard_names or "None",
        )

    console.print(table)
    console.print(
        "\n💡 Use [bold]sup chart info <ID>[/] for detailed information",
        style=RICH_STYLES["dim"],
    )

    if workspace_hostname:
        console.print(
            "🔗 Click ID for API endpoint, Name for chart editor",
            style=RICH_STYLES["dim"],
        )


def display_chart_details(chart: Dict[str, Any]) -> None:
    """Display detailed chart information."""
    from rich.panel import Panel

    chart_id = chart.get("id", "")
    name = chart.get("slice_name", "Unknown")
    viz_type = chart.get("viz_type", "Unknown")

    # Basic info
    info_lines = [
        f"ID: {chart_id}",
        f"Name: {name}",
        f"Visualization Type: {viz_type}",
        f"Dataset: {chart.get('datasource_name', 'Unknown')}",
    ]

    if chart.get("description"):
        info_lines.append(f"Description: {chart['description']}")

    panel_content = "\n".join(info_lines)
    console.print(Panel(panel_content, title=f"Chart: {name}", border_style="magenta"))

    # Show dashboards if available
    dashboards = chart.get("dashboards", [])
    if dashboards:
        console.print(
            f"\n{EMOJIS['info']} Used in {len(dashboards)} dashboard(s):",
            style=RICH_STYLES["header"],
        )
        for dashboard in dashboards[:5]:  # Show first 5 dashboards
            dash_name = dashboard.get(
                "dashboard_title",
                f"Dashboard {dashboard.get('id', '')}",
            )
            console.print(f"  • {dash_name}", style=RICH_STYLES["dim"])

        if len(dashboards) > 5:
            console.print(
                f"  ... and {len(dashboards) - 5} more",
                style=RICH_STYLES["dim"],
            )
