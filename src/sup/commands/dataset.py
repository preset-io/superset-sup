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
    instance: Annotated[
        Optional[str],
        typer.Option(
            "--instance",
            help="Superset instance name (self-hosted). Use 'sup instance list' to see available instances.",
        ),
    ] = None,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Preset workspace ID"),
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
            client = SupSupersetClient.from_context(
                ctx, workspace_id=workspace_id, instance_name=instance
            )

            # Use server-side filtering only - no client-side nonsense
            datasets = client.get_datasets(
                silent=True,
                limit=limit_filter or 100,  # Default to 100 for list view
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

    except ValueError as e:
        # from_context() provides helpful error messages for missing config
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
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
    instance: Annotated[
        Optional[str],
        typer.Option(
            "--instance",
            help="Superset instance name (self-hosted). Use 'sup instance list' to see available instances.",
        ),
    ] = None,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Preset workspace ID"),
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
            client = SupSupersetClient.from_context(
                ctx, workspace_id=workspace_id, instance_name=instance
            )
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

    except ValueError as e:
        # from_context() provides helpful error messages for missing config
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
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
    # Output/connection options
    instance: Annotated[
        Optional[str],
        typer.Option(
            "--instance",
            help="Superset instance name (self-hosted). Use 'sup instance list' to see available instances.",
        ),
    ] = None,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Preset workspace ID"),
    ] = None,
    # Pull-specific options
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
        client = SupSupersetClient.from_context(
            ctx, workspace_id=workspace_id, instance_name=instance
        )

        with data_spinner("datasets to export", silent=porcelain) as sp:
            # Get datasets (server-side filtering)
            # If no limit specified, fetch all datasets via pagination
            if limit:
                datasets = client.get_datasets(
                    silent=True,
                    text_search=search_filter,
                    limit=limit,
                )
            else:
                # Fetch all datasets via pagination
                datasets = []
                page = 0
                page_size = 100  # Larger page size for efficiency
                while True:
                    page_datasets = client.get_datasets(
                        silent=True,
                        text_search=search_filter,
                        limit=page_size,
                        page=page,
                    )
                    if not page_datasets:
                        break
                    datasets.extend(page_datasets)
                    # If we got less than page_size, we've reached the end
                    if len(page_datasets) < page_size:
                        break
                    page += 1

            # Client-side filtering
            if id_filter:
                datasets = [d for d in datasets if d.get("id") == id_filter]
            elif ids_filter:
                id_list = [int(x.strip()) for x in ids_filter.split(",")]
                datasets = [d for d in datasets if d.get("id") in id_list]

            if mine_filter:
                try:
                    current_user = client.client.get_me()  # type: ignore[attr-defined]
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


