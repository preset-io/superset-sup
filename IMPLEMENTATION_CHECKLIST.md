# Implementation Checklist

Use this checklist to track progress through all phases.

## Pre-Implementation

- [ ] Read ANALYSIS_INDEX.md
- [ ] Read SELF_HOSTED_REFACTORING_SUMMARY.md
- [ ] Review REFACTORING_PLAN.md with team
- [ ] Get approval to proceed
- [ ] Verify test environment (Keycloak + self-hosted Superset) is accessible
- [ ] Backup current codebase
- [ ] Create feature branch: `git checkout -b feature/self-hosted-oauth2`

## Phase 1: Core Client Refactoring (2-3 hours)

### Settings Configuration (`src/sup/config/settings.py`)

- [ ] Add `current_instance_name` field to `SupProjectState` (line ~210)
- [ ] Add `current_instance_name` field to `SupGlobalConfig` (line ~150)
- [ ] Add `get_instance_name()` method to `SupContext`
- [ ] Add `get_superset_instance_config()` method to `SupContext`
- [ ] Add `has_superset_instances()` method to `SupContext`
- [ ] Add `set_instance_context()` method to `SupContext`
- [ ] Add `get_all_instance_names()` method to `SupContext`
- [ ] Test file loads/saves with new fields
- [ ] Verify backward compatibility: old config files still load

### Superset Client (`src/sup/clients/superset.py`)

- [ ] Add import: `from preset_cli.auth.factory import create_superset_auth`
- [ ] Refactor `from_context()` method signature (add `instance_name` parameter)
- [ ] Update `from_context()` docstring
- [ ] Add `_from_instance()` classmethod
- [ ] Add `_from_preset_workspace()` classmethod (move existing logic here)
- [ ] Update `__init__` to set `is_self_hosted` flag
- [ ] Test Preset path still works (no regressions)
- [ ] Test self-hosted path works with OAuth2
- [ ] Test error handling for missing config

### Unit Tests (`tests/clients/test_superset_self_hosted.py`)

- [ ] Create new test file
- [ ] Test `from_context()` with instance_name parameter
- [ ] Test fallback to workspace if no instance
- [ ] Test helpful error when nothing configured
- [ ] Test `_from_instance()` with valid config
- [ ] Test `_from_instance()` with missing config
- [ ] Test `_from_preset_workspace()` still works
- [ ] Test both paths in same config
- [ ] Run: `uv run pytest tests/clients/test_superset_self_hosted.py -v`
- [ ] Run all existing tests: `uv run pytest tests/ -v` (no regressions)

### Manual Testing (Phase 1)

- [ ] Create `~/.sup/config.yml` with superset_instances entry
- [ ] Test: `python -c "from sup.config.settings import SupContext; ctx = SupContext(); print(ctx.get_all_instance_names())"`
- [ ] Test: `python -c "from sup.config.settings import SupContext; from sup.clients.superset import SupSupersetClient; ctx = SupContext(); ctx.set_instance_context('test'); client = SupSupersetClient.from_context(ctx)"`
- [ ] Verify no errors
- [ ] Test with actual Keycloak credentials:
  ```bash
  export SUPERSET_OAUTH_CLIENT_SECRET="..."
  export SUPERSET_OAUTH_SERVICE_PASSWORD="..."
  python -c "from sup.clients.superset import SupSupersetClient; from sup.config.settings import SupContext; ctx = SupContext(); client = SupSupersetClient.from_context(ctx); print(f'Connected: {client.workspace_url}')"
  ```
- [ ] Verify connection works

### Phase 1 Complete

- [ ] All unit tests pass
- [ ] All existing tests pass (no regressions)
- [ ] Manual tests pass
- [ ] Code reviewed by team member
- [ ] Commit: `git commit -m "Phase 1: Dual-path client factory for self-hosted Superset"`

---

## Phase 2: Config Auth Command (1-2 hours)

### Config Command (`src/sup/commands/config.py`)

- [ ] Update `auth_setup()` function docstring
- [ ] Add welcome message asking "Preset or self-hosted?"
- [ ] Create branching logic for two paths
- [ ] **Preset path:**
  - [ ] Keep existing flow (no changes)
  - [ ] Test existing Preset setup still works
