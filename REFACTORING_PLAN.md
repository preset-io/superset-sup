# Refactoring sup CLI for Self-Hosted Superset with OAuth2/OIDC

## Problem Statement

The `sup` CLI currently requires Preset workspace configuration and API tokens for all operations. This prevents it from working with self-hosted Superset instances authenticated via OAuth2/OIDC providers (like Keycloak).

**Current Limitation Chain:**
1. `sup config auth` only accepts Preset API tokens (line 298: "You can find your API credentials at: https://manage.app.preset.io")
2. `SupSupersetClient.from_context()` requires a workspace ID and fetches the hostname via Preset API (lines 59-90)
3. Functional commands (`dataset list`, `chart pull`, etc.) all depend on `SupSupersetClient.from_context()` 
4. Workspace commands (`workspace list`, `workspace use`) require `SupPresetClient` which needs Preset API tokens

## Proposed Architecture

### 1. Dual Authentication Paths

**Path A: Preset (Current)**
- Use Preset API tokens → Get workspace info → Fetch Superset instance URL → Use SupPresetAuth

**Path B: Self-Hosted Superset (New)**
- Configure Superset instance in config → Use OAuth2/OIDC auth directly → Access Superset API

### 2. Configuration Enhancement

Current config structure supports both, but commands don't use it:

```yaml
superset_instances:
  superset-qa:
    url: https://bi-qa.ol.mit.edu
    auth_method: oauth
    oauth_token_url: https://sso-qa.ol.mit.edu/realms/ol-data-platform/protocol/openid-connect/token
    oauth_client_id: ol-superset-client
    oauth_client_secret: ${ENV:SUPERSET_OAUTH_CLIENT_SECRET}
    oauth_username: superset_service@ol.dev
    oauth_password: ${ENV:SUPERSET_OAUTH_SERVICE_PASSWORD}
```

### 3. New Command Structure

Replace workspace-dependent commands with instance-aware commands:

```bash
# New command group: sup instance (replaces workspace for self-hosted)
sup instance list              # List configured Superset instances
sup instance use <name>        # Select default instance
sup instance show              # Show current instance + auth status

# Existing commands enhanced:
sup dataset list              # Works with current instance (no --workspace-id needed)
sup chart pull                # Works with current instance
sup sql "SELECT ..."          # Works with current instance

# New flags added:
sup dataset list --instance=superset-qa   # Override instance selection
sup chart pull --instance=superset-qa

# Legacy Preset path still works:
sup workspace list            # Lists Preset workspaces (if credentials configured)
sup workspace use 123         # Sets Preset workspace
```

## Implementation Phases

### Phase 1: Instance-Aware Client Factory (CRITICAL PATH)

**Files to modify:**
- `src/sup/clients/superset.py` → Refactor `SupSupersetClient.from_context()`
- `src/sup/config/settings.py` → Add instance selection logic
- `src/preset_cli/auth/factory.py` → Already supports both auth methods ✅

**Changes:**
1. Update `SupSupersetClient.from_context()` to:
   - Accept optional `instance_name` parameter
   - Check if Preset workspace is configured first (backward compatible)
   - Fall back to self-hosted Superset instance configuration
   - Support both OAuth2 and username/password auth via factory

2. Update `SupContext` to track instance selection:
   ```python
   current_instance_name: Optional[str] = None  # self-hosted instance name
   ```

3. Environment variable support:
   ```bash
   SUP_INSTANCE_NAME=superset-qa  # Select instance
   ```

**Dependencies:** None - uses existing `create_superset_auth()`

### Phase 2: Config Auth Command Refactor

**File:** `src/sup/commands/config.py::auth_setup()`

**Changes:**
1. Welcome screen: Ask "Are you using Preset or self-hosted Superset?"
2. Branch logic:
   - **Preset path:** Current flow (API token setup)
   - **Self-hosted path:** 
     - Ask for instance name
     - Ask auth method:
       - `username_password` - Built-in Superset auth (default for open-source)
       - `oauth` - External OAuth2/OIDC provider (Keycloak, Okta, Auth0, etc.)
       - `jwt` - Pre-generated JWT token
     - Collect appropriate credentials
     - Save to `superset_instances[instance_name]`
     - Test connection

3. Simplify config file validation:
   - Check for Preset tokens OR self-hosted instances
   - Don't require both

### Phase 3: Instance Command Group

**New file:** `src/sup/commands/instance.py`

**Commands:**
```python
@app.command("list")
def list_instances():
    """List configured Superset instances."""
    # Show all configured instances in config
    # Show auth status for each
    # Highlight current instance

@app.command("use")
def use_instance(name: str):
    """Set default Superset instance."""
    # Validate instance exists
    # Save to context
    # Test connection

@app.command("show")
def show_instance():
    """Show current instance details."""
    # Instance name, URL, auth method
    # Auth status (valid credentials?)
```

