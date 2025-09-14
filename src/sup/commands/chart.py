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
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES

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
        typer.Option("--limit", "-l", help="Maximum number of results"),
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
                    sp.text = (
                        f"Found {len(charts)} charts, "
                        f"showing {len(filtered_charts)} after filtering"
                    )
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
            # Use the new table system with proper width management
            from sup.output.tables import display_charts_table as display_charts_table_new

            workspace_hostname = ctx.get_workspace_hostname()
            display_charts_table_new(filtered_charts, workspace_hostname)

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
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
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
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(chart, default_flow_style=False, indent=2))
        else:
            display_chart_details(chart)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get chart info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("sql")
def chart_sql(
    chart_id: Annotated[int, typer.Argument(help="Chart ID to get SQL for")],
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
    Get the compiled SQL query that powers a chart.

    This shows the actual SQL that Superset generates and executes
    to produce the chart data. Perfect for understanding chart logic!

    Examples:
        sup chart sql 3628                    # Beautiful SQL display
        sup chart sql 3628 --json            # JSON format for agents
        sup chart sql 3628 --porcelain       # Machine-readable
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    if not porcelain:
        console.print(
            f"{EMOJIS['sql']} Getting compiled SQL for chart {chart_id}...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)

        # Get chart metadata first
        chart = client.get_chart(chart_id, silent=True)
        chart_name = chart.get("slice_name", "Unknown")

        # Get the compiled SQL
        query_result = client.get_chart_data(chart_id, result_type="query", silent=True)

        # Extract SQL queries
        sql_queries = []
        if "result" in query_result:
            for result_item in query_result["result"]:
                if result_item.get("query"):
                    sql_queries.append(result_item["query"])

        # Display based on output format
        if porcelain:
            # Porcelain: preserve SQL formatting, just print raw SQL
            for sql in sql_queries:
                print(sql.strip())
        elif json_output:
            import json

            output = {
                "chart_id": chart_id,
                "chart_name": chart_name,
                "sql_queries": sql_queries,
            }
            console.print(json.dumps(output, indent=2))
        elif yaml_output:
            import yaml

            output = {
                "chart_id": chart_id,
                "chart_name": chart_name,
                "sql_queries": sql_queries,
            }
            console.print(yaml.safe_dump(output, default_flow_style=False, indent=2))
        else:
            # Beautiful Rich display
            display_chart_sql_rich(chart_id, chart_name, sql_queries)

    except Exception:
        if not porcelain:
            console.print(
                f"{EMOJIS['warning']} Chart SQL endpoint under development",
                style=RICH_STYLES["warning"],
            )
            console.print(
                "API payload structure needs refinement to match Superset frontend.",
                style=RICH_STYLES["dim"],
            )
        raise typer.Exit(1)


@app.command("data")
def chart_data(
    chart_id: Annotated[int, typer.Argument(help="Chart ID to get data for")],
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
    csv_output: Annotated[bool, typer.Option("--csv", "-c", help="Output as CSV")] = False,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum rows to display"),
    ] = None,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Get the actual data results from a chart.

    This executes the chart and returns the data that would be displayed.
    Perfect for agents to access chart data programmatically!

    Examples:
        sup chart data 3628                   # Beautiful table display
        sup chart data 3628 --json           # JSON for agents
        sup chart data 3628 --csv            # CSV export
        sup chart data 3628 --limit 10       # Limit rows
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    if not porcelain:
        console.print(
            f"{EMOJIS['chart']} Getting data for chart {chart_id}...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)

        # Get chart metadata first
        chart = client.get_chart(chart_id, silent=True)
        chart_name = chart.get("slice_name", "Unknown")

        # Get the chart data
        data_result = client.get_chart_data(chart_id, result_type="results", silent=True)

        # Extract and format data
        if "result" in data_result and data_result["result"]:
            result_item = data_result["result"][0]

            if "data" in result_item:
                import pandas as pd

                data = result_item["data"]
                df = pd.DataFrame(data)

                # Apply limit if specified
                if limit:
                    df = df.head(limit)

                # Display based on output format
                if porcelain:
                    # Tab-separated values
                    for _, row in df.iterrows():
                        values = [str(val) if not pd.isna(val) else "" for val in row]
                        print("\t".join(values))
                elif json_output:
                    import json

                    console.print(
                        json.dumps(data[:limit] if limit else data, indent=2, default=str),
                    )
                elif yaml_output:
                    import yaml

                    console.print(
                        yaml.safe_dump(
                            data[:limit] if limit else data,
                            default_flow_style=False,
                            indent=2,
                        ),
                    )
                elif csv_output:
                    # CSV output
                    from io import StringIO

                    csv_buffer = StringIO()
                    df.to_csv(csv_buffer, index=False)
                    console.print(csv_buffer.getvalue().rstrip())
                else:
                    # Beautiful table using existing formatter
                    from sup.output.formatters import QueryResult, display_query_results

                    query_result = QueryResult(
                        data=df,
                        query=f"Chart data: {chart_name}",
                        execution_time=result_item.get("duration"),
                        database_id=chart.get("datasource_id"),
                    )
                    display_query_results(query_result, output_format="table", porcelain=False)
            else:
                if not porcelain:
                    console.print(
                        f"{EMOJIS['warning']} No data found in chart result",
                        style=RICH_STYLES["warning"],
                    )
                raise typer.Exit(1)
        else:
            if not porcelain:
                console.print(
                    f"{EMOJIS['warning']} Could not retrieve chart data",
                    style=RICH_STYLES["warning"],
                )
            raise typer.Exit(1)

    except Exception:
        if not porcelain:
            console.print(
                f"{EMOJIS['warning']} Chart data endpoint under development",
                style=RICH_STYLES["warning"],
            )
            console.print(
                "API payload structure needs refinement to match Superset frontend.",
                style=RICH_STYLES["dim"],
            )
        raise typer.Exit(1)


def display_chart_sql_rich(chart_id: int, chart_name: str, sql_queries: List[str]) -> None:
    """Display SQL queries with beautiful Rich formatting."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    if not sql_queries:
        console.print(
            f"{EMOJIS['warning']} No SQL queries found for chart {chart_id}",
            style=RICH_STYLES["warning"],
        )
        console.print(
            "This chart might use a dataset-based approach without direct SQL.",
            style=RICH_STYLES["dim"],
        )
        return

    console.print(
        f"{EMOJIS['sql']} SQL Query for Chart {chart_id}: {chart_name}",
        style=RICH_STYLES["header"],
    )

    for i, sql_query in enumerate(sql_queries, 1):
        title = f"SQL Query {i}" if len(sql_queries) > 1 else "Compiled SQL Query"
        sql_syntax = Syntax(sql_query, "sql", theme="monokai", line_numbers=False)
        console.print(Panel(sql_syntax, title=title, border_style=COLORS.info))


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
        border_style=RICH_STYLES["brand"],
    )

    table.add_column("ID", style=COLORS.secondary, no_wrap=True)
    table.add_column("Name", style="bright_white", no_wrap=False)
    table.add_column("Type", style=COLORS.warning, no_wrap=True)
    table.add_column("Dataset", style=COLORS.info, no_wrap=True)
    table.add_column("Dashboards", style=COLORS.success, no_wrap=True)

    for chart in charts:
        chart_id = chart.get("id", "")
        name = chart.get("slice_name", "Unknown")
        viz_type = chart.get("viz_type", "Unknown")
        dataset_name = (
            chart.get("datasource_name_text")
            or chart.get("datasource_name")
            or (f"ID:{chart.get('datasource_id')}" if chart.get("datasource_id") else "Unknown")
        )

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
            name_link = f"https://{workspace_hostname}/superset/explore/?slice_id={chart_id}"
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
    console.print(Panel(panel_content, title=f"Chart: {name}", border_style=RICH_STYLES["brand"]))

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


def display_chart_sql_compiled(ctx, client, chart_id: int, chart: Dict[str, Any]) -> None:
    """Get and display the compiled SQL query that powers a chart."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    chart_name = chart.get("slice_name", "Unknown")

    console.print(
        f"{EMOJIS['sql']} Compiled SQL Query for Chart {chart_id}: {chart_name}",
        style=RICH_STYLES["header"],
    )

    try:
        # Use the chart data endpoint to get the compiled SQL
        query_result = client.get_chart_data(chart_id, result_type="query", silent=True)

        # Extract SQL from the result
        sql_queries = []
        if "result" in query_result:
            for result_item in query_result["result"]:
                if result_item.get("query"):
                    sql_queries.append(result_item["query"])

        if sql_queries:
            for i, sql_query in enumerate(sql_queries, 1):
                title = f"SQL Query {i}" if len(sql_queries) > 1 else "Compiled SQL Query"
                sql_syntax = Syntax(sql_query, "sql", theme="monokai", line_numbers=False)
                console.print(Panel(sql_syntax, title=title, border_style=COLORS.info))
        else:
            console.print(
                f"{EMOJIS['warning']} Could not retrieve compiled SQL query",
                style=RICH_STYLES["warning"],
            )
            console.print(
                "The chart might use a complex visualization that doesn't expose SQL.",
                style=RICH_STYLES["dim"],
            )

    except Exception:
        console.print(
            f"{EMOJIS['warning']} Chart data endpoint not yet fully implemented",
            style=RICH_STYLES["warning"],
        )
        console.print(
            "This feature is under development - the API payload structure needs refinement.",
            style=RICH_STYLES["dim"],
        )
        console.print(
            f"💡 Try [bold]sup dataset info {chart.get('datasource_id', '')}[/] to see the underlying dataset",  # noqa: E501
            style=RICH_STYLES["dim"],
        )


def display_chart_data_results(ctx, client, chart_id: int, chart: Dict[str, Any]) -> None:
    """Get and display the actual data results from a chart."""
    import pandas as pd

    from sup.output.formatters import QueryResult, display_query_results

    chart_name = chart.get("slice_name", "Unknown")

    console.print(
        f"{EMOJIS['chart']} Data Results for Chart {chart_id}: {chart_name}",
        style=RICH_STYLES["header"],
    )

    try:
        # Use the chart data endpoint to get the actual data
        data_result = client.get_chart_data(chart_id, result_type="results", silent=True)

        # Extract data from the result
        if "result" in data_result and data_result["result"]:
            result_item = data_result["result"][0]  # Usually one result

            if "data" in result_item:
                # Convert to DataFrame for display
                data = result_item["data"]
                df = pd.DataFrame(data)

                # Create QueryResult object for display
                query_result = QueryResult(
                    data=df,
                    query=f"Chart data for: {chart_name}",
                    execution_time=result_item.get("duration"),
                    database_id=chart.get("datasource_id"),
                )

                # Use existing query result formatter
                display_query_results(query_result, output_format="table", porcelain=False)
            else:
                console.print(
                    f"{EMOJIS['warning']} No data found in chart result",
                    style=RICH_STYLES["warning"],
                )
        else:
            console.print(
                f"{EMOJIS['warning']} Could not retrieve chart data",
                style=RICH_STYLES["warning"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to get chart data: {e}",
            style=RICH_STYLES["error"],
        )


@app.command("export")
def export_charts(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Assets folder to export chart definitions to (defaults to configured folder)",
        ),
    ] = None,
    # Universal filters - reuse existing list command patterns
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Export specific chart by ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Export multiple charts by IDs (comma-separated)"),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name", help="Export charts matching name pattern (supports wildcards)"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", help="Export only charts you own"),
    ] = False,
    created_after: Annotated[
        Optional[str],
        typer.Option(
            "--created-after",
            help="Export charts created after date (YYYY-MM-DD)",
        ),
    ] = None,
    modified_after: Annotated[
        Optional[str],
        typer.Option(
            "--modified-after",
            help="Export charts modified after date (YYYY-MM-DD)",
        ),
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of charts to export"),
    ] = None,
    # Export-specific options
    workspace_id: Annotated[
        Optional[int],
        typer.Option(
            "--workspace-id",
            "-w",
            help="Workspace ID (defaults to configured workspace)",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files"),
    ] = False,
    disable_jinja_escaping: Annotated[
        bool,
        typer.Option(
            "--disable-jinja-escaping",
            help="Export raw YAML without escaping {{ }} templates (may cause import conflicts)",
        ),
    ] = False,
    force_unix_eol: Annotated[
        bool,
        typer.Option("--force-unix-eol", help="Force Unix end-of-line characters"),
    ] = False,
    skip_dependencies: Annotated[
        bool,
        typer.Option(
            "--skip-dependencies",
            help="Export charts only, without related datasets and database connections",
        ),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    Export chart definitions from Superset workspace to local filesystem.

    Downloads chart configurations as YAML files that can be:
    • Version controlled with git
    • Modified and re-imported
    • Backed up for disaster recovery
    • Migrated between workspaces

    The export creates a directory structure with:
    • charts/ - Chart definition files
    • datasets/ - Related dataset definitions (when dependencies included)
    • databases/ - Database connection configs (when dependencies included)
    • metadata.yaml - Export metadata

    Dependencies (datasets & databases) are included by default for complete,
    importable chart packages. Use --skip-dependencies to export charts only.

    By default, existing {{ }} Jinja2 templates in charts are escaped to prevent
    conflicts during import. Use --disable-jinja-escaping for raw export.

    Examples:
        sup chart export                             # Export all charts + dependencies
        sup chart export --mine                      # Export your charts + dependencies
        sup chart export --id=3586                  # Export specific chart + dependencies
        sup chart export --name="*sales*"           # Export matching charts + dependencies
        sup chart export --mine --skip-dependencies # Export your charts only (no deps)
    """
    import re
    from pathlib import Path
    from typing import Any, Callable, Union
    from zipfile import ZipFile

    import yaml

    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.filters.chart import apply_chart_filters, parse_chart_filters
    from sup.output.spinners import data_spinner

    # Jinja2 escaping markers (from original implementation)
    JINJA2_OPEN_MARKER = "__JINJA2_OPEN__"
    JINJA2_CLOSE_MARKER = "__JINJA2_CLOSE__"

    def get_newline_char(force_unix_eol: bool = False) -> Union[str, None]:
        """Returns the newline character used by the open function"""
        return "\n" if force_unix_eol else None

    def traverse_data(value: Any, handler: Callable) -> Any:
        """Process value according to its data type"""
        if isinstance(value, dict):
            return {k: traverse_data(v, handler) for k, v in value.items()}
        elif isinstance(value, list):
            return [traverse_data(item, handler) for item in value]
        elif isinstance(value, str):
            return handler(value)
        else:
            return value

    def handle_string(value):
        """Handle Jinja2 escaping for strings"""
        # Escape existing Jinja2 templates
        value = re.sub(r"{{", JINJA2_OPEN_MARKER, value)
        value = re.sub(r"}}", JINJA2_CLOSE_MARKER, value)
        return value

    def remove_root(file_name: str) -> str:
        """Remove root directory from file path"""
        parts = Path(file_name).parts
        return str(Path(*parts[1:])) if len(parts) > 1 else file_name

    # Resolve assets folder using config default
    ctx = SupContext()
    resolved_assets_folder = ctx.get_assets_folder(cli_override=assets_folder)

    if not porcelain:
        console.print(
            f"{EMOJIS['export']} Exporting charts to {resolved_assets_folder}...",
            style=RICH_STYLES["info"],
        )

    try:
        # Resolve assets folder path
        output_path = Path(resolved_assets_folder)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            console.print(
                f"{EMOJIS['error']} Path exists but is not a directory: {resolved_assets_folder}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        # Get charts using existing filtering logic
        client = SupSupersetClient.from_context(ctx, workspace_id)

        with data_spinner("charts to export", silent=porcelain) as sp:
            # Parse filters using existing logic
            filters = parse_chart_filters(
                id_filter=id_filter,
                ids_filter=ids_filter,
                name_filter=name_filter,
                mine_filter=mine_filter,
                team_filter=None,  # Team inferred from workspace context
                created_after=created_after,
                modified_after=modified_after,
                limit_filter=limit,
            )

            # Get all charts and apply filters
            all_charts = client.get_charts(
                silent=True,
                limit=None,  # Get all, then filter
            )
            filtered_charts = apply_chart_filters(all_charts, filters)

            # Extract IDs for export
            chart_ids = [chart["id"] for chart in filtered_charts]

            if sp:
                sp.text = f"Found {len(chart_ids)} charts to export"

        if not chart_ids:
            console.print(
                f"{EMOJIS['warning']} No charts match your filters",
                style=RICH_STYLES["warning"],
            )
            return

        # Consistent dependency policy - all filters work the same way
        should_include_dependencies = not skip_dependencies

        if not porcelain:
            dependency_msg = " (with dependencies)" if should_include_dependencies else ""
            console.print(
                f"{EMOJIS['info']} Exporting {len(chart_ids)} charts{dependency_msg}...",
                style=RICH_STYLES["info"],
            )

        # Export using existing API
        zip_buffer = client.client.export_zip("chart", chart_ids)

        # Process ZIP contents
        with ZipFile(zip_buffer) as bundle:
            contents = {
                remove_root(file_name): bundle.read(file_name).decode()
                for file_name in bundle.namelist()
            }

        # Save files to filesystem
        files_written = 0
        for file_name, file_contents in contents.items():
            # Skip related files unless dependencies are requested
            if not should_include_dependencies and not file_name.startswith("chart"):
                continue

            target = output_path / file_name
            if target.exists() and not overwrite:
                if not porcelain:
                    console.print(
                        f"{EMOJIS['warning']} File exists, skipping: {target}",
                        style=RICH_STYLES["warning"],
                    )
                continue

            # Create directory if needed
            if not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)

            # Handle Jinja2 escaping if requested
            if not disable_jinja_escaping:
                try:
                    asset_content = yaml.safe_load(file_contents)
                    for key, value in asset_content.items():
                        asset_content[key] = traverse_data(value, handle_string)
                    file_contents = yaml.dump(asset_content, sort_keys=False)
                except yaml.YAMLError:
                    # If YAML parsing fails, write as-is
                    pass

            # Write file with proper line endings
            newline = get_newline_char(force_unix_eol)
            with open(target, "w", encoding="utf-8", newline=newline) as output:
                output.write(file_contents)

            files_written += 1

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} Exported {files_written} files to {resolved_assets_folder}",
                style=RICH_STYLES["success"],
            )
        else:
            print(f"{files_written}\t{resolved_assets_folder}")

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to export charts: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
