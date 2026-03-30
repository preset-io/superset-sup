"""
Asset ownership management commands for sup CLI.

Handles export and import of dataset, chart, and dashboard ownership metadata.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

import typer
import yaml
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

_logger = logging.getLogger(__name__)

app = typer.Typer(help="Manage asset ownership", no_args_is_help=True)

RESOURCE_TYPES = ["dataset", "chart", "dashboard"]


@app.command("export")
def export_ownership(
    path: Annotated[
        Path,
        typer.Argument(help="Output file path"),
    ] = Path("ownership.yaml"),
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Override workspace"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML to stdout")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Export asset ownership to a YAML file.

    Exports ownership metadata for datasets, charts, and dashboards.

    Example:
        sup ownership export
        sup ownership export ownership.yaml
        sup ownership export --json
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        with spinner("Exporting ownership metadata", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)

            ownership = defaultdict(list)
            total = 0
            for resource_name in RESOURCE_TYPES:
                for resource in client.client.export_ownership(resource_name):
                    ownership[resource_name].append(
                        {
                            "name": resource["name"],
                            "uuid": str(resource["uuid"]),
                            "owners": resource["owners"],
                        },
                    )
                    total += 1

        ownership_dict = dict(ownership)

        if json_output:
            import json

            console.print(json.dumps(ownership_dict, indent=2))
        elif yaml_output:
            console.print(yaml.safe_dump(ownership_dict, default_flow_style=False))
        elif porcelain:
            for resource_name, resources in ownership_dict.items():
                for res in resources:
                    owners = ",".join(res.get("owners", []))
                    print(f"{resource_name}\t{res['name']}\t{res['uuid']}\t{owners}")
        else:
            with open(path, "w", encoding="utf-8") as output:
                yaml.dump(ownership_dict, output)

            console.print(
                f"{EMOJIS['success']} Exported ownership for {total} assets to {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to export ownership: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("import")
def import_ownership(
    path: Annotated[
        Path,
        typer.Argument(help="Input YAML file path"),
    ] = Path("ownership.yaml"),
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Override workspace"),
    ] = None,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error",
            "-c",
            help="Continue if an asset fails to import ownership",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying"),
    ] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Import asset ownership from a YAML file.

    Reads ownership metadata from a YAML file and applies it to assets in the workspace.
    Supports checkpoint/resume via progress.log when using --continue-on-error.

    Example:
        sup ownership import
        sup ownership import ownership.yaml
        sup ownership import --continue-on-error
        sup ownership import --dry-run
    """
    from preset_cli.cli.superset.lib import (
        LogType,
        clean_logs,
        get_logs,
        write_logs_to_file,
    )
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import spinner

    try:
        if not path.exists():
            if not porcelain:
                console.print(
                    f"{EMOJIS['error']} File not found: {path}",
                    style=RICH_STYLES["error"],
                )
            raise typer.Exit(1)

        with open(path, encoding="utf-8") as input_:
            config = yaml.load(input_, Loader=yaml.SafeLoader)

        if not config:
            if not porcelain:
                console.print("No ownership data found in file.", style=RICH_STYLES["dim"])
            return

        # Count total assets
        total = sum(len(resources) for resources in config.values())

        if dry_run:
            if not porcelain:
                console.print(
                    f"{EMOJIS['info']} Dry run: would import ownership for {total} assets",
                    style=RICH_STYLES["info"],
                )
                for resource_name, resources in config.items():
                    console.print(
                        f"  {resource_name}: {len(resources)} assets",
                        style=RICH_STYLES["dim"],
                    )
            else:
                for resource_name, resources in config.items():
                    for res in resources:
                        print(f"import\t{resource_name}\t{res.get('name', 'unnamed')}")
            return

        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)

        # Get checkpoint logs
        log_file_path, logs = get_logs(LogType.OWNERSHIP)
        assets_to_skip = {log["uuid"] for log in logs[LogType.OWNERSHIP]} | {
            log["uuid"] for log in logs[LogType.ASSETS] if log["status"] == "FAILED"
        }

        # Build user email->id map
        users = {user["email"]: user["id"] for user in client.client.export_users()}

        imported = 0
        failed = 0

        with spinner(f"Importing ownership for {total} assets", silent=porcelain) as sp:
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                for resource_name, resources in config.items():
                    resource_ids = {
                        str(v): k for k, v in client.client.get_uuids(resource_name).items()
                    }

                    for ownership in resources:
                        if ownership["uuid"] in assets_to_skip:
                            continue

                        asset_log = {"uuid": ownership["uuid"], "status": "SUCCESS"}

                        try:
                            client.client.import_ownership(
                                resource_name,
                                ownership,
                                users,
                                resource_ids,
                            )
                            imported += 1
                        except Exception as exc:
                            _logger.debug(
                                "Failed to import ownership for %s %s: %s",
                                resource_name,
                                ownership["name"],
                                str(exc),
                            )
                            if not continue_on_error:
                                raise
                            asset_log["status"] = "FAILED"
                            failed += 1

                        logs[LogType.OWNERSHIP].append(asset_log)
                        write_logs_to_file(log_file, logs)

                        if sp:
                            sp.text = f"Imported {imported}/{total} assets"

        # Clean up logs on success
        if not continue_on_error or not any(
            log["status"] == "FAILED" for log in logs[LogType.OWNERSHIP]
        ):
            clean_logs(LogType.OWNERSHIP, logs)

        if porcelain:
            print(f"imported:{imported}")
            if failed:
                print(f"failed:{failed}")
        else:
            msg = f"{EMOJIS['success']} Imported ownership for {imported} assets"
            if failed:
                msg += f" ({failed} failed)"
            console.print(msg, style=RICH_STYLES["success"])

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to import ownership: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
