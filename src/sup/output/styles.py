"""
Rich styling and color schemes for sup CLI.

Simple semantic color system with Preset branding.
"""


class COLORS:
    """Simple, essential colors for sup CLI with authentic Preset branding."""

    # Core colors - using hex for authentic Preset branding
    primary = "#10B981"  # Emerald green - authentic Preset brand
    secondary = "#06B6D4"  # Sky cyan - technical/data accent
    muted = "white"  # Dimmed content (accessible)

    # Status colors
    success = "#10B981"  # Success (same as brand - emerald green)
    warning = "#F59E0B"  # Amber warning
    error = "#EF4444"  # Red errors
    info = "#3B82F6"  # Blue information


# Simple Rich style mappings using core colors
RICH_STYLES = {
    # Brand styles (Preset identity)
    "brand": f"bold {COLORS.primary}",  # Primary Preset green
    "brand_secondary": f"bold {COLORS.secondary}",  # Secondary brand style
    # Semantic status styles
    "success": f"bold {COLORS.success}",  # Success actions
    "error": f"bold {COLORS.error}",  # Errors and failures
    "warning": f"bold {COLORS.warning}",  # Warnings and cautions
    "info": f"bold {COLORS.info}",  # Information and help
    # Content hierarchy styles
    "primary": "bold white",  # Primary content/headers
    "secondary": "white",  # Secondary content
    "muted": f"dim {COLORS.muted}",  # Less important content
    "emphasis": f"bold {COLORS.primary}",  # Emphasized content (brand color)
    # Interactive styles
    "link": f"{COLORS.info} underline",  # Clickable links
    "accent": COLORS.secondary,  # Technical/data accent
    "data": COLORS.secondary,  # Data values and results
    # Legacy aliases (for backward compatibility)
    "header": "bold white",  # Headers
    "dim": f"dim {COLORS.muted}",  # Dimmed text
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
    "download": "📥",
    "upload": "📤",
    "search": "🔍",
    "config": "⚙️",
    "workspace": "🏢",
    "sql": "📝",
    "dashboard": "📈",
    "user": "👤",
    "plus": "➕",
    "refresh": "🔄",
    "trash": "🗑️",
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
    return status_styles.get(status, RICH_STYLES["muted"])


class SemanticColors:
    """Semantic color accessor for consistent branding throughout sup CLI."""

    # Brand colors (using enum for clean access)
    primary = RICH_STYLES["brand"]  # Preset green - main brand
    secondary = RICH_STYLES["brand_secondary"]  # Secondary brand
    emphasis = RICH_STYLES["emphasis"]  # Emphasized brand content

    # Status colors
    success = RICH_STYLES["success"]  # Success states
    error = RICH_STYLES["error"]  # Error states
    warning = RICH_STYLES["warning"]  # Warning states
    info = RICH_STYLES["info"]  # Information

    # Content hierarchy
    heading = RICH_STYLES["primary"]  # Major headings
    subheading = RICH_STYLES["secondary"]  # Minor headings
    text = RICH_STYLES["secondary"]  # Normal text
    muted = RICH_STYLES["muted"]  # Less important text

    # Interactive elements
    link = RICH_STYLES["link"]  # Clickable links
    accent = RICH_STYLES["accent"]  # Data/technical accent
    data = RICH_STYLES["data"]  # Data values

    @classmethod
    def get_chart_color(cls, index: int) -> str:
        """Get chart color by index for data visualization."""
        chart_colors = [
            COLORS.primary,  # green
            COLORS.secondary,  # cyan
            COLORS.info,  # blue
            COLORS.warning,  # yellow
            COLORS.error,  # red
        ]
        return chart_colors[index % len(chart_colors)]


# Convenience instance for easy imports: colors.primary, colors.success, etc.
colors = SemanticColors()
