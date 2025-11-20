"""
DRY Refactored chart management commands for sup CLI.

Demonstrates how chart commands become much cleaner with decorators
and consolidated output handling.
"""

from typing import Optional

import typer
from typing_extensions import Annotated

from sup.config.settings import OutputOptions
from sup.decorators import with_output_options, with_universal_filters
from sup.filters.base import UniversalFilters
from sup.filters.chart import apply_chart_filters
from sup.output.formatters import display_entity_results
from sup.output.styles import EMOJIS, RICH_STYLES
from sup.output.tables import display_charts_table
from sup.output.console import console

app = typer.Typer(help="Manage charts", no_args_is_help=True)


@app.command("list")
@with_universal_filters
@with_output_options
def list_charts(
    filters: UniversalFilters,
    output: OutputOptions,
    # Only chart-specific filters
    dashboard_id: Annotated[
        Optional[int],
        typer.Option("--dashboard-id", help="Filter by dashboard ID"),
    ] = None,
    viz_type: Annotated[
        Optional[str],
        typer.Option("--viz-type", help="Filter by visualization type"),
    ] = None,
    dataset_id: Annotated[
        Optional[int],
        typer.Option("--dataset-id", help="Filter by dataset ID"),
    ] = None,
):
    """
    List charts - now with 80% less code duplication!

    Compare this to chart.py - we went from 110 lines of parameters
    to just 3 entity-specific parameters.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        # Create ChartFilters from universal filters with chart-specific fields
        from sup.filters.chart import ChartFilters

        chart_filters = ChartFilters(
            # Copy universal filters
            id=filters.id,
            ids=filters.ids,
            name=filters.name,
            mine=filters.mine,
            team_id=filters.team_id,
            created_after=filters.created_after,
            modified_after=filters.modified_after,
            limit=filters.limit,
            offset=filters.offset,
            page=filters.page,
            page_size=filters.page_size,
            order=filters.order,
            desc=filters.desc,
            # Chart-specific filters
            dashboard_id=dashboard_id,
            viz_type=viz_type,
            dataset_id=dataset_id,
        )

        # Get charts with spinner
        with data_spinner("charts", silent=output.porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, output.workspace_id)

            page = (filters.page - 1) if filters.page else 0
            charts = client.get_charts(silent=True, limit=filters.limit, page=page)

            filtered_charts = apply_chart_filters(charts, chart_filters)

            if sp:
                sp.text = (
                    f"Found {len(charts)} charts, showing {len(filtered_charts)} after filtering"
                )

        # Single consolidated output call
        display_entity_results(
            items=filtered_charts,
            output_format=output.format.value,
            porcelain=output.porcelain,
            porcelain_fields=[
                "id",
                "slice_name",
                "viz_type",
                "datasource_name",
                "dashboards",
            ],
            table_display_func=lambda items: display_charts_table(
                items,
                ctx.get_workspace_hostname(),
            ),
        )

    except Exception as e:
        if not output.porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list charts: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
@with_output_options
def chart_info(
    chart_id: Annotated[int, typer.Argument(help="Chart ID to inspect")],
    output: OutputOptions,
):
    """Chart info - no more repeated parameter definitions!"""
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    if not output.porcelain:
        console.print(
            f"{EMOJIS['info']} Loading chart {chart_id} details...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, output.workspace_id)
        chart = client.get_chart(chart_id, silent=output.porcelain)

        if output.porcelain:
            print(f"{chart_id}\t{chart.get('slice_name', '')}\t{chart.get('viz_type', '')}")
        elif output.json_output:
            import json

            print(json.dumps(chart, indent=2, default=str))
        else:
            from sup.commands.chart import display_chart_details

            display_chart_details(chart)

    except Exception as e:
        if not output.porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get chart info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
