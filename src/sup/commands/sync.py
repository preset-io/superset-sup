"""
Sync command for sup CLI.

Provides multi-target asset synchronization with Jinja templating support.
Handles complex workflows like pulling from one workspace and pushing to multiple
targets with environment-specific customization.
"""

from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.config.sync import SyncConfig, validate_sync_folder
from sup.output.styles import EMOJIS, RICH_STYLES


def format_sync_help():
    """Create beautifully formatted help text for sync command group."""
    from sup.output.styles import COLORS

    return f"""\
[not dim][bold bright_white]🔄 Multi-target asset synchronization[/bold bright_white][/not dim]

[bold {COLORS.primary}]Key Features:[/bold {COLORS.primary}]
• [bright_white]Git-ready folder structure:[/bright_white] [cyan]sync_config.yml[/cyan] + [cyan]assets/[/cyan] folder  # noqa: E501
• [bright_white]Jinja2 templating:[/bright_white] Environment-specific customization with variables
• [bright_white]Precise asset selection:[/bright_white] Universal filters work with sync operations
• [bright_white]Enterprise workflows:[/bright_white] Multi-customer deployments, environment promotion  # noqa: E501
• [bright_white]Safe operations:[/bright_white] Dry-run mode, overwrite protection, validation

[bold {COLORS.primary}]Common Workflows:[/bold {COLORS.primary}]
• [bright_white]Environment promotion:[/bright_white] Dev → Staging → Production
• [bright_white]Multi-customer deployment:[/bright_white] Template → Customer A, B, C
• [bright_white]Backup & restore:[/bright_white] Pull assets for version control

[bold {COLORS.primary}]Quick Start:[/bold {COLORS.primary}]
• [bold]Step 1:[/bold] [cyan]sup sync create ./my_sync --source 123 --targets 456,789[/cyan]
• [bold]Step 2:[/bold] [cyan]sup sync run ./my_sync --dry-run[/cyan] - Preview operations
• [bold]Step 3:[/bold] [cyan]sup sync run ./my_sync[/cyan] - Execute synchronization"""  # noqa: E501


app = typer.Typer(help=format_sync_help(), rich_markup_mode="rich", no_args_is_help=True)
console = Console()


