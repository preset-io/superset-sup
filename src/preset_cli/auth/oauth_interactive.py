"""
Interactive OAuth2 authorization code flow with PKCE for Superset.

This module implements the OAuth2 authorization code flow with PKCE
(Proof Key for Code Exchange) for interactive browser-based authentication.
Similar to tools like `gh auth login` or `aws sso login`.

When no credentials are provided, this flow:
1. Generates a PKCE code verifier and challenge
2. Starts a local HTTP server to receive the callback
3. Opens the user's browser to the authorization URL
4. Receives the authorization code via callback
5. Exchanges the code for access and refresh tokens
6. Stores tokens securely for future use

Example:
    >>> from yarl import URL
    >>> from preset_cli.auth.oauth_interactive import InteractiveOAuthAuth
    >>> from preset_cli.api.clients.superset import SupersetClient
    >>>
    >>> auth = InteractiveOAuthAuth(
    ...     base_url=URL("https://superset.example.com"),
    ...     authorization_url=URL("https://auth.example.com/authorize"),
    ...     token_url=URL("https://auth.example.com/token"),
    ...     client_id="superset-cli",
    ... )
    >>> # Browser opens automatically, user logs in
    >>> client = SupersetClient(URL("https://superset.example.com"), auth)
"""

import base64
import hashlib
import json
import logging
import secrets
import webbrowser
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse

from yarl import URL

from preset_cli.auth.main import Auth

