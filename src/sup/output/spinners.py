"""
Beautiful spinner system for sup CLI.

Provides elegant loading indicators and status updates.
"""

from contextlib import contextmanager
from typing import Optional

from halo import Halo

from sup.output.styles import EMOJIS


def _should_use_color() -> bool:
    """Check if colors should be used (respects monochrome setting)."""
    try:
        from sup.output.console import get_console

        console = get_console()
        return not console.no_color
    except Exception:
        return True  # Default to colors if can't determine


@contextmanager
def spinner(
    text: str,
    success_text: Optional[str] = None,
    error_text: Optional[str] = None,
    silent: bool = False,
):
    """
    Context manager for beautiful loading spinners.

    Args:
        text: Loading message to display
        success_text: Message to show on success (default: ✅ Done)
        error_text: Message to show on error (default: ❌ Failed)
        silent: If True, suppress spinner (for porcelain mode)

    Usage:
        with spinner("Loading datasets...") as sp:
            datasets = fetch_datasets()
            sp.text = f"Found {len(datasets)} datasets"
    """
    if silent:
        # In silent mode (porcelain), don't show spinner
        yield None
        return

    # Respect monochrome mode
    use_color = _should_use_color()
    color = "cyan" if use_color else None
    text_color = "white" if use_color else None

    with Halo(
        text=text, spinner="dots12", color=color, text_color=text_color, enabled=use_color or None
    ) as sp:
        try:
            yield sp
            # Success message
            if success_text:
                sp.succeed(success_text)
            else:
                sp.succeed(f"{EMOJIS['success']} Done")
        except Exception:
            # Error message
            if error_text:
                sp.fail(error_text)
            else:
                sp.fail(f"{EMOJIS['error']} Failed")
            raise


def loading_spinner(text: str, silent: bool = False):
    """Simple loading spinner factory."""
    return spinner(text, silent=silent)


def query_spinner(query: str, silent: bool = False):
    """Specialized spinner for SQL query execution."""
    # Truncate long queries for spinner display
    display_query = query[:50] + "..." if len(query) > 50 else query
    return spinner(f"Executing: {display_query}", silent=silent)


def data_spinner(entity_type: str, count: Optional[int] = None, silent: bool = False):
    """Specialized spinner for data loading operations."""
    text = f"Loading {entity_type}..."
    success_text = f"{EMOJIS['success']} Found {count} {entity_type}" if count is not None else None
    return spinner(text, success_text=success_text, silent=silent)
