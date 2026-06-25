"""Tests for auth factory."""

from unittest.mock import patch

import pytest
from yarl import URL

from preset_cli.auth.factory import create_superset_auth
from preset_cli.auth.oauth_superset import OAuthSupersetAuth
from preset_cli.auth.superset import SupersetJWTAuth, UsernamePasswordAuth
from sup.config.settings import SupersetInstanceConfig


def test_factory_creates_username_password_auth(requests_mock):
    """Test factory creates UsernamePasswordAuth."""
    # UsernamePasswordAuth logs in via the Superset security API on construction.
    requests_mock.post(
        "https://superset.example.com/api/v1/security/login",
        json={"access_token": "test-token"},
    )

    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="username_password",
        username="admin",
        password="secret",
    )

    auth = create_superset_auth(config)

    assert isinstance(auth, UsernamePasswordAuth)
    assert auth.token == "test-token"


def test_factory_creates_jwt_auth():
    """Test factory creates SupersetJWTAuth."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="jwt",
        jwt_token="eyJhbGc...",
    )

    auth = create_superset_auth(config)

    assert isinstance(auth, SupersetJWTAuth)


def test_factory_creates_oauth_auth():
    """Test factory creates OAuthSupersetAuth."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/token",
        oauth_client_id="client-123",
        oauth_client_secret="secret-456",
        oauth_username="service@example.com",
        oauth_password="password",
    )

    with patch("preset_cli.auth.oauth_superset.OAuthSupersetAuth.auth"):
        auth = create_superset_auth(config)

    assert isinstance(auth, OAuthSupersetAuth)
    assert auth.client_id == "client-123"
    assert auth.username == "service@example.com"


def test_factory_validates_username_password():
    """Test factory validates username_password config."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="username_password",
        username="admin",
        # Missing password
    )

    with pytest.raises(ValueError, match="requires both 'username' and 'password'"):
        create_superset_auth(config)


def test_factory_validates_jwt():
    """Test factory validates jwt config."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="jwt",
        # Missing jwt_token
    )

    with pytest.raises(ValueError, match="requires 'jwt_token'"):
        create_superset_auth(config)


def test_factory_validates_oauth_complete():
    """Test factory validates all OAuth2 fields."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/token",
        oauth_client_id="client-123",
        # Missing client_secret, username, password
    )

    with pytest.raises(ValueError, match="Missing: client_secret"):
        create_superset_auth(config)


def test_factory_unknown_auth_method():
    """Test factory rejects unknown auth method."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",  # This will fail validation since not all fields provided
    )
    config.auth_method = "unknown"  # Bypass pattern validation for test

    # Actually we can't bypass pattern validation with pydantic, so test direct call
    with pytest.raises(ValueError, match="Unknown authentication method"):
        create_superset_auth(config)


def test_factory_oauth_uses_custom_scope():
    """Test factory passes custom oauth_scope."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/token",
        oauth_client_id="client-123",
        oauth_client_secret="secret",
        oauth_username="user",
        oauth_password="pass",
        oauth_scope="custom scope",
    )

    with patch("preset_cli.auth.oauth_superset.OAuthSupersetAuth.auth"):
        auth = create_superset_auth(config)

    assert auth.scope == "custom scope"


def test_factory_oauth_uses_custom_token_type():
    """Test factory passes custom oauth_token_type."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/token",
        oauth_client_id="client-123",
        oauth_client_secret="secret",
        oauth_username="user",
        oauth_password="pass",
        oauth_token_type="CustomToken",
    )

    with patch("preset_cli.auth.oauth_superset.OAuthSupersetAuth.auth"):
        auth = create_superset_auth(config)

    assert auth.token_type == "CustomToken"


def test_factory_passes_correct_urls():
    """Test factory creates auth with correct URLs."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com/",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/oauth2/token",
        oauth_client_id="client",
        oauth_client_secret="secret",
        oauth_username="user",
        oauth_password="pass",
    )

    with patch("preset_cli.auth.oauth_superset.OAuthSupersetAuth.auth"):
        auth = create_superset_auth(config)

    assert auth.base_url == URL("https://superset.example.com/")
    assert auth.token_url == URL("https://auth.example.com/oauth2/token")


def test_factory_oauth_missing_token_url():
    """Test factory validates oauth_token_url is present."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        # Missing oauth_token_url
        oauth_client_id="client",
        oauth_client_secret="secret",
        oauth_username="user",
        oauth_password="pass",
    )

    with pytest.raises(ValueError, match="Missing: token_url"):
        create_superset_auth(config)


def test_factory_oauth_missing_multiple_fields():
    """Test factory reports all missing OAuth2 fields."""
    config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/token",
        # Missing client_id, client_secret, username, password
    )

    with pytest.raises(ValueError) as exc_info:
        create_superset_auth(config)

    error_msg = str(exc_info.value)
    assert "client_id" in error_msg
    assert "client_secret" in error_msg
    assert "username" in error_msg
    assert "password" in error_msg
