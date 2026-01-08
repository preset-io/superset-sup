# Phase 1: Instance-Aware Client Factory Implementation

## Overview

Make `SupSupersetClient.from_context()` work with both Preset workspaces and self-hosted Superset instances configured via OAuth2/OIDC.

## Architecture Diagram

```
SupContext (config + state)
    ↓
    ├─→ get_workspace_id() + Preset tokens?
    │   ↓
    │   Use Preset path (existing)
    │   ├─→ SupPresetClient.get_all_workspaces()
    │   ├─→ Look up workspace hostname
    │   ├─→ Build workspace URL
    │   ├─→ SupPresetAuth (JWT via Preset API)
    │   └─→ SupSupersetClient(workspace_url, auth)
    │
    └─→ Else, check current_instance_name
        ↓
        Use self-hosted path (new)
        ├─→ Get instance from superset_instances[name]
        ├─→ create_superset_auth(instance_config)
        └─→ SupSupersetClient(instance.url, auth)
```

## Changes Required

### 1. Update `src/sup/config/settings.py`

Add instance tracking to `SupContext`:

```python
class SupProjectState(BaseSettings):
    """Project-specific state stored in .sup/state.yml."""
    
    # ... existing fields ...
    
    # Current Superset instance (for self-hosted workflows)
    current_instance_name: Optional[str] = None  # e.g., "superset-qa"

class SupContext:
    """Context manager combining global config and project state."""
    
    def __init__(self):
        self.global_config = SupGlobalConfig.load_from_file()
        self.project_state = SupProjectState.load_from_file()
    
    def get_instance_name(self, cli_override: Optional[str] = None) -> Optional[str]:
        """Get current instance name with proper precedence."""
        env_instance_name = get_env_var("instance_name")
        return (
            cli_override
            or env_instance_name
            or self.project_state.current_instance_name
            or self.global_config.current_instance_name  # NEW
        )
    
    def set_instance_context(self, instance_name: str, persist: bool = False) -> None:
        """Set current Superset instance."""
        if persist:
            self.global_config.current_instance_name = instance_name
            self.global_config.save_to_file()
        else:
            self.project_state.current_instance_name = instance_name
            self.project_state.save_to_file()
    
    def get_superset_instance_config(
        self, instance_name: Optional[str] = None
    ) -> Optional[SupersetInstanceConfig]:
        """Get Superset instance configuration by name."""
        name = instance_name or self.get_instance_name()
        if not name:
            return None
        return self.global_config.superset_instances.get(name)
    
    def has_superset_instances(self) -> bool:
        """Check if any Superset instances are configured."""
        return len(self.global_config.superset_instances) > 0
```

### 2. Update `src/sup/clients/superset.py`

Refactor `SupSupersetClient.from_context()` to support both paths:

```python
from preset_cli.auth.factory import create_superset_auth
from preset_cli.auth.main import Auth

class SupSupersetClient:
    """Superset client wrapper with sup-specific functionality."""

    def __init__(self, workspace_url: str, auth: Auth):
        self.workspace_url = workspace_url
        self.auth = auth
        self.client = SupersetClient(workspace_url, auth)
        self.is_self_hosted = True  # Track for future use

    @classmethod
    def from_context(
        cls,
        ctx: SupContext,
        workspace_id: Optional[int] = None,
        instance_name: Optional[str] = None,
    ) -> "SupSupersetClient":
        """
        Create Superset client from sup configuration context.
        
        Supports both:
        1. Preset workspaces (uses workspace_id + API tokens)
        2. Self-hosted Superset instances (uses instance_name + OAuth2/OIDC)
        
        Precedence:
        1. instance_name parameter (explicit)
        2. workspace_id parameter (explicit)
        3. Current instance from context
        4. Current workspace from context
        5. Error
        
        Args:
            ctx: SupContext with config and state
            workspace_id: Preset workspace ID (legacy)
            instance_name: Self-hosted instance name
            
        Returns:
            SupSupersetClient configured for the workspace or instance
            
        Raises:
            ValueError: If neither workspace nor instance is configured
        """
        # Try self-hosted path first if instance is specified or configured
        if instance_name or (workspace_id is None and ctx.get_instance_name()):
            return cls._from_instance(ctx, instance_name)
        
        # Fall back to Preset path (existing behavior)
        if workspace_id or ctx.get_workspace_id():
            return cls._from_preset_workspace(ctx, workspace_id)
        
        # Neither configured - helpful error
        raise ValueError(
            "No workspace or instance configured.\n\n"
            "For Preset users:\n"
            "  sup workspace list\n"
            "  sup workspace use <ID>\n\n"
            "For self-hosted Superset:\n"
            "  sup instance list\n"
            "  sup instance use <NAME>"
        )
    
    @classmethod
    def _from_instance(
        cls,
        ctx: SupContext,
        instance_name: Optional[str] = None,
    ) -> "SupSupersetClient":
        """Create client for self-hosted Superset instance."""
        # Get instance name
        name = instance_name or ctx.get_instance_name()
        if not name:
            raise ValueError(
                "No Superset instance configured.\n\n"
                "Run: sup instance use <NAME>"
            )
        
        # Get instance configuration
        instance_config = ctx.get_superset_instance_config(name)
        if not instance_config:
            raise ValueError(
                f"Instance '{name}' not found in configuration.\n\n"
                "Run: sup instance list"
            )
        
        # Create auth handler via factory
        try:
            auth = create_superset_auth(instance_config)
        except ValueError as e:
            console.print(
                f"{EMOJIS['error']} Authentication failed: {e}",
                style=RICH_STYLES["error"],
            )
            raise
        
        client = cls(instance_config.url, auth)
        client.is_self_hosted = True
        return client
    
    @classmethod
    def _from_preset_workspace(
        cls,
        ctx: SupContext,
        workspace_id: Optional[int] = None,
    ) -> "SupSupersetClient":
        """Create client for Preset workspace (existing implementation)."""
        from sup.clients.preset import SupPresetClient
        
        # Get workspace ID from context if not provided
        if workspace_id is None:
            workspace_id = ctx.get_workspace_id()

        if not workspace_id:
            console.print(
                f"{EMOJIS['error']} No workspace configured",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup workspace list[/] and [bold]sup workspace use <ID>[/]",
                style=RICH_STYLES["info"],
            )
            raise ValueError("No workspace configured")

        # Check if we have cached hostname
        hostname = None
        current_workspace_id = ctx.get_workspace_id()
        if current_workspace_id == workspace_id:
            hostname = ctx.get_workspace_hostname()

        if not hostname:
            # Fetch from Preset API
            preset_client = SupPresetClient.from_context(ctx, silent=True)
            workspaces = preset_client.get_all_workspaces(silent=True)

            workspace = None
            for ws in workspaces:
                if ws.get("id") == workspace_id:
                    workspace = ws
                    break

            if not workspace:
                console.print(
                    f"{EMOJIS['error']} Workspace {workspace_id} not found",
                    style=RICH_STYLES["error"],
                )
                raise ValueError(f"Workspace {workspace_id} not found")

            hostname = workspace.get("hostname")
            if not hostname:
                console.print(
                    f"{EMOJIS['error']} No hostname for workspace {workspace_id}",
                    style=RICH_STYLES["error"],
                )
                raise ValueError(f"No hostname for workspace {workspace_id}")

            ctx.set_workspace_context(workspace_id, hostname=hostname)

        workspace_url = f"https://{hostname}/"
        auth = SupPresetAuth.from_sup_config(ctx, silent=True)
        
        client = cls(workspace_url, auth)
        client.is_self_hosted = False
        return client
```

