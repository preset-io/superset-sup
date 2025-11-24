Self-Hosted Superset Setup Guide
=================================

Complete guide for setting up sup with self-hosted Apache Superset instances.

Quick Start
-----------

Get sup working with your self-hosted Superset instance in 5 minutes:

1. Install sup
~~~~~~~~~~~~~~

.. code-block:: bash

   pip install superset-sup

2. Create Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``~/.sup/config.yml``:

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://auth.example.com/oauth2/token
       oauth_client_id: superset-cli
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}

3. Set Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="your-client-secret"
   export SUPERSET_SERVICE_PASSWORD="your-service-password"

4. Test Connection
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup dataset list

If you see datasets, it's working! ✅

Authentication Methods
----------------------

OAuth2/OIDC (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~

**Best for:** Self-hosted Superset with external identity providers

**Providers Supported:**

- Keycloak
- Okta
- Auth0
- Dex
- Azure AD
- Amazon Cognito
- Any OAuth2 provider supporting password grant

**Configuration:**

.. code-block:: yaml

   auth_method: oauth
   oauth_token_url: https://auth.example.com/oauth2/token
   oauth_client_id: your-client-id
   oauth_client_secret: ${ENV:OAUTH_SECRET}
   oauth_username: service-account
   oauth_password: ${ENV:SERVICE_PASSWORD}
   oauth_scope: "openid profile email roles"
   oauth_token_type: "Bearer"

**Advantages:**

- Centralized identity management
- No password stored in config files
- Automatic token refresh
- Works with service accounts

Username/Password
~~~~~~~~~~~~~~~~~

**Best for:** Simple self-hosted Superset instances without external auth

**Configuration:**

.. code-block:: yaml

   auth_method: username_password
   username: admin
   password: ${ENV:SUPERSET_PASSWORD}

**Advantages:**

- Simple setup
- Works with built-in Superset auth

**Disadvantages:**

- Requires storing credentials
- No integration with external identity providers

JWT Token
~~~~~~~~~

**Best for:** Pre-generated JWT tokens or programmatic access

**Configuration:**

.. code-block:: yaml

   auth_method: jwt
   jwt_token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

**Advantages:**

- Secure token-based auth
- No password storage

**Disadvantages:**

- Requires pre-generated token
- Token must be manually refreshed

OAuth2/OIDC Setup
-----------------

Keycloak
~~~~~~~~

Keycloak is an open-source identity provider. Here's how to configure it:

1. Create Client in Keycloak
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Go to Keycloak Admin Console
2. Select your realm
3. Navigate to **Clients** → **Create**
4. Client ID: ``superset-cli``
5. Client Protocol: ``openid-connect``
6. Save

2. Configure Client
^^^^^^^^^^^^^^^^^^

In client settings:

- **Access Type:** ``confidential``
- **Standard Flow Enabled:** ``OFF``
- **Direct Access Grants Enabled:** ``ON``
- **Service Accounts Enabled:** ``ON``

Click **Save**.

3. Get Client Secret
^^^^^^^^^^^^^^^^^^^^

Go to **Credentials** tab → Copy **Secret**

4. Create Service User
^^^^^^^^^^^^^^^^^^^^^^

1. Navigate to **Users** → **Add User**
2. Username: ``superset-service``
3. Set permanent password

5. Assign Roles (Optional)
^^^^^^^^^^^^^^^^^^^^^^^^^

If Superset checks role claims, assign appropriate roles to the service user.

6. Configure sup
^^^^^^^^^^^^^^^

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://keycloak.example.com/auth/realms/master/protocol/openid-connect/token
       oauth_client_id: superset-cli
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}
       oauth_scope: "openid profile email"

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="<client-secret-from-keycloak>"
   export SUPERSET_SERVICE_PASSWORD="<service-user-password>"

7. Test
^^^^^^

.. code-block:: bash

   sup dataset list

Okta
~~~~

1. Create OAuth App in Okta
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Go to **Applications** → **Create App**
2. Platform: ``Web``
3. Sign on method: ``OAuth 2.0``
4. Create

2. Configure App
^^^^^^^^^^^^^^^

- **Login redirect URIs:** (leave empty for CLI)
- **Grant type:** Enable ``Resource Owner Password``
- **Client Authentication:** ``Client Secret Basic``

