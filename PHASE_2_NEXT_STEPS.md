# Phase 2: Commands Integration - Next Steps

## Overview

Phase 1 is complete and committed. The dual-path client factory is ready. Phase 2 focuses on integrating instance support into sup commands.

## Phase 2 Objectives

Update all sup commands to support both Preset workspaces and self-hosted instances.

## Commands Requiring Updates

### High Priority (Core Workflows)

1. **`sup dataset list`** (`src/sup/commands/dataset.py`)
   - Current: Only works with workspace_id
   - Required: Add `--instance` parameter
   - Update: Use instance-aware `SupSupersetClient.from_context()`

2. **`sup chart list`** (`src/sup/commands/chart.py`)
   - Current: Only works with workspace_id
   - Required: Add `--instance` parameter
   - Update: Use instance-aware client

3. **`sup sql`** (`src/sup/commands/sql.py`)
   - Current: Requires workspace_id + database_id
   - Required: Add instance support
   - Pattern: Same as dataset/chart

### Medium Priority (Management)

4. **`sup database list`** (`src/sup/commands/database.py`)
   - Add instance support
   - Pattern: Similar to dataset list

5. **`sup dashboard list`** (`src/sup/commands/dashboard.py`)
   - Add instance support
   - Already has stub structure

6. **`sup user list`** (`src/sup/commands/user.py`)
   - Add instance support
   - Read-only (no push/pull)

### Lower Priority (Advanced)

7. **`sup query list`** (`src/sup/commands/query.py`)
   - Add instance support
   - Discovery-only

8. **`sup sync`** (`src/sup/commands/sync.py`)
   - Add instance support for multi-instance workflows
   - Requires careful error handling

## Implementation Pattern

Each command needs:

### 1. Add `--instance` Parameter

```python
@app.command()
def list(
    instance: Optional[str] = typer.Option(
        None,
        "--instance",
        help="Superset instance name (for self-hosted)",
    ),
    workspace_id: Optional[int] = typer.Option(
        None,
        "--workspace-id",
        help="Preset workspace ID",
    ),
    # ... other parameters ...
):
```

### 2. Update Client Creation

Replace:
```python
ctx = SupContext()
client = SupSupersetClient.from_context(ctx, workspace_id=workspace_id)
```

With:
```python
ctx = SupContext()
try:
    client = SupSupersetClient.from_context(
        ctx,
        workspace_id=workspace_id,
        instance_name=instance,
    )
except ValueError as e:
    console.print(f"{EMOJIS['error']} {e}", style=RICH_STYLES["error"])
    raise typer.Exit(1)
```

### 3. Add Help Text About Instance Usage

```
  --instance TEXT                Superset instance name (self-hosted).
                                 Use 'sup instance list' to see available
                                 instances. [env: SUP_INSTANCE_NAME]

  --workspace-id INTEGER         Preset workspace ID. Use 'sup workspace
                                 list' to see available workspaces.
                                 [env: SUP_WORKSPACE_ID]
```

## Error Handling Strategy

Each command should handle both error cases gracefully:

```python
try:
    client = SupSupersetClient.from_context(ctx, workspace_id, instance_name)
except ValueError as e:
    # from_context() provides helpful error message
    console.print(f"{EMOJIS['error']} {e}", style=RICH_STYLES["error"])
    raise typer.Exit(1)
```

The error message from `from_context()` already guides users:
```
No workspace or instance configured.

For Preset users:
  sup workspace list
  sup workspace use <ID>

For self-hosted Superset:
  sup instance list
  sup instance use <NAME>
```

## Testing Strategy for Phase 2

For each command, add test cases for:

1. Instance-based execution (mocked self-hosted)
2. Workspace-based execution (mocked Preset)
3. Instance parameter override
4. Workspace parameter override
5. Error when neither configured
6. Auth failure for instance

Example test structure:
```python
def test_dataset_list_with_instance():
    """Test dataset list against self-hosted instance."""
    with patch.object(SupSupersetClient, 'from_context') as mock_client:
        # Test instance path
        
def test_dataset_list_with_workspace():
    """Test dataset list against Preset workspace."""
    with patch.object(SupSupersetClient, 'from_context') as mock_client:
        # Test workspace path
```

## Implementation Order

Suggested order for Phase 2 work:

1. **Start with `sup dataset list`** - Most straightforward, no dependencies
2. **Then `sup chart list`** - Similar pattern
3. **Then `sup database list`** - Simple enumeration
4. **Then `sup sql`** - Adds complexity with database_id handling
5. **Then `sup user list`** - Similar to dataset list
6. **Finally `sup dashboard list`, `sup query list`, `sup sync`** - Advanced

## Code Search Helpers

Find all commands that use workspace_id:
```bash
grep -r "workspace_id" src/sup/commands/*.py | grep -v "__pycache__"
```

Find all places creating SupSupersetClient:
```bash
grep -r "SupSupersetClient.from_context" src/sup/commands/
```

## Key Files to Reference

- **Pattern example**: `src/sup/commands/workspace.py` - Uses workspace context correctly
- **Client implementation**: `src/sup/clients/superset.py` - Dual-path factory with error handling
- **Config system**: `src/sup/config/settings.py` - Instance methods and precedence
- **Test example**: `tests/clients/test_superset_self_hosted.py` - How to mock both paths

## Commit Message Template for Phase 2

```
Phase 2: Add instance support to [COMMAND] command

- Add --instance parameter to [command] command
- Update SupSupersetClient.from_context() call to support instance_name
- Add error handling for missing workspace or instance
- Update help text to guide users on Preset vs self-hosted
- Add tests for both instance and workspace execution paths

Maintains backward compatibility - existing --workspace-id usage unchanged.
```

## Configuration Examples for Testing

Test with self-hosted instance:
```yaml
# ~/.sup/config.yml
superset_instances:
  test:
    url: "https://superset.example.com"
    auth_method: "username_password"
    username: "admin"
    password: "admin"
```

Then:
```bash
sup instance use test
sup dataset list
```

Or with explicit parameter:
```bash
sup dataset list --instance test
```

## Success Criteria for Phase 2

For each command update:
- ✅ `--instance` parameter works
- ✅ `--workspace-id` parameter still works
- ✅ Context-based instance selection works
- ✅ Context-based workspace selection works (unchanged)
- ✅ Helpful error messages on misconfiguration
- ✅ Tests pass for both paths
- ✅ 100% backward compatible

## Notes

- Don't modify Phase 1 code unless bugs are found
- Phase 1 client factory is stable and well-tested
- All error messages come from `SupSupersetClient.from_context()`
- Use existing `console`, `EMOJIS`, `RICH_STYLES` for consistency
- Environment variable support (`SUP_INSTANCE_NAME`) handled automatically by `get_instance_name()`

Ready for Phase 2 when team signals start.
