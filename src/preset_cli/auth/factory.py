"""
Factory for creating appropriate authentication handlers.

Encapsulates the logic for instantiating the correct auth class
based on configuration, handling validation and providing helpful
error messages.
"""

from typing import Union

from yarl import URL

from preset_cli.auth.main import Auth
from preset_cli.auth.oauth_interactive import InteractiveOAuthAuth
from preset_cli.auth.oauth_superset import OAuthSupersetAuth
from preset_cli.auth.superset import SupersetJWTAuth, UsernamePasswordAuth
from sup.config.settings import SupersetInstanceConfig


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
        # Validate required OAuth2 fields
        if not config.oauth_token_url:
            raise ValueError(
                "OAuth2 authentication requires 'oauth_token_url' in configuration"
            )

        base_url = URL(config.url)
        token_url = URL(config.oauth_token_url)

        # If client_id and client_secret are provided, use them
        # Otherwise, use interactive flow (will require manual setup)
        if config.oauth_client_id and config.oauth_client_secret:
            # Check if username/password are provided for password grant
            if config.oauth_username and config.oauth_password:
                # Use resource owner password credentials grant
                return OAuthSupersetAuth(
                    base_url=base_url,
                    token_url=token_url,
                    client_id=config.oauth_client_id,
                    client_secret=config.oauth_client_secret,
                    username=config.oauth_username,
                    password=config.oauth_password,
                    scope=config.oauth_scope,
                    token_type=config.oauth_token_type,
                )
            else:
                # Use client credentials grant
                return OAuthSupersetAuth(
                    base_url=base_url,
                    token_url=token_url,
                    client_id=config.oauth_client_id,
                    client_secret=config.oauth_client_secret,
                    username=None,
                    password=None,
                    scope=config.oauth_scope,
                    token_type=config.oauth_token_type,
                )
        
        # No client credentials provided - use interactive browser flow
        # Requires authorization URL
        if not config.oauth_authorization_url:
            raise ValueError(
                "Interactive OAuth flow requires 'oauth_authorization_url'. "
                "Either provide oauth_client_id + oauth_client_secret for "
                "non-interactive flow, or oauth_authorization_url for interactive flow."
            )

        return InteractiveOAuthAuth(
            base_url=base_url,
            authorization_url=URL(config.oauth_authorization_url),
            token_url=token_url,
            client_id=config.oauth_client_id or "superset-cli",
            scope=config.oauth_scope,
            token_type=config.oauth_token_type,
        )

    else:
        raise ValueError(
            f"Unknown authentication method: '{config.auth_method}'. "
            f"Must be one of: username_password, jwt, oauth",
        )