Save and note **Client ID** and **Client Secret**.

3. Create Service Account User
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Go to **Users** → **Add User**
2. Username: ``superset-service``
3. First Name: ``Superset``
4. Last Name: ``Service``
5. Email: ``superset-service@example.com``

4. Set Password
^^^^^^^^^^^^^^^

Assign a permanent password to the service user.

5. Configure sup
^^^^^^^^^^^^^^^

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://example.okta.com/oauth2/v1/token
       oauth_client_id: <client-id>
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service@example.com
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}
       oauth_scope: "openid profile email"

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="<client-secret>"
   export SUPERSET_SERVICE_PASSWORD="<user-password>"

6. Test
^^^^^^

.. code-block:: bash

   sup dataset list

Auth0
~~~~~

1. Create Application in Auth0
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Go to **Applications** → **Create Application**
2. Choose **Machine to Machine** (best for service accounts)
3. Name: ``Superset CLI``

2. Configure App
^^^^^^^^^^^^^^^

- Keep defaults (no user interaction needed)
- Go to **Settings** tab
- Note **Client ID** and **Client Secret**

3. Create Service User (Optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Auth0 with Machine-to-Machine typically uses client credentials directly. If you need a user account:

1. Go to **Users** → **Create User**
2. Email: ``superset-service@example.com``
3. Password: Create a strong one

4. Configure sup
^^^^^^^^^^^^^^^

For Machine-to-Machine (recommended):

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://example.auth0.com/oauth/token
       oauth_client_id: <client-id>
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: <client-id>  # Use client ID as username for M2M
       oauth_password: ${ENV:SUPERSET_OAUTH_SECRET}  # Use secret as password
       oauth_scope: "openid profile email"

For User-based authentication:

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://example.auth0.com/oauth/token
       oauth_client_id: <client-id>
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service@example.com
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}
       oauth_scope: "openid profile email"

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="<client-secret>"
   export SUPERSET_SERVICE_PASSWORD="<user-password>"  # If using user-based auth

5. Test
^^^^^^

.. code-block:: bash

   sup dataset list

Azure AD
~~~~~~~~

1. Register Application in Azure AD
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Go to **Azure Portal** → **Azure Active Directory**
2. **App registrations** → **New registration**
3. Name: ``Superset CLI``
4. Supported account types: ``Accounts in this organizational directory only``

2. Configure Permissions
^^^^^^^^^^^^^^^^^^^^^^^^

1. Go to **Certificates & secrets**
2. **New client secret** → Copy value

3. Get Tenant ID and Client ID
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In **Overview**:

- Copy **Directory (tenant) ID**
- Copy **Application (client) ID**

4. Create Service Principal User
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Azure AD doesn't have traditional "service users" like other providers. Instead:

1. Go to **Users** → **New user**
2. User name: ``superset-service``
3. Name: ``Superset Service``
4. Password: Generate permanent password

5. Configure sup
^^^^^^^^^^^^^^^

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token
       oauth_client_id: <client-id>
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service@yourtenant.onmicrosoft.com
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}
       oauth_scope: "openid profile email"

Replace ``{tenant-id}`` with your directory tenant ID.

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="<client-secret>"
   export SUPERSET_SERVICE_PASSWORD="<user-password>"

6. Test
^^^^^^

.. code-block:: bash

   sup dataset list

Amazon Cognito
~~~~~~~~~~~~~~

1. Create User Pool
^^^^^^^^^^^^^^^^^^^

1. Go to **Amazon Cognito** → **User Pools**
2. **Create user pool**
3. Configure sign-in options (email recommended)
4. Create pool

2. Create App Client
^^^^^^^^^^^^^^^^^^^^

1. In User Pool → **App integration** → **App clients and analytics**
2. **Create app client**
3. Client name: ``Superset CLI``
4. Check **Resource Owner Password Credentials grant**
5. Create

Note the **Client ID** and generate **Client Secret**.

3. Create Service User
^^^^^^^^^^^^^^^^^^^^^^

1. Go to **Users** → **Create user**
2. Username: ``superset-service``
3. Message delivery method: ``Email``
4. Temporary password: Set one
5. Create

Set permanent password afterward.

