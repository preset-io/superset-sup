"""
Rich styling and color schemes for sup CLI.

Inspired by Superset's brand colors with modern terminal aesthetics.
"""

# Primary color scheme inspired by Superset's brand
COLORS = {
    # Primary colors
    "primary": "#20A7C9",  # Superset blue
    "secondary": "#1565C0",  # Darker blue
    "accent": "#00BCD4",  # Cyan accent
    # Status colors
    "success": "#4CAF50",  # Green
    "warning": "#FF9800",  # Orange
    "error": "#F44336",  # Red
    "info": "#2196F3",  # Blue
    # UI colors
    "text": "#FFFFFF",  # White text
    "text_dim": "#B0BEC5",  # Dim gray
    "border": "#37474F",  # Dark gray borders
    "background": "#263238",  # Dark background
    # Data visualization
    "chart_1": "#1F77B4",  # Blue
    "chart_2": "#FF7F0E",  # Orange
    "chart_3": "#2CA02C",  # Green
    "chart_4": "#D62728",  # Red
    "chart_5": "#9467BD",  # Purple
}

# Rich style mappings for easy use throughout the CLI
RICH_STYLES = {
    "brand": "bold cyan",
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
    "dim": "dim white",
    "header": "bold bright_white",
    "data": "cyan",
    "link": "blue underline",
    "accent": "bright_cyan",
    "muted": "bright_black",
}

# Emoji mappings for consistent usage
EMOJIS = {
    # Command status indicators
    "loading": "⏳",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "rocket": "🚀",
    "chart": "📊",
    "database": "🗄️",
    "table": "📋",
    "sync": "🔄",
    "export": "📤",
    "import": "📥",
    "search": "🔍",
    "config": "⚙️",
    "workspace": "🏢",
    "sql": "💾",
    "dashboard": "📈",
    "user": "👤",
    "lock": "🔐",
    "link": "🔗",
    "fire": "🔥",
    "star": "⭐",
    "party": "🎉",
}


def get_status_emoji(status: str) -> str:
    """Get emoji for a given status."""
    return EMOJIS.get(status, "")


def get_status_style(status: str) -> str:
    """Get Rich style for a given status."""
    status_styles = {
        "success": RICH_STYLES["success"],
        "error": RICH_STYLES["error"],
        "warning": RICH_STYLES["warning"],
        "info": RICH_STYLES["info"],
        "loading": RICH_STYLES["accent"],
    }
    return status_styles.get(status, RICH_STYLES["dim"])
