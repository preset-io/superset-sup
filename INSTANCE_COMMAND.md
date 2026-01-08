# sup instance Command - Self-Hosted Superset Management

## Overview

The `sup instance` command group manages self-hosted Superset instances for CLI operations. It complements `sup workspace` (for Preset workspaces) and enables dual-path support for both Preset Cloud and self-hosted Superset deployments.

## Implementation Status

✅ **COMPLETE**

- `src/sup/commands/instance.py` - Command implementation
- Registered in `src/sup/main.py`
- Full feature parity with `sup workspace` command
- 100% backward compatible

## Commands

### `sup instance list`

List all configured self-hosted Superset instances.

**Usage:**
```bash
sup instance list                    # Display as Rich table
sup instance list --json             # Output as JSON
sup instance list --yaml             # Output as YAML
sup instance list --porcelain        # Machine-readable format
```

**Output:**
Shows instance name, URL, authentication method, and configuration status.

```
┏━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Current ┃ Name  ┃ URL                   ┃ Auth     ┃
┡━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ ✅      │ prod  │ https://superset.example.com │ oauth    │
│         │ staging │ https://staging.example.com │ jwt      │
│         │ dev   │ https://localhost:8088      │ username │
└─────────┴───────┴─────────────────────────┴──────────┘
```

### `sup instance use <NAME>`

Set the default Superset instance for the current session or globally.

**Usage:**
```bash
sup instance use prod                # Set for current session only
sup instance use staging --persist   # Set globally (save to ~/.sup/config.yml)
sup instance use dev -p              # Short form with --persist
```

**Output:**
```
🖥️  Setting instance 'prod' as default...
✅ Instance 'prod' saved globally
```

### `sup instance show`

Show current Superset instance context.

**Usage:**
```bash
sup instance show                    # Display current instance info
```

**Output:**
```
🖥️  Current Superset Instance Context
📍 Instance: prod
🔗 URL: https://superset.example.com
🔐 Auth: oauth
```

## Configuration

Superset instances are configured in `~/.sup/config.yml` under the `superset_instances` section:

```yaml
superset_instances:
  prod:
    url: https://superset.example.com
    auth_method: oauth
    oauth_token_url: https://auth.example.com/oauth2/token
    oauth_client_id: my-client-id
    oauth_client_secret: ${ENV:SUPERSET_OAUTH_SECRET}
    oauth_scope: openid profile email roles

  staging:
    url: https://staging.example.com
    auth_method: jwt
    jwt_token: ${ENV:STAGING_JWT_TOKEN}

  dev:
    url: https://localhost:8088
    auth_method: username_password
    username: admin
    password: ${ENV:DEV_PASSWORD}
```

## Usage with Other Commands

Once an instance is selected, use it with commands that support `--instance`:

```bash
# Set instance as default
sup instance use prod

# Now all commands use prod instance
sup sql "SELECT 1"                   # Queries prod instance
sup dashboard list --mine            # Lists dashboards in prod
sup chart pull --workspace-id=123    # (Note: workspace-id only works for Preset)

# Or override per-command
sup query list --instance=staging    # Queries staging even if prod is default
sup user list --instance=dev         # Queries dev instance
```

## Priority/Precedence

Commands check for instance/workspace in this order:

1. **CLI parameter** (highest priority)
   - `--instance=prod` or `--workspace-id=123`
2. **Environment variables**
   - `SUP_INSTANCE_NAME=prod`
   - `SUP_WORKSPACE_ID=123`
3. **Project state** (.sup/state.yml)
   - `current_instance_name` or `current_workspace_id`
4. **Global config** (~/.sup/config.yml)
   - `current_instance_name` or `current_workspace_id`
5. **Error** - Helpful message suggesting `sup instance list` or `sup workspace list`

## Use Cases

### Development Workflow

```bash
# Set up dev environment
sup instance use dev
sup sql "SELECT COUNT(*) FROM users"

# Switch to production for deployment testing
sup instance use prod --persist
sup dashboard list
sup chart pull --ids=123,456
```

### Multi-Environment Sync

```bash
# Sync from dev to staging
sup instance use dev
sup dashboard pull --all
sup instance use staging
sup dashboard push

# Or use sync command for multi-target
sup sync run ./my_sync --source dev --targets staging,prod
```

