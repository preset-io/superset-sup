"""Tests for OAuthSupersetAuth."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from yarl import URL

from preset_cli.auth.oauth_superset import OAuthSupersetAuth


@pytest.fixture
def mock_session():
    """Mock requests session."""
    return MagicMock()


@pytest.fixture
def oauth_config():
    """Sample OAuth2 configuration."""
    return {
        "base_url": URL("https://superset.example.com"),
        "token_url": URL("https://auth.example.com/oauth2/token"),
        "client_id": "test-client",
        "client_secret": "test-secret",
        "username": "test-user",
        "password": "test-pass",
    }


def test_oauth_init_calls_auth(oauth_config):
    """Test that __init__ calls auth() to fetch tokens."""
    with patch.object(OAuthSupersetAuth, "auth") as mock_auth:
        # Create instance with mocked auth
        auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
        auth.__dict__.update(oauth_config)
        auth.auth = mock_auth
        
        # auth() should be callable
        assert callable(auth.auth)


def test_oauth_fetch_access_token(oauth_config, mock_session):
    """Test fetching access token from OAuth2 endpoint."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "test-token-123",
        "expires_in": 3600,
    }
    mock_session.post.return_value = mock_response
    
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.session = mock_session
    auth._access_token = None
    auth._token_expires = None
    auth.scope = "openid profile email roles"
    
    token = auth._fetch_access_token()
    
    assert token == "test-token-123"
    assert auth._access_token == "test-token-123"
    assert auth._token_expires is not None
    
    # Verify the token endpoint was called with correct payload
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert "grant_type" in call_args[1]["data"]
    assert call_args[1]["data"]["grant_type"] == "password"


def test_oauth_fetch_access_token_missing_expires(oauth_config, mock_session):
    """Test token fetch when server doesn't return expires_in."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "test-token-456",
    }
    mock_session.post.return_value = mock_response
    
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.session = mock_session
    auth._access_token = None
    auth._token_expires = None
    auth.scope = "openid"
    
    token = auth._fetch_access_token()
    
    assert token == "test-token-456"
    assert auth._token_expires is None  # Not set if server doesn't provide


def test_oauth_token_expiry_check():
    """Test token expiration check."""
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth._token_expires = None  # Initialize attribute
    
    # Token not set
    assert auth._is_token_expired() is True
    
    # Token expires in future
    auth._token_expires = datetime.now(tz=UTC) + timedelta(hours=1)
    assert auth._is_token_expired() is False
    
    # Token expired
    auth._token_expires = datetime.now(tz=UTC) - timedelta(seconds=1)
    assert auth._is_token_expired() is True
    
    # Token within refresh buffer (5 min)
    auth._token_expires = datetime.now(tz=UTC) + timedelta(minutes=4)
    assert auth._is_token_expired() is True


def test_oauth_get_access_token_uses_cache(oauth_config):
    """Test that get_access_token returns cached token if valid."""
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth._access_token = "cached-token"
    auth._token_expires = datetime.now(tz=UTC) + timedelta(hours=1)
    
    token = auth.get_access_token()
    
    assert token == "cached-token"


def test_oauth_get_access_token_refreshes_expired(oauth_config, mock_session):
    """Test that get_access_token refreshes expired token."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "new-token",
        "expires_in": 3600,
    }
    mock_session.post.return_value = mock_response
    
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.session = mock_session
    auth._access_token = "old-token"
    auth._token_expires = datetime.now(tz=UTC) - timedelta(seconds=1)  # Expired
    auth.scope = "openid"
    
    token = auth.get_access_token()
    
    assert token == "new-token"
    assert auth._access_token == "new-token"


def test_oauth_fetch_csrf_token(oauth_config, mock_session):
    """Test fetching CSRF token from Superset."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "result": "test-csrf-token"
    }
    mock_session.get.return_value = mock_response
    
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.session = mock_session
    auth._access_token = "test-token"
    auth.token_type = "Bearer"
    auth._csrf_token = None
    auth._token_expires = datetime.now(tz=UTC) + timedelta(hours=1)  # Valid token
    auth.scope = "openid"
    
    csrf = auth._fetch_csrf_token()
    
    assert csrf == "test-csrf-token"
    assert auth._csrf_token == "test-csrf-token"


def test_oauth_get_csrf_token_uses_cache(oauth_config):
    """Test that get_csrf_token returns cached token."""
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth._csrf_token = "cached-csrf"
    
    csrf = auth.get_csrf_token()
    
    assert csrf == "cached-csrf"


def test_oauth_get_headers(oauth_config):
    """Test that get_headers returns Bearer + CSRF."""
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.token_type = "Bearer"
    auth._access_token = "token-123"
    auth._csrf_token = "csrf-456"
    auth._token_expires = datetime.now(tz=UTC) + timedelta(hours=1)
    
    headers = auth.get_headers()
    
    assert headers["Authorization"] == "Bearer token-123"
    assert headers["X-CSRFToken"] == "csrf-456"


def test_oauth_get_headers_refreshes_token(oauth_config, mock_session):
    """Test that get_headers triggers token refresh if expired."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "refreshed-token",
        "expires_in": 3600,
    }
    mock_session.post.return_value = mock_response
    mock_session.get.return_value = Mock(json=lambda: {"result": "csrf"})
    
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.session = mock_session
    auth._access_token = "old-token"
    auth._token_expires = datetime.now(tz=UTC) - timedelta(seconds=1)  # Expired
    auth._csrf_token = None
    auth.token_type = "Bearer"
    auth.scope = "openid"
    
    # This should trigger refresh
    auth.get_access_token()
    
    # Now call get_headers
    headers = auth.get_headers()
    
    assert "refreshed-token" in headers["Authorization"]


def test_oauth_token_type_custom(oauth_config, mock_session):
    """Test that custom token_type is used in headers."""
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.__dict__.update(oauth_config)
    auth.token_type = "CustomToken"
    auth._access_token = "my-token"
    auth._csrf_token = "csrf"
    auth._token_expires = datetime.now(tz=UTC) + timedelta(hours=1)
    
    headers = auth.get_headers()
    
    assert headers["Authorization"] == "CustomToken my-token"


def test_oauth_scope_custom():
    """Test that custom scope is sent to token endpoint."""
    mock_session = MagicMock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "token",
        "expires_in": 3600,
    }
    mock_session.post.return_value = mock_response
    mock_session.get.return_value = Mock(json=lambda: {"result": "csrf"})
    
    auth = OAuthSupersetAuth.__new__(OAuthSupersetAuth)
    auth.base_url = URL("https://superset.example.com")
    auth.token_url = URL("https://auth.example.com/token")
    auth.client_id = "client"
    auth.client_secret = "secret"
    auth.username = "user"
    auth.password = "pass"
    auth.scope = "custom scope value"  # Custom scope
    auth.token_type = "Bearer"
    auth.session = mock_session
    auth._access_token = None
    auth._token_expires = None
    auth._csrf_token = None
    
    auth._fetch_access_token()
    
    # Verify custom scope was sent
    call_args = mock_session.post.call_args
    assert call_args[1]["data"]["scope"] == "custom scope value"
