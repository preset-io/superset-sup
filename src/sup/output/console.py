"""
Centralized console configuration for sup CLI.

Provides a console factory that respects user preferences like monochrome mode.
"""

import os
from typing import Optional

from rich.console import Console
from rich.theme import Theme

_console_cache: Optional[Console] = None


def get_console(force_no_color: bool = False, theme: Optional[Theme] = None) -> Console:
    """
    Get a configured Rich Console instance that respects user preferences.

    Checks (in order):
    1. force_no_color parameter
    2. NO_COLOR environment variable (universal standard)
    3. sup config color_output setting

    Args:
        force_no_color: Override all settings and force no color output
        theme: Optional Rich theme to apply

    Returns:
        Configured Console instance
    """
    global _console_cache

    # Determine if we should disable colors
    no_color = force_no_color

    if not no_color:
        # Check NO_COLOR env var (universal standard: https://no-color.org/)
        if os.environ.get("NO_COLOR"):
            no_color = True

    if not no_color:
        # Check sup config
        try:
            from sup.config.settings import SupContext

            ctx = SupContext()
            config = ctx.global_config
            # Invert color_output to get no_color
            no_color = not config.color_output
        except Exception:
            # If config loading fails, default to colors enabled
            no_color = False

    # Create console with appropriate settings (cache it)
    # Note: We don't cache themed consoles since they may differ
    if theme is not None:
        return Console(no_color=no_color, theme=theme)

    if _console_cache is None or _console_cache.no_color != no_color:
        _console_cache = Console(no_color=no_color)

    return _console_cache


def reset_console_cache():
    """Reset the console cache (useful for testing or config changes)."""
    global _console_cache
    _console_cache = None


# Export a default console instance for convenience
# This dynamically gets the current console, respecting any config changes


class _ConsoleProxy:
    """Proxy object that always returns the current console."""

    def __getattr__(self, name):
        return getattr(get_console(), name)

    def __call__(self, *args, **kwargs):
        return get_console()(*args, **kwargs)


console = _ConsoleProxy()
