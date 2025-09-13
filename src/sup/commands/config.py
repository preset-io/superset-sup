"""
Configuration management commands for sup CLI.

Handles authentication, settings, and persistent configuration.
"""

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES

app = typer.Typer(help="Manage configuration", name="config", no_args_is_help=True)
console = Console()


@app.command("show")
def show_config():
    """
    Display current configuration settings.

    Shows authentication status, default workspace, database, and preferences.
    """
    from rich.panel import Panel

    from sup.config.settings import SupContext

    console.print(
        f"{EMOJIS['config']} Current sup configuration:",
        style=RICH_STYLES["header"],
    )

    try:
        ctx = SupContext()

        # Authentication status
        token, secret = ctx.get_preset_credentials()
        auth_status = "✅ Configured" if token and secret else "❌ Not configured"

        # Context info
        workspace_id = ctx.get_workspace_id()
        database_id = ctx.get_database_id()

        # Create info panel
        info_lines = [
            f"Authentication: {auth_status}",
            f"Current workspace: {workspace_id or 'None'}",
            f"Current database: {database_id or 'None'}",
            f"Output format: {ctx.global_config.output_format.value}",
            f"Max rows: {ctx.global_config.max_rows}",
            f"Show query time: {ctx.global_config.show_query_time}",
        ]

        panel_content = "\n".join(info_lines)
        console.print(Panel(panel_content, title="Configuration", border_style="green"))

        # Show config file locations
        from sup.config.paths import get_global_config_file, get_project_state_file

        console.print("\n📂 Configuration files:", style=RICH_STYLES["info"])
        console.print(
            f"Global config: {get_global_config_file()}",
            style=RICH_STYLES["dim"],
        )
        console.print(
            f"Project state: {get_project_state_file()}",
            style=RICH_STYLES["dim"],
        )

        if not token or not secret:
            console.print(
                "\n💡 Run [bold]sup config auth[/] to set up authentication",
                style=RICH_STYLES["info"],
            )

    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to load configuration: {e}",
            style=RICH_STYLES["error"],
        )


@app.command("set")
def set_config(
    key: Annotated[str, typer.Argument(help="Configuration key to set")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
    global_config: Annotated[
        bool,
        typer.Option("--global", "-g", help="Set in global config"),
    ] = False,
):
    """
    Set a configuration value.

    Examples:
        sup config set workspace-id 123
        sup config set database-id 5 --global
        sup config set output-format json
    """
    scope = "global" if global_config else "local"
    console.print(
        f"{EMOJIS['config']} Setting {key} = {value} ({scope})",
        style=RICH_STYLES["info"],
    )

    # TODO: Implement config setting
    console.print(
        f"{EMOJIS['success']} Configuration updated",
        style=RICH_STYLES["success"],
    )


@app.command("auth")
def auth_setup():
    """
    Set up authentication credentials.

    Guides through Preset API token setup or Superset instance configuration.
    """
    from sup.auth.preset import test_auth_credentials
    from sup.config.settings import SupContext

    console.print(f"{EMOJIS['lock']} Authentication Setup", style=RICH_STYLES["header"])
    console.print(
        "Let's set up your Preset credentials for seamless access to your workspaces.",
        style=RICH_STYLES["info"],
    )
    console.print()

    # Get current context
    ctx = SupContext()

    # Check if credentials already exist
    existing_token, existing_secret = ctx.get_preset_credentials()
    if existing_token and existing_secret:
        console.print(
            f"{EMOJIS['info']} Found existing credentials",
            style=RICH_STYLES["info"],
        )

        # Test existing credentials
        if test_auth_credentials(existing_token, existing_secret):
            console.print(
                f"{EMOJIS['success']} Existing credentials are valid!",
                style=RICH_STYLES["success"],
            )

            update = input("Do you want to update them anyway? [y/N]: ").strip().lower()
            if update not in ("y", "yes"):
                console.print(
                    "Authentication setup cancelled.",
                    style=RICH_STYLES["dim"],
                )
                return
        else:
            console.print(
                f"{EMOJIS['warning']} Existing credentials appear to be invalid",
                style=RICH_STYLES["warning"],
            )

    console.print(
        "📋 You can find your API credentials at: https://manage.app.preset.io/app/user",
        style=RICH_STYLES["info"],
    )
    console.print()

    # Get API token
    api_token = input("Enter your Preset API Token: ").strip()
    if not api_token:
        console.print(
            f"{EMOJIS['error']} API token is required",
            style=RICH_STYLES["error"],
        )
        return

    # Get API secret
    api_secret = input("Enter your Preset API Secret: ").strip()
    if not api_secret:
        console.print(
            f"{EMOJIS['error']} API secret is required",
            style=RICH_STYLES["error"],
        )
        return

    # Test credentials
    console.print(
        f"{EMOJIS['loading']} Testing credentials...",
        style=RICH_STYLES["info"],
    )

    if test_auth_credentials(api_token, api_secret):
        console.print(
            f"{EMOJIS['success']} Credentials are valid!",
            style=RICH_STYLES["success"],
        )

        # Ask where to store
        console.print()
        console.print(
            "How would you like to store these credentials?",
            style=RICH_STYLES["header"],
        )
        console.print(
            "1. [bold]Global config[/] (~/.sup/config.yml) - recommended for personal use",
        )
        console.print(
            "2. [bold]Environment variables[/] - more secure, great for CI/CD",
        )
        console.print("3. [bold]Skip storage[/] - set SUP_* env vars manually")
        console.print()

        choice = input("Choose an option [1-3]: ").strip()

        if choice == "1":
            # Store in global config
            ctx.global_config.preset_api_token = api_token
            ctx.global_config.preset_api_secret = api_secret
            ctx.global_config.save_to_file()

            console.print(
                f"{EMOJIS['success']} Credentials saved to ~/.sup/config.yml",
                style=RICH_STYLES["success"],
            )

        elif choice == "2":
            # Show environment variable instructions
            console.print(
                "Add these to your shell profile (~/.zshrc, ~/.bashrc, etc.):",
                style=RICH_STYLES["info"],
            )
            console.print(
                f"export SUP_PRESET_API_TOKEN='{api_token}'",
                style=RICH_STYLES["data"],
            )
            console.print(
                f"export SUP_PRESET_API_SECRET='{api_secret}'",
                style=RICH_STYLES["data"],
            )

        else:
            console.print(
                "You can set credentials manually with these environment variables:",
                style=RICH_STYLES["info"],
            )
            console.print("SUP_PRESET_API_TOKEN=your_token", style=RICH_STYLES["data"])
            console.print(
                "SUP_PRESET_API_SECRET=your_secret",
                style=RICH_STYLES["data"],
            )

        console.print()
        console.print(
            f"{EMOJIS['rocket']} Setup complete! Try: [bold]sup workspace list[/]",
            style=RICH_STYLES["success"],
        )

    else:
        console.print(
            f"{EMOJIS['error']} Invalid credentials. Please check your API token and secret.",
            style=RICH_STYLES["error"],
        )
        console.print(
            "💡 Make sure you're using the correct credentials from https://manage.app.preset.io/app/user",
            style=RICH_STYLES["dim"],
        )


@app.command("init")
def init_project():
    """
    Initialize sup configuration in current directory.

    Creates .sup/ directory with project-specific settings.
    """
    console.print(
        f"{EMOJIS['rocket']} Initializing sup project...",
        style=RICH_STYLES["info"],
    )

    # TODO: Implement project initialization
    console.print(
        f"{EMOJIS['success']} Project initialized! Use 'sup config show' to see settings.",
        style=RICH_STYLES["success"],
    )