@app.command("push")
def push_datasets(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Path to assets folder with datasets. Defaults to assets_folder or './assets'."
        ),
    ] = None,
    # Target configuration
    instance: Annotated[
        Optional[str],
        typer.Option(
            "--instance",
            help="Target self-hosted instance name. Use 'sup instance list'.",
        ),
    ] = None,
    workspace_id: Annotated[
        Optional[int],
        typer.Option(
            "--workspace-id",
            "-w",
            help="Target workspace ID (Preset). If not specified, uses configured target.",
        ),
    ] = None,
    # Import options
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite existing datasets with same UUID",
        ),
    ] = False,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            help="Continue importing remaining datasets if one fails",
        ),
    ] = False,
    load_env: Annotated[
        bool,
        typer.Option(
            "--load-env",
            help="Load environment variables for Jinja2 templating",
        ),
    ] = False,
    disable_jinja_templating: Annotated[
        bool,
        typer.Option(
            "--disable-jinja-templating",
            help="Disable Jinja2 templating in dataset definitions",
        ),
    ] = False,
    template_options: Annotated[
        Optional[list[str]],
        typer.Option(
            "--option",
            "-o",
            help="Jinja2 template variable (format: KEY=VALUE). Can be used multiple times.",
        ),
    ] = None,
    # Database transformation options
    database_uuid: Annotated[
        Optional[str],
        typer.Option(
            "--database-uuid",
            help="Replace all database UUIDs with this UUID in target",
        ),
    ] = None,
    database_name: Annotated[
        Optional[str],
        typer.Option(
            "--database-name",
            help="Use database with this name from target (auto-fetches UUID)",
        ),
    ] = None,
    auto_map_databases: Annotated[
        bool,
        typer.Option(
            "--auto-map-databases",
            help="Auto-map databases by matching names between source and target",
        ),
    ] = False,
    # Control flags
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation prompts",
        ),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option(
            "--porcelain",
            help="Machine-readable output (no decorations, no prompts)",
        ),
    ] = False,
):
    """
    Import datasets to Superset instance or Preset workspace.

    Supports both self-hosted Superset instances and Preset workspaces with
    dependency resolution (automatically imports required databases).

    Database UUID transformation allows importing assets across environments
    by updating database references to match target instance databases.

    Examples:
        # Import to self-hosted instance
        sup instance use production
        sup dataset push assets/

        # Import to Preset workspace
        sup dataset push assets/ --workspace-id 123

        # Import with auto-mapped databases (recommended)
        sup dataset push assets/ --auto-map-databases

        # Import with specific database UUID
        sup dataset push assets/ --database-uuid abc-123-def

        # Import with database name lookup
        sup dataset push assets/ --database-name "Trino"

        # Import with overwrite
        sup dataset push assets/ --overwrite --force

        # Import with custom template variables
        sup dataset push assets/ --option ENV=prod --option REGION=us-east
    """
    from pathlib import Path

    from preset_cli.cli.superset.lib import get_import_summary
    from preset_cli.cli.superset.sync.native.command import ResourceType, native
    from sup.config.settings import SupContext

    try:
        ctx = SupContext()

        # Resolve assets folder
        resolved_assets_folder = (
            assets_folder
            or ctx.global_config.assets_folder
            or ctx.project_state.assets_folder
            or "./assets"
        )

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
        import click

        from sup.auth.preset import SupPresetAuth

        # Check if we're using self-hosted instance or Preset workspace
        instance_name = instance or ctx.get_instance_name()
        source_workspace_id = ctx.get_workspace_id()

        # For self-hosted instances, we don't need workspace IDs
        if instance_name:
            # Self-hosted path - instance is the target
            console.print(
                f"{EMOJIS['info']} Using self-hosted instance: [cyan]{instance_name}[/cyan]",
                style=RICH_STYLES["info"],
            )

            # Skip workspace ID validation for self-hosted
            use_instance_path = True
        else:
            # Preset workspace path - need workspace IDs
            use_instance_path = False
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
            if use_instance_path:
                # Self-hosted instance confirmation
                console.print(
                    f"{EMOJIS['warning']} Import Operation Summary",
                    style=RICH_STYLES["warning"],
                )
                console.print(f"📁 Assets folder: [cyan]{resolved_assets_folder}[/cyan]")
                console.print(f"📥 Target instance: [cyan]{instance_name}[/cyan]")
                console.print(
                    "⚠️  [bold]This will import datasets[/bold] - may overwrite existing assets",
                    style=RICH_STYLES["warning"],
                )
            else:
                # Preset workspace confirmation
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
                        "🔄 [bold]Cross-workspace import[/bold] - copying to different workspace",
                        style=RICH_STYLES["info"],
                    )
                else:
                    console.print(
                        "⚠️  [bold]Same-workspace import[/bold] - may overwrite existing datasets",
                        style=RICH_STYLES["warning"],
                    )

            if not typer.confirm("Continue with import operation?"):
                console.print(
                    f"{EMOJIS['info']} Import cancelled",
                    style=RICH_STYLES["info"],
                )
                raise typer.Exit(0)

        # Get target URL and auth based on instance or workspace
        if use_instance_path:
            # Self-hosted instance path
            instance_config = ctx.get_superset_instance_config(instance_name)
            if not instance_config:
                console.print(
                    f"{EMOJIS['error']} Instance configuration not found: {instance_name}",
                    style=RICH_STYLES["error"],
                )
                raise typer.Exit(1)

            workspace_url = instance_config.url
            if not workspace_url.endswith("/"):
                workspace_url += "/"

            # Create auth for self-hosted instance
            from preset_cli.auth.factory import create_superset_auth

            try:
                auth = create_superset_auth(instance_config)
            except ValueError as e:
                console.print(
                    f"{EMOJIS['error']} Authentication configuration error: {e}",
                    style=RICH_STYLES["error"],
                )
                raise typer.Exit(1)

        else:
            # Preset workspace path (original logic)
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

        # Apply database UUID transformation if requested
        temp_dir = None
        use_split_import = not auto_map_databases  # Don't use split when auto-mapping
        
        try:
            if database_uuid or database_name or auto_map_databases:
                from sup.utils.database_transform import transform_database_refs

                if not porcelain:
                    if database_uuid:
                        console.print(
                            f"{EMOJIS['info']} Transforming database refs to UUID: {database_uuid}",
                            style=RICH_STYLES["info"],
                        )
                    elif database_name:
                        console.print(
                            f"{EMOJIS['info']} Looking up database: {database_name}",
                            style=RICH_STYLES["info"],
                        )
                    elif auto_map_databases:
                        console.print(
                            f"{EMOJIS['info']} Auto-mapping databases by name...",
                            style=RICH_STYLES["info"],
                        )

                temp_dir = transform_database_refs(
                    assets_dir=resolved_assets_folder,
                    instance_url=workspace_url,
                    auth=auth,
                    database_uuid=database_uuid,
                    database_name=database_name,
                    auto_map=auto_map_databases,
                )

                # Use transformed assets
                if temp_dir:
                    resolved_assets_folder = temp_dir
                    if not porcelain:
                        console.print(
                            f"{EMOJIS['success']} Database UUIDs transformed",
                            style=RICH_STYLES["success"],
                        )
        except ValueError as e:
            console.print(
                f"{EMOJIS['error']} Database transformation failed: {e}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        # Create mock click context that native() expects
        import_command = click.Command("import")
        mock_ctx = click.Context(import_command)
        mock_ctx.obj = {
            "AUTH": auth,
            "INSTANCE": workspace_url,
        }

        if not porcelain:
            console.print(
                f"{EMOJIS['info']} Processing datasets and dependencies...",
                style=RICH_STYLES["info"],
            )

        # Call the existing native() function with dataset-specific settings
        with mock_ctx:
            mock_ctx.invoke(
                native,
                directory=resolved_assets_folder,
                option=template_options or (),
                asset_type=ResourceType.DATASET,
                overwrite=overwrite,
                disable_jinja_templating=disable_jinja_templating,
                disallow_edits=True,
                external_url_prefix="",
                load_env=load_env,
                split=use_split_import,  # Use bundle import when auto-mapping to avoid password prompts
                continue_on_error=continue_on_error,
                db_password=(),
            )

        summary = get_import_summary()
        if not porcelain:
            failed_entries = summary["failed"]
            if failed_entries:
                console.print(
                    f"{EMOJIS['warning']} Dataset import completed with "
                    f"{len(failed_entries)} failure(s) "
                    f"({len(summary['succeeded'])} succeeded):",
                    style=RICH_STYLES["warning"],
                )
                for entry in failed_entries:
                    try:
                        path_str = str(Path(entry.get("path", "")).relative_to("bundle"))
                    except ValueError:
                        path_str = entry.get("path", "")
                    error_msg = entry.get("error", "")
                    line = f"  \u2717 {path_str}"
                    if error_msg:
                        line += f"\n    {error_msg}"
                    console.print(line, style=RICH_STYLES["error"])
            else:
                console.print(
                    f"{EMOJIS['success']} Dataset import completed successfully",
                    style=RICH_STYLES["success"],
                )

        if summary["has_failures"]:
            raise typer.Exit(1)

    except typer.Exit:
        # Re-raise typer exits (our own error handling)
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to import datasets: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
    finally:
        if temp_dir:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