- [ ] **Self-hosted path:**
  - [ ] Ask for instance name
  - [ ] Ask for auth method (oauth, username_password, jwt)
  - [ ] Branch based on auth method:
    - [ ] OAuth2: collect token_url, client_id, secret, username, password, scope
    - [ ] Username/password: collect username, password
    - [ ] JWT: collect jwt_token
  - [ ] Test connection by calling `create_superset_auth()`
  - [ ] If test succeeds, save to config
  - [ ] If test fails, show error and retry
- [ ] Update help text to mention both paths
- [ ] Update `show_config()` to show both Preset and instances

### Manual Testing (Phase 2)

- [ ] Run `sup config auth` (Preset path)
  - [ ] Verify existing Preset setup still works
- [ ] Run `sup config auth` (self-hosted path)
  - [ ] Select "self-hosted"
  - [ ] Enter instance name "superset-qa"
  - [ ] Select OAuth2
  - [ ] Enter credentials
  - [ ] Verify connection test works
  - [ ] Verify saved to `~/.sup/config.yml`
- [ ] Run `sup config show`
  - [ ] Verify both Preset tokens and instances shown

### Phase 2 Complete

- [ ] All tests pass
- [ ] Preset setup still works
- [ ] Self-hosted OAuth2 setup works
- [ ] Config file properly saved and loaded
- [ ] Code reviewed
- [ ] Commit: `git commit -m "Phase 2: Enhanced config auth for self-hosted setup"`

---

## Phase 3: Instance Commands (1 hour)

### New Instance Command (`src/sup/commands/instance.py`)

- [ ] Create new file
- [ ] Implement `list_instances()` command
  - [ ] Show all configured instances
  - [ ] Show auth method for each
  - [ ] Highlight current instance
  - [ ] Support --json, --yaml, --porcelain output
- [ ] Implement `use_instance()` command
  - [ ] Accept instance name
  - [ ] Save to context
  - [ ] Test connection
  - [ ] Show confirmation message
- [ ] Implement `show_instance()` command
  - [ ] Show current instance details
  - [ ] Show URL and auth method
  - [ ] Test auth status

### Register in Main App (`src/sup/main.py`)

- [ ] Import instance module
- [ ] Add to app.add_typer()
- [ ] Test: `sup instance list` works

### Manual Testing (Phase 3)

- [ ] Run `sup instance list`
  - [ ] Shows superset-qa instance
  - [ ] Shows OAuth auth method
- [ ] Run `sup instance use superset-qa`
  - [ ] Saves to .sup/state.yml
  - [ ] Shows confirmation
  - [ ] Tests connection (should succeed with proper env vars)
- [ ] Run `sup instance show`
  - [ ] Shows current instance details
  - [ ] Shows auth is valid

### Phase 3 Complete

- [ ] All instance commands work
- [ ] Config/state files properly managed
- [ ] Tests pass
- [ ] Code reviewed
- [ ] Commit: `git commit -m "Phase 3: Instance management commands"`

---

## Phase 4: Functional Command Updates (2-3 hours)

### Update Each Command

For each of these files, make the same type of changes:

- [ ] `src/sup/commands/dataset.py`
- [ ] `src/sup/commands/chart.py`
- [ ] `src/sup/commands/dashboard.py`
- [ ] `src/sup/commands/database.py`
- [ ] `src/sup/commands/sql.py`

**For each file:**
- [ ] Add `--instance` parameter to main list/pull command
- [ ] Update `SupSupersetClient.from_context()` call to pass `instance_name` if provided
- [ ] Update help text to mention both Preset and self-hosted
- [ ] Test command works with both workspace and instance

**Example:**
```python
@app.command("list")
def list_datasets(
    # ... existing parameters ...
    instance: Annotated[
        Optional[str],
        typer.Option("--instance", help="Superset instance name (for self-hosted)"),
    ] = None,
):
    # ...
    client = SupSupersetClient.from_context(ctx, workspace_id, instance_name=instance)
```

### Manual Testing (Phase 4)

- [ ] Test `sup dataset list` with Preset workspace
  - [ ] Should still work without changes
