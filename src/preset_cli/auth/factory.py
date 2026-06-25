"""
Factory for creating appropriate authentication handlers.

Encapsulates the logic for instantiating the correct auth class
based on configuration, handling validation and providing helpful
error messages.
"""

from yarl import URL

from preset_cli.auth.main import Auth
from preset_cli.auth.oauth_interactive import InteractiveOAuthAuth
from preset_cli.auth.oauth_superset import OAuthSupersetAuth
from preset_cli.auth.superset import SupersetJWTAuth, UsernamePasswordAuth
from sup.config.settings import SupersetInstanceConfig


def _missing_oauth_fields(required: dict) -> list:
    """Return the names of required OAuth2 fields that are unset."""
    return [name for name, value in required.items() if not value]


def create_superset_auth(
    config: SupersetInstanceConfig,
) -> Auth:
    """
    Create appropriate Superset authentication handler based on configuration.

    Validates configuration completeness and instantiates the correct auth
    class (UsernamePasswordAuth, SupersetJWTAuth, or OAuthSupersetAuth).

    Args:
        config: Superset instance configuration object

    Returns:
        Configured authentication instance ready to use with SupersetClient

    Raises:
        ValueError: If configuration is incomplete or auth_method is unknown

    Example:
        >>> config = SupersetInstanceConfig(
        ...     url="https://superset.example.com",
        ...     auth_method="oauth",
        ...     oauth_token_url="https://auth.example.com/oauth2/token",
        ...     oauth_client_id="superset-cli",
        ...     oauth_client_secret="secret123",
        ...     oauth_username="service-account@example.com",
        ...     oauth_password="password123",
        ... )
        >>> auth = create_superset_auth(config)
        >>> # Use with SupersetClient
        >>> from preset_cli.api.clients.superset import SupersetClient
        >>> client = SupersetClient(URL(config.url), auth)
    """
    base_url = URL(config.url)

    if config.auth_method == "username_password":
        if not config.username or not config.password:
            raise ValueError(
                "Username/password authentication requires both 'username' "
                "and 'password' fields in configuration",
            )
        return UsernamePasswordAuth(base_url, config.username, config.password)

    elif config.auth_method == "jwt":
        if not config.jwt_token:
            raise ValueError(
                "JWT authentication requires 'jwt_token' field in configuration",
            )
        return SupersetJWTAuth(config.jwt_token, base_url)

    elif config.auth_method == "oauth":
        # An authorization URL selects the interactive browser (PKCE) flow, which
        # needs no client secret or service credentials. Otherwise fall back to the
        # non-interactive resource-owner password grant, which requires the full
        # set of credentials. Each path reports exactly which fields are missing.
        if config.oauth_authorization_url:
            missing = _missing_oauth_fields({"token_url": config.oauth_token_url})
            if missing:
                raise ValueError(
                    "Interactive OAuth2 authentication is missing required "
                    f"configuration. Missing: {', '.join(missing)}"
                )
            return InteractiveOAuthAuth(
                base_url=base_url,
                authorization_url=URL(config.oauth_authorization_url),
                token_url=URL(config.oauth_token_url),
                client_id=config.oauth_client_id or "superset-cli",
                scope=config.oauth_scope,
                token_type=config.oauth_token_type,
            )

        missing = _missing_oauth_fields(
            {
                "token_url": config.oauth_token_url,
                "client_id": config.oauth_client_id,
                "client_secret": config.oauth_client_secret,
                "username": config.oauth_username,
                "password": config.oauth_password,
            },
        )
        if missing:
            raise ValueError(
                "OAuth2 authentication is missing required configuration. "
                f"Missing: {', '.join(missing)}. Provide oauth_authorization_url "
                "instead to use the interactive browser flow."
            )

        # Validated present above; narrow Optional[str] -> str for the constructor.
        assert config.oauth_client_id is not None  # nosec B101
        assert config.oauth_client_secret is not None  # nosec B101
        return OAuthSupersetAuth(
            base_url=base_url,
            token_url=URL(config.oauth_token_url),
            client_id=config.oauth_client_id,
            client_secret=config.oauth_client_secret,
            username=config.oauth_username,
            password=config.oauth_password,
            scope=config.oauth_scope,
            token_type=config.oauth_token_type,
        )

    else:
        raise ValueError(
            f"Unknown authentication method: '{config.auth_method}'. "
            f"Must be one of: username_password, jwt, oauth",
        )
