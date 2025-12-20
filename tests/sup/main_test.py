"""
Tests for ``sup.main``.
"""

# pylint: disable=redefined-outer-name, invalid-name

from typer.testing import CliRunner

from sup.main import app


def test_sup_help() -> None:
    """
    Test the ``sup --help`` command.
    """
    runner = CliRunner()
    result = runner.invoke(app, ["--help"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Usage: sup [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "--help" in result.stdout or "Show this message" in result.stdout


def test_sup_version() -> None:
    """
    Test the ``sup --version`` command.
    """
    runner = CliRunner()
    result = runner.invoke(app, ["--version"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "version" in result.stdout.lower()


def test_sup_no_command() -> None:
    """
    Test the ``sup`` command with no subcommand (should show banner).
    """
    runner = CliRunner()
    result = runner.invoke(app, [], catch_exceptions=False)

    # Should exit successfully and show banner/help message
    assert result.exit_code == 0
    assert "Use sup --help for available commands" in result.stdout.lower() or "help" in result.stdout.lower()


def test_sup_command_modules() -> None:
    """
    Test that main command modules are displayed in help output.
    """
    runner = CliRunner()
    result = runner.invoke(app, ["--help"], catch_exceptions=False)

    assert result.exit_code == 0
    # Check that key command module headers are mentioned in help
    help_output = result.stdout.lower()
    assert "─ options ─" in help_output
    assert "─ configuration & setup ─" in help_output
    assert "─ direct data access ─" in help_output
    assert "─ manage assets ─" in help_output
    assert "─ synchronize assets across workspaces ─" in help_output
