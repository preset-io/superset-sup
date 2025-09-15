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

from sup.commands.template_params import DisableJinjaOption, LoadEnvOption, TemplateOptions
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

    if not porcelain:
        console.print(
            f"{EMOJIS['info']} Loading dashboard {dashboard_id} details...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id)
        dashboard = client.get_dashboard(dashboard_id, silent=porcelain)

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


@app.command("push")
def push_dashboards(
    assets_folder: Annotated[
        Optional[str],
        typer.Argument(
            help="Assets folder to push dashboard definitions from (defaults to configured folder)",
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
        typer.Option("--overwrite", help="Overwrite existing dashboards"),
    ] = False,
    # Template processing options
    template_options: TemplateOptions = None,
    load_env: LoadEnvOption = False,
    disable_jinja_templating: DisableJinjaOption = False,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            help="Continue importing even if some dashboards fail",
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
) -> None:
    """
    Push dashboards from assets folder to workspace.

    Reads dashboard configurations from YAML files and creates/updates dashboards in
    the workspace. Automatically handles dependencies (datasets, databases, charts)
    when present in the assets folder.

    The push processes directory structure:
    • dashboards/ - Dashboard definition files to push
    • charts/ - Chart definitions (pushed first as dependencies)
    • datasets/ - Dataset definitions (pushed first as dependencies)
    • databases/ - Database connections (pushed first as dependencies)
    • metadata.yaml - Push metadata and validation

    Dependencies are pushed in correct order: databases → datasets → charts → dashboards
    to ensure all required objects exist before dashboard creation.

    By default, Jinja2 templating is enabled for parameterized assets.
    Use --disable-jinja-templating to push raw YAML without processing.

    Template Support:
    • --option key=value: Pass template variables (can be used multiple times)
    • --load-env: Make environment variables available as env['VAR_NAME']
    • dashboard.overrides.yaml files are automatically applied

    Examples:
        sup dashboard push                               # Push to configured target workspace
        sup dashboard push ./backup                      # Push from specific folder
        sup dashboard push --workspace-id=456            # Push to specific workspace
        sup dashboard push --overwrite --force           # Overwrite without confirmation
        sup dashboard push --continue-on-error           # Skip failed dashboards, continue
        sup dashboard push --option env=prod --load-env  # Template with variables
    """
    import click

    from preset_cli.cli.superset.sync.native.command import ResourceType, native
    from sup.auth.preset import SupPresetAuth
    from sup.config.settings import SupContext

    # Resolve assets folder using config default
    ctx = SupContext()
    resolved_assets_folder = ctx.get_assets_folder(cli_override=assets_folder)

    # Resolve target workspace
    target_workspace_id = workspace_id or ctx.config.target_workspace_id
    if not target_workspace_id:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} No target workspace configured. "
                f"Use --workspace-id or 'sup workspace set-target'",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)

    # Show import summary unless in porcelain mode
    if not porcelain:
        console.print(f"{EMOJIS['import']} Importing dashboards from {resolved_assets_folder}...")

        console.print(
            f"\n{EMOJIS['warning']} Import Operation Summary",
            style=RICH_STYLES["warning"],
        )
        console.print(f"📁 Assets folder: {resolved_assets_folder}")
        console.print(f"📤 Source workspace: {ctx.config.workspace_id}")
        console.print(f"📥 Target workspace: {target_workspace_id}")

        if ctx.config.workspace_id != target_workspace_id:
            console.print("🔄 Cross-workspace import - assets copied to different workspace")
        else:
            console.print("🔄 Same-workspace import - assets updated in place")

        if not force:
            response = typer.confirm("Continue with import operation?")
            if not response:
                console.print("Import cancelled")
                raise typer.Exit(0)

    try:
        # Get target workspace hostname for authentication
        target_hostname = ctx.get_workspace_hostname(target_workspace_id)
        if not target_hostname:
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} Could not determine hostname "
                    f"for workspace {target_workspace_id}",
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
                f"{EMOJIS['info']} Processing dashboards and dependencies...",
                style=RICH_STYLES["info"],
            )

        # Call the existing native() function with dashboard-specific settings
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
                asset_type=ResourceType.DASHBOARD,
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
                f"{EMOJIS['success']} Dashboard import completed successfully",
                style=RICH_STYLES["success"],
            )

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to import dashboards: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
