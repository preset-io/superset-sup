"""Tests for sup.commands.database - 100% coverage."""

import json
from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.database import app, display_database_details

runner = CliRunner()


def _make_spinner_mocks():
    """Create mock spinner context manager."""
    mock_spinner_cm = MagicMock()
    mock_spinner_obj = MagicMock()
    mock_spinner_cm.__enter__ = MagicMock(return_value=mock_spinner_obj)
    mock_spinner_cm.__exit__ = MagicMock(return_value=False)
    return mock_spinner_cm, mock_spinner_obj


SAMPLE_DATABASES = [
    {
        "id": 1,
        "database_name": "Production",
        "backend": "postgresql",
        "expose_in_sqllab": True,
        "allow_ctas": True,
        "allow_cvas": False,
        "allow_dml": True,
        "allow_file_upload": False,
        "allow_run_async": True,
        "uuid": "abc-123",
    },
    {
        "id": 2,
        "database_name": "Staging",
        "backend": "mysql",
        "expose_in_sqllab": False,
    },
]


class TestListDatabases:
    """Tests for list_databases command."""

    def test_table_output(self):
        spinner_cm, spinner_obj = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_databases.return_value = SAMPLE_DATABASES

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_client.display_databases_table.assert_called_once_with(SAMPLE_DATABASES)
        assert spinner_obj.text == "Found 2 databases"

    def test_json_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_databases.return_value = SAMPLE_DATABASES

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 2
        assert parsed[0]["database_name"] == "Production"

    def test_yaml_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_databases.return_value = SAMPLE_DATABASES

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["list", "--yaml"])

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert len(parsed) == 2

    def test_porcelain_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_databases.return_value = SAMPLE_DATABASES

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm) as mock_ds, \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ), \
             patch("sup.output.formatters.display_porcelain_list") as mock_porcelain:
            result = runner.invoke(app, ["list", "--porcelain"])

        assert result.exit_code == 0
        mock_porcelain.assert_called_once_with(
            SAMPLE_DATABASES,
            ["id", "database_name", "backend", "expose_in_sqllab"],
        )
        mock_ds.assert_called_once_with("databases", silent=True)

    def test_spinner_none(self):
        """Cover the `if sp:` branch when spinner is None."""
        spinner_cm = MagicMock()
        spinner_cm.__enter__ = MagicMock(return_value=None)
        spinner_cm.__exit__ = MagicMock(return_value=False)
        mock_client = MagicMock()
        mock_client.get_databases.return_value = SAMPLE_DATABASES

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0

    def test_error_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch(
                 "sup.config.settings.SupContext",
                 side_effect=RuntimeError("fail"),
             ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "Failed to list databases" in result.output

    def test_error_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch(
                 "sup.config.settings.SupContext",
                 side_effect=RuntimeError("fail"),
             ):
            result = runner.invoke(app, ["list", "--porcelain"])

        assert result.exit_code == 1
        assert "Failed to list databases" not in result.output


class TestUseDatabase:
    """Tests for use_database command."""

    def test_persist_true(self):
        mock_ctx = MagicMock()

        with patch("sup.config.settings.SupContext", return_value=mock_ctx):
            result = runner.invoke(app, ["use", "42", "--persist"])

        assert result.exit_code == 0
        mock_ctx.set_database_context.assert_called_once_with(42, persist=True)
        assert "saved globally" in result.output

    def test_persist_false(self):
        mock_ctx = MagicMock()

        with patch("sup.config.settings.SupContext", return_value=mock_ctx):
            result = runner.invoke(app, ["use", "42"])

        assert result.exit_code == 0
        mock_ctx.set_database_context.assert_called_once_with(42, persist=False)
        assert "for this project" in result.output
        assert "--persist" in result.output

    def test_error(self):
        with patch(
            "sup.config.settings.SupContext",
            side_effect=RuntimeError("boom"),
        ):
            result = runner.invoke(app, ["use", "42"])

        assert result.exit_code == 1
        assert "Failed to set database" in result.output


class TestDatabaseInfo:
    """Tests for database_info command."""

    def test_table_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_database.return_value = SAMPLE_DATABASES[0]

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ), \
             patch("sup.commands.database.display_database_details") as mock_display:
            result = runner.invoke(app, ["info", "1"])

        assert result.exit_code == 0
        mock_display.assert_called_once_with(SAMPLE_DATABASES[0])

    def test_porcelain_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_database.return_value = SAMPLE_DATABASES[0]

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["info", "1", "--porcelain"])

        assert result.exit_code == 0
        assert "1\tProduction\tpostgresql" in result.output

    def test_json_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_database.return_value = SAMPLE_DATABASES[0]

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["info", "1", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["id"] == 1

    def test_yaml_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_database.return_value = SAMPLE_DATABASES[0]

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch("sup.config.settings.SupContext"), \
             patch(
                 "sup.clients.superset.SupSupersetClient.from_context",
                 return_value=mock_client,
             ):
            result = runner.invoke(app, ["info", "1", "--yaml"])

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert parsed["id"] == 1

    def test_error_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch(
                 "sup.config.settings.SupContext",
                 side_effect=RuntimeError("boom"),
             ):
            result = runner.invoke(app, ["info", "1"])

        assert result.exit_code == 1
        assert "Failed to get database info" in result.output

    def test_error_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), \
             patch(
                 "sup.config.settings.SupContext",
                 side_effect=RuntimeError("boom"),
             ):
            result = runner.invoke(app, ["info", "1", "--porcelain"])

        assert result.exit_code == 1
        assert "Failed to get database info" not in result.output


