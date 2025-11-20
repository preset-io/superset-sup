"""
Chart management commands for sup CLI.

Handles chart listing, details, export, import, and sync operations.
"""

from typing import Any, Dict, List, Optional

import typer
from rich.table import Table
from typing_extensions import Annotated

from sup.commands.template_params import DisableJinjaOption, LoadEnvOption, TemplateOptions
from sup.filters.chart import parse_chart_filters
from sup.output.console import console
from sup.output.formatters import display_porcelain_list
from sup.output.spinners import data_spinner, query_spinner
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage charts", no_args_is_help=True)


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
    search_filter: Annotated[
        Optional[str],
        typer.Option(
            "--search",
            help="Search charts by text (server-side search across multiple fields)",
        ),
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
        sup chart list --search="week" --limit 10        # Server search for "week", max 10
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
            search_filter,
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

            # Use server-side filtering where available
            page = (filters.page - 1) if filters.page else 0
            charts = client.get_charts(
                silent=True,
                limit=None,  # Get all charts for client-side filtering
                page=page,
                text_search=filters.search,  # Pass search term to server
            )

            # Apply client-side filters for chart-specific options
            from sup.filters.chart import apply_chart_filters

            # Get current user ID for --mine filter
            current_user_id = None
            if filters.mine:
                try:
                    current_user = client.client.get_me()  # type: ignore[attr-defined]
                    current_user_id = current_user.get("id")
                except Exception:
                    pass

            charts = apply_chart_filters(charts, filters, current_user_id)

            # Apply limit after filtering
            if filters.limit:
                charts = charts[: filters.limit]

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(charts)} charts"

        # Display results
        if porcelain:
            # Tab-separated: ID, Name, VizType, Dataset, Dashboard
            display_porcelain_list(
                charts,
                ["id", "slice_name", "viz_type", "datasource_name", "dashboards"],
            )
        elif json_output:
            import json

            console.print(json.dumps(charts, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(charts, default_flow_style=False, indent=2),
            )
        else:
            # Use the new table system with proper width management
            from sup.output.tables import display_charts_table as display_charts_table_new

            workspace_hostname = ctx.get_workspace_hostname()
            display_charts_table_new(charts, workspace_hostname)

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
    from sup.output.spinners import data_spinner

    try:
        with data_spinner(f"chart {chart_id}", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)
            chart = client.get_chart(chart_id, silent=True)

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
            workspace_hostname = ctx.get_workspace_hostname()
            display_chart_details(chart, workspace_hostname, client)

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

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)

        # Get chart metadata and SQL with spinner
        with query_spinner(f"chart {chart_id} SQL", silent=porcelain) as sp:
            # Get chart metadata first
            chart = client.get_chart(chart_id, silent=True)
            chart_name = chart.get("slice_name", "Unknown")

            if sp:
                sp.text = f"Getting compiled SQL for chart: {chart_name}"

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

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to retrieve chart SQL: {e}",
                style=RICH_STYLES["error"],
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

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)

        # Get chart metadata and data with spinner
        with data_spinner(f"chart {chart_id} data", silent=porcelain) as sp:
            # Get chart metadata first
            chart = client.get_chart(chart_id, silent=True)
            chart_name = chart.get("slice_name", "Unknown")

            if sp:
                sp.text = f"Getting data for chart: {chart_name}"

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

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to retrieve chart data: {e}",
                style=RICH_STYLES["error"],
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


