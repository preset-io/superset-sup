Authentication Cheatsheet
=========================

Quick reference for configuring sup with different authentication methods.

Configuration File Location
----------------------------

.. code-block:: text

   ~/.sup/config.yml

Set file permissions:

.. code-block:: bash

   chmod 600 ~/.sup/config.yml

Quick Setup Templates
---------------------

OAuth2/OIDC (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   superset_instances:
     my-instance:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://auth.example.com/oauth2/token
       oauth_client_id: your-client-id
       oauth_client_secret: ${ENV:OAUTH_SECRET}
       oauth_username: service-account
       oauth_password: ${ENV:SERVICE_PASSWORD}

.. code-block:: bash

   export OAUTH_SECRET="your-client-secret"
   export SERVICE_PASSWORD="your-service-password"
   sup dataset list

Username/Password
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   superset_instances:
     my-instance:
       url: https://superset.example.com
       auth_method: username_password
       username: admin
       password: ${ENV:SUPERSET_PASSWORD}

.. code-block:: bash

   export SUPERSET_PASSWORD="your-password"
   sup dataset list

JWT Token
~~~~~~~~~

.. code-block:: yaml

   superset_instances:
     my-instance:
       url: https://superset.example.com
       auth_method: jwt
       jwt_token: ${ENV:JWT_TOKEN}

.. code-block:: bash

   export JWT_TOKEN="eyJhbGc..."
   sup dataset list

Preset (Default)
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Set environment variables
   export SUP_PRESET_API_TOKEN="your-token"
   export SUP_PRESET_API_SECRET="your-secret"

   # Then use sup normally
   sup workspace list
   sup dataset list

Provider-Specific Token URLs
----------------------------

Keycloak
~~~~~~~~

.. code-block:: text

   https://keycloak.example.com/auth/realms/{realm}/protocol/openid-connect/token

Okta
~~~~

.. code-block:: text

   https://{org}.okta.com/oauth2/v1/token

Auth0
~~~~~

.. code-block:: text

   https://{domain}.auth0.com/oauth/token

Azure AD
~~~~~~~~

.. code-block:: text

   https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token

Amazon Cognito
~~~~~~~~~~~~~~

.. code-block:: text

   https://{domain}.auth.{region}.amazoncognito.com/oauth2/token

Dex
~~~

.. code-block:: text

   https://dex.example.com/dex/token

Common Scopes
-------------

.. code-block:: yaml

   # Minimal (works with most providers)
   oauth_scope: "openid profile email"

   # With roles (for RBAC)
   oauth_scope: "openid profile email roles"

   # Custom provider scopes
   oauth_scope: "openid profile email groups"

Testing Configuration
---------------------

Test if configuration is valid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup config show

Test if authentication works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup dataset list

Test with JSON output (for debugging)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup dataset list --json

Test SQL execution
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup sql "SELECT 1"

Troubleshooting Quick Fixes
---------------------------

| "Invalid client credentials"
| → Check ``oauth_client_id`` and ``oauth_client_secret``

| "Invalid username or password"
| → Check service account exists and password is correct

| "Token endpoint unreachable"
| → Check token URL is correct: ``curl https://your-token-url``

| "401 Unauthorized on CSRF token"
| → Check service account has Superset access

| "scopes insufficient"
| → Add more scopes: ``oauth_scope: "openid profile email roles"``

Environment Variables
---------------------

All sensitive values should use environment variables:

.. code-block:: bash

   # OAuth2
   export SUPERSET_OAUTH_SECRET="..."      # oauth_client_secret
   export SUPERSET_SERVICE_PASSWORD="..."  # oauth_password

   # Basic Auth
   export SUPERSET_PASSWORD="..."          # password

   # JWT
   export SUPERSET_JWT_TOKEN="..."         # jwt_token

   # Preset
   export SUP_PRESET_API_TOKEN="..."
   export SUP_PRESET_API_SECRET="..."

Never commit secrets to git!

Multiple Instances
-------------------

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset-prod.com
       auth_method: oauth
       oauth_token_url: https://auth.com/token
       oauth_client_id: prod-client
       oauth_client_secret: ${ENV:PROD_SECRET}
       oauth_username: prod-service
       oauth_password: ${ENV:PROD_PASSWORD}

     staging:
       url: https://superset-staging.com
       auth_method: oauth
       oauth_token_url: https://auth-staging.com/token
       oauth_client_id: staging-client
       oauth_client_secret: ${ENV:STAGING_SECRET}
       oauth_username: staging-service
       oauth_password: ${ENV:STAGING_PASSWORD}

     local:
       url: http://localhost:8088
       auth_method: username_password
       username: admin
       password: ${ENV:LOCAL_PASSWORD}

Switch between instances:

.. code-block:: bash

   sup workspace use 123 --instance production
   sup workspace use 456 --instance staging

Security Checklist
------------------

- [ ] Config file permissions: ``chmod 600 ~/.sup/config.yml``
- [ ] Secrets in environment variables, not config file
- [ ] ``.env`` files added to ``.gitignore``
- [ ] Using service account, not personal credentials
- [ ] OAuth2 enabled with strong client secret
- [ ] Credentials rotated regularly
- [ ] Access logs reviewed periodically

Common Commands
---------------

Configuration
~~~~~~~~~~~~~

.. code-block:: bash

   sup config show              # View current config
   sup config auth              # Interactive auth setup

Testing
~~~~~~~

.. code-block:: bash

   sup dataset list             # Test connection
   sup sql "SELECT 1"          # Test database access
   sup database list           # List available databases

Work with instances
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup workspace list          # List Preset workspaces (if using Preset)
   sup workspace use 123       # Set active workspace

Assets
~~~~~~

.. code-block:: bash

   sup dataset list            # List datasets
   sup chart list              # List charts
   sup dashboard list          # List dashboards
   sup chart pull --mine       # Pull your charts
   sup chart push              # Push to target workspace

Documentation Links
-------------------

- **Full Setup Guide:** :doc:`self_hosted_setup`
- **Authentication Guide:** :doc:`authentication`
- **Main Documentation:** `README <../README.md>`_

Getting Help
------------

- **Issues:** https://github.com/preset-io/superset-sup/issues
- **Discussions:** https://github.com/preset-io/superset-sup/discussions

Found a mistake? Help us improve by submitting a PR!