class TestDisplayDatabaseDetails:
    """Tests for display_database_details helper."""

    def test_full_capabilities(self):
        db = {
            "id": 1,
            "database_name": "ProdDB",
            "backend": "postgresql",
            "expose_in_sqllab": True,
            "allow_ctas": True,
            "allow_cvas": True,
            "allow_dml": True,
            "allow_file_upload": True,
            "allow_run_async": True,
            "uuid": "abc-123-def",
        }
        with patch("sup.commands.database.console") as mock_console:
            display_database_details(db)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "CTAS" in content
            assert "CVAS" in content
            assert "DML" in content
            assert "File Upload" in content
            assert "Async Queries" in content
            assert "abc-123-def" in content

    def test_no_capabilities(self):
        db = {
            "id": 2,
            "database_name": "BasicDB",
            "backend": "sqlite",
            "expose_in_sqllab": False,
        }
        with patch("sup.commands.database.console") as mock_console:
            display_database_details(db)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "Capabilities" not in content
            assert "UUID" not in content

    def test_with_uuid(self):
        db = {
            "id": 3,
            "database_name": "TestDB",
            "backend": "mysql",
            "expose_in_sqllab": True,
            "uuid": "xyz-789",
        }
        with patch("sup.commands.database.console") as mock_console:
            display_database_details(db)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "xyz-789" in content

    def test_without_uuid(self):
        db = {
            "id": 4,
            "database_name": "NoDB",
            "backend": "bigquery",
            "expose_in_sqllab": False,
        }
        with patch("sup.commands.database.console") as mock_console:
            display_database_details(db)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "UUID" not in content

    def test_partial_capabilities(self):
        """Only some capabilities enabled."""
        db = {
            "id": 5,
            "database_name": "PartialDB",
            "backend": "postgres",
            "expose_in_sqllab": True,
            "allow_ctas": True,
            "allow_cvas": False,
            "allow_dml": False,
            "allow_file_upload": True,
            "allow_run_async": False,
        }
        with patch("sup.commands.database.console") as mock_console:
            display_database_details(db)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "CTAS" in content
            assert "File Upload" in content
            assert "CVAS" not in content
            assert "DML" not in content
            assert "Async" not in content
