# Self-Hosted Superset Refactoring - Complete Analysis

## Status: Ready for Implementation

Your OAuth2/OIDC authentication implementation is solid. The refactoring needed is in the `sup` CLI to use it.

## Current State ✅

**What's Working:**
- Built-in username/password auth for Superset (default open-source)
- `OAuthSupersetAuth` class with automatic token refresh (for external providers)
- `SupersetJWTAuth` for JWT token authentication
- `UsernamePasswordAuth` for basic Superset auth
- Configuration models supporting all auth methods
- `create_superset_auth()` factory routing to correct method
- Comprehensive documentation for all auth types
- Zero new dependencies

**Generated Config (Username/Password - Default):**
```yaml
superset_instances:
  superset-qa:
    url: https://bi-qa.ol.mit.edu
    auth_method: username_password
    username: superset_cli_user
    password: ${ENV:SUPERSET_PASSWORD}
```

**Alternative: OAuth2/OIDC (External Provider):**
```yaml
superset_instances:
  superset-qa-oauth:
    url: https://bi-qa.ol.mit.edu
    auth_method: oauth
    oauth_token_url: https://sso-qa.ol.mit.edu/realms/ol-data-platform/protocol/openid-connect/token
    oauth_client_id: ol-superset-client
    oauth_client_secret: ${ENV:SUPERSET_OAUTH_CLIENT_SECRET}
    oauth_username: superset_service@ol.dev
    oauth_password: ${ENV:SUPERSET_OAUTH_SERVICE_PASSWORD}
    oauth_scope: "openid profile email"
```

## The Problem 🚨

The `sup` CLI requires Preset workspaces everywhere and doesn't support self-hosted instances:

| Command | Current | With Self-Hosted | Status |
|---------|---------|-----------------|---------|
| `sup config auth` | Preset tokens only | + username/password, OAuth2, JWT | ❌ Phase 2 |
| `sup workspace list` | Lists Preset | N/A (no workspace concept) | ❌ Phase 5 |
| `sup dataset list` | Requires workspace ID | Requires instance name | ❌ Phase 4 |
| `sup chart pull` | Requires workspace ID | Requires instance name | ❌ Phase 4 |
| `sup instance use` | N/A | Select instance | ❌ Phase 3 |

### Root Cause: Two-Layer Indirection

```
sup command → SupSupersetClient.from_context()
  ↓
  Requires workspace_id → SupPresetClient.get_workspace_hostname()
  ↓
  Requires Preset API tokens → Can't use self-hosted
```

**Why it fails with self-hosted:**
- No Preset workspace exists
- No Preset API tokens configured
- No way to get Superset instance URL

## The Solution: Dual-Path Architecture

### Design Principle

Let users choose their path once:

```bash
# Path A: Preset users (existing)
sup config auth                    # → Enter Preset API token + secret
sup workspace list                 # → Shows Preset workspaces
sup workspace use 123              # → Selects workspace
sup dataset list                   # → Uses workspace 123

# Path B: Self-hosted users (new)
sup config auth                    # → Choose auth type, configure instance
sup instance use superset-qa       # → Selects instance from config
sup dataset list                   # → Uses instance superset-qa
```

### Implementation Strategy

**Phase 1: Core Client Refactoring** (CRITICAL)
- `SupSupersetClient.from_context()` tries both paths
- Preset path: workspace_id → hostname via Preset API
- Self-hosted path: instance_name → config.url via local config
- Both use appropriate auth (SupPresetAuth vs OAuthSupersetAuth)

**Phase 2: Config Auth Refactoring** (User-Facing)
- Ask "Preset or self-hosted?"
- Branch to appropriate setup
- Save credentials properly

**Phase 3: Instance Commands** (UX)
- `sup instance list` → Show configured instances
- `sup instance use` → Select instance
- `sup instance show` → Show current + auth status

**Phase 4: Functional Command Updates** (Mechanical)
- Add `--instance` flag to all commands
- Update help text
- Update error messages

**Phase 5: Workspace Graceful Degradation** (Polish)
- Keep workspace commands for Preset
- Show helpful error if Preset not configured
- Suggest `sup instance` alternative

## Implementation Effort

### Lines of Code (Estimated)