_logger = logging.getLogger(__name__)


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    authorization_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):  # noqa: N802
        """Handle GET request with authorization code."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            CallbackHandler.authorization_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
                <html>
                <head><title>Authentication Successful</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: green;">&#10003; Authentication Successful</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
                """
            self.wfile.write(html.encode('utf-8'))
        elif "error" in params:
            CallbackHandler.error = params["error"][0]
            error_desc = params.get("error_description", ["Unknown error"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""
                <html>
                <head><title>Authentication Failed</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: red;">&#10007; Authentication Failed</h1>
                    <p>{error_desc}</p>
                    <p>Please return to the terminal and try again.</p>
                </body>
                </html>
                """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Invalid callback - missing code or error parameter")

    def log_message(self, format, *args):  # noqa: ARG002
        """Suppress default HTTP server logging."""
        pass


class InteractiveOAuthAuth(Auth):
    """
    Interactive OAuth2 authorization code flow with PKCE for Superset.

    Implements browser-based authentication flow similar to modern CLI tools.
    Uses PKCE for security without requiring a client secret.

    Attributes:
        base_url: Base URL of the Superset instance
        authorization_url: OAuth2 authorization endpoint URL
        token_url: OAuth2 token endpoint URL
        client_id: OAuth2 client ID
        client_secret: Optional OAuth2 client secret (for confidential clients)
        scope: OAuth2 scopes to request
        redirect_port: Local port for callback server (default: 8080)
    """

    def __init__(
        self,
        base_url: URL,
        authorization_url: URL,
        token_url: URL,
        client_id: str,
        client_secret: Optional[str] = None,
        scope: str = "openid profile email",
        redirect_port: int = 8080,
        token_type: str = "Bearer",
    ):
        """
        Initialize interactive OAuth2 authentication.

        Args:
            base_url: Base URL of Superset instance
            authorization_url: OAuth2 authorization endpoint URL
            token_url: OAuth2 token endpoint URL
            client_id: OAuth2 client ID
            client_secret: Optional client secret (for confidential clients)
            scope: OAuth2 scopes to request
            redirect_port: Local port for callback (default: 8080)
            token_type: Token type for Authorization header (default: Bearer)
        """
        super().__init__()

        self.base_url = URL(base_url) if isinstance(base_url, str) else base_url
        self.authorization_url = (
            URL(authorization_url)
            if isinstance(authorization_url, str)
            else authorization_url
        )
        self.token_url = URL(token_url) if isinstance(token_url, str) else token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.redirect_port = redirect_port
        self.redirect_uri = f"http://localhost:{redirect_port}/callback"
        self.token_type = token_type
        
        # Token cache file path - store per base_url to support multiple instances
        self._token_cache_dir = Path.home() / ".sup" / "tokens"
        self._token_cache_dir.mkdir(parents=True, exist_ok=True)
        # Use base URL hostname as filename to separate different Superset instances
        cache_filename = base_url.host.replace(":", "_") + ".json"
        self._token_cache_file = self._token_cache_dir / cache_filename

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._csrf_token: Optional[str] = None

        # Try to load cached tokens first
        if not self._load_cached_tokens():
            # No cached tokens, start interactive flow
            self.auth()

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate cryptographically random code verifier
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(
            "utf-8"
        )
        code_verifier = code_verifier.rstrip("=")

        # Create SHA256 hash of verifier
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8")
        code_challenge = code_challenge.rstrip("=")

        return code_verifier, code_challenge

    def _start_callback_server(self) -> HTTPServer:
        """
        Start local HTTP server to receive OAuth callback.

        Returns:
            Running HTTP server instance
        """
        server = HTTPServer(("localhost", self.redirect_port), CallbackHandler)
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()
        return server

    def _perform_interactive_flow(self) -> tuple[str, Optional[str]]:
        """
        Perform interactive browser-based OAuth flow.

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            RuntimeError: If authentication fails or user cancels
        """
        # Reset callback handler state before starting new flow
        CallbackHandler.authorization_code = None
        CallbackHandler.error = None
        
        # Generate PKCE parameters
        code_verifier, code_challenge = self._generate_pkce_pair()

        # Start local callback server
        _logger.info("Starting local callback server on port %d", self.redirect_port)
        server = self._start_callback_server()

        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self.authorization_url}?{urlencode(auth_params)}"

        # Open browser
        _logger.info("Opening browser for authentication...")
        print("\n🔐 Opening browser for authentication...")
        print(f"If browser doesn't open, visit: {auth_url}\n")

        if not webbrowser.open(auth_url):
            _logger.warning("Failed to open browser automatically")
            print(f"⚠️  Please manually open: {auth_url}")

        # Wait for callback (with timeout)
        _logger.info("Waiting for authentication callback...")
        print("⏳ Waiting for you to complete authentication in browser...")

        # Wait for callback handler to receive code
        import time

        timeout = 120  # 2 minutes
        start_time = time.time()
        while (
            CallbackHandler.authorization_code is None
            and CallbackHandler.error is None
            and (time.time() - start_time) < timeout
        ):
            time.sleep(0.5)

        server.server_close()

        if CallbackHandler.error:
            raise RuntimeError(
                f"Authentication failed: {CallbackHandler.error}. "
                "Please try again."
            )

        if CallbackHandler.authorization_code is None:
            raise RuntimeError(
                "Authentication timeout. No response received within 2 minutes."
            )

        auth_code = CallbackHandler.authorization_code
        CallbackHandler.authorization_code = None  # Reset for next use
        CallbackHandler.error = None  # Reset error state

        _logger.info("Received authorization code, exchanging for tokens...")
        print("✓ Authentication successful! Exchanging code for tokens...\n")

        # Exchange code for tokens
        token_payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        if self.client_secret:
            token_payload["client_secret"] = self.client_secret

        response = self.session.post(self.token_url, data=token_payload)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        # Calculate token expiration
        if "expires_in" in token_data:
            expires_in = int(token_data["expires_in"])
            self._token_expires = datetime.now(tz=UTC) + timedelta(seconds=expires_in)

        return access_token, refresh_token

    def _load_cached_tokens(self) -> bool:
        """
        Load cached tokens from disk if available.

        Returns:
            True if valid cached tokens were loaded, False otherwise
        """
        if not self._token_cache_file.exists():
            _logger.debug("No cached tokens found at %s", self._token_cache_file)
            return False
        
        try:
            with open(self._token_cache_file) as f:
                cache_data = json.load(f)
            
            # Validate cache structure
            if not all(key in cache_data for key in ["access_token", "refresh_token", "expires_at"]):
                _logger.warning("Invalid token cache structure, ignoring")
                return False
            
            # Parse expiration time
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            
            # Check if we have a valid access token or can refresh
            if datetime.now(tz=UTC) < expires_at:
                # Access token is still valid
                _logger.info("Loaded valid access token from cache")
                self._access_token = cache_data["access_token"]
                self._refresh_token = cache_data["refresh_token"]
                self._token_expires = expires_at
                return True
            elif cache_data.get("refresh_token"):
                # Access token expired but we have refresh token
                _logger.info("Access token expired, will attempt refresh")
                self._refresh_token = cache_data["refresh_token"]
                return False  # Return False to trigger refresh
            else:
                _logger.info("Cached tokens expired and no refresh token available")
                return False
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            _logger.warning("Failed to load cached tokens: %s", e)
            return False

    def _cache_tokens(self):
        """Save tokens to disk for future use."""
        if not self._access_token:
            _logger.warning("No access token to cache")
            return
        
        try:
            cache_data = {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._token_expires.isoformat() if self._token_expires else None,
                "cached_at": datetime.now(tz=UTC).isoformat(),
            }
            
            # Write atomically by writing to temp file then renaming
            temp_file = self._token_cache_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            
            # Set restrictive permissions (readable only by owner)
            temp_file.chmod(0o600)
            
            # Atomic rename
            temp_file.rename(self._token_cache_file)
            
            _logger.info("Cached tokens to %s", self._token_cache_file)
            
        except Exception as e:
            _logger.warning("Failed to cache tokens: %s", e)

    def _is_token_expired(self) -> bool:
        """Check if access token has expired."""
        if self._token_expires is None:
            return True

        # Refresh 5 minutes before expiry
        buffer = timedelta(minutes=5)
        return datetime.now(tz=UTC) >= (self._token_expires - buffer)

    def _fetch_access_token(self) -> str:
        """
        Fetch access token via interactive OAuth flow or refresh.

        Returns:
            Access token string

        Raises:
            RuntimeError: If authentication fails
        """
        # First, try to load cached tokens
        if self._load_cached_tokens():
            _logger.info("Using cached access token")
            return self._access_token
        
        # If we have a refresh token (from cache or previous auth), try to refresh
        if self._refresh_token:
            try:
                _logger.info("Refreshing access token...")
                new_token = self._refresh_access_token()
                self._cache_tokens()  # Cache the refreshed tokens
                return new_token
            except Exception as e:
                _logger.warning("Token refresh failed: %s", e)
                # Fall through to interactive flow

        # No valid cached token and refresh failed (or no refresh token)
        # Perform interactive flow
        _logger.info("Starting interactive OAuth flow...")
        access_token, refresh_token = self._perform_interactive_flow()

        self._access_token = access_token
        self._refresh_token = refresh_token
        self._cache_tokens()

        return access_token

    def _refresh_access_token(self) -> str:
        """
        Refresh access token using refresh token.

        Returns:
            New access token

        Raises:
            requests.HTTPError: If refresh fails
        """
        if not self._refresh_token:
            raise RuntimeError("No refresh token available")

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": self._refresh_token,
        }

        if self.client_secret:
            payload["client_secret"] = self.client_secret

        response = self.session.post(self.token_url, data=payload)
        response.raise_for_status()

        token_data = response.json()
        self._access_token = token_data["access_token"]

        if "refresh_token" in token_data:
            self._refresh_token = token_data["refresh_token"]

        if "expires_in" in token_data:
            expires_in = int(token_data["expires_in"])
            self._token_expires = datetime.now(tz=UTC) + timedelta(seconds=expires_in)

        self._cache_tokens()

        return self._access_token

    def auth(self) -> None:
        """
        Perform authentication, fetching tokens.
        
        This method is called by the base Auth class for initial auth
        and reauthorization on 401 responses.
        """
        self._fetch_access_token()
        self.session.headers.update(self.get_headers())

    def get_token(self) -> str:
        """
        Get valid access token.

        Handles token refresh and expiration automatically.

        Returns:
            Valid access token
        """
        if self._access_token and not self._is_token_expired():
            return self._access_token

        return self._fetch_access_token()

    def get_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for requests.

        Returns:
            Dictionary with Authorization header
        """
        token = self.get_token()
        return {
            "Authorization": f"{self.token_type} {token}",
        }
    
    def clear_cached_tokens(self):
        """Clear cached tokens from disk (for logout)."""
        try:
            if self._token_cache_file.exists():
                self._token_cache_file.unlink()
                _logger.info("Cleared cached tokens from %s", self._token_cache_file)
        except Exception as e:
            _logger.warning("Failed to clear cached tokens: %s", e)
        
        # Clear in-memory tokens
        self._access_token = None
        self._refresh_token = None
        self._token_expires = None

    def add_auth(self, request):
        """Add authentication to request."""
        request.headers.update(self.get_headers())
        return request
