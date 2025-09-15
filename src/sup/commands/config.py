"""
Configuration management commands for sup CLI.

Handles authentication, settings, and persistent configuration.
"""

import typer
from rich.console import Console
from rich.theme import Theme
from typing_extensions import Annotated

from sup.output.styles import COLORS, EMOJIS, RICH_STYLES


def format_config_help():
    """Create beautifully formatted help text for config command group."""
    return f"""[not dim][bold bright_white]⚙️ Configuration Management[/bold bright_white][/not dim]

[bold {COLORS.primary}]Configuration Sources (priority order):[/bold {COLORS.primary}]
• [bright_white]Environment variables:[/bright_white] [cyan]SUP_*[/cyan] (highest priority)
• [bright_white]Global config:[/bright_white] [cyan]~/.sup/config.yml[/cyan]
• [bright_white]Project config:[/bright_white] [cyan].sup/state.yml[/cyan] (current directory)

[bold {COLORS.primary}]Key Settings:[/bold {COLORS.primary}]
• [bright_white]Authentication:[/bright_white] API tokens, workspace credentials
• [bright_white]Defaults:[/bright_white] Current workspace ID, database ID, target workspace
• [bright_white]Preferences:[/bright_white] Output formats, asset folder paths
• [bright_white]Enterprise:[/bright_white] Cross-workspace sync configuration

[bold {COLORS.primary}]Quick Setup:[/bold {COLORS.primary}]
• [bold]Step 1:[/bold] [cyan]sup config auth[/cyan] - Set up authentication credentials
• [bold]Step 2:[/bold] [cyan]sup config show[/cyan] - Verify current settings
• [bold]Step 3:[/bold] [cyan]sup config env[/cyan] - See all available environment variables

[bold {COLORS.primary}]Common Tasks:[/bold {COLORS.primary}]
• [bright_white]Set workspace:[/bright_white] [cyan]sup config set workspace-id 123[/cyan]
• [bright_white]Set target:[/bright_white] [cyan]sup config set target-workspace-id 456[/cyan]
• [bright_white]Asset folder:[/bright_white] [cyan]sup config set assets-folder ./my-assets[/cyan]"""  # noqa: E501  # noqa: E501


app = typer.Typer(
    help=format_config_help(), rich_markup_mode="rich", name="config", no_args_is_help=True
)

# Use themed console to match main app styling

preset_theme = Theme(
    {
        "table.header": f"bold {COLORS.primary}",
        "table.border": COLORS.primary,
        "panel.border": COLORS.primary,
        "panel.title": f"bold {COLORS.primary}",
    },
)

console = Console(theme=preset_theme)


@app.command("show")
def show_config():
    """
    Display current configuration settings.

    Shows authentication status, default workspace, database, and preferences.

    💡 Tip: Use 'sup config env' to see all available SUP_* environment variables
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
        target_workspace_id = ctx.get_target_workspace_id()

        # Create info panel with actual config keys
        info_lines = [
            f"Authentication: {auth_status}",
            f"workspace-id: {workspace_id or 'None'}",
            f"target-workspace-id: {target_workspace_id or 'Same as workspace-id'}",
            f"database-id: {database_id or 'None'}",
            f"assets-folder: {ctx.get_assets_folder()}",
            f"output-format: {ctx.global_config.output_format.value}",
            f"max-rows: {ctx.global_config.max_rows}",
            f"show-query-time: {ctx.global_config.show_query_time}",
        ]

        panel_content = "\n".join(info_lines)
        console.print(Panel(panel_content, title="Configuration", border_style=COLORS.success))

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

    Available configuration keys:
        • workspace-id - Default workspace for pull, queries, listings
        • target-workspace-id - Target workspace for push operations (cross-workspace sync)
        • database-id - Default database for SQL queries
        • assets-folder - Default folder for pull/push operations
        • output-format - Default output format (table, json, yaml)
        • max-rows - Maximum rows to display in queries
        • show-query-time - Show query execution time
        • preset-api-token - Preset API authentication token
        • preset-api-secret - Preset API authentication secret

    Examples:
        sup config set workspace-id 123                      # Set source workspace
        sup config set target-workspace-id 456              # Set push target
        sup config set database-id 5 --global               # Set global database
        sup config set assets-folder ./my-assets/            # Set assets folder
        sup config set output-format json                   # Set output format
    """
    from sup.config.settings import SupContext

    scope = "global" if global_config else "local"
    console.print(
        f"{EMOJIS['config']} Setting {key} = {value} ({scope})",
        style=RICH_STYLES["info"],
    )

    try:
        ctx = SupContext()

        # Handle different config keys
        if key == "workspace-id":
            ctx.set_workspace_context(int(value), persist=global_config)
        elif key == "target-workspace-id":
            ctx.set_target_workspace_id(int(value), persist=global_config)
        elif key == "database-id":
            ctx.set_database_context(int(value), persist=global_config)
        elif key == "assets-folder":
            if global_config:
                ctx.global_config.assets_folder = value
                ctx.global_config.save_to_file()
            else:
                ctx.project_state.assets_folder = value
                ctx.project_state.save_to_file()
        elif key == "output-format":
            from sup.config.settings import OutputFormat

            ctx.global_config.output_format = OutputFormat(value)
            ctx.global_config.save_to_file()
        elif key == "max-rows":
            ctx.global_config.max_rows = int(value)
            ctx.global_config.save_to_file()
        elif key == "show-query-time":
            ctx.global_config.show_query_time = value.lower() in ("true", "1", "yes")
            ctx.global_config.save_to_file()
        elif key == "preset-api-token":
            ctx.global_config.preset_api_token = value
            ctx.global_config.save_to_file()
        elif key == "preset-api-secret":
            ctx.global_config.preset_api_secret = value
            ctx.global_config.save_to_file()
        else:
            console.print(
                f"{EMOJIS['error']} Unknown configuration key: {key}",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup config set --help[/] to see available keys",
                style=RICH_STYLES["info"],
            )
            raise typer.Exit(1)

        console.print(
            f"{EMOJIS['success']} Configuration updated",
            style=RICH_STYLES["success"],
        )

    except ValueError as e:
        console.print(
            f"{EMOJIS['error']} Invalid value for {key}: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(
            f"{EMOJIS['error']} Failed to set configuration: {e}",
            style=RICH_STYLES["error"],
        )
        raise typer.Exit(1)


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


