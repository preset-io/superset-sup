Installation
=============

Get sup installed and ready to use.

System Requirements
-------------------

Python
~~~~~~

- Python 3.8 or later (3.9+ recommended)
- pip or uv package manager

Operating System
~~~~~~~~~~~~~~~~

- macOS (10.14+)
- Linux (Ubuntu 18.04+, CentOS 7+, Debian 10+)
- Windows (Windows 10 or later, requires WSL2 for best experience)

Network
~~~~~~~

- HTTPS access to your Superset instance
- Network access to OAuth2 token endpoint (if using OAuth2)

Installation Methods
--------------------

Option 1: Install from PyPI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install superset-sup

Or with specific version:

.. code-block:: bash

   pip install superset-sup==0.1.0

Option 2: Install from GitHub (Latest Development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install git+https://github.com/preset-io/superset-sup.git

Option 3: Install with uv (Faster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have `uv <https://github.com/astral-sh/uv>`_ installed:

.. code-block:: bash

   uv pip install superset-sup

Option 4: Development Installation (For Contributors)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Clone repository
   git clone https://github.com/preset-io/superset-sup.git
   cd superset-sup

   # Install in development mode
   pip install -e ".[dev]"

   # Or with uv
   uv pip install -e ".[dev]"

Option 5: Using Docker (Container Deployment)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

   FROM python:3.11-slim

   RUN pip install superset-sup

   WORKDIR /app
   COPY config.yml ~/.sup/config.yml
   COPY .env .

   ENTRYPOINT ["sup"]

Build and run:

.. code-block:: bash

   docker build -t superset-sup .
   docker run -it --env-file .env superset-sup dataset list

Verify Installation
-------------------

Check Installation
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup --version

Expected output:

.. code-block:: text

   sup, version X.Y.Z

View Help
~~~~~~~~~

.. code-block:: bash

   sup --help

This shows all available commands organized by category.

Test with Simple Command
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup config show

This displays your current configuration (before setting up authentication).

Configuration
--------------

Initial Setup
~~~~~~~~~~~~~

After installation, configure sup for your Superset instance.

Option 1: Interactive Setup (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   sup config auth

This launches an interactive wizard to:

1. Select Preset or self-hosted Superset
2. Choose authentication method
3. Enter credentials
4. Test connection

Option 2: Manual Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Edit ``~/.sup/config.yml``:

.. code-block:: bash

   mkdir -p ~/.sup
   nano ~/.sup/config.yml

Add your configuration:

.. code-block:: yaml

   # Preset (if using Preset workspaces)
   preset_api_token: your-token
   preset_api_secret: your-secret

   # Self-hosted Superset
   superset_instances:
     production:
       url: https://superset.example.com
       auth_method: oauth
       oauth_token_url: https://auth.example.com/oauth2/token
       oauth_client_id: your-client-id
       oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
       oauth_username: service-account
       oauth_password: ${ENV:SUPERSET_SERVICE_PASSWORD}

Option 3: Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set credentials via environment variables (for CI/CD):

.. code-block:: bash

   # Preset
   export SUP_PRESET_API_TOKEN="your-token"
   export SUP_PRESET_API_SECRET="your-secret"

   # Self-hosted (OAuth2)
   export SUPERSET_OAUTH_SECRET="your-secret"
   export SUPERSET_SERVICE_PASSWORD="your-password"

Secure Your Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Protect sensitive configuration:

.. code-block:: bash

   # Restrict config file permissions
   chmod 600 ~/.sup/config.yml

   # If using .env file
   chmod 600 .env

Add to ``.gitignore`` to prevent accidental commits:

.. code-block:: text

   .env
   .sup/
   ~/.sup/

Next Steps
----------

1. Configure Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Choose your setup method:

- **Preset users:** Set API token/secret
- **Self-hosted (OAuth2):** Follow :doc:`self_hosted_setup`
- **Self-hosted (Basic Auth):** Set username/password
- **JWT tokens:** Set your JWT token

2. Test Connection
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sup dataset list

If you see datasets, you're good to go!

3. Explore Features
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # View available commands
   sup --help

   # Execute SQL
   sup sql "SELECT COUNT(*) FROM your_table"

   # List charts
   sup chart list --mine

   # List dashboards
   sup dashboard list

4. Read Documentation
~~~~~~~~~~~~~~~~~~~~~

- :doc:`authentication_cheatsheet` - Quick auth reference
- :doc:`self_hosted_setup` - Complete self-hosted guide
- `Main README <../README.md>`_ - Feature overview

Upgrading
---------

Upgrade to Latest Version
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install --upgrade superset-sup

Or with uv:

.. code-block:: bash

   uv pip install --upgrade superset-sup

Check for Updates
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip list --outdated | grep superset-sup

Verify Upgrade
~~~~~~~~~~~~~~

.. code-block:: bash

   sup --version

Troubleshooting
---------------

"Command not found: sup"
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** ``sup`` command is not recognized

**Solutions:**

1. Check installation:

   .. code-block:: bash

      pip show superset-sup

2. Reinstall:

   .. code-block:: bash

      pip uninstall superset-sup
      pip install superset-sup

3. Check PATH:

   .. code-block:: bash

      which sup
      python -m pip show -f superset-sup

4. Use python module:

   .. code-block:: bash

      python -m sup --help

"ModuleNotFoundError: No module named 'sup'"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Python can't find sup module

**Solutions:**

1. Reinstall package:

   .. code-block:: bash

      pip uninstall superset-sup
      pip install superset-sup

2. Check Python version:

   .. code-block:: bash

      python --version

   (Must be 3.8+)

3. Use virtual environment:

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate
      pip install superset-sup

"sup config show" shows no configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Configuration isn't being loaded

**Solutions:**

1. Check config file exists:

   .. code-block:: bash

      ls -la ~/.sup/config.yml

2. Check file is readable:

   .. code-block:: bash

      cat ~/.sup/config.yml

3. Check YAML syntax:

   .. code-block:: bash

      python -c "import yaml; yaml.safe_load(open('~/.sup/config.yml'))"

Authentication fails after installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Can't authenticate with credentials

**Solutions:**

1. Verify credentials:

   .. code-block:: bash

      sup config show

2. Check environment variables:

   .. code-block:: bash

      echo $SUPERSET_OAUTH_SECRET

3. Test connection:

   .. code-block:: bash

      sup sql "SELECT 1"

4. See detailed error:

   .. code-block:: bash

      sup dataset list --debug

Installation with specific Python version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have multiple Python versions installed:

.. code-block:: bash

   # Use specific Python version
   python3.11 -m pip install superset-sup

   # Verify
   python3.11 -m sup --version

Install dependencies only
~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to install just the dependencies (useful for CI/CD):

.. code-block:: bash

   pip install superset-sup --no-deps

Uninstallation
--------------

Remove sup
~~~~~~~~~~

.. code-block:: bash

   pip uninstall superset-sup

Clean up configuration (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   rm -rf ~/.sup

Getting Help
------------

Documentation
~~~~~~~~~~~~~

- `Documentation Index <index.html>`_ - Start here
- `Main README <../README.md>`_ - Feature overview
- :doc:`self_hosted_setup` - Self-hosted guide

Community Support
~~~~~~~~~~~~~~~~~

- **Issues:** https://github.com/preset-io/superset-sup/issues
- **Discussions:** https://github.com/preset-io/superset-sup/discussions

Preset Support (for Preset customers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Preset Support Portal:** https://support.preset.io
