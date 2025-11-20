"""
Dashboard management commands for sup CLI.

Working version without decorators - follows dataset.py pattern.
"""

from typing import Any, Dict, Optional

import typer

# Removed: from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.formatters import display_porcelain_list
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES
from sup.output.tables import display_dashboards_table

app = typer.Typer(help="Manage dashboards", no_args_is_help=True)


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


@app.command("pull")
def pull_dashboards(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Assets folder to pull dashboard definitions to (defaults to configured folder)",
        ),
    ] = None,
    # Universal filters - same as list command
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Pull specific dashboard by ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Pull multiple dashboards by IDs (comma-separated)"),
    ] = None,
    search_filter: Annotated[
        Optional[str],
        typer.Option("--search", help="Pull dashboards matching search pattern"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", help="Pull only dashboards you own"),
    ] = False,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of dashboards to pull"),
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
            help="Pull dashboards only, without related charts, datasets, and databases",
        ),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    Pull dashboard definitions from Superset workspace to local filesystem.

    Downloads dashboard configurations as YAML files following the same pattern as chart pull.

    Examples:
        sup dashboard pull                           # Pull all dashboards + dependencies
        sup dashboard pull --mine                    # Pull your dashboards + dependencies
        sup dashboard pull --id=254                  # Pull specific dashboard + dependencies
        sup dashboard pull --search="sales"          # Pull matching dashboards + dependencies
        sup dashboard pull --skip-dependencies       # Pull dashboards only (no deps)
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
            f"{EMOJIS['export']} Exporting dashboards to {resolved_assets_folder}...",
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

        # Get dashboards using existing API
        client = SupSupersetClient.from_context(ctx, workspace_id)

        with data_spinner("dashboards to export", silent=porcelain) as sp:
            # Get dashboards (server-side filtering)
            dashboards = client.get_dashboards(
                silent=True,
                text_search=search_filter,
            )

            # Client-side filtering
            if id_filter:
                dashboards = [d for d in dashboards if d.get("id") == id_filter]
            elif ids_filter:
                id_list = [int(x.strip()) for x in ids_filter.split(",")]
                dashboards = [d for d in dashboards if d.get("id") in id_list]

            if mine_filter:
                try:
                    current_user = client.client.get_me()
                    current_user_id = current_user.get("id")
                    dashboards = [
                        d
                        for d in dashboards
                        if any(owner.get("id") == current_user_id for owner in d.get("owners", []))
                    ]
                except Exception:
                    pass

            if limit:
                dashboards = dashboards[:limit]

            # Extract IDs for export
            dashboard_ids = [dashboard["id"] for dashboard in dashboards]

            if sp:
                sp.text = f"Found {len(dashboard_ids)} dashboards to export"

        if not dashboard_ids:
            console.print(
                f"{EMOJIS['warning']} No dashboards match your filters",
                style=RICH_STYLES["warning"],
            )
            return

        # Export using existing API
        should_include_dependencies = not skip_dependencies

        if not porcelain:
            dependency_msg = " (with dependencies)" if should_include_dependencies else ""
            console.print(
                f"{EMOJIS['info']} Exporting {len(dashboard_ids)} dashboards{dependency_msg}...",
                style=RICH_STYLES["info"],
            )

        zip_buffer = client.client.export_zip("dashboard", dashboard_ids)

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
            if not should_include_dependencies and not file_name.startswith("dashboard"):
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
                f"{EMOJIS['error']} Failed to export dashboards: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