def display_chart_details(
    chart: Dict[str, Any],
    workspace_hostname: Optional[str] = None,
    client: Optional[Any] = None,
) -> None:
    """Display detailed chart information."""
    import json

    from rich.panel import Panel

    chart_id = chart.get("id", "")
    name = chart.get("slice_name", "Unknown")
    viz_type = chart.get("viz_type", "Unknown")

    # Try to get dataset name from multiple sources
    dataset_name = chart.get("datasource_name_text") or chart.get("datasource_name")

    # If not in chart metadata, try to extract datasource ID and fetch dataset
    if (not dataset_name or dataset_name == "Unknown") and client:
        dataset_id = None
        dataset_type = None

        # Try query_context first (most reliable - current datasource)
        query_context = chart.get("query_context")
        if query_context and query_context not in ["", "{}"]:
            try:
                qc_data = (
                    json.loads(query_context) if isinstance(query_context, str) else query_context
                )
                datasource_info = qc_data.get("datasource")
                if datasource_info and isinstance(datasource_info, dict):
                    dataset_id = datasource_info.get("id")
                    dataset_type = datasource_info.get("type")
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass

        # Fallback to params if query_context didn't work
        if not dataset_id:
            params = chart.get("params", "{}")
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                    datasource_key = params.get("datasource")
                    if datasource_key and "__" in datasource_key:
                        dataset_id, dataset_type = datasource_key.split("__")
                        dataset_id = int(dataset_id)
                except (json.JSONDecodeError, ValueError):
                    pass

        # Now fetch the dataset if we have an ID
        if dataset_id:
            try:
                response = client.client.session.get(
                    f"{client.client.baseurl}/api/v1/dataset/{dataset_id}"
                )
                if response.status_code == 200:
                    dataset_data = response.json()
                    if "result" in dataset_data:
                        ds = dataset_data["result"]
                        table_name = ds.get("table_name", "")
                        schema = ds.get("schema", "")
                        if schema and table_name:
                            dataset_name = f"{schema}.{table_name}"
                        elif table_name:
                            dataset_name = table_name
                        else:
                            dataset_name = f"Dataset ID: {dataset_id}"
                else:
                    dataset_name = f"Dataset ID: {dataset_id} (not found)"
            except Exception:
                dataset_name = f"Dataset ID: {dataset_id}"

    if not dataset_name:
        dataset_name = "Unknown"

    # Basic info
    info_lines = [
        f"ID: {chart_id}",
        f"Name: {name}",
        f"Visualization Type: {viz_type}",
        f"Dataset: {dataset_name}",
    ]

    # Add chart URL if hostname available
    if workspace_hostname:
        chart_url = f"https://{workspace_hostname}/explore/?slice_id={chart_id}"
        info_lines.append(f"URL: {chart_url}")

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