### 3. Update error handling in commands

All commands using `SupSupersetClient.from_context()` need to handle both error cases:

```python
# In dataset.py, chart.py, etc.
try:
    ctx = SupContext()
    client = SupSupersetClient.from_context(ctx, workspace_id)
except ValueError as e:
    console.print(f"{EMOJIS['error']} {e}", style=RICH_STYLES["error"])
    raise typer.Exit(1)
```

## Testing Plan

### Unit Tests

File: `tests/clients/test_superset_client.py`

```python
def test_from_context_preset_workspace(ctx_with_workspace, mock_preset_client):
    """Test Preset workspace path (existing)."""
    # Arrange: ctx has workspace_id, Preset tokens
    # Act: SupSupersetClient.from_context(ctx)
    # Assert: Returns Preset-authenticated client

def test_from_context_self_hosted_instance(ctx_with_instance):
    """Test self-hosted instance path (new)."""
    # Arrange: ctx has instance configured with OAuth2
    # Act: SupSupersetClient.from_context(ctx)
    # Assert: Returns OAuth2-authenticated client

def test_from_context_instance_name_override(ctx_with_both):
    """Test instance_name parameter overrides context."""
    # Arrange: ctx has both workspace and instance
    # Act: SupSupersetClient.from_context(ctx, instance_name="foo")
    # Assert: Uses instance, not workspace

def test_from_context_no_config(ctx_empty):
    """Test helpful error when nothing configured."""
    # Assert: ValueError with clear message about both paths

def test_auth_factory_called_with_instance_config(ctx_with_instance):
    """Test that create_superset_auth receives correct config."""
    # Mock create_superset_auth
    # Assert: Called with SupersetInstanceConfig from context
```

### Integration Tests

File: `tests/integration/test_self_hosted_commands.py`

```python
def test_dataset_list_with_self_hosted_instance(self_hosted_superset):
    """Test dataset list against real self-hosted Superset."""
    # Use real Keycloak + self-hosted Superset from test environment
    # Verify datasets are returned
    
def test_config_auth_self_hosted_workflow(tmp_config):
    """Test complete config auth workflow for self-hosted."""
    # Create instance in config
    # Test connection
    # Verify credentials valid
```

## Backward Compatibility

✅ **Fully backward compatible:**
- All existing Preset code paths unchanged
- Workspace ID parameter still works
- Environment variables still work (`SUP_WORKSPACE_ID`)
- Default behavior unchanged (Preset takes priority)

## Success Criteria

1. ✅ `SupSupersetClient.from_context(ctx)` works with self-hosted instance
2. ✅ `create_superset_auth()` properly called with instance config
3. ✅ OAuth2 tokens automatically refreshed during client use
4. ✅ All existing Preset tests pass
5. ✅ New self-hosted tests pass
6. ✅ Error messages guide users to correct next step

## Example Usage

```python
# Self-hosted path
ctx = SupContext()
ctx.project_state.current_instance_name = "superset-qa"
ctx.project_state.save_to_file()

client = SupSupersetClient.from_context(ctx)
datasets = client.get_datasets()

# Preset path (unchanged)
client = SupSupersetClient.from_context(ctx, workspace_id=123)
datasets = client.get_datasets()

# Override
client = SupSupersetClient.from_context(ctx, instance_name="production")
```