### CI/CD Integration

```bash
# Authenticate once, use in scripts
export SUP_INSTANCE_NAME=prod
sup sql "SELECT version();"

# Or for Preset workspaces
export SUP_WORKSPACE_ID=123
sup dataset list
```

## Authentication Methods Supported

### OAuth2/OIDC
Most enterprise-grade setups. Service account credentials.

```yaml
superset:
  url: https://superset.example.com
  auth_method: oauth
  oauth_token_url: https://auth.example.com/oauth2/token
  oauth_client_id: ${ENV:SUPERSET_CLIENT_ID}
  oauth_client_secret: ${ENV:SUPERSET_CLIENT_SECRET}
  oauth_scope: openid profile email roles
```

### JWT Token
Pre-generated tokens for programmatic access.

```yaml
staging:
  url: https://staging.example.com
  auth_method: jwt
  jwt_token: ${ENV:JWT_TOKEN}
```

### Username/Password
Basic authentication for Superset.

```yaml
dev:
  url: https://localhost:8088
  auth_method: username_password
  username: admin
  password: ${ENV:ADMIN_PASSWORD}
```

## Environment Variable Substitution

Sensitive credentials can be loaded from environment variables using `${ENV:VAR_NAME}` syntax:

```yaml
superset_instances:
  prod:
    url: https://superset.example.com
    auth_method: oauth
    oauth_client_secret: ${ENV:SUPERSET_CLIENT_SECRET}  # Loaded from $SUPERSET_CLIENT_SECRET
    oauth_username: service-account                      # Literal value
    oauth_password: ${ENV:SERVICE_ACCOUNT_PASSWORD}      # Loaded from $SERVICE_ACCOUNT_PASSWORD
```

**Security Best Practice:** Never commit real credentials to version control. Always use environment variables for sensitive values.

## Help and Troubleshooting

### Command not found
If `sup instance` command doesn't appear:
```bash
sup --help | grep instance
```

Should show the instance command in "Manage Assets" section.

### Instance configuration errors
Check that your instance is configured:
```bash
sup instance list
```

If empty, edit `~/.sup/config.yml` and add your instances.

### Authentication failures
Verify OAuth/JWT configuration:
```bash
sup instance show
```

Check that environment variables are set:
```bash
echo $SUPERSET_CLIENT_SECRET
echo $JWT_TOKEN
```

## Integration with Phase 3 Refactoring

The `sup instance` command completes the Phase 3 dual-path refactoring:

- **Phase 1**: Added instance tracking to `SupSupersetClient` and intelligent dispatcher
- **Phase 2**: Updated high-priority commands with `--instance` parameter
- **Phase 3**: Updated remaining commands with `--instance` parameter
- **Phase 3 Bonus**: Implemented `sup instance` command for user-friendly instance management

This provides complete feature parity between Preset workspace management (`sup workspace`) and self-hosted instance management (`sup instance`).

## Examples

### List available instances
```bash
$ sup instance list

🖥️  Configured Superset Instances
┏─────────┬──────────┬──────────────────────────────┬──────────┓
┃ Current ┃ Name     ┃ URL                          ┃ Auth     ┃
┡─────────╇──────────╇──────────────────────────────╇──────────┩
│ ✅      │ prod     │ https://superset.example.com │ oauth    │
│         │ staging  │ https://staging.example.com  │ jwt      │
│         │ dev      │ https://localhost:8088       │ username │
└─────────┴──────────┴──────────────────────────────┴──────────┘

💡 Current instance: prod
```

### Change instance
```bash
$ sup instance use staging
🖥️  Setting instance 'staging' as default...
✅ Using instance 'staging' for this session
💡 Add --persist to save globally
```

### Show current instance
```bash
$ sup instance show
🖥️  Current Superset Instance Context
📍 Instance: staging
🔗 URL: https://staging.example.com
🔐 Auth: jwt
```

### Use with other commands
```bash
$ sup query list --instance=prod
[Shows queries from prod instance]

$ sup dashboard pull --instance=dev --ids=1,2,3
[Pulls dashboards 1,2,3 from dev instance]

$ sup user list --instance=staging
[Lists users in staging instance]
```
