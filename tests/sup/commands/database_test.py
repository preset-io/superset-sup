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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm) as mock_ds, patch(
            "sup.config.settings.SupContext"
        ), patch(
            "sup.clients.superset.SupSupersetClient.from_context",
            return_value=mock_client,
        ), patch("sup.output.formatters.display_porcelain_list") as mock_porcelain:
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
            "sup.clients.superset.SupSupersetClient.from_context",
            return_value=mock_client,
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0

    def test_error_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "Failed to list databases" in result.output

    def test_error_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
            "sup.clients.superset.SupSupersetClient.from_context",
            return_value=mock_client,
        ), patch("sup.commands.database.display_database_details") as mock_display:
            result = runner.invoke(app, ["info", "1"])

        assert result.exit_code == 0
        mock_display.assert_called_once_with(SAMPLE_DATABASES[0])

    def test_porcelain_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.get_database.return_value = SAMPLE_DATABASES[0]

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
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

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext"
        ), patch(
            "sup.clients.superset.SupSupersetClient.from_context",
            return_value=mock_client,
        ):
            result = runner.invoke(app, ["info", "1", "--yaml"])

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert parsed["id"] == 1

    def test_error_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
            "sup.config.settings.SupContext",
            side_effect=RuntimeError("boom"),
        ):
            result = runner.invoke(app, ["info", "1"])

        assert result.exit_code == 1
        assert "Failed to get database info" in result.output

    def test_error_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with patch("sup.output.spinners.data_spinner", return_value=spinner_cm), patch(
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


# ---------------------------------------------------------------------------
# pull_databases tests
# ---------------------------------------------------------------------------

PATCH_CTX = "sup.config.settings.SupContext"
PATCH_CLIENT = "sup.clients.superset.SupSupersetClient"
PATCH_SPINNER = "sup.output.spinners.data_spinner"


class TestPullDatabases:
    def _make_zip(self, tmp_path):
        """Create a mock zip buffer with database YAML."""
        import io
        from zipfile import ZipFile

        buf = io.BytesIO()
        with ZipFile(buf, "w") as zf:
            zf.writestr("db_export/databases/prod.yaml", "database_name: prod")
        buf.seek(0)
        return buf

    def _setup_mocks(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx = MagicMock()
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        ctx.get_assets_folder.return_value = str(assets)
        mock_ctx_cls.return_value = ctx

        client = MagicMock()
        client.get_databases.return_value = [{"id": 1, "database_name": "prod"}]
        client.client.export_zip.return_value = self._make_zip(tmp_path)
        mock_client_cls.from_context.return_value = client

        sp = MagicMock()
        mock_spinner.return_value.__enter__ = MagicMock(return_value=sp)
        mock_spinner.return_value.__exit__ = MagicMock(return_value=False)

        return ctx, client, sp

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_all(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0
        assert "Exported" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_by_id(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        result = runner.invoke(app, ["pull", "--id", "1"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_by_ids(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        result = runner.invoke(app, ["pull", "--ids", "1,2"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_no_match(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        client.get_databases.return_value = []
        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0
        assert "No databases" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        # In porcelain mode, data_spinner yields None
        mock_spinner.return_value.__enter__ = MagicMock(return_value=None)
        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_overwrite(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        assets = tmp_path / "assets"
        db_dir = assets / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "prod.yaml").write_text("old content")
        result = runner.invoke(app, ["pull", "--overwrite"])
        assert result.exit_code == 0
        assert "database_name" in (db_dir / "prod.yaml").read_text()

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_skip_existing(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        assets = tmp_path / "assets"
        db_dir = assets / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "prod.yaml").write_text("old content")
        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0
        assert (db_dir / "prod.yaml").read_text() == "old content"

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_disable_jinja_escaping(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        result = runner.invoke(app, ["pull", "--disable-jinja-escaping"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_force_unix_eol(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        result = runner.invoke(app, ["pull", "--force-unix-eol"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_creates_output_dir(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        new_dir = tmp_path / "new_assets"
        ctx.get_assets_folder.return_value = str(new_dir)
        assert not new_dir.exists()
        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0
        assert new_dir.exists()

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_porcelain_output(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0
        # Porcelain outputs "count\tpath"
        assert "\t" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_skip_existing_porcelain(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        ctx, client, sp = self._setup_mocks(mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path)
        assets = tmp_path / "assets"
        db_dir = assets / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "prod.yaml").write_text("old content")
        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0
        assert (db_dir / "prod.yaml").read_text() == "old content"

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_error_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(tmp_path)
        mock_ctx_cls.return_value = ctx
        mock_client_cls.from_context.side_effect = Exception("fail")
        mock_spinner.return_value.__enter__ = MagicMock(side_effect=Exception("fail"))
        mock_spinner.return_value.__exit__ = MagicMock(return_value=False)
        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_path_is_file(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx = MagicMock()
        fpath = tmp_path / "notdir"
        fpath.write_text("x")
        ctx.get_assets_folder.return_value = str(fpath)
        mock_ctx_cls.return_value = ctx
        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_error(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(tmp_path)
        mock_ctx_cls.return_value = ctx
        mock_client_cls.from_context.side_effect = Exception("connection failed")
        mock_spinner.return_value.__enter__ = MagicMock(side_effect=Exception("connection failed"))
        mock_spinner.return_value.__exit__ = MagicMock(return_value=False)
        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# _escape_jinja / _traverse_escape tests
# ---------------------------------------------------------------------------


class TestEscapeJinja:
    def test_escapes_jinja_markers(self):
        from sup.lib import escape_jinja

        result = escape_jinja("key: '{{ value }}'")
        assert "__JINJA2_OPEN__" in result
        assert "__JINJA2_CLOSE__" in result

    def test_invalid_yaml_returns_unchanged(self):
        from sup.lib import escape_jinja

        content = "not: valid: yaml: {{{"
        assert escape_jinja(content) == content

    def test_non_dict_yaml_returns_unchanged(self):
        from sup.lib import escape_jinja

        content = "- item1\n- item2"
        assert escape_jinja(content) == content

    def test_traverse_nested(self):
        from sup.lib import _traverse_escape

        data = {"a": {"b": "{{ x }}", "c": [1, "{{ y }}"]}}
        result = _traverse_escape(data)
        assert "__JINJA2_OPEN__" in result["a"]["b"]
        assert "__JINJA2_OPEN__" in result["a"]["c"][1]
        assert result["a"]["c"][0] == 1