4. Configure sup
^^^^^^^^^^^^^^^

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/token
       oauth_client_id: <client-id>
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: superset-service
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}
       oauth_scope: "openid profile email"

Replace ``{cognito-domain}`` with your Cognito domain and ``{region}`` with your AWS region.

.. code-block:: bash

   export SUPERSET_OAUTH_SECRET="<client-secret>"
   export SUPERSET_SERVICE_PASSWORD="<user-password>"

5. Test
^^^^^^

.. code-block:: bash

   sup dataset list

Username/Password Setup
-----------------------

For Standard Superset Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your Superset instance uses built-in authentication (not OAuth2):

1. Create Service User in Superset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Log in to Superset Admin
2. **Settings** → **Users**
3. Create new user: ``superset-service``
4. Set a strong password
5. Assign appropriate role (e.g., Admin or read-only as needed)

2. Configure sup
^^^^^^^^^^^^^^^

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: username_password
       username: superset-service
       password: ${ENV:SUPERSET_PASSWORD}

.. code-block:: bash

   export SUPERSET_PASSWORD="<strong-password>"

3. Test
^^^^^^

.. code-block:: bash

   sup dataset list

JWT Token Setup
---------------

For Pre-Generated JWT Tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your Superset instance uses JWT authentication:

1. Generate JWT Token
^^^^^^^^^^^^^^^^^^^^^

Using your Superset instance's JWT secret:

.. code-block:: python

   import jwt
   from datetime import datetime, timedelta

   secret = "your-superset-jwt-secret"
   payload = {
       "iat": datetime.utcnow(),
       "exp": datetime.utcnow() + timedelta(days=365),
       "user_id": 1,  # Your service user ID
       "username": "superset-service"
   }
   token = jwt.encode(payload, secret, algorithm="HS256")
   print(token)

2. Configure sup
^^^^^^^^^^^^^^^

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: jwt
       jwt_token: ${ENV:SUPERSET_JWT_TOKEN}

.. code-block:: bash

   export SUPERSET_JWT_TOKEN="<your-generated-jwt-token>"

3. Test
^^^^^^

.. code-block:: bash

   sup dataset list

Configuration Examples
----------------------

Multiple Self-Hosted Instances
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   superset_instances:
     production:
       url: https://superset-prod.example.com
       auth_method: oauth
       oauth_token_url: https://auth.example.com/oauth2/token
       oauth_client_id: superset-cli-prod
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET_PROD}
       oauth_username: superset-service-prod
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD_PROD}

     staging:
       url: https://superset-staging.example.com
       auth_method: oauth
       oauth_token_url: https://auth-staging.example.com/oauth2/token
       oauth_client_id: superset-cli-staging
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET_STAGING}
       oauth_username: superset-service-staging
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD_STAGING}

     local:
       url: http://localhost:8088
       auth_method: username_password
       username: admin
       password: ${ENV:SUPERSET_LOCAL_PASSWORD}

Mixed Authentication Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   superset_instances:
     # Enterprise with OAuth2
     enterprise:
       url: https://superset.acme.com
       auth_method: oauth
       oauth_token_url: https://auth.acme.com/oauth2/token
       oauth_client_id: superset-cli
       oauth_client_secret: ${ENV:OAUTH_SECRET}
       oauth_username: superset-service
       oauth_password: ${ENV:SERVICE_PASSWORD}

     # Legacy with Basic Auth
     legacy:
       url: https://old-superset.acme.com
       auth_method: username_password
       username: admin
       password: ${ENV:LEGACY_PASSWORD}

     # Development with JWT
     dev:
       url: https://dev-superset.acme.com
       auth_method: jwt
       jwt_token: ${ENV:DEV_JWT_TOKEN}

Troubleshooting
---------------

Error: "Invalid client credentials"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Client ID or secret is incorrect

**Solution:**

1. Verify ``oauth_client_id`` and ``oauth_client_secret`` match your OIDC provider
2. Ensure the client is registered for Resource Owner Password grant
3. Check that the client hasn't been revoked

**Provider-specific:**

- **Keycloak:** Check **Credentials** tab for exact secret
- **Okta:** Verify client ID in app settings
- **Auth0:** Ensure app has correct type selected
- **Azure AD:** Check tenant ID is correct in token URL