| Phase | File | Changes | Risk |
|-------|------|---------|------|
| 1 | `settings.py` | +30 | Low |
| 1 | `superset.py` | +150 (refactor) | Low |
| 2 | `config.py` | +100 | Med |
| 3 | `instance.py` | +200 (new) | Low |
| 4 | `dataset.py`, etc | +30 ea × 5 | Low |
| 5 | `workspace.py` | +30 | Low |
| | **Total** | **~650** | **Low** |

### Time Estimate

- Phase 1: 2-3 hours (core logic, tests)
- Phase 2: 1-2 hours (config UX)
- Phase 3: 1 hour (simple commands)
- Phase 4: 2-3 hours (mechanical updates × 5 commands)
- Phase 5: 30 min (error messages)
- **Total: 7-9 hours**

## Key Files to Modify

### Required (Phase 1-2)
- ✅ `src/sup/config/settings.py` - Instance context
- ✅ `src/sup/clients/superset.py` - Dual-path logic
- ✅ `src/sup/commands/config.py` - Auth setup

### Recommended (Phase 3)
- 🔨 `src/sup/commands/instance.py` - New file

### Updates (Phase 4)
- 🔨 `src/sup/commands/{dataset,chart,dashboard,database,sql}.py` - Add flags

### Documentation
- 🔨 `docs/self_hosted_setup.rst` - Add sup CLI instructions
- 🔨 `README.md` - Mention self-hosted support

## Why This Works

✅ **Leverages existing code:**
- `create_superset_auth()` already handles both paths
- Config schema already supports OAuth2
- Tests exist for OAuth2

✅ **Backward compatible:**
- Preset users unaffected
- Workspace commands unchanged (until Phase 5)
- New code only triggered by instance config

✅ **Clean separation:**
- Each path is independent
- Clear precedence rules
- Easy to test both

✅ **User friendly:**
- One command for setup (`sup config auth`)
- No config file editing required
- Environment variables for secrets

## Next Steps

### Immediate
1. Review REFACTORING_PLAN.md for full strategy
2. Review IMPLEMENTATION_PHASE_1.md for technical details
3. Decide on implementation order

### Phase 1 Development
1. Add `current_instance_name` to `SupProjectState`
2. Add `get_instance_name()` to `SupContext`
3. Refactor `SupSupersetClient.from_context()` with `_from_instance()` method
4. Write unit tests for both paths
5. Test with actual Keycloak + self-hosted Superset

### Before Phase 2
1. All Phase 1 tests pass
2. Verify `create_superset_auth()` works with instance config
3. Manual test: `client = SupSupersetClient.from_context(ctx)` with instance

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Break Preset workflow | Keep all Preset code unchanged, default to Preset path |
| Config file corruption | Validate config load, provide migration script |
| User confusion | Clear help text, error messages guide to correct command |
| OAuth2 token expiry | Existing OAuthSupersetAuth handles refresh ✅ |
| Missing instance config | Helpful error suggests `sup instance list` |

## Success Metrics

Once complete, users will be able to work with self-hosted Superset using any auth method:

```bash
# Example 1: Username/Password (default for open-source Superset)
export SUPERSET_PASSWORD="..."
sup config auth    # → Interactive setup
sup instance use superset-qa
sup dataset list
sup chart pull --name "My Chart"

# Example 2: OAuth2/OIDC (for Keycloak, Okta, Auth0, etc.)
export SUPERSET_OAUTH_CLIENT_SECRET="..."
export SUPERSET_OAUTH_SERVICE_PASSWORD="..."
sup config auth    # → Choose OAuth2 option
sup instance use superset-qa-oauth
sup dataset list

# Example 3: JWT Token
sup config auth    # → Paste pre-generated JWT token
sup instance use superset-qa-jwt
sup dataset list

# All commands support --instance override
sup dataset list --instance=superset-qa
sup chart pull --instance=superset-qa-oauth
```

## Files in This Analysis

1. **REFACTORING_PLAN.md** - High-level strategy and phases
2. **IMPLEMENTATION_PHASE_1.md** - Detailed technical spec for Phase 1
3. **SELF_HOSTED_REFACTORING_SUMMARY.md** - This file
4. **superset-qa-config.yml** - Ready-to-use Keycloak config

## Questions?

The refactoring plan is clear and low-risk. The OAuth2 implementation is solid. The main work is wiring the CLI to use it.

Ready to start Phase 1?
