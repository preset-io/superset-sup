"""Tests for sup.commands.theme module."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sup.commands.theme import app

runner = CliRunner()


def test_test_colors():
    """test_colors prints color options via console."""
    with patch("sup.commands.theme.console") as mock_console:
        result = runner.invoke(app, ["colors"])
        assert result.exit_code == 0
        # console.print called for each color option (2 calls per color + header)
        assert mock_console.print.call_count > 0


def test_test_palette():
    """test_palette prints the full color palette."""
    with patch("sup.commands.theme.console") as mock_console:
        result = runner.invoke(app, ["palette"])
        assert result.exit_code == 0
        assert mock_console.print.call_count > 0


def test_test_banner():
    """test_banner calls show_banner from sup.main."""
    with patch("sup.main.show_banner") as mock_show_banner:
        result = runner.invoke(app, ["banner"])
        assert result.exit_code == 0
        mock_show_banner.assert_called_once()
