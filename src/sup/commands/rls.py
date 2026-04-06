"""
Row-Level Security (RLS) management commands for sup CLI.

Handles pull and push of RLS rules for Superset workspaces.
"""

from pathlib import Path
from typing import Optional

import typer
import yaml
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage row-level security rules", no_args_is_help=True)


@app.command("pull")
def pull_rls(
    path: Annotated[
        Path,
        typer.Argument(help="Output file path"),
    ] = Path("rls.yaml"),
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
    Pull RLS rules to a YAML file.

    Pulls all row-level security rules from the workspace to a YAML file
    that can be version-controlled and pushed into other workspaces.

    Example:
        sup rls pull
        sup rls pull rules.yaml
        sup rls pull --json
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("RLS rules", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)
            rules = list(client.client.export_rls())

        if json_output:
            import json

            console.print(json.dumps(rules, indent=2))
        elif yaml_output:
            console.print(yaml.safe_dump(rules, default_flow_style=False, sort_keys=False))
        elif porcelain:
            for rule in rules:
                name = rule.get("name", "")
                tables = ",".join(rule.get("tables", []))
                print(f"{name}\t{tables}")
        else:
            with open(path, "w", encoding="utf-8") as output:
                yaml.dump(rules, output, sort_keys=False)

            console.print(
                f"{EMOJIS['success']} Pulled {len(rules)} RLS rules to {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to pull RLS rules: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("push")
def push_rls(
    path: Annotated[
        Path,
        typer.Argument(help="Input YAML file path"),
    ] = Path("rls.yaml"),
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Override workspace"),
    ] = None,
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
    Push RLS rules from a YAML file.

    Reads RLS rules from a YAML file and pushes them into the workspace.
    Use --dry-run to preview what would be pushed.

    Example:
        sup rls push
        sup rls push rules.yaml
        sup rls push --dry-run
    """
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
            rules = yaml.load(input_, Loader=yaml.SafeLoader)

        if not rules:
            if not porcelain:
                console.print("No RLS rules found in file.", style=RICH_STYLES["dim"])
            return

        if dry_run:
            if not porcelain:
                console.print(
                    f"{EMOJIS['info']} Dry run: would push {len(rules)} RLS rules",
                    style=RICH_STYLES["info"],
                )
                for rule in rules:
                    name = rule.get("name", "unnamed")
                    console.print(f"  - {name}", style=RICH_STYLES["dim"])
            else:
                for rule in rules:
                    print(f"import\t{rule.get('name', 'unnamed')}")
            return

        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)

        with spinner(f"Pushing {len(rules)} RLS rules", silent=porcelain):
            for rule in rules:
                client.client.import_rls(rule)

        if porcelain:
            print(f"pushed:{len(rules)}")
        else:
            console.print(
                f"{EMOJIS['success']} Pushed {len(rules)} RLS rules from {path}",
                style=RICH_STYLES["success"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to push RLS rules: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
