"""
Superset instance management commands for sup CLI.

Handles listing and selecting self-hosted Superset instances for CLI operations.
"""


import typer
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage self-hosted Superset instances", no_args_is_help=True)


@app.command("list")
def list_instances(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    List all configured self-hosted Superset instances.

    Shows instance name, URL, authentication method, and configuration status.
    """
    from sup.config.settings import SupContext
    from sup.output.formatters import display_porcelain_list
    from sup.output.spinners import data_spinner

    try:
        with data_spinner("Superset instances", silent=porcelain) as sp:
            ctx = SupContext()
            instance_names = ctx.get_all_instance_names()

            # Get instance configs
            instances = []
            for name in instance_names:
                config = ctx.get_superset_instance_config(name)
                if config:
                    instances.append(
                        {
                            "name": name,
                            "url": config.url,
                            "auth_method": config.auth_method,
                            "status": "configured",
                        }
                    )

            # Update spinner with results
            if sp:
                sp.text = f"Found {len(instances)} instances"

        if not instances:
            if not porcelain:
                console.print(
                    f"{EMOJIS['info']} No Superset instances configured",
                    style=RICH_STYLES["info"],
                )
                console.print(
                    "💡 Add instances to ~/.sup/config.yml under superset_instances",
                    style=RICH_STYLES["dim"],
                )
            return

        if porcelain:
            # Tab-separated: Name, URL, Auth Method, Status
            display_porcelain_list(
                instances,
                ["name", "url", "auth_method", "status"],
            )
        elif json_output:
            import json

            console.print(json.dumps(instances, indent=2))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(instances, default_flow_style=False, indent=2),
            )
        else:
            display_instances_table(instances, ctx)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list instances: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_instances_table(instances: list, ctx) -> None:
    """Display instances in a beautiful Rich table."""
    from rich.table import Table

    if not instances:
        console.print(
            f"{EMOJIS['warning']} No instances configured",
            style=RICH_STYLES["warning"],
        )
        return

    # Get current instance
    current_instance = ctx.get_instance_name()

    table = Table(
        title=f"{EMOJIS['server']} Configured Superset Instances",
        show_header=True,
        header_style="bold #10B981",
        border_style="#10B981",
    )

    table.add_column("Current", justify="center", width=8)
    table.add_column("Name", style="cyan", min_width=15)
    table.add_column("URL", style="bright_white", min_width=30)
    table.add_column("Auth Method", style="yellow", min_width=15)

    for instance in instances:
        is_current = "✅" if instance["name"] == current_instance else ""
        table.add_row(
            is_current,
            instance["name"],
            instance["url"],
            instance["auth_method"],
        )

    console.print(table)

    if current_instance:
        console.print(
            f"\n💡 Current instance: [cyan]{current_instance}[/cyan]",
            style=RICH_STYLES["info"],
        )
    else:
        console.print(
            "\n💡 Use [bold]sup instance use <NAME>[/] to set an instance as default",
            style=RICH_STYLES["dim"],
        )


@app.command("use")
def use_instance(
    instance_name: Annotated[str, typer.Argument(help="Instance name to use as default")],
    persist: Annotated[
        bool,
        typer.Option("--persist", "-p", help="Save to global config"),
    ] = False,
):
    """
    Set the default Superset instance for current session.

    This instance will be used for all subsequent commands unless overridden with --instance.

    Examples:
      sup instance use prod
      sup instance use staging
      sup instance use dev --persist
    """
    from sup.config.settings import SupContext

    try:
        ctx = SupContext()

        # Validate instance exists
        instance_config = ctx.get_superset_instance_config(instance_name)
        if not instance_config:
            console.print(
                f"{EMOJIS['error']} Instance '{instance_name}' not found",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup instance list[/] to see available instances",
                style=RICH_STYLES["info"],
            )
            raise typer.Exit(1)

        console.print(
            f"{EMOJIS['server']} Setting instance '{instance_name}' as default...",
            style=RICH_STYLES["info"],
        )

        ctx.set_instance_context(instance_name, persist=persist)

        if persist:
            console.print(
                f"{EMOJIS['success']} Instance '{instance_name}' saved globally",
                style=RICH_STYLES["success"],
            )
        else:
            console.print(
                f"{EMOJIS['success']} Using instance '{instance_name}' for this session",
                style=RICH_STYLES["success"],
            )
            console.print(
                "💡 Add --persist to save globally",
                style=RICH_STYLES["dim"],
            )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to set instance: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


@app.command("show")
def show_instance_context():
    """
    Show current Superset instance context.

    Displays the instance configured for use in the current session.
    """
    from sup.config.settings import SupContext

    try:
        ctx = SupContext()
        current_instance = ctx.get_instance_name()

        console.print(
            f"{EMOJIS['server']} Current Superset Instance Context",
            style=RICH_STYLES["header"],
        )

        if current_instance:
            instance_config = ctx.get_superset_instance_config(current_instance)
            if instance_config:
                console.print(
                    f"📍 Instance: [cyan]{current_instance}[/cyan]",
                    style=RICH_STYLES["info"],
                )
                console.print(
                    f"🔗 URL: [bright_white]{instance_config.url}[/bright_white]",
                    style=RICH_STYLES["info"],
                )
                console.print(
                    f"🔐 Auth: [yellow]{instance_config.auth_method}[/yellow]",
                    style=RICH_STYLES["info"],
                )
            else:
                console.print(
                    f"⚠️  Instance '{current_instance}' configured but not found",
                    style=RICH_STYLES["warning"],
                )
        else:
            console.print(
                "📍 Instance: [dim]Not configured[/dim]",
                style=RICH_STYLES["warning"],
            )
            console.print(
                "💡 Run [bold]sup instance list[/] and [bold]sup instance use <NAME>[/]",
                style=RICH_STYLES["dim"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to show instance context: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
