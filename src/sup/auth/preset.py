"""
Preset authentication for sup CLI.

Builds on preset_cli's auth system with sup-specific configuration.
"""

from typing import Optional

from yarl import URL

from preset_cli.auth.lib import get_access_token
from preset_cli.auth.preset import JWTTokenError
from preset_cli.auth.preset import PresetAuth as BasePresetAuth
from sup.config.settings import SupContext
from sup.output.styles import EMOJIS, RICH_STYLES
from sup.output.console import console


class SupPresetAuth(BasePresetAuth):
    """
    Preset authentication integrated with sup's configuration system.
    """

    @classmethod
    def from_sup_config(
        cls,
        ctx: SupContext,
        workspace_url: Optional[str] = None,
        silent: bool = False,
    ) -> "SupPresetAuth":
        """
        Create authentication from sup configuration.

        Args:
            ctx: sup configuration context
            workspace_url: Optional workspace URL override
            silent: If True, suppress auth messages (for porcelain mode)

        Returns:
            Configured SupPresetAuth instance

        Raises:
            JWTTokenError: If authentication fails or credentials are missing
        """
        # Get credentials from sup config
        api_token, api_secret = ctx.get_preset_credentials()

        if not api_token or not api_secret:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} No Preset credentials found",
                    style=RICH_STYLES["error"],
                )
                console.print(
                    "💡 Run [bold]sup config auth[/] to set up authentication",
                    style=RICH_STYLES["info"],
                )
            raise JWTTokenError("Missing Preset API credentials")

        # Use workspace URL or default to Preset's main API
        if workspace_url:
            base_url = URL(workspace_url)
        else:
            # For now, default to app.preset.io - this will be configurable
            base_url = URL("https://api.app.preset.io/")

        try:
            if not silent:
                console.print("Authenticating with Preset...", style=RICH_STYLES["dim"])
            return cls(base_url, api_token, api_secret)
        except Exception as ex:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Authentication failed: {ex}",
                    style=RICH_STYLES["error"],
                )
            raise


def get_preset_auth(
    ctx: SupContext,
    workspace_url: Optional[str] = None,
) -> SupPresetAuth:
    """
    Get authenticated Preset client.

    This is the main entry point for sup commands that need Preset authentication.
    """
    return SupPresetAuth.from_sup_config(ctx, workspace_url)


def test_auth_credentials(
    api_token: str,
    api_secret: str,
    base_url: str = "https://api.app.preset.io/",
) -> bool:
    """
    Test if Preset credentials are valid.

    Returns:
        True if credentials work, False otherwise
    """
    try:
        get_access_token(URL(base_url), api_token, api_secret)
        return True
    except Exception:
        return False
