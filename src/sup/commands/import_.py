"""
Top-level import command for sup CLI.

Provides full Jinja-templated YAML import of all asset types,
equivalent to legacy `preset-cli superset sync native` / `import-assets`.
"""

from pathlib import Path
from typing import List, Optional

import typer
from typing_extensions import Annotated

from sup.commands.template_params import DisableJinjaOption, LoadEnvOption, TemplateOptions
from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Import assets from directory", no_args_is_help=True)


@app.command("native")
def import_native(
    directory: Annotated[
        str,
        typer.Argument(help="Directory containing asset YAML files"),
    ],
    workspace_id: Annotated[
        Optional[int],
        typer.Option(
            "--workspace-id",
            "-w",
            help="Target workspace ID (defaults to configured target)",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing resources"),
    ] = False,
    template_options: TemplateOptions = None,
    load_env: LoadEnvOption = False,
    disable_jinja_templating: DisableJinjaOption = False,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            "-c",
            help="Continue importing even if some assets fail",
        ),
    ] = False,
    split: Annotated[
        bool,
        typer.Option(
            "--split",
            "-s",
            help="Import assets individually instead of as a bundle",
        ),
    ] = False,
    asset_type: Annotated[
        Optional[str],
        typer.Option(
            "--asset-type",
            help="Import only specific asset type (database, dataset, chart, dashboard)",
        ),
    ] = None,
    db_password: Annotated[
        Optional[List[str]],
        typer.Option(
            "--db-password",
            help="Database password (uuid=password, repeatable)",
        ),
    ] = None,
    disallow_edits: Annotated[
        bool,
        typer.Option(
            "--disallow-edits",
            help="Mark imported assets as externally managed",
        ),
    ] = False,
    external_url_prefix: Annotated[
        str,
        typer.Option(
            "--external-url-prefix",
            help="Base URL for external resources",
        ),
    ] = "",
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
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Import assets from a directory of YAML files (native import).

    Full-featured import with Jinja2 templating support, equivalent to
    the legacy `preset-cli superset sync native` / `import-assets` command.

    Supports importing databases, datasets, charts, and dashboards from
    YAML files with optional Jinja2 template processing.

    Examples:
        sup import native ./assets                           # Import all assets
        sup import native ./assets --overwrite               # Overwrite existing
        sup import native ./assets --asset-type chart        # Import only charts
        sup import native ./assets --split --continue-on-error  # Individual import
        sup import native ./assets --option env=prod         # With template vars
        sup import native ./assets --load-env                # With env vars
    """
    import click

    from preset_cli.cli.superset.sync.native.command import ResourceType, native

    from sup.auth.preset import SupPresetAuth
    from sup.clients.preset import SupPresetClient
    from sup.config.settings import SupContext

    try:
        # Verify directory exists
        dir_path = Path(directory)
        if not dir_path.exists():
            console.print(
                f"{EMOJIS['error']} Directory not found: {directory}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)
        elif not dir_path.is_dir():
            console.print(
                f"{EMOJIS['error']} Path is not a directory: {directory}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        # Resolve asset type enum if specified
        resource_type = None
        if asset_type:
            type_map = {
                "database": ResourceType.DATABASE,
                "dataset": ResourceType.DATASET,
                "chart": ResourceType.CHART,
                "dashboard": ResourceType.DASHBOARD,
            }
            resource_type = type_map.get(asset_type.lower())
            if resource_type is None:
                console.print(
                    f"{EMOJIS['error']} Invalid asset type: {asset_type}. "
                    "Use: database, dataset, chart, dashboard",
                    style=RICH_STYLES["error"],
                )
                raise typer.Exit(1)

        ctx = SupContext()

        # Get target workspace
        target_workspace_id = ctx.get_target_workspace_id(cli_override=workspace_id)
        if not target_workspace_id:
            # Fall back to source workspace
            target_workspace_id = ctx.get_workspace_id()

        if not target_workspace_id:
            console.print(
                f"{EMOJIS['error']} No workspace configured",
                style=RICH_STYLES["error"],
            )
            console.print(
                "Run [bold]sup workspace use <ID>[/] or pass --workspace-id",
                style=RICH_STYLES["info"],
            )
            raise typer.Exit(1)

        # Safety confirmation
        if not force and not porcelain:
            console.print(
                f"{EMOJIS['warning']} Import Operation",
                style=RICH_STYLES["warning"],
            )
            console.print(f"Directory: [cyan]{directory}[/cyan]")
            console.print(f"Target workspace: [cyan]{target_workspace_id}[/cyan]")
            if asset_type:
                console.print(f"Asset type: [cyan]{asset_type}[/cyan]")
            if overwrite:
                console.print("[bold yellow]Overwrite mode enabled[/bold yellow]")

            if not typer.confirm("Continue with import?"):
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
                f"{EMOJIS['error']} Workspace {target_workspace_id} not found",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        target_hostname = target_workspace.get("hostname")
        if not target_hostname:
            console.print(
                f"{EMOJIS['error']} No hostname for workspace {target_workspace_id}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        workspace_url = f"https://{target_hostname}/"
        auth = SupPresetAuth.from_sup_config(ctx, silent=True)

        if not porcelain:
            console.print(
                f"{EMOJIS['info']} Importing assets from {directory}...",
                style=RICH_STYLES["info"],
            )

        # Create mock Click context and invoke native()
        import_command = click.Command("import")
        mock_ctx = click.Context(import_command)
        mock_ctx.obj = {
            "AUTH": auth,
            "INSTANCE": workspace_url,
        }

        with mock_ctx:
            mock_ctx.invoke(
                native,
                directory=directory,
                option=template_options or (),
                asset_type=resource_type,
                overwrite=overwrite,
                disable_jinja_templating=disable_jinja_templating,
                disallow_edits=disallow_edits,
                external_url_prefix=external_url_prefix,
                load_env=load_env,
                split=split,
                continue_on_error=continue_on_error,
                db_password=tuple(db_password) if db_password else (),
            )

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} Import completed successfully",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to import assets: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