- [ ] Test `sup dataset list --instance=superset-qa`
  - [ ] Should work with self-hosted instance
- [ ] Test `sup chart pull --instance=superset-qa`
  - [ ] Should work with self-hosted instance
- [ ] Test all commands with env var: `SUP_INSTANCE_NAME=superset-qa`
  - [ ] All commands should use instance without --instance flag

### Phase 4 Complete

- [ ] All 5 commands support --instance flag
- [ ] All commands work with both Preset and self-hosted
- [ ] Tests pass
- [ ] Code reviewed
- [ ] Commit: `git commit -m "Phase 4: Add --instance flag to functional commands"`

---

## Phase 5: Workspace Graceful Degradation (30 min)

### Workspace Commands (`src/sup/commands/workspace.py`)

- [ ] Keep all existing workspace commands unchanged
- [ ] Add error handling for missing Preset credentials
- [ ] Update error messages to suggest `sup instance` alternative
- [ ] Example error message:
  ```
  ❌ No Preset credentials configured
  
  💡 To use Preset workspaces:
     sup config auth    # Set up Preset API token
     sup workspace list
  
  💡 To use self-hosted Superset:
     sup config auth    # Set up instance authentication
     sup instance list
  ```

### Manual Testing (Phase 5)

- [ ] Test `sup workspace list` with Preset credentials
  - [ ] Should work as before
- [ ] Test `sup workspace list` without Preset credentials
  - [ ] Should show helpful error message
  - [ ] Should suggest `sup instance` alternative

### Phase 5 Complete

- [ ] Helpful error messages for missing Preset config
- [ ] Tests pass
- [ ] Code reviewed
- [ ] Commit: `git commit -m "Phase 5: Graceful degradation for workspace commands"`

---

## Documentation Updates

- [ ] Update `docs/self_hosted_setup.rst` with sup CLI instructions
  - [ ] Add section for "Using sup with self-hosted Superset"
  - [ ] Update Keycloak example to show `sup config auth` workflow
  - [ ] Add examples for `sup instance` commands
- [ ] Update `README.md`
  - [ ] Add self-hosted Superset section
  - [ ] Mention OAuth2/OIDC support
  - [ ] Link to documentation
- [ ] Add CHANGELOG entry for new feature

---

## Final Integration Testing

- [ ] Fresh environment: `rm -rf ~/.sup/`
- [ ] Setup from scratch:
  ```bash
  sup config auth          # Setup self-hosted
  sup instance list        # Should show superset-qa
  sup instance use superset-qa
  sup dataset list         # Should list datasets
  sup chart pull --mine    # Should pull charts
  ```
- [ ] Verify end-to-end workflow works
- [ ] Test with real Keycloak + self-hosted Superset

---

## Code Quality & Testing

- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Code formatting: `uv run ruff format src/`
- [ ] Code linting: `uv run ruff check src/`
- [ ] Type checking passes
- [ ] No new warnings in CI

---

## Deployment Checklist

- [ ] All branches merged to main
- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG updated
- [ ] Documentation links verified
- [ ] Release notes prepared
- [ ] Tagged: `git tag -a v0.X.Y -m "Self-hosted OAuth2 support"`
- [ ] Pushed: `git push origin main --tags`
- [ ] Published: `uv publish` (or equivalent)

---

## Post-Deployment

- [ ] Monitor issues for self-hosted users
- [ ] Update docs based on user feedback
- [ ] Consider Phase 6: dbt integration for self-hosted (future)
- [ ] Consider Phase 7: Multi-instance sync (future)

---

## Rollback Plan (If Needed)

```bash
# If critical issue found in Phase N:
git revert <commit>
uv publish --revert  # (or manual rollback)
Communicate issue to users
Fix and re-release
```

---

## Sign-Off

- [ ] Project manager approval
- [ ] Code review approval
- [ ] QA sign-off
- [ ] Product approval

**Status:** [ ] Ready to Start | [ ] In Progress | [ ] Complete

**Date Started:** ___________
**Date Completed:** ___________
**Total Hours:** ___________
**Notes:** ___________________________________________________________________________