Error: "Invalid username or password"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Service account credentials are incorrect

**Solution:**

1. Verify ``oauth_username`` and ``oauth_password`` are correct
2. Check service account hasn't been disabled/locked
3. Ensure service account has permission to access OAuth2
4. For OAuth2, verify service account exists in the OIDC provider

**Provider-specific:**

- **Keycloak:** Check user exists and password is set
- **Okta:** Verify user hasn't been deactivated
- **Auth0:** Check user exists if using user-based auth
- **Azure AD:** Verify user exists in your tenant
- **Cognito:** Check user status in User Pool

Error: "Token endpoint unreachable"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Network connectivity or incorrect token URL

**Solution:**

1. Verify ``oauth_token_url`` is correct
2. Check firewall allows outbound HTTPS
3. Ping token endpoint to verify connectivity
4. Check for proxy/VPN requirements

**Test connectivity:**

.. code-block:: bash

   curl -I https://auth.example.com/oauth2/token

Error: "CSRF token fetch failed" or "401 Unauthorized"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** OAuth2 token is valid but service account lacks Superset permissions

**Solution:**

1. Verify service account has Superset access
2. Check Superset is configured with OIDC/OAuth2
3. Ensure service account has appropriate role in Superset
4. Check Superset API authentication settings

**Verify Superset OIDC configuration:**

.. code-block:: bash

   curl https://superset.example.com/api/v1/security/csrf_token/ \
     -H "Authorization: Bearer YOUR_TOKEN"

Error: "scopes insufficient"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** OAuth2 scopes don't match provider requirements

**Solution:**

1. Check what scopes your OIDC provider requires
2. Update ``oauth_scope`` in config
3. Ensure service account has permission for requested scopes

**Common scopes:**

.. code-block:: yaml

   oauth_scope: "openid profile email"           # Minimum
   oauth_scope: "openid profile email roles"     # With roles
   oauth_scope: "openid profile email custom"    # Custom scopes

Security Best Practices
-----------------------

1. Use Environment Variables for Secrets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**DO:**

.. code-block:: yaml

   oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
   oauth_password: ${ENV:SERVICE_PASSWORD}

**DON'T:**

.. code-block:: yaml

   oauth_client_secret: "my-secret-123"  # Never hardcode!
   oauth_password: "password123"         # Never hardcode!

2. Protect Configuration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   chmod 600 ~/.sup/config.yml
   chmod 600 .sup/state.yml

3. Create Dedicated Service Accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Don't use personal user credentials
- Create account with minimal required permissions
- Use strong, unique passwords
- Rotate credentials regularly

4. Use OAuth2 Instead of Username/Password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OAuth2 provides:

- Better security (no password in configs)
- Token expiration and refresh
- Centralized identity management
- Audit trail in OIDC provider

5. Secure Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**In local development:**

.. code-block:: bash

   # .env file (add to .gitignore!)
   export SUPERSET_OAUTH_SECRET="..."
   export SERVICE_PASSWORD="..."

   # Load in shell
   source .env

**In CI/CD:**

- Use secrets management (GitHub Secrets, GitLab Variables, etc.)
- Never commit secrets to git
- Use short-lived tokens when possible

**In production:**

- Use environment-specific secret management
- Rotate credentials regularly
- Monitor access logs
- Use least-privilege principle

6. Regular Credential Rotation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rotate credentials regularly:

.. code-block:: bash

   # In OIDC provider, generate new client secret
   # Update config file with new secret
   export SUPERSET_OAUTH_SECRET="new-secret"

   # Test
   sup dataset list

   # When working, remove old secret from OIDC provider

7. Audit Access
~~~~~~~~~~~~~~~

Monitor who accessed Superset:

- Check Superset audit logs
- Check OIDC provider access logs
- Review sup command history

8. Network Security
~~~~~~~~~~~~~~~~~~~

- Use HTTPS for all connections
- Verify SSL certificates
- Use VPN/private networks when possible
- Firewall restrict token endpoint access

Getting Help
------------

- **Issues:** https://github.com/preset-io/superset-sup/issues
- **Discussions:** https://github.com/preset-io/superset-sup/discussions
- **Documentation:** https://superset-sup.readthedocs.io/

Found a problem with this guide? Please open an issue or submit a PR!
