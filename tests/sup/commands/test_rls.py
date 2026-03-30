"""Tests for the sup rls export/import commands."""

from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.rls import app

runner = CliRunner()

SAMPLE_RLS = [
    {
        "clause": "client_id = 9",
        "description": "Rule description",
        "filter_type": "Regular",
        "group_key": "department",
        "name": "Rule name",
        "roles": ["Gamma"],
        "tables": ["main.test_table"],
    },
]

PATCH_CLIENT = "sup.clients.superset.SupSupersetClient"
PATCH_CONTEXT = "sup.config.settings.SupContext"


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_rls.return_value = iter(SAMPLE_RLS)
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["export", "rls.yaml"])
        assert result.exit_code == 0
        with open("rls.yaml") as f:
            exported = yaml.safe_load(f)
        assert len(exported) == 1
        assert exported[0]["name"] == "Rule name"


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls_json(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_rls.return_value = iter(SAMPLE_RLS)
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["export", "--json"])
    assert result.exit_code == 0
    assert "Rule name" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls_yaml(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_rls.return_value = iter(SAMPLE_RLS)
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["export", "--yaml"])
    assert result.exit_code == 0
    assert "Rule name" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_rls.return_value = iter(SAMPLE_RLS)
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["export", "--porcelain"])
    assert result.exit_code == 0
    assert "Rule name\tmain.test_table" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls_error(_MockContext, MockClient):
    MockClient.from_context.side_effect = RuntimeError("boom")
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 1
    assert "Failed to export RLS rules" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls_error_porcelain(_MockContext, MockClient):
    MockClient.from_context.side_effect = RuntimeError("boom")
    result = runner.invoke(app, ["export", "--porcelain"])
    assert result.exit_code == 1
    assert "Failed" not in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_rls(_MockContext, MockClient):
    mock_client = MagicMock()
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml"])
        assert result.exit_code == 0
    mock_client.client.import_rls.assert_called_once_with(SAMPLE_RLS[0])


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_rls_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml", "--porcelain"])
        assert result.exit_code == 0
        assert "imported:1" in result.output


def test_import_rls_dry_run():
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_import_rls_dry_run_porcelain():
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml", "--dry-run", "--porcelain"])
        assert result.exit_code == 0
        assert "import\tRule name" in result.output


def test_import_rls_file_not_found():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml"])
        assert result.exit_code == 1


def test_import_rls_file_not_found_porcelain():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "File not found" not in result.output


def test_import_rls_empty_file():
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["import", "rls.yaml"])
        assert result.exit_code == 0
        assert "No RLS rules found" in result.output


def test_import_rls_empty_file_porcelain():
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["import", "rls.yaml", "--porcelain"])
        assert result.exit_code == 0


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_rls_error(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.import_rls.side_effect = RuntimeError("boom")
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml"])
        assert result.exit_code == 1
        assert "Failed to import RLS rules" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_rls_error_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.import_rls.side_effect = RuntimeError("boom")
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "Failed" not in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_rls_multiple_rules(_MockContext, MockClient):
    mock_client = MagicMock()
    MockClient.from_context.return_value = mock_client
    rules = SAMPLE_RLS + [
        {
            "clause": "region = 'US'",
            "description": "US only",
            "filter_type": "Regular",
            "group_key": "region",
            "name": "US Filter",
            "roles": ["Alpha"],
            "tables": ["sales"],
        },
    ]
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(rules, f)
        result = runner.invoke(app, ["import", "rls.yaml"])
        assert result.exit_code == 0
    assert mock_client.client.import_rls.call_count == 2


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_rls_typer_exit(_MockContext, MockClient):
    """Cover except typer.Exit: raise in export."""
    import typer

    MockClient.from_context.side_effect = typer.Exit(1)
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 1


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_rls_typer_exit(_MockContext, MockClient):
    """Cover except typer.Exit: raise in import."""
    import typer

    MockClient.from_context.side_effect = typer.Exit(1)
    with runner.isolated_filesystem():
        with open("rls.yaml", "w") as f:
            yaml.dump(SAMPLE_RLS, f)
        result = runner.invoke(app, ["import", "rls.yaml"])
        assert result.exit_code == 1
