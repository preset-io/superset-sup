"""
Shared push (import) logic for sup CLI entity commands.

Provides a reusable function for pushing assets to Superset workspaces
via the legacy native() Click command, bridging Typer -> Click context.
"""

from pathlib import Path
from typing import List, Optional

import click
import typer

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES


def push_assets(
    asset_type_enum,
    asset_label: str,
    assets_folder: Optional[str],
    workspace_id: Optional[int],
    overwrite: bool,
    template_options: Optional[List[str]],
    load_env: bool,
    disable_jinja_templating: bool,
    continue_on_error: bool,
    force: bool,
    porcelain: bool,
) -> None:
    """
    Push assets from local filesystem to a Superset workspace.

    This bridges Typer commands to the legacy Click-based native() import function,
    reusing all existing import logic (dependency resolution, Jinja2 templating, etc.).

    Args:
        asset_type_enum: ResourceType enum value (e.g., ResourceType.CHART)
        asset_label: Human-readable label (e.g., "charts", "dashboards")
        assets_folder: Override assets folder path
        workspace_id: Override target workspace ID
        overwrite: Whether to overwrite existing assets
        template_options: Jinja2 template key=value pairs
        load_env: Whether to load environment variables for templates
        disable_jinja_templating: Whether to disable Jinja2 processing
        continue_on_error: Whether to skip failed assets
        force: Whether to skip confirmation prompts
        porcelain: Whether to use machine-readable output
    """
    from preset_cli.cli.superset.sync.native.command import native

    from sup.auth.preset import SupPresetAuth
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext

    ctx = SupContext()
    resolved_assets_folder = ctx.get_assets_folder(cli_override=assets_folder)

    if not porcelain:
        console.print(
            f"{EMOJIS['import']} Importing {asset_label} from {resolved_assets_folder}...",
            style=RICH_STYLES["info"],
        )

    # Verify assets folder exists
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

    # Get source and target workspace context
    source_workspace_id = ctx.get_workspace_id()
    target_workspace_id = ctx.get_target_workspace_id(cli_override=workspace_id)

    if not source_workspace_id:
        console.print(
            f"{EMOJIS['error']} No source workspace configured",
            style=RICH_STYLES["error"],
        )
        console.print(
            "Run [bold]sup workspace list[/] and [bold]sup workspace use <ID>[/]",
            style=RICH_STYLES["info"],
        )
        raise typer.Exit(1)

    if not target_workspace_id:
        console.print(
            f"{EMOJIS['error']} No target workspace configured",
            style=RICH_STYLES["error"],
        )
        console.print(
            "Set target: [bold]sup workspace set-target <ID>[/]",
            style=RICH_STYLES["info"],
        )
        raise typer.Exit(1)

    # Safety confirmation
    if not force and not porcelain:
        is_cross_workspace = target_workspace_id != source_workspace_id

        console.print(
            f"{EMOJIS['warning']} Import Operation Summary",
            style=RICH_STYLES["warning"],
        )
        console.print(f"Assets folder: [cyan]{resolved_assets_folder}[/cyan]")
        console.print(f"Source workspace: [cyan]{source_workspace_id}[/cyan]")
        console.print(f"Target workspace: [cyan]{target_workspace_id}[/cyan]")

        if is_cross_workspace:
            console.print(
                "[bold]Cross-workspace import[/bold] - assets copied to different workspace",
                style=RICH_STYLES["info"],
            )
        else:
            console.print(
                "[bold]Same-workspace import[/bold] - may overwrite existing assets",
                style=RICH_STYLES["warning"],
            )

        if not typer.confirm("Continue with import operation?"):
            console.print(
                f"{EMOJIS['info']} Import cancelled",
                style=RICH_STYLES["info"],
            )
            raise typer.Exit(0)

    # Resolve target workspace URL
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

    # Create mock Click context for native()
    import_command = click.Command("import")
    mock_ctx = click.Context(import_command)
    mock_ctx.obj = {
        "AUTH": auth,
        "INSTANCE": workspace_url,
    }

    if not porcelain:
        console.print(
            f"{EMOJIS['info']} Processing {asset_label} and dependencies...",
            style=RICH_STYLES["info"],
        )

    # Call the legacy native() function
    with mock_ctx:
        mock_ctx.invoke(
            native,
            directory=resolved_assets_folder,
            option=template_options or (),
            asset_type=asset_type_enum,
            overwrite=overwrite,
            disable_jinja_templating=disable_jinja_templating,
            disallow_edits=True,
            external_url_prefix="",
            load_env=load_env,
            split=True,
            continue_on_error=continue_on_error,
            db_password=(),
        )

    if not porcelain:
        console.print(
            f"{EMOJIS['success']} {asset_label.capitalize()} import completed successfully",
            style=RICH_STYLES["success"],
        )
