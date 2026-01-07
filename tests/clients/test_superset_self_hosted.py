"""Tests for self-hosted Superset client path."""

import pytest
from unittest.mock import MagicMock, patch

from sup.clients.superset import SupSupersetClient
from sup.config.settings import SupContext, SupersetInstanceConfig


@pytest.fixture
def context_with_instance():
    """Create a context with self-hosted instance configured."""
    ctx = MagicMock(spec=SupContext)
    instance_config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/oauth2/token",
        oauth_client_id="test-client",
        oauth_client_secret="test-secret",
        oauth_username="service@example.com",
        oauth_password="password",
    )

    ctx.get_instance_name.return_value = "test-instance"
    ctx.get_workspace_id.return_value = None
    ctx.get_superset_instance_config.return_value = instance_config

    return ctx


def test_from_context_with_instance_name(context_with_instance):
    """Test from_context uses instance when provided."""
    with patch("sup.clients.superset.create_superset_auth") as mock_auth:
        mock_auth.return_value = MagicMock()

        client = SupSupersetClient.from_context(
            context_with_instance,
            instance_name="test-instance",
        )

        assert client.is_self_hosted is True
        assert client.workspace_url == "https://superset.example.com"


def test_from_context_falls_back_to_workspace(context_with_instance):
    """Test from_context falls back to workspace if no instance."""
    context_with_instance.get_instance_name.return_value = None
    context_with_instance.get_workspace_id.return_value = 123

    with patch.object(
        SupSupersetClient, "_from_preset_workspace"
    ) as mock_preset:
        mock_preset.return_value = MagicMock(is_self_hosted=False)

        SupSupersetClient.from_context(context_with_instance)

        mock_preset.assert_called_once()


def test_from_context_no_config_raises_error(context_with_instance):
    """Test from_context raises helpful error when nothing configured."""
    context_with_instance.get_instance_name.return_value = None
    context_with_instance.get_workspace_id.return_value = None

    with pytest.raises(ValueError) as exc_info:
        SupSupersetClient.from_context(context_with_instance)

    assert "instance" in str(exc_info.value).lower()
    assert "workspace" in str(exc_info.value).lower()


def test_from_instance_missing_config(context_with_instance):
    """Test _from_instance raises error if instance not found."""
    context_with_instance.get_superset_instance_config.return_value = None

    with pytest.raises(ValueError) as exc_info:
        SupSupersetClient._from_instance(context_with_instance, "missing")

    assert "missing" in str(exc_info.value).lower()


def test_from_context_instance_parameter_override(context_with_instance):
    """Test instance_name parameter overrides context."""
    with patch("sup.clients.superset.create_superset_auth") as mock_auth:
        mock_auth.return_value = MagicMock()
        other_config = SupersetInstanceConfig(
            url="https://other.example.com",
            auth_method="username_password",
            username="user",
            password="pass",
        )
        # Set up to return different config based on name
        context_with_instance.get_superset_instance_config.side_effect = (
            lambda name=None: other_config if name == "other" else None
        )

        client = SupSupersetClient.from_context(
            context_with_instance,
            instance_name="other",
        )

        assert client.workspace_url == "https://other.example.com"


def test_from_context_workspace_parameter_override(context_with_instance):
    """Test workspace_id parameter overrides instance in context."""
    context_with_instance.get_instance_name.return_value = "test-instance"

    with patch.object(
        SupSupersetClient, "_from_preset_workspace"
    ) as mock_preset:
        mock_preset.return_value = MagicMock(is_self_hosted=False)

        SupSupersetClient.from_context(
            context_with_instance,
            workspace_id=456,
        )

        # Should call _from_preset_workspace, not _from_instance
        mock_preset.assert_called_once()


def test_from_instance_auth_factory_called(context_with_instance):
    """Test that create_superset_auth is called with instance config."""
    with patch("sup.clients.superset.create_superset_auth") as mock_auth:
        mock_auth.return_value = MagicMock()

        SupSupersetClient.from_context(
            context_with_instance,
            instance_name="test-instance",
        )

        # Verify auth factory was called with instance config
        mock_auth.assert_called_once()
        call_args = mock_auth.call_args[0]
        assert isinstance(call_args[0], SupersetInstanceConfig)
        assert call_args[0].auth_method == "oauth"


def test_from_instance_auth_error_handling(context_with_instance):
    """Test error handling when auth factory fails."""
    with patch("sup.clients.superset.create_superset_auth") as mock_auth:
        mock_auth.side_effect = ValueError("Invalid credentials")

        with pytest.raises(ValueError):
            SupSupersetClient.from_context(
                context_with_instance,
                instance_name="test-instance",
            )