@app.command("run")
def run_sync(
    sync_folder: Annotated[
        str,
        typer.Argument(help="Path to sync folder containing sync_config.yml"),
    ],
    pull_only: Annotated[
        bool,
        typer.Option("--pull-only", help="Only pull from source, don't push to targets"),
    ] = False,
    push_only: Annotated[
        bool,
        typer.Option("--push-only", help="Only push to targets, don't pull from source"),
    ] = False,
    target: Annotated[
        Optional[str],
        typer.Option("--target", help="Push to specific target only (by name or workspace ID)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompts"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
) -> None:
    """
    Run a multi-target sync operation.

    Pulls assets from source workspace, applies Jinja templating, and pushes
    to configured target workspaces. The sync folder must contain a sync_config.yml
    file with source, targets, and asset selection configuration.

    Examples:
        sup sync run ./multi_customer_sync                    # Full pull → push
        sup sync run ./multi_customer_sync --pull-only        # Just pull
        sup sync run ./multi_customer_sync --push-only        # Just push to targets
        sup sync run ./multi_customer_sync --target customer_a # Push to specific target
        sup sync run ./multi_customer_sync --dry-run          # Preview actions
    """
    if pull_only and push_only:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Cannot specify both --pull-only and --push-only",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)

    # Validate and load sync configuration
    sync_path = Path(sync_folder).resolve()
    if not validate_sync_folder(sync_path):
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Invalid sync folder: {sync_path}",
                style=RICH_STYLES["error"],
            )
            console.print("Expected sync_config.yml file in the folder")
        raise typer.Exit(1)

    try:
        sync_config = SyncConfig.from_yaml(sync_path / "sync_config.yml")
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to load sync config: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)

    # Validate target selection if specified
    selected_targets = sync_config.targets
    if target:
        target_config = sync_config.get_target_by_name(target)
        if not target_config:
            # Try by workspace ID
            try:
                target_workspace_id = int(target)
                target_config = sync_config.get_target_by_workspace_id(target_workspace_id)
            except ValueError:
                pass

        if not target_config:
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} Target '{target}' not found in sync config",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(1)
        selected_targets = [target_config]

    # Show sync summary
    if not porcelain:
        display_sync_summary(
            sync_config,
            selected_targets,
            pull_only,
            push_only,
            dry_run,
            sync_path,
        )

        if not force and not dry_run:
            response = typer.confirm("Continue with sync operation?")
            if not response:
                console.print("Sync cancelled")
                raise typer.Exit(0)

    try:
        # Execute sync operations
        if not push_only:
            execute_pull(sync_config, sync_path, dry_run, porcelain)

        if not pull_only:
            execute_push(sync_config, selected_targets, sync_path, dry_run, porcelain)

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} Sync operation completed successfully",
                style=RICH_STYLES["success"],
            )

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Sync operation failed: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("create")
def create_sync(
    sync_folder: Annotated[
        str,
        typer.Argument(help="Path to create new sync folder"),
    ],
    source_workspace_id: Annotated[
        int,
        typer.Option("--source", help="Source workspace ID"),
    ],
    target_workspace_ids: Annotated[
        str,
        typer.Option("--targets", help="Target workspace IDs (comma-separated)"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing sync folder"),
    ] = False,
) -> None:
    """
    Create a new sync configuration folder with example config.

    Creates a sync folder with sync_config.yml and assets/ directory.
    Provides a starting point for customizing sync operations.

    Examples:
        sup sync create ./my_sync --source 123 --targets 456,789
        sup sync create ./customer_sync --source 100 --targets 200,300,400
    """
    sync_path = Path(sync_folder).resolve()

    # Check if folder exists
    if sync_path.exists() and not force:
        console.print(
            f"{EMOJIS['error']} Sync folder already exists: {sync_path}",
            style=RICH_STYLES["error"],
        )
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Parse target workspace IDs
    try:
        target_ids = [int(id_.strip()) for id_ in target_workspace_ids.split(",")]
    except ValueError as e:
        console.print(
            f"{EMOJIS['error']} Invalid target workspace IDs: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)

    try:
        # Create sync configuration
        sync_config = SyncConfig.create_example(
            source_workspace_id=source_workspace_id,
            target_workspace_ids=target_ids,
        )

        # Create folder structure
        sync_path.mkdir(parents=True, exist_ok=True)
        assets_folder = sync_config.assets_folder(sync_path)
        assets_folder.mkdir(exist_ok=True)

        # Create subdirectories for assets
        for asset_type in ["charts", "dashboards", "datasets", "databases"]:
            (assets_folder / asset_type).mkdir(exist_ok=True)

        # Save configuration
        config_file = sync_config.sync_config_path(sync_path)
        sync_config.to_yaml(config_file)

        console.print(
            f"{EMOJIS['success']} Created sync folder: {sync_path}",
            style=RICH_STYLES["success"],
        )
        console.print(f"📁 Sync config: {config_file}")
        console.print(f"📁 Assets folder: {assets_folder}")

        console.print(
            "\n💡 Next steps:",
            style=RICH_STYLES["info"],
        )
        console.print("1. Edit sync_config.yml to customize asset selection")
        console.print("2. Run: sup sync run ./my_sync --pull-only")
        console.print("3. Review pulled assets in assets/ folder")
        console.print("4. Run: sup sync run ./my_sync")

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to create sync folder: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


@app.command("validate")
def validate_sync(
    sync_folder: Annotated[
        str,
        typer.Argument(help="Path to sync folder to validate"),
    ],
) -> None:
    """
    Validate a sync configuration folder.

    Checks sync_config.yml for syntax errors, validates workspace IDs,
    and verifies folder structure.

    Examples:
        sup sync validate ./my_sync
    """
    sync_path = Path(sync_folder).resolve()

    if not sync_path.exists():
        console.print(
            f"{EMOJIS['error']} Sync folder does not exist: {sync_path}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)

    config_path = sync_path / "sync_config.yml"
    if not config_path.exists():
        console.print(
            f"{EMOJIS['error']} sync_config.yml not found in {sync_path}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)

    try:
        sync_config = SyncConfig.from_yaml(config_path)
        console.print(
            f"{EMOJIS['success']} Sync configuration is valid",
            style=RICH_STYLES["success"],
        )

        # Show configuration summary
        display_sync_summary(sync_config, sync_config.targets, False, False, False, sync_path)

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Invalid sync configuration: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


def display_sync_summary(
    sync_config: SyncConfig,
    targets: List,
    pull_only: bool,
    push_only: bool,
    dry_run: bool,
    sync_path: Path,
) -> None:
    """Display a summary of the sync operation."""
    console.print(
        f"\n{EMOJIS['sync']} Sync Operation Summary",
        style=RICH_STYLES["header"],
    )

    # Operation type
    if pull_only:
        operation = "Pull Only"
    elif push_only:
        operation = "Push Only"
    else:
        operation = "Full Sync (Pull + Push)"

    if dry_run:
        operation += " (Dry Run)"

    console.print(f"🔄 Operation: {operation}")
    console.print(f"📁 Sync folder: {sync_path}")

    # Source info
    console.print("\n📤 Source:")
    console.print(f"   Workspace ID: {sync_config.source.workspace_id}")

    # Asset selection summary
    assets = sync_config.source.assets
    asset_summary = []
    for asset_type in ["charts", "dashboards", "datasets", "databases"]:
        asset_config = getattr(assets, asset_type)
        if asset_config:
            summary = f"{asset_type}: {asset_config.selection}"
            if asset_config.selection == "ids":
                summary += f" ({len(asset_config.ids or [])} items)"
            asset_summary.append(summary)

    if asset_summary:
        console.print(f"   Assets: {', '.join(asset_summary)}")

    # Targets info
    console.print(f"\n📥 Targets ({len(targets)}):")
    for target in targets:
        name_display = f" ({target.name})" if target.name else ""
        overwrite = target.get_effective_overwrite(sync_config.target_defaults)
        console.print(f"   • {target.workspace_id}{name_display} [overwrite: {overwrite}]")


def execute_pull(sync_config: SyncConfig, sync_path: Path, dry_run: bool, porcelain: bool) -> None:
    """Execute the pull operation from source workspace."""
    if not porcelain:
        console.print(
            f"\n{EMOJIS['download']} Pulling from workspace {sync_config.source.workspace_id}...",
            style=RICH_STYLES["info"],
        )

    if dry_run:
        # Show what would be pulled for each asset type
        asset_summary = []
        assets = sync_config.source.assets
        for asset_type in ["databases", "datasets", "charts", "dashboards"]:
            asset_config = getattr(assets, asset_type)
            if asset_config:
                summary = f"{asset_type}: {asset_config.selection}"
                if asset_config.selection == "ids":
                    summary += f" ({len(asset_config.ids or [])} items)"
                asset_summary.append(summary)

        if not porcelain:
            console.print("   [DRY RUN] Would pull assets to assets/ folder:")
            for summary in asset_summary:
                console.print(f"     • {summary}")
        return

    # Import the export functionality from legacy CLI
    from preset_cli.cli.superset.export import export_resource
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    try:
        # Get current context and client
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, sync_config.source.workspace_id)

        # Use the sync config's assets folder method
        assets_path = sync_config.assets_folder(sync_path)

        # Create assets directory if it doesn't exist
        assets_path.mkdir(parents=True, exist_ok=True)

        # Process each asset type
        assets = sync_config.source.assets
        total_files = 0

        for asset_type in ["databases", "datasets", "charts", "dashboards"]:
            asset_config = getattr(assets, asset_type)
            if not asset_config:
                continue

            if not porcelain:
                console.print(f"   Pulling {asset_type}...")

            # Get asset IDs based on selection
            if asset_config.selection == "all":
                # Get all assets of this type
                resources = client.client.get_resources(asset_type.rstrip("s"))  # Remove plural
                requested_ids = set(resource["id"] for resource in resources)
            elif asset_config.selection == "ids":
                requested_ids = set(asset_config.ids or [])
            else:
                # TODO: Support other selection types (mine, filter)
                if not porcelain:
                    console.print(
                        f"     Skipping {asset_type}: {asset_config.selection} "
                        "not implemented yet"
                    )
                continue

            if not requested_ids:
                if not porcelain:
                    console.print(f"     No {asset_type} to pull")
                continue

            # Use the legacy export_resource function with overwrite=True
            export_resource(
                resource_name=asset_type.rstrip("s"),  # Remove plural: charts -> chart
                requested_ids=requested_ids,
                root=assets_path,
                client=client.client,  # Use underlying SupersetClient
                overwrite=True,  # Always overwrite in sync
                disable_jinja_escaping=False,
                skip_related=not asset_config.include_dependencies,
                force_unix_eol=False,
            )

            total_files += len(requested_ids)

            if not porcelain:
                console.print(f"     Pulled {len(requested_ids)} {asset_type}")

        if not porcelain:
            console.print(f"   Pull operation completed - {total_files} assets exported")

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Pull operation failed: {e}",
                style=RICH_STYLES["error"],
            )
        raise


def execute_push(
    sync_config: SyncConfig,
    targets: List,
    sync_path: Path,
    dry_run: bool,
    porcelain: bool,
) -> None:
    """Execute push operations to target workspaces."""
    from preset_cli.cli.superset.sync.native.command import (
        is_yaml_config,
        load_user_modules,
        render_yaml,
        import_resources_individually,
        raise_helper,
        ResourceType,
    )
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    import yaml
    from pathlib import Path as PathlibPath

    for target in targets:
        name_display = f" ({target.name})" if target.name else ""

        if not porcelain:
            console.print(
                f"\n{EMOJIS['upload']} Pushing to workspace {target.workspace_id}{name_display}...",
                style=RICH_STYLES["info"],
            )

        if dry_run:
            context = target.get_effective_jinja_context(sync_config.target_defaults)
            if not porcelain:
                console.print(f"   [DRY RUN] Would push with Jinja context: {context}")
            continue

        try:
            # Get client for target workspace
            ctx = SupContext()
            if not porcelain:
                console.print(f"   🎯 Target workspace ID from config: {target.workspace_id}")
            client = SupSupersetClient.from_context(ctx, target.workspace_id)

            # Verify we're using the right workspace
            if not porcelain:
                console.print(f"   🔗 Client base URL: {client.client.baseurl}")

            # Get Jinja context for this target
            # Get assets folder from sync config
            assets_path = sync_config.assets_folder(sync_path)

            if not assets_path.exists():
                raise Exception(f"Assets folder not found: {assets_path}")

            jinja_env = dict(target.get_effective_jinja_context(sync_config.target_defaults))
            jinja_env["instance"] = client.client.baseurl
            jinja_env["functions"] = load_user_modules(assets_path / "functions")
            jinja_env["raise"] = raise_helper

            # Read all YAML files and render with Jinja2
            configs = {}
            queue = [assets_path]

            while queue:
                path_name = queue.pop()
                relative_path = path_name.relative_to(assets_path)

                if path_name.is_dir() and not path_name.stem.startswith("."):
                    queue.extend(path_name.glob("*"))
                elif is_yaml_config(relative_path):
                    # Skip metadata.yaml and tags.yaml - they'll be generated by import_resources
                    if path_name.name in ("metadata.yaml", "tags.yaml"):
                        continue

                    # Render YAML with Jinja context
                    config = render_yaml(path_name, jinja_env)

                    # Handle overrides if they exist
                    overrides_path = path_name.with_suffix(".overrides" + path_name.suffix)
                    if overrides_path.exists():
                        overrides = render_yaml(overrides_path, jinja_env)
                        from preset_cli.lib import dict_merge
                        dict_merge(config, overrides)

                    configs[PathlibPath("bundle") / relative_path] = config

            # Get overwrite setting for this target
            overwrite = target.get_effective_overwrite(sync_config.target_defaults)

            # Import all assets as a bundle
            if configs:
                if not porcelain:
                    console.print(f"   📦 Preparing to push {len(configs)} assets...")
                    console.print(f"   🔧 Overwrite mode: {overwrite}")

                contents = {str(k): yaml.dump(v) for k, v in configs.items()}

                # Log what we're pushing
                if not porcelain:
                    asset_counts: Dict[str, int] = {}
                    for path in configs.keys():
                        asset_type = path.parts[1] if len(path.parts) > 1 else "unknown"
                        asset_counts[asset_type] = asset_counts.get(asset_type, 0) + 1
                    console.print(f"   📊 Asset breakdown: {dict(asset_counts)}")

                try:
                    # Debug: Save the bundle for inspection
                    if not porcelain:
                        debug_zip_path = sync_path / "debug_bundle.zip"
                        console.print(f"   🐛 Saving debug bundle to: {debug_zip_path}")

                        from datetime import datetime, timezone
                        from zipfile import ZipFile
                        from io import BytesIO

                        # Create the same bundle that will be sent
                        debug_contents = dict(contents)
                        debug_contents["bundle/metadata.yaml"] = yaml.dump(
                            dict(
                                version="1.0.0",
                                type=ResourceType.ASSET.metadata_type,
                                timestamp=datetime.now(tz=timezone.utc).isoformat(),
                            ),
                        )

                        with open(debug_zip_path, 'wb') as f:
                            buf = BytesIO()
                            with ZipFile(buf, "w") as bundle:
                                for file_path, file_content in debug_contents.items():
                                    content = (
                                        file_content.encode()
                                        if isinstance(file_content, str)
                                        else file_content
                                    )
                                    bundle.writestr(file_path, content)
                            f.write(buf.getvalue())

                        console.print(f"   📋 Bundle contains {len(debug_contents)} files")

                    # Capture click output
                    import sys
                    from io import StringIO

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    captured_output = StringIO()

                    try:
                        sys.stdout = captured_output
                        sys.stderr = captured_output

                        # Try individual import for better error messages
                        if not porcelain:
                            console.print("   🔍 Using split import for better error visibility...")
                        import_resources_individually(
                            configs,
                            client.client,  # Use underlying SupersetClient
                            overwrite,
                            ResourceType.ASSET,
                            continue_on_error=False,
                        )
                    finally:
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr

                        # Show captured output if any
                        output = captured_output.getvalue()
                        if output and not porcelain:
                            console.print(f"   📝 Import output:")
                            console.print(output)

                    if not porcelain:
                        success_message = (
                            f"   {EMOJIS['success']} Pushed {len(configs)} assets to "
                            f"workspace {target.workspace_id}"
                        )
                        console.print(success_message, style=RICH_STYLES["success"])
                except Exception as import_error:
                    if not porcelain:
                        console.print(
                            f"   {EMOJIS['error']} Import failed with error: {import_error}",
                            style=RICH_STYLES["error"],
                        )
                        # Try to extract more details from the error
                        errors = getattr(import_error, "errors", None)
                        if errors:
                            console.print("   📋 Error details:")
                            for err in errors:
                                console.print(f"      - {err}")
                    raise
            else:
                if not porcelain:
                    console.print(
                        f"   {EMOJIS['warning']} No assets found to push",
                        style=RICH_STYLES["warning"],
                    )

        except Exception as e:
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} Push to {target.workspace_id} failed: {e}",
                    style=RICH_STYLES["error"],
                )
            raise


if __name__ == "__main__":
    app()