@app.command("pull")
def pull_charts(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Assets folder to pull chart definitions to (defaults to configured folder)",
        ),
    ] = None,
    # Universal filters - reuse existing list command patterns
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Pull specific chart by ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Pull multiple charts by IDs (comma-separated)"),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name", help="Pull charts matching name pattern (supports wildcards)"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", help="Pull only charts you own"),
    ] = False,
    created_after: Annotated[
        Optional[str],
        typer.Option(
            "--created-after",
            help="Pull charts created after date (YYYY-MM-DD)",
        ),
    ] = None,
    modified_after: Annotated[
        Optional[str],
        typer.Option(
            "--modified-after",
            help="Pull charts modified after date (YYYY-MM-DD)",
        ),
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of charts to pull"),
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
    Pull chart definitions from Superset workspace to local filesystem.

    Downloads chart configurations as YAML files that can be:
    • Version controlled with git
    • Modified and pushed back
    • Backed up for disaster recovery
    • Migrated between workspaces

    The pull creates a directory structure with:
    • charts/ - Chart definition files
    • datasets/ - Related dataset definitions (when dependencies included)
    • databases/ - Database connection configs (when dependencies included)
    • metadata.yaml - Pull metadata

    Dependencies (datasets & databases) are included by default for complete,
    pushable chart packages. Use --skip-dependencies to pull charts only.

    By default, existing {{ }} Jinja2 templates in charts are escaped to prevent
    conflicts during push. Use --disable-jinja-escaping for raw pull.

    Examples:
        sup chart pull                               # Pull all charts + dependencies
        sup chart pull --mine                        # Pull your charts + dependencies
        sup chart pull --id=3586                    # Pull specific chart + dependencies
        sup chart pull --name="*sales*"             # Pull matching charts + dependencies
        sup chart pull --mine --skip-dependencies   # Pull your charts only (no deps)
    """
    import re
    from pathlib import Path
    from typing import Any, Callable, Union
    from zipfile import ZipFile

    import yaml

    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.filters.chart import parse_chart_filters
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
                search_filter=name_filter,  # Map legacy name_filter to new search_filter
                mine_filter=mine_filter,
                team_filter=None,  # Team inferred from workspace context
                created_after=created_after,
                modified_after=modified_after,
                limit_filter=limit,
            )

            # Get charts with server-side filtering only
            charts = client.get_charts(
                silent=True,
                limit=None,  # Get all matching charts
                text_search=filters.search,  # Server-side search
            )

            # Extract IDs for export
            chart_ids = [chart["id"] for chart in charts]

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


@app.command("push")
def push_charts(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Assets folder to push chart definitions from (defaults to configured folder)",
        ),
    ] = None,
    # Import-specific options
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
        typer.Option("--overwrite", help="Overwrite existing charts"),
    ] = False,
    # Template processing options
    template_options: TemplateOptions = None,
    load_env: LoadEnvOption = False,
    disable_jinja_templating: DisableJinjaOption = False,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            help="Continue importing even if some charts fail",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation prompts (use with caution)",
        ),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    Push chart definitions from local filesystem to Superset workspace.

    Reads chart configurations from YAML files and creates/updates charts in
    the workspace. Automatically handles dependencies (datasets, databases)
    when present in the assets folder.

    The push processes directory structure:
    • charts/ - Chart definition files to push
    • datasets/ - Dataset definitions (pushed first as dependencies)
    • databases/ - Database connections (pushed first as dependencies)
    • metadata.yaml - Push metadata and validation

    Dependencies are pushed in correct order: databases → datasets → charts
    to ensure all required objects exist before chart creation.

    By default, Jinja2 templating is enabled for parameterized assets.
    Use --disable-jinja-templating to push raw YAML without processing.

    Template Support:
    • --option key=value: Pass template variables (can be used multiple times)
    • --load-env: Make environment variables available as env['VAR_NAME']
    • chart.overrides.yaml files are automatically applied

    Examples:
        sup chart push                               # Push to configured target workspace
        sup chart push ./backup                      # Push from specific folder
        sup chart push --workspace-id=456            # Push to specific workspace
        sup chart push --overwrite --force           # Overwrite without confirmation
        sup chart push --continue-on-error           # Skip failed charts, continue
        sup chart push --option env=prod --load-env  # Template with variables
    """
    from preset_cli.cli.superset.sync.native.command import ResourceType, native
    from sup.config.settings import SupContext

    # Resolve assets folder using config default
    ctx = SupContext()
    resolved_assets_folder = ctx.get_assets_folder(cli_override=assets_folder)

    if not porcelain:
        console.print(
            f"{EMOJIS['import']} Importing charts from {resolved_assets_folder}...",
            style=RICH_STYLES["info"],
        )

    try:
        # Verify assets folder exists
        from pathlib import Path

        assets_path = Path(resolved_assets_folder)
        if not assets_path.exists():
            console.print(
                f"{EMOJIS['error']} Assets folder does not exist: {resolved_assets_folder}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)
        elif not assets_path.is_dir():
            console.print(
                f"{EMOJIS['error']} Path is not a directory: {resolved_assets_folder}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        # Create a mock click context for the native() function
        # This reuses ALL the existing import logic while providing sup UX
        import click

        from sup.auth.preset import SupPresetAuth

        # Get source and target workspace context
        source_workspace_id = ctx.get_workspace_id()
        target_workspace_id = ctx.get_target_workspace_id(cli_override=workspace_id)

        if not source_workspace_id:
            console.print(
                f"{EMOJIS['error']} No source workspace configured",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup workspace list[/] and [bold]sup workspace use <ID>[/]",
                style=RICH_STYLES["info"],
            )
            raise typer.Exit(1)

        if not target_workspace_id:
            console.print(
                f"{EMOJIS['error']} No target workspace configured",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Set target: [bold]sup workspace set-import-target[/]",
                style=RICH_STYLES["info"],
            )
            raise typer.Exit(1)

        # Safety confirmation for potentially destructive imports
        if not force and not porcelain:
            is_cross_workspace = target_workspace_id != source_workspace_id

            console.print(
                f"{EMOJIS['warning']} Import Operation Summary",
                style=RICH_STYLES["warning"],
            )
            console.print(f"📁 Assets folder: [cyan]{resolved_assets_folder}[/cyan]")
            console.print(f"📤 Source workspace: [cyan]{source_workspace_id}[/cyan]")
            console.print(f"📥 Target workspace: [cyan]{target_workspace_id}[/cyan]")

            if is_cross_workspace:
                console.print(
                    "🔄 [bold]Cross-workspace import[/bold] - assets copied to different workspace",
                    style=RICH_STYLES["info"],
                )
            else:
                console.print(
                    "⚠️  [bold]Same-workspace import[/bold] - may overwrite existing charts",
                    style=RICH_STYLES["warning"],
                )

            if not typer.confirm("Continue with import operation?"):
                console.print(
                    f"{EMOJIS['info']} Import cancelled",
                    style=RICH_STYLES["info"],
                )
                raise typer.Exit(0)

        # Get target workspace URL (where we're importing TO)
        # We need to resolve the hostname for the TARGET workspace, not source
        from sup.clients.preset import SupPresetClient

        preset_client = SupPresetClient.from_context(ctx, silent=True)
        workspaces = preset_client.get_all_workspaces(silent=True)

        target_workspace = None
        for ws in workspaces:
            if ws.get("id") == target_workspace_id:
                target_workspace = ws
                break

        if not target_workspace:
            console.print(
                f"{EMOJIS['error']} Target workspace {target_workspace_id} not found",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        target_hostname = target_workspace.get("hostname")
        if not target_hostname:
            console.print(
                f"{EMOJIS['error']} No hostname for target workspace {target_workspace_id}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        workspace_url = f"https://{target_hostname}/"
        auth = SupPresetAuth.from_sup_config(ctx, silent=True)

        # Create mock click context that native() expects
        # Use a minimal command for the context
        import_command = click.Command("import")
        mock_ctx = click.Context(import_command)
        mock_ctx.obj = {
            "AUTH": auth,
            "INSTANCE": workspace_url,
        }

        if not porcelain:
            console.print(
                f"{EMOJIS['info']} Processing charts and dependencies...",
                style=RICH_STYLES["info"],
            )

        # Call the existing native() function with chart-specific settings
        # This gives us ALL the existing functionality: dependency resolution,
        # Jinja2 templating, database password handling, error management, etc.
        #
        # NOTE: native() is decorated with @click.pass_context, so we need to
        # manually pass the context using click's invoke() method
        with mock_ctx:
            mock_ctx.invoke(
                native,
                directory=resolved_assets_folder,
                option=template_options or (),  # Pass custom template variables
                asset_type=ResourceType.CHART,
                overwrite=overwrite,
                disable_jinja_templating=disable_jinja_templating,
                disallow_edits=True,  # Mark as externally managed
                external_url_prefix="",  # No external URL prefix
                load_env=load_env,  # Load environment variables if requested
                split=True,  # Import individually with dependency resolution
                continue_on_error=continue_on_error,
                db_password=(),  # No database passwords specified
            )

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} Chart import completed successfully",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        # Re-raise typer exits (our own error handling)
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to import charts: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
