"""
Tests for the dashboard push and dataset push commands.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sup.commands.dashboard import app as dashboard_app
from sup.commands.dataset import app as dataset_app

runner = CliRunner()

PATCH_PUSH = "sup.commands.push_helper.push_assets"


def test_dashboard_push_calls_push_assets():
    """Test that dashboard push delegates to push_assets with DASHBOARD type."""
    with patch(PATCH_PUSH) as mock_push:
        with runner.isolated_filesystem():
            result = runner.invoke(
                dashboard_app,
                ["push", "--force", "--porcelain"],
            )
        # push_assets is called (may fail inside but the delegation works)
        mock_push.assert_called_once()
        args = mock_push.call_args
        assert args.kwargs["asset_label"] == "dashboards"
        assert args.kwargs["force"] is True
        assert args.kwargs["porcelain"] is True


def test_dataset_push_calls_push_assets():
    """Test that dataset push delegates to push_assets with DATASET type."""
    with patch(PATCH_PUSH) as mock_push:
        with runner.isolated_filesystem():
            result = runner.invoke(
                dataset_app,
                ["push", "--force", "--porcelain"],
            )
        mock_push.assert_called_once()
        args = mock_push.call_args
        assert args.kwargs["asset_label"] == "datasets"
        assert args.kwargs["force"] is True


def test_dashboard_push_with_overwrite():
    """Test dashboard push with --overwrite flag."""
    with patch(PATCH_PUSH) as mock_push:
        result = runner.invoke(
            dashboard_app,
            ["push", "--overwrite", "--force", "--porcelain"],
        )
        mock_push.assert_called_once()
        assert mock_push.call_args.kwargs["overwrite"] is True


def test_dataset_push_with_continue_on_error():
    """Test dataset push with --continue-on-error flag."""
    with patch(PATCH_PUSH) as mock_push:
        result = runner.invoke(
            dataset_app,
            ["push", "--continue-on-error", "--force", "--porcelain"],
        )
        mock_push.assert_called_once()
        assert mock_push.call_args.kwargs["continue_on_error"] is True


def test_dashboard_push_with_assets_folder():
    """Test dashboard push with custom assets folder."""
    with patch(PATCH_PUSH) as mock_push:
        result = runner.invoke(
            dashboard_app,
            ["push", "./my_assets", "--force", "--porcelain"],
        )
        mock_push.assert_called_once()
        assert mock_push.call_args.kwargs["assets_folder"] == "./my_assets"
