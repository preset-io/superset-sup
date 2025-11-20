"""
Theme testing command for sup CLI.

Quick utility to test colors and styling in the terminal.
"""

import typer
# Removed: from rich.console import Console

app = typer.Typer(help="Test themes and colors", no_args_is_help=True)

# ASCII Art Banner for testing
BANNER = """██ ███████╗██╗   ██╗██████╗ ██╗
██ ██╔════╝██║   ██║██╔══██╗██║
   ███████╗██║   ██║██████╔╝██║
   ╚════██║██║   ██║██╔═══╝ ╚═╝
   ███████║╚██████╔╝██║     ██╗
   ╚══════╝ ╚═════╝ ╚═╝     ╚═╝"""


@app.command("colors")
def test_colors():
    """Test ASCII logo with different green options using hex colors for maximum distinction."""

    print("🎨 ASCII Logo Color Options (using hex colors for distinction):")
    print()

    # Use actual hex colors that should look different
    color_options = [
        ("#22C55E", "1. Modern Green (hex #22C55E)"),
        ("#10B981", "2. Emerald Green (hex #10B981)"),
        ("#06B6D4", "3. Sky Cyan (hex #06B6D4)"),
        ("#0EA5E9", "4. Blue Cyan (hex #0EA5E9)"),
        ("#3B82F6", "5. Pure Blue (hex #3B82F6)"),
        ("#FFFFFF", "6. White (neutral)"),
        ("green", "7. Terminal Green"),
        ("cyan", "8. Terminal Cyan"),
    ]

    for color, description in color_options:
        console.print(f"\n{description}:", style="bold white")
        console.print(BANNER, style=f"bold {color}")

        # Add color blocks for comparison
        console.print("   Block: ", end="")
        console.print("█████████████", style=f"bold {color}")
        print()


@app.command("palette")
def test_palette():
    """Test the full color palette."""
    from sup.output.styles import COLORS, colors

    console.print("\n🎨 Current Color Palette:", style="bold white")
    console.print("Primary (Brand): ", style="white", end="")
    console.print("■■■ Preset Green", style=f"bold {COLORS.primary}")

    console.print("Secondary (Accent): ", style="white", end="")
    console.print("■■■ Cyan", style=f"bold {COLORS.secondary}")

    console.print("Success: ", style="white", end="")
    console.print("■■■ Success Green", style=colors.success)

    console.print("Warning: ", style="white", end="")
    console.print("■■■ Warning Yellow", style=colors.warning)

    console.print("Error: ", style="white", end="")
    console.print("■■■ Error Red", style=colors.error)

    console.print("Info: ", style="white", end="")
    console.print("■■■ Info Blue", style=colors.info)

    console.print("Muted: ", style="white", end="")
    console.print("■■■ Muted Text", style=colors.muted)
    print()


@app.command("banner")
def test_banner():
    """Test the full banner with current branding."""
    from sup.main import show_banner

    show_banner()


if __name__ == "__main__":
    app()
