"""
OAuth2/OIDC authentication for self-hosted Superset instances.

This module provides authentication for Superset instances that delegate auth
to external OIDC providers. It implements the OAuth2 resource owner password
grant flow for service account authentication.

Example:
    >>> from yarl import URL
    >>> from preset_cli.auth.oauth_superset import OAuthSupersetAuth
    >>> from preset_cli.api.clients.superset import SupersetClient
    >>>
    >>> auth = OAuthSupersetAuth(
    ...     base_url=URL("https://superset.example.com"),
    ...     token_url=URL("https://auth.example.com/oauth2/token"),
    ...     client_id="superset-cli",
    ...     client_secret="secret123",
    ...     username="service-account@example.com",
    ...     password="account-password",
    ... )
    >>> client = SupersetClient(URL("https://superset.example.com"), auth)
    >>> datasets = client.get_datasets()
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from yarl import URL

from preset_cli.auth.main import Auth

_logger = logging.getLogger(__name__)


class OAuthSupersetAuth(Auth):  # pylint: disable=too-few-public-methods
    """
    OAuth2 authentication for Superset instances with external OIDC providers.

    Uses the OAuth2 resource owner password grant flow for service account
    authentication. Automatically refreshes access tokens based on expiration
    time returned by the token endpoint.

    Attributes:
        base_url: Base URL of the Superset instance
        token_url: OAuth2 token endpoint URL
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        username: Service account username
        password: Service account password
        scope: OAuth2 scopes to request (default: OpenID Connect standard scopes)
        token_type: Token type in Authorization header (default: Bearer)
    """

    def __init__(
        self,
        base_url: URL,
        token_url: URL,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        scope: str = "openid profile email roles",
        token_type: str = "Bearer",
    ):
        """
        Initialize OAuth2 authentication for Superset.

        Args:
            base_url: Base URL of Superset instance
                (e.g., https://superset.example.com)
            token_url: OAuth2 token endpoint URL
                (e.g., https://auth.example.com/oauth2/token)
            client_id: OAuth2 client ID registered with OIDC provider
            client_secret: OAuth2 client secret for client authentication
            username: Service account username (not a regular user email)
            password: Service account password
            scope: OAuth2 scopes to request. Default includes standard OIDC scopes
                for profile information and roles. Can be customized per provider.
            token_type: Authorization header token type. Default "Bearer" works
                with standard Superset OIDC configuration.

        Raises:
            requests.HTTPError: If initial token fetch fails
        """
        super().__init__()

        self.base_url = URL(base_url) if isinstance(base_url, str) else base_url
        self.token_url = URL(token_url) if isinstance(token_url, str) else token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.scope = scope
        self.token_type = token_type

        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._csrf_token: Optional[str] = None

        # Fetch initial tokens
        self.auth()

    def _is_token_expired(self) -> bool:
        """
        Check if the access token has expired.

        Includes a 5-minute buffer to account for network latency and
        server time skew. This ensures the token is refreshed before
        it actually becomes invalid.

        Returns:
            True if token has expired or is about to expire, False otherwise.
        """
        if self._token_expires is None:
            return True

        # Refresh 5 minutes before actual expiry for safety
        buffer = timedelta(minutes=5)
        return datetime.now(tz=UTC) >= (self._token_expires - buffer)

    def _fetch_access_token(self) -> str:
        """
        Fetch a new access token from the OAuth2 token endpoint.

        Implements the OAuth2 resource owner password grant flow:
        https://tools.ietf.org/html/rfc6749#section-4.3

        Sends the client credentials (client_id, client_secret) and
        user credentials (username, password) to the token endpoint
        and retrieves an access token.

        Returns:
            Access token string

        Raises:
            requests.HTTPError: If token endpoint returns an error
            KeyError: If response is missing required 'access_token' field
        """
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "scope": self.scope,
        }

        _logger.debug(
            "Fetching access token from %s for user %s",
            self.token_url,
            self.username,
        )

        response = self.session.post(self.token_url, data=payload)
        response.raise_for_status()

        token_data = response.json()
        self._access_token = token_data["access_token"]

        # Track token expiration time if the server provides it
        if "expires_in" in token_data:
            expires_in = token_data["expires_in"]
            self._token_expires = datetime.now(tz=UTC) + timedelta(
                seconds=expires_in,
            )
            _logger.debug(
                "Access token will expire in %d seconds (%s)",
                expires_in,
                self._token_expires,
            )

        return self._access_token

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Checks if the current token has expired. If it has, fetches
        a new token from the token endpoint. Otherwise returns the
        cached token.

        Returns:
            Current or refreshed access token string
        """
        if self._access_token is None or self._is_token_expired():
            _logger.debug("Access token expired or not set, refreshing...")
            return self._fetch_access_token()
        return self._access_token

    def _fetch_csrf_token(self) -> str:
        """
        Fetch a CSRF token from the Superset security endpoint.

        The Superset API requires CSRF tokens for state-changing
        operations (POST, PUT, DELETE). Fetches the token by making
        an authenticated GET request to the CSRF endpoint with the
        Bearer token.

        Returns:
            CSRF token string

        Raises:
            requests.HTTPError: If CSRF endpoint returns an error
            KeyError: If response is missing 'result' field
        """
        headers = {
            "Authorization": f"{self.token_type} {self.get_access_token()}",
        }

        _logger.debug("Fetching CSRF token from Superset")

        response = self.session.get(
            self.base_url / "api/v1/security/csrf_token/",
            headers=headers,
        )
        response.raise_for_status()

        self._csrf_token = response.json().get("result")
        _logger.debug("Successfully fetched CSRF token")

        return self._csrf_token

    def get_csrf_token(self) -> str:
        """
        Get CSRF token, fetching if needed.

        CSRF tokens are stateless and can be reused across requests,
        but we refetch if the access token is refreshed to maintain
        consistency.

        Returns:
            CSRF token string
        """
        if self._csrf_token is None:
            return self._fetch_csrf_token()
        return self._csrf_token

    def get_headers(self) -> Dict[str, str]:
        """
        Return authentication headers for Superset API requests.

        Includes:
        - Authorization: Bearer token (auto-refreshed if expired)
        - X-CSRFToken: CSRF token for state-changing operations

        These headers should be added to all API requests made through
        the authenticated session.

        Returns:
            Dictionary of HTTP headers to include in requests
        """
        return {
            "Authorization": f"{self.token_type} {self.get_access_token()}",
            "X-CSRFToken": self.get_csrf_token(),
        }

    def auth(self) -> None:
        """
        Initialize authentication by fetching tokens.

        Called automatically on object creation and on 401 responses
        from the Superset API (via the reauth hook in the base Auth class).

        Fetches both the access token and CSRF token. These are cached
        and reused until expiration.

        Raises:
            requests.HTTPError: If token endpoint is unreachable
        """
        _logger.debug("Initializing OAuth2 authentication")
        self._fetch_access_token()
        self._fetch_csrf_token()
