"""
dbt sync command for sup CLI.

Provides synchronization between dbt Core/Cloud projects and Superset workspaces.
Syncs models to datasets, metrics, and writes back exposures.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES


def format_dbt_help():
    """Create beautifully formatted help text for dbt command group."""
    from sup.output.styles import COLORS

    return f"""\
[not dim][bold bright_white]🔄 dbt to Superset synchronization[/bold bright_white][/not dim]

[bold {COLORS.primary}]Key Features:[/bold {COLORS.primary}]
• [bright_white]Model sync:[/bright_white] dbt models → Superset datasets with schema & metrics
• [bright_white]Database sync:[/bright_white] dbt profiles → Superset database connections
• [bright_white]Exposures:[/bright_white] Superset charts/dashboards → dbt exposures
• [bright_white]Selective sync:[/bright_white] Use --select and --exclude for model filtering
• [bright_white]Metadata preservation:[/bright_white] Keep Superset customizations

[bold {COLORS.primary}]Supported Sources:[/bold {COLORS.primary}]
• [bright_white]dbt Core:[/bright_white] Local manifest.json from dbt compile/run
• [bright_white]dbt Cloud:[/bright_white] Remote manifest via API integration

[bold {COLORS.primary}]Common Workflows:[/bold {COLORS.primary}]
• [bright_white]Initial setup:[/bright_white] Import database, sync all models
• [bright_white]Development:[/bright_white] Sync specific models during iteration
• [bright_white]Documentation:[/bright_white] Write exposures back to dbt project"""


app = typer.Typer(help=format_dbt_help(), rich_markup_mode="rich", no_args_is_help=True)


def _resolve_manifest(file_path: str) -> Path:
    """
    Resolve a manifest.json path from either a direct path or a dbt_project.yml.

    If file_path points to a dbt_project.yml, reads it to find target-path
    and returns the resolved manifest.json path.
    """
    import yaml

    path = Path(file_path)

    if path.name == "dbt_project.yml":
        if not path.exists():
            return path  # Let caller handle the error

        with open(path, encoding="utf-8") as f:
            project = yaml.safe_load(f)

        target_path = project.get("target-path", "target")
        return path.parent / target_path / "manifest.json"

    return path


def _dry_run_preview(
    manifest_path: str,
    select: Optional[List[str]],
    exclude: Optional[List[str]],
    import_db: bool,
    exposures_path: Optional[str],
    porcelain: bool,
) -> None:
    """Preview what would be synced without making changes."""
    import json

    from preset_cli.cli.superset.sync.dbt.lib import apply_select
    from preset_cli.cli.superset.sync.dbt.schemas import ModelSchema

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    model_schema = ModelSchema()
    all_models = []
    for node in data.get("nodes", {}).values():
        if node.get("resource_type") == "model":
            unique_id = node["unique_id"]
            node["children"] = data.get("child_map", {}).get(unique_id, [])
            all_models.append(model_schema.load(node))

    selected = apply_select(all_models, tuple(select or []), tuple(exclude or []))

    if porcelain:
        for model in selected:
            print(f"{model['name']}\t{model['schema']}\t{model['database']}")
    else:
        console.print(
            f"{EMOJIS['info']} DRY RUN - {len(selected)} models would be synced:",
            style=RICH_STYLES["info"],
        )
        for model in selected:
            console.print(
                f"  - {model['name']} ({model['schema']}.{model['database']})",
                style=RICH_STYLES["dim"],
            )
        if import_db:
            console.print("  Database connection would be imported")
        if exposures_path:
            console.print(f"  Exposures would be written to: {exposures_path}")


@app.command("core")
def sync_dbt_core(
    manifest_path: Annotated[
        str,
        typer.Argument(help="Path to dbt manifest.json file"),
    ],
    project: Annotated[
        Optional[str],
        typer.Option("--project", help="Name of the dbt project"),
    ] = None,
    target: Annotated[
        Optional[str],
        typer.Option("--target", help="dbt target name"),
    ] = None,
    profiles_path: Annotated[
        Optional[str],
        typer.Option("--profiles", help="Path to profiles.yml file"),
    ] = None,
    exposures_path: Annotated[
        Optional[str],
        typer.Option("--exposures", help="Path where exposures will be written"),
    ] = None,
    import_db: Annotated[
        bool,
        typer.Option("--import-db", help="Import database connection to Superset"),
    ] = False,
    disallow_edits: Annotated[
        bool,
        typer.Option("--disallow-edits", help="Mark resources as managed externally"),
    ] = False,
    external_url_prefix: Annotated[
        str,
        typer.Option("--external-url-prefix", help="Base URL for external resources"),
    ] = "",
    select: Annotated[
        Optional[List[str]],
        typer.Option("--select", "-s", help="Model selection (can be used multiple times)"),
    ] = None,
    exclude: Annotated[
        Optional[List[str]],
        typer.Option("--exclude", "-x", help="Models to exclude (can be used multiple times)"),
    ] = None,
    exposures_only: Annotated[
        bool,
        typer.Option("--exposures-only", help="Only fetch exposures, don't sync models"),
    ] = False,
    preserve_metadata: Annotated[
        bool,
        typer.Option("--preserve-metadata", help="Preserve Superset column/metric configurations"),
    ] = False,
    merge_metadata: Annotated[
        bool,
        typer.Option("--merge-metadata", help="Merge dbt and Superset metadata intelligently"),
    ] = False,
    raise_failures: Annotated[
        bool,
        typer.Option("--raise-failures", help="Exit with error if a model fails to sync"),
    ] = False,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Target workspace ID (overrides config)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying them"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
) -> None:
    """
    Sync a dbt Core project to Superset.

    Reads a compiled manifest.json file from your dbt project and syncs
    models as datasets, metrics as Superset metrics, and optionally writes
    back Superset charts/dashboards as dbt exposures.

    Examples:
        sup dbt core ./target/manifest.json --import-db
        sup dbt core ./target/manifest.json --select tag:mart
        sup dbt core ./target/manifest.json --exposures ./models/exposures.yml
        sup dbt core ./target/manifest.json --preserve-metadata --select +orders
    """
    from preset_cli.cli.superset.sync.dbt.command import dbt_core as legacy_dbt_core
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    # Resolve manifest (supports dbt_project.yml)
    manifest = _resolve_manifest(manifest_path)
    if not manifest.exists():
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Manifest file not found: {manifest}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)

    # Use resolved path for the rest of the command
    manifest_path = str(manifest)

    if not porcelain:
        console.print(
            f"{EMOJIS['sync']} Syncing dbt Core project to Superset",
            style=RICH_STYLES["header"],
        )
        console.print(f"📄 Manifest: {manifest_path}")

        if select:
            console.print(f"✅ Selected: {', '.join(select)}")
        if exclude:
            console.print(f"❌ Excluded: {', '.join(exclude)}")

        if import_db:
            console.print("🗄️  Will import database connection")
        if exposures_path:
            console.print(f"📝 Will write exposures to: {exposures_path}")

    if dry_run:
        _dry_run_preview(manifest_path, select, exclude, import_db, exposures_path, porcelain)
        return

    try:
        # Get current context and client
        ctx = SupContext()

        # Use specified workspace or current
        if workspace_id:
            if not porcelain:
                console.print(f"🎯 Using workspace: {workspace_id}")
            client = SupSupersetClient.from_context(ctx, workspace_id)
        else:
            client = SupSupersetClient.from_context(ctx)

        # Use click's context to pass the client
        import click
        from click.testing import CliRunner

        runner = CliRunner()

        # Build command line args
        cmd_args = [str(manifest_path)]
        if project:
            cmd_args.extend(["--project", project])
        if target:
            cmd_args.extend(["--target", target])
        if profiles_path:
            cmd_args.extend(["--profiles", profiles_path])
        if exposures_path:
            cmd_args.extend(["--exposures", exposures_path])
        if import_db:
            cmd_args.append("--import-db")
        if disallow_edits:
            cmd_args.append("--disallow-edits")
        if external_url_prefix:
            cmd_args.extend(["--external-url-prefix", external_url_prefix])
        for s in select or []:
            cmd_args.extend(["--select", s])
        for e in exclude or []:
            cmd_args.extend(["--exclude", e])
        if exposures_only:
            cmd_args.append("--exposures-only")
        if preserve_metadata:
            cmd_args.append("--preserve-metadata")
        if merge_metadata:
            cmd_args.append("--merge-metadata")
        if raise_failures:
            cmd_args.append("--raise-failures")

        # Execute the legacy command with our client
        with click.Context(legacy_dbt_core) as ctx_click:
            ctx_click.obj = {"client": client.client}  # Pass underlying SupersetClient
            result = runner.invoke(legacy_dbt_core, cmd_args, obj=ctx_click.obj)

        if result.exit_code != 0:
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} dbt sync failed: {result.output}",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(result.exit_code)

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} dbt Core sync completed successfully",
                style=RICH_STYLES["success"],
            )
            if result.output:
                console.print(result.output)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Sync failed: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("cloud")
def sync_dbt_cloud(
    token: Annotated[
        Optional[str],
        typer.Argument(help="dbt Cloud API token (or use config/env var)"),
    ] = None,
    account_id: Annotated[
        Optional[int],
        typer.Argument(help="dbt Cloud account ID"),
    ] = None,
    project_id: Annotated[
        Optional[int],
        typer.Argument(help="dbt Cloud project ID"),
    ] = None,
    job_id: Annotated[
        Optional[int],
        typer.Argument(help="dbt Cloud job ID"),
    ] = None,
    exposures_path: Annotated[
        Optional[str],
        typer.Option("--exposures", help="Path where exposures will be written"),
    ] = None,
    disallow_edits: Annotated[
        bool,
        typer.Option("--disallow-edits", help="Mark resources as managed externally"),
    ] = False,
    external_url_prefix: Annotated[
        str,
        typer.Option("--external-url-prefix", help="Base URL for external resources"),
    ] = "",
    select: Annotated[
        Optional[List[str]],
        typer.Option("--select", "-s", help="Model selection (can be used multiple times)"),
    ] = None,
    exclude: Annotated[
        Optional[List[str]],
        typer.Option("--exclude", "-x", help="Models to exclude (can be used multiple times)"),
    ] = None,
    exposures_only: Annotated[
        bool,
        typer.Option("--exposures-only", help="Only fetch exposures, don't sync models"),
    ] = False,
    preserve_metadata: Annotated[
        bool,
        typer.Option("--preserve-metadata", help="Preserve Superset column/metric configurations"),
    ] = False,
    merge_metadata: Annotated[
        bool,
        typer.Option("--merge-metadata", help="Merge dbt and Superset metadata intelligently"),
    ] = False,
    access_url: Annotated[
        Optional[str],
        typer.Option("--access-url", help="Custom API URL for dbt Cloud"),
    ] = None,
    raise_failures: Annotated[
        bool,
        typer.Option("--raise-failures", help="Exit with error if a model fails to sync"),
    ] = False,
    database_id: Annotated[
        Optional[int],
        typer.Option("--database-id", help="The database ID to associate synced models with"),
    ] = None,
    database_name: Annotated[
        Optional[str],
        typer.Option(
            "--database-name", help="The DB connection name to associate synced models with"
        ),
    ] = None,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Target workspace ID (overrides config)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying them"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
) -> None:
    """
    Sync a dbt Cloud project to Superset.

    Connects to dbt Cloud API to fetch the latest manifest and syncs
    models as datasets, metrics as Superset metrics, and optionally writes
    back Superset charts/dashboards as dbt exposures.

    TOKEN can be provided as argument, config, or env var (DBT_CLOUD_API_TOKEN).
    Account, project, and job IDs can be provided as arguments or via config:
        sup config set dbt-cloud-account-id 12345
        sup config set dbt-cloud-project-id 67890
        sup config set dbt-cloud-api-token YOUR_TOKEN

    If IDs are not provided, you'll be prompted to select interactively.

    Examples:
        sup dbt cloud YOUR_TOKEN                  # Interactive selection
        sup dbt cloud YOUR_TOKEN 12345 67890      # Specific account & project
        sup dbt cloud YOUR_TOKEN 12345 67890 111  # Specific job
        sup dbt cloud --select tag:mart           # Using config for credentials
    """
    import os

    from sup.config.settings import SupContext

    # Get config values
    ctx = SupContext()
    config = ctx.config

    # Use provided values or fall back to config/env
    token = token or config.dbt_cloud_api_token or os.environ.get("DBT_CLOUD_API_TOKEN")
    account_id = account_id or config.dbt_cloud_account_id
    project_id = project_id or config.dbt_cloud_project_id
    job_id = job_id or config.dbt_cloud_job_id

    # Validate required token
    if not token:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} dbt Cloud API token required. Provide as argument or:",
                style=RICH_STYLES["error"],
            )
            console.print("  sup config set dbt-cloud-api-token YOUR_TOKEN")
            console.print("  export DBT_CLOUD_API_TOKEN=YOUR_TOKEN")
        raise typer.Exit(1)

    if not porcelain:
        console.print(
            f"{EMOJIS['sync']} Syncing dbt Cloud project to Superset",
            style=RICH_STYLES["header"],
        )
        if account_id:
            console.print(f"☁️  Account: {account_id}")
        if project_id:
            console.print(f"📦 Project: {project_id}")
        if job_id:
            console.print(f"🔧 Job: {job_id}")

        if select:
            console.print(f"✅ Selected: {', '.join(select)}")
        if exclude:
            console.print(f"❌ Excluded: {', '.join(exclude)}")

        if exposures_path:
            console.print(f"📝 Will write exposures to: {exposures_path}")

    if dry_run:
        masked_token = f"****{token[-4:]}" if len(token) >= 4 else "****"
        if porcelain:
            print(f"token:{masked_token}")
            if account_id:
                print(f"account_id:{account_id}")
            if project_id:
                print(f"project_id:{project_id}")
            if job_id:
                print(f"job_id:{job_id}")
            if workspace_id:
                print(f"workspace_id:{workspace_id}")
            if select:
                print(f"select:{','.join(select)}")
            if exclude:
                print(f"exclude:{','.join(exclude)}")
            print(f"exposures:{exposures_path or 'no'}")
            print(f"import_db:{'yes' if database_id or database_name else 'no'}")
            print(f"disallow_edits:{'yes' if disallow_edits else 'no'}")
            print(f"exposures_only:{'yes' if exposures_only else 'no'}")
            print(f"preserve_metadata:{'yes' if preserve_metadata else 'no'}")
            print(f"merge_metadata:{'yes' if merge_metadata else 'no'}")
        else:
            console.print(
                f"{EMOJIS['info']} DRY RUN - No changes will be made",
                style=RICH_STYLES["info"],
            )
            console.print()
            console.print("[bold bright_white]Sync Configuration Summary[/bold bright_white]")
            console.print(f"  Token: {masked_token}")
            if account_id:
                console.print(f"  Account ID: {account_id}")
            if project_id:
                console.print(f"  Project ID: {project_id}")
            if job_id:
                console.print(f"  Job ID: {job_id}")
            if workspace_id:
                console.print(f"  Target workspace: {workspace_id}")
            if select:
                console.print(f"  Select: {', '.join(select)}")
            if exclude:
                console.print(f"  Exclude: {', '.join(exclude)}")
            if exposures_path:
                console.print(f"  Exposures: {exposures_path}")
            else:
                console.print("  Exposures: not configured")
            if database_id:
                console.print(f"  Database ID: {database_id}")
            if database_name:
                console.print(f"  Database name: {database_name}")
            console.print(f"  Disallow edits: {'yes' if disallow_edits else 'no'}")
            console.print(f"  Exposures only: {'yes' if exposures_only else 'no'}")
            console.print(f"  Preserve metadata: {'yes' if preserve_metadata else 'no'}")
            console.print(f"  Merge metadata: {'yes' if merge_metadata else 'no'}")
        return

    try:
        from preset_cli.cli.superset.sync.dbt.command import dbt_cloud as legacy_dbt_cloud
        from sup.clients.superset import SupSupersetClient

        # Get client for workspace
        if workspace_id:
            if not porcelain:
                console.print(f"🎯 Using workspace: {workspace_id}")
            client = SupSupersetClient.from_context(ctx, workspace_id)
        else:
            client = SupSupersetClient.from_context(ctx)

        # Build command line args for legacy command
        import click
        from click.testing import CliRunner

        runner = CliRunner()

        # Build args: token [account_id] [project_id] [job_id]
        cmd_args = [token]
        if account_id:
            cmd_args.append(str(account_id))
        if project_id:
            cmd_args.append(str(project_id))
        if job_id:
            cmd_args.append(str(job_id))

        # Add options
        if exposures_path:
            cmd_args.extend(["--exposures", exposures_path])
        if disallow_edits:
            cmd_args.append("--disallow-edits")
        if external_url_prefix:
            cmd_args.extend(["--external-url-prefix", external_url_prefix])
        for s in select or []:
            cmd_args.extend(["--select", s])
        for e in exclude or []:
            cmd_args.extend(["--exclude", e])
        if exposures_only:
            cmd_args.append("--exposures-only")
        if preserve_metadata:
            cmd_args.append("--preserve-metadata")
        if merge_metadata:
            cmd_args.append("--merge-metadata")
        if access_url:
            cmd_args.extend(["--access-url", access_url])
        if raise_failures:
            cmd_args.append("--raise-failures")
        if database_id:
            cmd_args.extend(["--database-id", str(database_id)])
        if database_name:
            cmd_args.extend(["--database-name", database_name])

        # Execute with client context
        with click.Context(legacy_dbt_cloud) as ctx_click:
            ctx_click.obj = {"client": client.client}
            result = runner.invoke(legacy_dbt_cloud, cmd_args, obj=ctx_click.obj)

        if result.exit_code != 0:
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} dbt Cloud sync failed: {result.output}",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(result.exit_code)

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} dbt Cloud sync completed successfully",
                style=RICH_STYLES["success"],
            )
            if result.output:
                console.print(result.output)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Sync failed: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("list-models")
def list_models(
    manifest_path: Annotated[
        str,
        typer.Argument(help="Path to dbt manifest.json file"),
    ],
    select: Annotated[
        Optional[List[str]],
        typer.Option("--select", "-s", help="Model selection (can be used multiple times)"),
    ] = None,
    exclude: Annotated[
        Optional[List[str]],
        typer.Option("--exclude", "-x", help="Models to exclude (can be used multiple times)"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: table, json, yaml"),
    ] = "table",
) -> None:
    """
    List dbt models from a manifest file.

    Useful for previewing which models will be synced before running
    the full sync operation.

    Examples:
        sup dbt list-models ./target/manifest.json
        sup dbt list-models ./target/manifest.json --select tag:mart
        sup dbt list-models ./target/manifest.json --format json
    """
    import json
    from pathlib import Path

    manifest = Path(manifest_path)
    if not manifest.exists():
        console.print(
            f"{EMOJIS['error']} Manifest file not found: {manifest_path}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)

    try:
        with open(manifest) as f:
            data = json.load(f)

        models = data.get("nodes", {})

        # Filter to only model nodes and convert to list
        from preset_cli.cli.superset.sync.dbt.lib import apply_select
        from preset_cli.cli.superset.sync.dbt.schemas import ModelSchema

        model_schema = ModelSchema()
        all_models = []
        for node_id, node in models.items():
            if node.get("resource_type") == "model":
                # Add children info for selection logic
                unique_id = node["unique_id"]
                node["children"] = data.get("child_map", {}).get(unique_id, [])
                all_models.append(model_schema.load(node))

        # Apply dbt selection logic
        selected_models = apply_select(all_models, tuple(select or []), tuple(exclude or []))

        # Convert to display format
        model_list: List[Dict[str, Any]] = []
        for model in selected_models:
            model_list.append(
                {
                    "name": model["name"],
                    "schema": model["schema"],
                    "database": model["database"],
                    "tags": model["tags"],
                    "materialized": model["config"].get("materialized"),
                }
            )

        if format == "json":
            import json

            console.print(json.dumps(model_list, indent=2))
        elif format == "yaml":
            import yaml

            console.print(yaml.dump(model_list, default_flow_style=False))
        else:
            # Table format
            from rich.table import Table

            table = Table(title=f"dbt Models ({len(model_list)} total)")
            table.add_column("Name", style="cyan")
            table.add_column("Schema", style="green")
            table.add_column("Database", style="yellow")
            table.add_column("Materialized", style="blue")
            table.add_column("Tags", style="magenta")

            for model_dict in model_list:
                table.add_row(
                    model_dict["name"],
                    model_dict["schema"],
                    model_dict["database"],
                    model_dict["materialized"],
                    ", ".join(model_dict["tags"]),
                )

            console.print(table)

        console.print(
            f"\n{EMOJIS['info']} Found {len(model_list)} models",
            style=RICH_STYLES["info"],
        )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to parse manifest: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
