"""
Theme management commands for sup CLI.

Handles theme listing, pull, and push operations using Superset's
GET /api/v1/theme/export/ and POST /api/v1/theme/import/ endpoints.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from zipfile import ZipFile

import typer
from rich.table import Table
from typing_extensions import Annotated

from sup.lib import remove_root, safe_extract_path
from sup.output.console import console
from sup.output.formatters import display_porcelain_list
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage themes", no_args_is_help=True)


@app.command("list")
def list_themes(
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
        typer.Option("--search", help="Search themes by name (server-side)"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", "-m", help="Show only themes you own"),
    ] = False,
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
) -> None:
    """
    List themes in the current or specified workspace.

    Examples:
        sup theme list                         # All themes
        sup theme list --search="dark"         # Search by name
        sup theme list --limit 10              # First 10 themes
        sup theme list --json                  # Output as JSON
        sup theme list --porcelain             # Machine-readable IDs + names
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("themes", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            page = (page_filter - 1) if page_filter else 0
            themes = client.get_themes(
                silent=True,
                limit=page_size_filter or limit_filter,
                page=page,
                text_search=search_filter,
            )

            if id_filter:
                themes = [t for t in themes if t.get("id") == id_filter]
            elif ids_filter:
                id_list = [int(x.strip()) for x in ids_filter.split(",")]
                themes = [t for t in themes if t.get("id") in id_list]

            if mine_filter:
                try:
                    current_user = client.client.get_me()  # type: ignore[attr-defined]
                    current_user_id = current_user.get("id")
                    if current_user_id:
                        themes = [
                            t
                            for t in themes
                            if t.get("changed_by", {}).get("id") == current_user_id
                        ]
                except Exception:
                    pass

            if limit_filter and not page_size_filter:
                themes = themes[:limit_filter]

            if offset_filter:
                themes = themes[offset_filter:]

            if sp:
                sp.text = f"Found {len(themes)} themes"

        if porcelain:
            display_porcelain_list(themes, fields=["id", "theme_name"])
        elif json_output:
            import json

            console.print(json.dumps(themes, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(themes, default_flow_style=False, indent=2),
            )
        else:
            _display_themes_table(themes)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list themes: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("pull")
def pull_themes(
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output directory for exported YAML files"),
    ] = "./assets",
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Pull specific theme by ID"),
    ] = None,
    ids_filter: Annotated[
        Optional[str],
        typer.Option("--ids", help="Pull multiple themes by IDs (comma-separated)"),
    ] = None,
    search_filter: Annotated[
        Optional[str],
        typer.Option("--search", help="Pull themes matching search term"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompts"),
    ] = False,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
) -> None:
    """
    Pull theme definitions from workspace to local YAML files.

    Downloads theme configurations using GET /api/v1/theme/export/ and saves
    them as YAML files to the output directory.

    Examples:
        sup theme pull                           # Pull all themes to ./assets
        sup theme pull --output ./my_themes      # Custom output directory
        sup theme pull --id=1                    # Pull specific theme
        sup theme pull --search="dark" --overwrite  # Pull matching, overwrite
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        ctx = SupContext()
        resolved_output = ctx.get_assets_folder(cli_override=output)

        if not porcelain:
            console.print(
                f"{EMOJIS['export']} Pulling themes to {resolved_output}...",
                style=RICH_STYLES["info"],
            )

        output_path = Path(resolved_output)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            console.print(
                f"{EMOJIS['error']} Path exists but is not a directory: {resolved_output}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

        client = SupSupersetClient.from_context(ctx, workspace_id)

        with data_spinner("themes to pull", silent=porcelain) as sp:
            themes = client.get_themes(silent=True, text_search=search_filter)

            if id_filter:
                themes = [t for t in themes if t.get("id") == id_filter]
            elif ids_filter:
                id_list = [int(x.strip()) for x in ids_filter.split(",")]
                themes = [t for t in themes if t.get("id") in id_list]

            if sp:
                sp.text = f"Found {len(themes)} themes to pull"

        if not themes:
            console.print(
                f"{EMOJIS['warning']} No themes match your filters",
                style=RICH_STYLES["warning"],
            )
            return

        theme_ids = [t["id"] for t in themes]

        if not porcelain:
            console.print(
                f"{EMOJIS['info']} Pulling {len(theme_ids)} theme(s)...",
                style=RICH_STYLES["info"],
            )

        zip_buffer = client.client.export_zip("theme", theme_ids)

        with ZipFile(zip_buffer) as bundle:
            contents = {remove_root(name): bundle.read(name).decode() for name in bundle.namelist()}

        files_written = 0
        resolved_base = output_path.resolve()
        for file_name, file_contents in contents.items():
            target = safe_extract_path(resolved_base, file_name)
            if target.exists() and not overwrite:
                if not porcelain:
                    console.print(
                        f"{EMOJIS['warning']} File exists, skipping: {target}",
                        style=RICH_STYLES["warning"],
                    )
                continue
            if not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(file_contents)
            files_written += 1

        if not porcelain:
            console.print(
                f"{EMOJIS['success']} Pulled {files_written} file(s) to {resolved_output}",
                style=RICH_STYLES["success"],
            )
        else:
            print(f"{files_written}\t{resolved_output}")

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to pull themes: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("push")
def push_themes(
    path: Annotated[
        str,
        typer.Argument(help="Path to YAML file or directory containing theme YAML files"),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing themes"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompts"),
    ] = False,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
) -> None:
    """
    Push theme definitions from YAML files to workspace.

    Reads theme YAML files and imports them via POST /api/v1/theme/import/.
    Accepts a single YAML file or a directory containing theme YAML files.

    Examples:
        sup theme push ./assets/themes/my_theme.yaml
        sup theme push ./assets/themes/ --overwrite
        sup theme push ./assets/ --force
    """
    import datetime
    import io

    import yaml

    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    ctx = SupContext()
    import_path = Path(path).resolve()

    if not import_path.exists():
        console.print(
            f"{EMOJIS['error']} Path does not exist: {import_path}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)

    # Collect YAML files to import
    yaml_files: List[Path] = []
    if import_path.is_file():
        if import_path.suffix in (".yaml", ".yml"):
            yaml_files = [import_path]
        else:
            console.print(
                f"{EMOJIS['error']} File must be a YAML file (.yaml or .yml): {import_path}",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)
    elif import_path.is_dir():
        # Recursively find theme YAML files
        yaml_files = list(import_path.rglob("themes/*.yaml")) + list(
            import_path.rglob("themes/*.yml")
        )
        if not yaml_files:
            # Fall back to any YAML files in the directory
            yaml_files = list(import_path.glob("*.yaml")) + list(import_path.glob("*.yml"))

    if not yaml_files:
        console.print(
            f"{EMOJIS['warning']} No theme YAML files found at: {import_path}",
            style=RICH_STYLES["warning"],
        )
        return

    if not porcelain:
        console.print(
            f"{EMOJIS['import']} Pushing {len(yaml_files)} theme file(s)...",
            style=RICH_STYLES["info"],
        )

    try:
        client = SupSupersetClient.from_context(ctx, workspace_id)

        # Build a ZIP bundle from the YAML files (matching Superset's expected format)
        buf = io.BytesIO()
        with ZipFile(buf, "w") as bundle:
            for yaml_file in yaml_files:
                # Use relative path under "bundle/themes/" structure
                arc_name = f"bundle/themes/{yaml_file.name}"
                bundle.writestr(arc_name, yaml_file.read_text(encoding="utf-8"))

            # Write metadata required by Superset's import dispatcher
            metadata = yaml.safe_dump(
                {
                    "version": "1.0.0",
                    "type": "Theme",
                    "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                }
            )
            bundle.writestr("bundle/metadata.yaml", metadata)
        buf.seek(0)

        success = client.client.import_zip("theme", buf, overwrite=overwrite)

        if success:
            if not porcelain:
                console.print(
                    f"{EMOJIS['success']} Successfully pushed {len(yaml_files)} theme(s)",
                    style=RICH_STYLES["success"],
                )
            else:
                print(str(len(yaml_files)))
        else:
            console.print(
                f"{EMOJIS['error']} Push returned unexpected response",
                style=RICH_STYLES["error"],
            )
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to push themes: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def _display_themes_table(
    themes: List[Dict[str, Any]],
) -> None:
    """Display themes in a Rich table."""
    if not themes:
        console.print(
            f"{EMOJIS['warning']} No themes found",
            style=RICH_STYLES["warning"],
        )
        return

    table = Table(
        title=f"{EMOJIS['table']} Available Themes",
        show_header=True,
        header_style=RICH_STYLES["header"],
        border_style=COLORS.secondary,
    )

    table.add_column("ID", style=COLORS.secondary, no_wrap=True)
    table.add_column("Name", style="bright_white", no_wrap=False)
    table.add_column("System Default", style=COLORS.success, no_wrap=True)
    table.add_column("System Dark", style=COLORS.info, no_wrap=True)
    table.add_column("Modified", style=RICH_STYLES["dim"], no_wrap=True)

    for theme in themes:
        theme_id = str(theme.get("id", ""))
        name = theme.get("theme_name", "Unknown")
        is_default = "\u2713" if theme.get("is_system_default") else ""
        is_dark = "\u2713" if theme.get("is_system_dark") else ""
        modified = theme.get("changed_on_delta_humanized", "")

        table.add_row(theme_id, name, is_default, is_dark, modified)

    console.print(table)
