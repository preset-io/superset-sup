"""
Tests for the sup import native command.
"""

import os
from unittest.mock import patch

from typer.testing import CliRunner

from sup.commands.import_ import import_native

# Create a test app wrapping the command directly
import typer

test_app = typer.Typer()
test_app.command()(import_native)

runner = CliRunner()


def test_import_native_dir_not_found():
    """Test importing from non-existent directory."""
    with runner.isolated_filesystem():
        result = runner.invoke(test_app, ["nonexistent_dir", "--force", "--porcelain"])
        assert result.exit_code == 1


def test_import_native_not_a_directory():
    """Test importing from a file instead of directory."""
    with runner.isolated_filesystem():
        with open("not_a_dir", "w") as f:
            f.write("hello")
        result = runner.invoke(test_app, ["not_a_dir", "--force", "--porcelain"])
        assert result.exit_code == 1


def test_import_native_invalid_asset_type():
    """Test importing with invalid asset type."""
    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--asset-type", "invalid", "--force", "--porcelain"],
        )
        assert result.exit_code == 1


@patch("sup.config.settings.SupContext")
def test_import_native_no_workspace(MockContext):
    """Test importing without configured workspace."""
    mock_ctx = MockContext.return_value
    mock_ctx.get_target_workspace_id.return_value = None
    mock_ctx.get_workspace_id.return_value = None

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 1
