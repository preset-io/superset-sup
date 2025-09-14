"""
Dataset management commands for sup CLI.

Handles dataset listing, details, export, import, and sync operations.
"""

from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from sup.filters.dataset import apply_dataset_filters, parse_dataset_filters
from sup.output.formatters import display_porcelain_list
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage datasets", no_args_is_help=True)
console = Console()


@app.command("list")
def list_datasets(
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
        typer.Option("--mine", help="Show only datasets you own"),
    ] = False,
    team_filter: Annotated[
        Optional[int],
        typer.Option("--team", help="Filter by team ID"),
    ] = None,
    created_after: Annotated[
        Optional[str],
        typer.Option(
            "--created-after",
            help="Show datasets created after date (YYYY-MM-DD)",
        ),
    ] = None,
    modified_after: Annotated[
        Optional[str],
        typer.Option(
            "--modified-after",
            help="Show datasets modified after date (YYYY-MM-DD)",
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
    # Dataset-specific filters
    database_id: Annotated[
        Optional[int],
        typer.Option("--database-id", help="Filter by database ID"),
    ] = None,
    schema: Annotated[
        Optional[str],
        typer.Option("--schema", help="Filter by schema name pattern"),
    ] = None,
    table_type: Annotated[
        Optional[str],
        typer.Option("--table-type", help="Filter by table type (table, view, etc.)"),
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
    List datasets in the current or specified workspace.

    Examples:
        sup dataset list                                    # All datasets
        sup dataset list --mine                            # My datasets only
        sup dataset list --database-id=1 --porcelain      # Specific DB, machine-readable
        sup dataset list --name="sales*" --json           # Pattern matching, JSON
        sup dataset list --modified-after=2024-01-01      # Recent modifications
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        # Parse filters
        filters = parse_dataset_filters(
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
            database_id,
            schema,
            table_type,
        )

        # Get datasets from API with spinner (using server-side filtering for performance)
        with data_spinner("datasets", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Fetch datasets with fast pagination - only one page
            page = (filters.page - 1) if filters.page else 0
            datasets = client.get_datasets(silent=True, limit=filters.limit, page=page)

            # Apply complex client-side filters only if needed
            from sup.filters.api_params import needs_client_side_filtering

            if (
                needs_client_side_filtering(filters)
                or filters.database_id
                or filters.schema
                or filters.table_type
            ):
                filtered_datasets = apply_dataset_filters(datasets, filters)
            else:
                filtered_datasets = datasets

            # Update spinner with results
            if sp:
                if filtered_datasets != datasets:
                    sp.text = (
                        f"Found {len(datasets)} datasets, "
                        f"showing {len(filtered_datasets)} after filtering"
                    )
                else:
                    sp.text = f"Found {len(datasets)} datasets"

        # Display results
        if porcelain:
            # Tab-separated: ID, Name, Database, Schema, Type
            display_porcelain_list(
                filtered_datasets,
                ["id", "table_name", "database_name", "schema", "kind"],
            )
        elif json_output:
            import json

            console.print(json.dumps(filtered_datasets, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(filtered_datasets, default_flow_style=False, indent=2),
            )
        else:
            # Get hostname for clickable links
            workspace_hostname = ctx.get_workspace_hostname()
            display_datasets_table(filtered_datasets, workspace_hostname)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list datasets: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
def dataset_info(
    dataset_id: Annotated[int, typer.Argument(help="Dataset ID to inspect")],
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
    Show detailed information about a dataset.

    Displays schema, columns, metrics, and metadata.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    if not porcelain:
        console.print(
            f"{EMOJIS['info']} Loading dataset {dataset_id} details...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)
        dataset = client.get_dataset(dataset_id, silent=porcelain)

        if porcelain:
            # Simple key-value output
            print(
                f"{dataset_id}\t{dataset.get('table_name', '')}\t{dataset.get('database_name', '')}",  # noqa: E501
            )
        elif json_output:
            import json

            console.print(json.dumps(dataset, indent=2, default=str))
        else:
            display_dataset_details(dataset)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get dataset info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("export")
def export_dataset(
    dataset_id: Annotated[
        Optional[int],
        typer.Argument(help="Dataset ID to export"),
    ] = None,
    folder: Annotated[
        Optional[str],
        typer.Option("--folder", help="Export folder (default: ./assets/)"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview export without writing files"),
    ] = False,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    # Filter options for bulk export
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Export multiple datasets (comma-separated IDs)"),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name", help="Export datasets matching name pattern"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", help="Export only datasets you own"),
    ] = False,
):
    """
    Export dataset(s) to YAML files.

    Examples:
        sup dataset export 123                           # Export single dataset
        sup dataset export --ids=1,2,3 --folder=./backup/  # Export multiple to custom folder
        sup dataset export --mine --dry-run             # Preview export of my datasets
    """
    console.print(
        f"{EMOJIS['export']} Exporting datasets...",
        style=RICH_STYLES["info"],
    )
    # TODO: Implement dataset export
    console.print(
        f"{EMOJIS['warning']} Dataset export not yet implemented",
        style=RICH_STYLES["warning"],
    )


def display_datasets_table(
    datasets: List[Dict[str, Any]],
    workspace_hostname: Optional[str] = None,
) -> None:
    """Display datasets in a beautiful Rich table with clickable links."""
    if not datasets:
        console.print(
            f"{EMOJIS['warning']} No datasets found",
            style=RICH_STYLES["warning"],
        )
        return

    table = Table(
        title=f"{EMOJIS['table']} Available Datasets",
        show_header=True,
        header_style=RICH_STYLES["header"],
        border_style="cyan",
    )

    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bright_white", no_wrap=False)
    table.add_column("Database", style="yellow", no_wrap=True)
    table.add_column("Schema", style="blue", no_wrap=True)
    table.add_column("Type", style="green", no_wrap=True)
    table.add_column("Columns", style=RICH_STYLES["accent"], no_wrap=True)

    for dataset in datasets:
        dataset_id = dataset.get("id", "")
        name = dataset.get("table_name", dataset.get("name", "Unknown"))
        database_name = dataset.get("database", {}).get("database_name", "Unknown")
        schema = dataset.get("schema", "") or "default"
        kind = dataset.get("kind", "physical")
        column_count = len(dataset.get("columns", []))

        # Create clickable links if hostname available
        if workspace_hostname:
            # ID links to API endpoint
            id_link = f"https://{workspace_hostname}/api/v1/dataset/{dataset_id}"
            id_display = f"[link={id_link}]{dataset_id}[/link]"

            # Name links to explore page (use explore_url if available)
            explore_url = dataset.get("explore_url")
            if explore_url:
                name_link = f"https://{workspace_hostname}{explore_url}"
            else:
                # Fallback to table list with filter
                name_link = (
                    f"https://{workspace_hostname}/tablemodelview/list/?_flt_1_table_name={name}"
                )
            name_display = f"[link={name_link}]{name}[/link]"
        else:
            # No clickable links if no hostname
            id_display = str(dataset_id)
            name_display = name

        table.add_row(
            id_display,
            name_display,
            database_name,
            schema,
            kind,
            str(column_count),
        )

    console.print(table)
    console.print(
        "\n💡 Use [bold]sup dataset info <ID>[/] for detailed information",
        style=RICH_STYLES["dim"],
    )

    if workspace_hostname:
        console.print(
            "🔗 Click ID for API endpoint, Name for GUI exploration",
            style=RICH_STYLES["dim"],
        )


def display_dataset_details(dataset: Dict[str, Any]) -> None:
    """Display detailed dataset information."""
    from rich.panel import Panel

    dataset_id = dataset.get("id", "")
    name = dataset.get("table_name", dataset.get("name", "Unknown"))
    database_info = dataset.get("database", {})

    # Basic info
    info_lines = [
        f"ID: {dataset_id}",
        f"Name: {name}",
        f"Database: {database_info.get('database_name', 'Unknown')}",
        f"Schema: {dataset.get('schema', 'default')}",
        f"Type: {dataset.get('kind', 'physical')}",
        f"Columns: {len(dataset.get('columns', []))}",
    ]

    if dataset.get("description"):
        info_lines.append(f"Description: {dataset['description']}")

    panel_content = "\n".join(info_lines)
    console.print(Panel(panel_content, title=f"Dataset: {name}", border_style="cyan"))

    # Show columns if available
    columns = dataset.get("columns", [])
    if columns:
        console.print(f"\n{EMOJIS['info']} Columns:", style=RICH_STYLES["header"])

        col_table = Table(
            show_header=True,
            header_style=RICH_STYLES["header"],
            border_style="dim",
        )
        col_table.add_column("Name", style="cyan")
        col_table.add_column("Type", style="yellow")
        col_table.add_column("Description", style="dim")

        for col in columns[:20]:  # Limit to first 20 columns
            col_name = col.get("column_name", "")
            col_type = col.get("type", "")
            col_desc = col.get("description", "") or "-"
            col_table.add_row(col_name, col_type, col_desc)

        console.print(col_table)

        if len(columns) > 20:
            console.print(
                f"... and {len(columns) - 20} more columns",
                style=RICH_STYLES["dim"],
            )
