Authentication
==============

sup supports multiple authentication methods for Preset and self-hosted Superset instances.

Preset Workspaces
-----------------

API Token (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~

Use API token and secret from Preset workspace settings:

.. code-block:: bash

   export SUP_PRESET_API_TOKEN="your-token"
   export SUP_PRESET_API_SECRET="your-secret"

Or configure in ``~/.sup/config.yml``:

.. code-block:: yaml

   preset:
     api_token: ${ENV:PRESET_API_TOKEN}
     api_secret: ${ENV:PRESET_API_SECRET}

Self-Hosted Superset
--------------------

Configure instances in ``~/.sup/config.yml`` under ``superset_instances``.

Interactive OAuth (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For interactive use with zero configuration - browser-based authentication with PKCE:

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_authorization_url: https://auth.example.com/oauth2/authorize
       oauth_token_url: https://auth.example.com/oauth2/token
       oauth_client_id: superset-cli
       oauth_scope: "openid profile email"

**No secrets needed!** Tokens are cached in ``~/.sup/tokens/`` after first authentication.

First run:

.. code-block:: bash

   $ sup dataset list
   🔐 Opening browser for authentication...
   ⏳ Waiting for you to complete authentication in browser...
   ✓ Authentication successful!
   [Shows datasets]

Subsequent runs use cached tokens:

.. code-block:: bash

   $ sup chart list
   [Uses cached token - instant, no browser!]

Token features:

- **Zero configuration**: No secrets to manage
- **Automatic refresh**: Tokens refreshed automatically when expired
- **Secure storage**: Cached with 0600 permissions in ``~/.sup/tokens/``
- **Per-instance**: Separate cache for each Superset instance
- **PKCE flow**: Industry-standard secure authentication without client secrets

OAuth2 with Service Account
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For automation, CI/CD, and service accounts (requires client secret):

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://auth.example.com/oauth2/token
       oauth_client_id: superset-service
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}
       oauth_scope: "openid profile email"

Set environment variables:

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="your-client-secret"
   export SUPERSET_SERVICE_PASSWORD="your-service-password"

Benefits:

- Centralized identity management
- Automatic token refresh with 5-minute safety buffer
- No passwords in config files
- Works with service accounts

Username/Password
~~~~~~~~~~~~~~~~~

For instances with built-in Superset authentication:

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: username_password
       username: superset-service
       password: ${ENV:SUPERSET_PASSWORD}

JWT Token
~~~~~~~~~

For pre-generated JWT tokens:

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: jwt
       jwt_token: ${ENV:SUPERSET_JWT_TOKEN}

Security Best Practices
-----------------------

1. **Use environment variables for secrets**

   .. code-block:: yaml

      oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
      password: ${ENV:SUPERSET_PASSWORD}

2. **Protect config files**

   .. code-block:: bash

      chmod 600 ~/.sup/config.yml

3. **Create dedicated service accounts** (not personal user accounts)

   - Limit permissions to required scope
   - Use strong, unique passwords

4. **Never commit secrets to git**

   - Add ``.env`` files to ``.gitignore``
   - Use secrets management in CI/CD

5. **Rotate credentials regularly**

   - Change client secrets in OIDC provider
   - Update passwords periodically

Provider-Specific Setup
-----------------------

See :doc:`self_hosted_setup` for step-by-step instructions for:

- Keycloak
- Okta
- Auth0
- Azure AD
- Amazon Cognito

Includes configuration examples, troubleshooting, and detailed security guidance.
