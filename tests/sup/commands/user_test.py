"""Tests for sup.commands.user - 100% coverage."""

import json
from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.user import app, display_user_details

runner = CliRunner()


def _make_spinner_mocks():
    """Create mock spinner context manager."""
    mock_spinner_cm = MagicMock()
    mock_spinner_obj = MagicMock()
    mock_spinner_cm.__enter__ = MagicMock(return_value=mock_spinner_obj)
    mock_spinner_cm.__exit__ = MagicMock(return_value=False)
    return mock_spinner_cm, mock_spinner_obj


SAMPLE_USERS = [
    {
        "id": 1,
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "username": "alice",
        "role": ["Admin"],
    },
    {
        "id": 2,
        "email": "bob@example.com",
        "first_name": "Bob",
        "last_name": "Jones",
        "username": "bob",
        "role": ["Creator"],
    },
]


class TestListUsers:
    """Tests for list_users command."""

    def test_table_output(self):
        spinner_cm, spinner_obj = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_client.display_users_table.assert_called_once()
        assert spinner_obj.text == "Found 2 users"

    def test_json_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 2
        assert parsed[0]["email"] == "alice@example.com"

    def test_yaml_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["list", "--yaml"])

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert len(parsed) == 2

    def test_porcelain_output(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm) as mock_ds,
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
            patch("sup.output.formatters.display_porcelain_list") as mock_porcelain,
        ):
            result = runner.invoke(app, ["list", "--porcelain"])

        assert result.exit_code == 0
        mock_porcelain.assert_called_once_with(
            [dict(u) for u in SAMPLE_USERS],
            ["id", "email", "first_name", "last_name", "username", "role"],
        )
        mock_ds.assert_called_once_with("users", silent=True)

    def test_with_limit(self):
        spinner_cm, spinner_obj = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["list", "--limit", "1"])

        assert result.exit_code == 0
        args = mock_client.display_users_table.call_args[0]
        assert len(args[0]) == 1
        assert spinner_obj.text == "Found 1 users"

    def test_spinner_none(self):
        """Cover the `if sp:` branch when spinner is None."""
        spinner_cm = MagicMock()
        spinner_cm.__enter__ = MagicMock(return_value=None)
        spinner_cm.__exit__ = MagicMock(return_value=False)
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0

    def test_error_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch(
                "sup.config.settings.SupContext",
                side_effect=RuntimeError("fail"),
            ),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "Failed to list users" in result.output

    def test_error_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch(
                "sup.config.settings.SupContext",
                side_effect=RuntimeError("fail"),
            ),
        ):
            result = runner.invoke(app, ["list", "--porcelain"])

        assert result.exit_code == 1
        assert "Failed to list users" not in result.output


class TestUserInfo:
    """Tests for user_info command."""

    def test_found_table(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
            patch("sup.commands.user.display_user_details") as mock_display,
        ):
            result = runner.invoke(app, ["info", "1"])

        assert result.exit_code == 0
        mock_display.assert_called_once()
        assert mock_display.call_args[0][0]["id"] == 1

    def test_found_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["info", "1", "--porcelain"])

        assert result.exit_code == 0
        assert "1\talice@example.com\tAlice\tSmith" in result.output

    def test_found_json(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["info", "1", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["id"] == 1

    def test_found_yaml(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["info", "1", "--yaml"])

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert parsed["id"] == 1

    def test_not_found_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["info", "999"])

        assert result.exit_code == 1
        assert "User 999 not found" in result.output

    def test_not_found_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()
        mock_client = MagicMock()
        mock_client.client.export_users.return_value = iter(SAMPLE_USERS)

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch("sup.config.settings.SupContext"),
            patch(
                "sup.clients.superset.SupSupersetClient.from_context",
                return_value=mock_client,
            ),
        ):
            result = runner.invoke(app, ["info", "999", "--porcelain"])

        assert result.exit_code == 1
        assert "not found" not in result.output

    def test_error_no_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch(
                "sup.config.settings.SupContext",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = runner.invoke(app, ["info", "1"])

        assert result.exit_code == 1
        assert "Failed to get user info" in result.output

    def test_error_porcelain(self):
        spinner_cm, _ = _make_spinner_mocks()

        with (
            patch("sup.output.spinners.data_spinner", return_value=spinner_cm),
            patch(
                "sup.config.settings.SupContext",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = runner.invoke(app, ["info", "1", "--porcelain"])

        assert result.exit_code == 1
        assert "Failed to get user info" not in result.output


class TestDisplayUserDetails:
    """Tests for display_user_details helper."""

    def test_roles_as_list(self):
        user = {
            "id": 1,
            "email": "a@b.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "username": "alice",
            "role": ["Admin", "Creator"],
        }
        with patch("sup.commands.user.console") as mock_console:
            display_user_details(user)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "Admin, Creator" in content

    def test_roles_as_string(self):
        user = {
            "id": 2,
            "email": "b@b.com",
            "first_name": "Bob",
            "last_name": "Jones",
            "username": "bob",
            "role": "Viewer",
        }
        with patch("sup.commands.user.console") as mock_console:
            display_user_details(user)
            content = mock_console.print.call_args[0][0].renderable
            assert "Viewer" in content

    def test_empty_roles(self):
        user = {
            "id": 3,
            "email": "c@c.com",
            "first_name": "Charlie",
            "last_name": "",
            "username": "charlie",
            "role": [],
        }
        with patch("sup.commands.user.console") as mock_console:
            display_user_details(user)
            content = mock_console.print.call_args[0][0].renderable
            assert "No roles" in content

    def test_empty_name(self):
        user = {
            "id": 4,
            "email": "d@d.com",
            "first_name": "",
            "last_name": "",
            "username": "anon",
            "role": [],
        }
        with patch("sup.commands.user.console") as mock_console:
            display_user_details(user)
            panel = mock_console.print.call_args[0][0]
            content = panel.renderable
            assert "Name: Unknown" in content
            assert "Unknown" in panel.title