**Register in main.py:**
```python
from sup.commands import instance
app.add_typer(instance.app, name="instance")
```

### Phase 4: Functional Command Updates

**Files:** All `src/sup/commands/*.py` (dataset, chart, dashboard, database, sql, etc.)

**Changes:**
1. Update each command to accept `--instance` flag (optional)
2. Update client instantiation:
   ```python
   # Before: requires workspace
   client = SupSupersetClient.from_context(ctx, workspace_id)
   
   # After: supports both workflows
   client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id, instance_name=instance)
   ```

3. Update help text to reflect both paths:
   ```python
   """
   List datasets in current workspace/instance.
   
   For Preset users: configure workspace with 'sup workspace use'
   For self-hosted: configure instance with 'sup instance use'
   """
   ```

### Phase 5: Workspace Command Graceful Degradation

**File:** `src/sup/commands/workspace.py`

**Changes:**
1. Keep existing workspace commands for Preset users
2. Add helpful error messages if Preset tokens aren't configured:
   ```
   ❌ No Preset credentials configured
   
   💡 To use Preset workspaces:
      sup config auth    # Set up Preset API token
      sup workspace list
   
   💡 To use self-hosted Superset:
      sup config auth    # Set up instance authentication
      sup instance list
   ```

## Migration Path for Users

### Preset Users (No Changes)
```bash
sup config auth                    # Configure Preset tokens (as before)
sup workspace list                 # Works unchanged
sup dataset list                   # Works unchanged
```

### Self-Hosted Users (New Path)
```bash
sup config auth                    # New: prompts for instance setup
sup instance list                  # New: shows configured instances
sup instance use superset-qa       # New: selects instance
sup dataset list                   # Works with selected instance
```

### Users with Both Setups
```bash
# Configure both Preset and self-hosted in config.yml
sup workspace list                 # Lists Preset workspaces
sup instance list                  # Lists self-hosted instances
sup dataset list --instance=superset-qa  # Use self-hosted
sup dataset list                   # Use Preset (default)
```

## Testing Strategy

### Unit Tests
- Mock `create_superset_auth()` with OAuth2 config
- Test `SupSupersetClient.from_context()` with both paths
- Test config validation for missing credentials

### Integration Tests
- Real self-hosted Superset instance with OAuth2 (use existing Keycloak setup)
- Test all functional commands with self-hosted auth

### Backward Compatibility
- Run existing Preset tests unchanged
- Verify workspace commands still work

## Risk Assessment

**Low Risk:**
- OAuth2/OIDC auth implementation already proven ✅
- Pydantic models already support both auth types ✅
- Factory function already exists ✅

**Medium Risk:**
- Config auth prompt needs careful UX design
- Graceful fallback for missing Preset/instance credentials
- Help text updates across all commands

**Mitigation:**
- Keep Preset path as default option in config auth
- Clear error messages guide users to correct command
- Update documentation with self-hosted examples

## Files Affected

### Core (Phase 1)
- `src/sup/clients/superset.py` - SupSupersetClient.from_context()
- `src/sup/config/settings.py` - SupContext, SupersetInstanceConfig

### Commands (Phases 2-5)
- `src/sup/commands/config.py` - auth_setup()
- `src/sup/commands/instance.py` - NEW
- `src/sup/commands/dataset.py` - add --instance flag
- `src/sup/commands/chart.py` - add --instance flag
- `src/sup/commands/dashboard.py` - add --instance flag
- `src/sup/commands/database.py` - add --instance flag
- `src/sup/commands/sql.py` - add --instance flag
- `src/sup/commands/workspace.py` - add helpful error messages

### Main Entry Point
- `src/sup/main.py` - register instance command group

### Documentation
- `docs/self_hosted_setup.rst` - Update with sup CLI instructions
- `README.md` - Add self-hosted Superset section

## Success Criteria

1. ✅ `sup config auth` supports Preset AND self-hosted setup
2. ✅ `sup instance use <name>` selects self-hosted instance
3. ✅ `sup dataset list` works with self-hosted instance
4. ✅ All existing Preset workflows continue working
5. ✅ Clear help text guides users to correct commands
6. ✅ Error messages suggest solutions

## Priority

**Phase 1 (SupSupersetClient):** Blocking all other work
**Phase 2 (Config auth):** User-facing critical
**Phase 3 (Instance commands):** Improves UX
**Phase 4 (Functional commands):** Completes feature
**Phase 5 (Workspace graceful):** Polish