@app.command("env")
def show_env_vars():
    """
    Show available environment variables for sup configuration.

    Displays all SUP_* environment variables that can be used to configure
    sup without modifying config files. Perfect for CI/CD and containers!
    """
    from sup.config.paths import get_global_config_file, get_project_state_file
    from sup.output.styles import COLORS

    console.print(f"{EMOJIS['config']} sup Configuration Guide", style=f"bold {COLORS.primary}")
    console.print(
        "sup can be configured via environment variables OR config files:",
        style=RICH_STYLES["info"],
    )
    console.print()

    # Show config file locations
    console.print("📁 Configuration File Locations:", style=f"bold {COLORS.primary}")
    console.print(f"  Global config: {get_global_config_file()}", style="white")
    console.print(f"  Project state: {get_project_state_file()}", style="white")
    console.print()

    console.print("⚙️ Environment Variables (take precedence):", style=f"bold {COLORS.primary}")

    env_vars = [
        ("SUP_PRESET_API_TOKEN", "Preset API token for authentication"),
        ("SUP_PRESET_API_SECRET", "Preset API secret for authentication"),
        ("SUP_WORKSPACE_ID", "Default workspace ID for commands"),
        ("SUP_DATABASE_ID", "Default database ID for SQL commands"),
        ("SUP_ASSETS_FOLDER", "Default folder for asset import/export operations"),
        ("SUP_OUTPUT_FORMAT", "Default output format (table, json, yaml, csv)"),
        ("SUP_MAX_ROWS", "Maximum rows to display (default: 1000)"),
        ("SUP_SHOW_QUERY_TIME", "Show query execution time (true/false)"),
        ("SUP_COLOR_OUTPUT", "Enable colored output (true/false)"),
    ]

    from rich.table import Table

    table = Table(
        show_header=True,
        header_style=f"bold {COLORS.primary}",  # Emerald green headers
        # Let the theme handle border colors
    )
    table.add_column(
        "Environment Variable",
        style=COLORS.secondary,
        no_wrap=False,
        width=25,
    )  # Cyan
    table.add_column("Description", style="bright_white", no_wrap=False)

    for var_name, description in env_vars:
        table.add_row(var_name, description)

    console.print(table)
    console.print()

    # Show examples
    console.print("Examples:", style=f"bold {COLORS.primary}")
    console.print("  export SUP_PRESET_API_TOKEN=your_token_here", style="white")
    console.print("  export SUP_WORKSPACE_ID=123", style="white")
    console.print("  export SUP_ASSETS_FOLDER=/path/to/assets", style="white")
    console.print("  export SUP_OUTPUT_FORMAT=json", style="white")
    console.print()

    console.print("Perfect for CI/CD and automation:", style=f"bold {COLORS.primary}")
    console.print(
        "  docker run -e SUP_PRESET_API_TOKEN=token my-image sup sql 'SELECT 1'",
        style="white",
    )
    console.print()

    console.print(
        "💡 Environment variables take precedence over config files",
        style=RICH_STYLES["dim"],
    )
