"""
Dataset management commands for sup CLI.

Handles dataset listing, details, export, import, and sync operations.
"""

from typing import Any, Dict, List, Optional

import typer

# Removed: from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.formatters import display_porcelain_list
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage datasets", no_args_is_help=True)


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
    search_filter: Annotated[
        Optional[str],
        typer.Option("--search", help="Search datasets by table name (server-side)"),
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
        # No complex filtering - just simple server-side search

        # Get datasets from API with spinner (using server-side filtering for performance)
        with data_spinner("datasets", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Use server-side filtering only - no client-side nonsense
            datasets = client.get_datasets(
                silent=True,
                limit=limit_filter,
                text_search=search_filter,  # Server-side table name search
            )

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(datasets)} datasets"

        # Display results
        if porcelain:
            # Tab-separated: ID, Name, Database, Schema, Type
            display_porcelain_list(
                datasets,
                ["id", "table_name", "database_name", "schema", "kind"],
            )
        elif json_output:
            import json

            console.print(json.dumps(datasets, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(datasets, default_flow_style=False, indent=2),
            )
        else:
            # Get hostname for clickable links
            workspace_hostname = ctx.get_workspace_hostname()
            display_datasets_table(datasets, workspace_hostname)

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
    from sup.output.spinners import data_spinner

    try:
        with data_spinner(f"dataset {dataset_id}", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)
            dataset = client.get_dataset(dataset_id, silent=True)

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


@app.command("pull")
def pull_datasets(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Assets folder to pull dataset definitions to (defaults to configured folder)",
        ),
    ] = None,
    # Universal filters - same as list command
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Pull specific dataset by ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Pull multiple datasets by IDs (comma-separated)"),
    ] = None,
    search_filter: Annotated[
        Optional[str],
        typer.Option("--search", help="Pull datasets matching search pattern"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", help="Pull only datasets you own"),
    ] = False,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of datasets to pull"),
    ] = None,
    # Pull-specific options
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
    skip_dependencies: Annotated[
        bool,
        typer.Option(
            "--skip-dependencies",
            help="Pull datasets only, without related database connections",
        ),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    Pull dataset definitions from Superset workspace to local filesystem.

    Downloads dataset configurations as YAML files following the same pattern as chart pull.

    Examples:
        sup dataset pull                           # Pull all datasets + dependencies
        sup dataset pull --mine                    # Pull your datasets + dependencies
        sup dataset pull --id=123                  # Pull specific dataset + dependencies
        sup dataset pull --search="sales"          # Pull matching datasets + dependencies
        sup dataset pull --skip-dependencies       # Pull datasets only (no databases)
    """
    from pathlib import Path
    from zipfile import ZipFile

    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    # Resolve assets folder using config default
    ctx = SupContext()
    resolved_assets_folder = ctx.get_assets_folder(cli_override=assets_folder)

    if not porcelain:
        console.print(
            f"{EMOJIS['export']} Exporting datasets to {resolved_assets_folder}...",
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

        # Get datasets using existing API
        client = SupSupersetClient.from_context(ctx, workspace_id)

        with data_spinner("datasets to export", silent=porcelain) as sp:
            # Get datasets (server-side filtering)
            datasets = client.get_datasets(
                silent=True,
                text_search=search_filter,
            )

            # Client-side filtering
            if id_filter:
                datasets = [d for d in datasets if d.get("id") == id_filter]
            elif ids_filter:
                id_list = [int(x.strip()) for x in ids_filter.split(",")]
                datasets = [d for d in datasets if d.get("id") in id_list]

            if mine_filter:
                try:
                    current_user = client.client.get_me()
                    current_user_id = current_user.get("id")
                    datasets = [
                        d
                        for d in datasets
                        if any(owner.get("id") == current_user_id for owner in d.get("owners", []))
                    ]
                except Exception:
                    pass

            if limit:
                datasets = datasets[:limit]

            # Extract IDs for export
            dataset_ids = [dataset["id"] for dataset in datasets]

            if sp:
                sp.text = f"Found {len(dataset_ids)} datasets to export"

        if not dataset_ids:
            console.print(
                f"{EMOJIS['warning']} No datasets match your filters",
                style=RICH_STYLES["warning"],
            )
            return

        # Export using existing API
        should_include_dependencies = not skip_dependencies

        if not porcelain:
            dependency_msg = " (with dependencies)" if should_include_dependencies else ""
            console.print(
                f"{EMOJIS['info']} Exporting {len(dataset_ids)} datasets{dependency_msg}...",
                style=RICH_STYLES["info"],
            )

        zip_buffer = client.client.export_zip("dataset", dataset_ids)

        # Process ZIP contents
        def remove_root(file_name: str) -> str:
            """Remove root directory from file path"""
            parts = Path(file_name).parts
            return str(Path(*parts[1:])) if len(parts) > 1 else file_name

        with ZipFile(zip_buffer) as bundle:
            contents = {
                remove_root(file_name): bundle.read(file_name).decode()
                for file_name in bundle.namelist()
            }

        # Save files to filesystem
        files_written = 0
        for file_name, file_contents in contents.items():
            # Skip related files unless dependencies are requested
            if not should_include_dependencies and not file_name.startswith("dataset"):
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

            # Write file
            with open(target, "w", encoding="utf-8") as output:
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
                f"{EMOJIS['error']} Failed to export datasets: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


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
        border_style=COLORS.secondary,
    )

    table.add_column("ID", style=COLORS.secondary, no_wrap=True)
    table.add_column("Name", style="bright_white", no_wrap=False)
    table.add_column("Database", style=COLORS.warning, no_wrap=True)
    table.add_column("Schema", style=COLORS.info, no_wrap=True)
    table.add_column("Type", style=COLORS.success, no_wrap=True)
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
    console.print(Panel(panel_content, title=f"Dataset: {name}", border_style=COLORS.secondary))

    # Show columns if available
    columns = dataset.get("columns", [])
    if columns:
        console.print(f"\n{EMOJIS['info']} Columns:", style=RICH_STYLES["header"])

        col_table = Table(
            show_header=True,
            header_style=RICH_STYLES["header"],
            border_style="dim",
        )
        col_table.add_column("Name", style=COLORS.secondary)
        col_table.add_column("Type", style=COLORS.warning)
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
