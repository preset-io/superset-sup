# Phase 1: Exact Code Changes

## File 1: `src/sup/config/settings.py`

### Change 1: Add field to SupProjectState

```python
# Around line 199, add to SupProjectState class:

class SupProjectState(BaseSettings):
    """Project-specific state stored in .sup/state.yml."""

    model_config = SettingsConfigDict(extra="ignore")

    # Current context
    current_workspace_id: Optional[int] = None
    current_workspace_url: Optional[str] = None
    current_workspace_hostname: Optional[str] = None
    current_database_id: Optional[int] = None
    current_team: Optional[str] = None
    
    # ADD THIS LINE:
    current_instance_name: Optional[str] = None  # Selected Superset instance (self-hosted)

    # Push target (only needed when pushing to different workspace than source)
    target_workspace_id: Optional[int] = None

    # ... rest of class unchanged ...
```

### Change 2: Add field to SupGlobalConfig

```python
# Around line 122, add to SupGlobalConfig class:

class SupGlobalConfig(BaseSettings):
    """Global configuration settings stored in ~/.sup/config.yml."""

    model_config = SettingsConfigDict(env_prefix="SUP_", extra="ignore")

    # Preset Authentication (Primary Focus)
    preset_api_token: Optional[str] = None
    preset_api_secret: Optional[str] = None

    # Superset Authentication (Extensible Design)
    superset_instances: Dict[str, SupersetInstanceConfig] = Field(default_factory=dict)

    # Global preferences
    output_format: OutputFormat = OutputFormat.table
    max_rows: int = 1000
    show_query_time: bool = True
    color_output: bool = True

    # ... existing fields ...

    # Current context (can be overridden by project state or env vars)
    current_workspace_id: Optional[int] = None
    current_database_id: Optional[int] = None
    
    # ADD THIS LINE:
    current_instance_name: Optional[str] = None  # Default Superset instance (self-hosted)

    # Push target (only needed when pushing to different workspace than source)
    target_workspace_id: Optional[int] = None

    # ... rest of class unchanged ...
```

### Change 3: Add methods to SupContext

```python
# Around line 247, in the SupContext class, add these new methods:

class SupContext:
    """Context manager combining global config, project state, and environment variables."""

    def __init__(self):
        self.global_config = SupGlobalConfig.load_from_file()
        self.project_state = SupProjectState.load_from_file()

    # ... existing methods (get_workspace_id, etc.) ...

    # ADD THESE NEW METHODS:

    def get_instance_name(self, cli_override: Optional[str] = None) -> Optional[str]:
        """Get current Superset instance name with proper precedence.
        
        Priority:
        1. CLI argument override
        2. Environment variable: SUP_INSTANCE_NAME
        3. Project state (.sup/state.yml)
        4. Global config (~/.sup/config.yml)
        
        Returns instance name or None if not configured.
        """
        env_instance_name = get_env_var("instance_name")
        return (
            cli_override
            or env_instance_name
            or self.project_state.current_instance_name
            or self.global_config.current_instance_name
        )

    def get_superset_instance_config(
        self, instance_name: Optional[str] = None
    ) -> Optional["SupersetInstanceConfig"]:
        """Get Superset instance configuration by name.
        
        Args:
            instance_name: Instance name to lookup. If None, uses current instance.
            
        Returns:
            SupersetInstanceConfig or None if not found.
        """
        name = instance_name or self.get_instance_name()
        if not name:
            return None
        return self.global_config.superset_instances.get(name)

    def has_superset_instances(self) -> bool:
        """Check if any Superset instances are configured."""
        return len(self.global_config.superset_instances) > 0

    def set_instance_context(self, instance_name: str, persist: bool = False) -> None:
        """Set current Superset instance.
        
        Args:
            instance_name: Instance name to select
            persist: If True, save to global config. If False, save to project state.
        """
        if persist:
            self.global_config.current_instance_name = instance_name
            self.global_config.save_to_file()
        else:
            self.project_state.current_instance_name = instance_name
            self.project_state.save_to_file()

    def get_all_instance_names(self) -> List[str]:
        """Get list of all configured instance names."""
        return list(self.global_config.superset_instances.keys())
```

---

## File 2: `src/sup/clients/superset.py`

### Replace the entire `from_context` method and add new helper methods

```python
# At the top of the file, add this import after existing imports:
from preset_cli.auth.factory import create_superset_auth

# Then, replace/refactor the SupSupersetClient class:

class SupSupersetClient:
    """
    Superset client wrapper with sup-specific functionality.
    
    Supports both:
    1. Preset workspaces (uses workspace_id + SupPresetAuth)
    2. Self-hosted Superset instances (uses instance_name + OAuthSupersetAuth/JWT/etc)
    """

    def __init__(self, workspace_url: str, auth):
        self.workspace_url = workspace_url
        self.auth = auth
        self.client = SupersetClient(workspace_url, auth)
        self.is_self_hosted = False  # Will be set by from_context

    @classmethod
    def from_context(
        cls,
        ctx,  # Type: SupContext
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
        3. Current instance from context (SUP_INSTANCE_NAME or .sup/state.yml)
        4. Current workspace from context (SUP_WORKSPACE_ID or .sup/state.yml)
        5. Error with helpful message
        
        Args:
            ctx: SupContext with configuration and state
            workspace_id: Preset workspace ID (legacy)
            instance_name: Self-hosted instance name
            
        Returns:
            SupSupersetClient configured for the workspace or instance
            
        Raises:
            ValueError: If neither workspace nor instance is configured
            
        Examples:
            # Use self-hosted instance
            client = SupSupersetClient.from_context(ctx, instance_name="prod")
            
            # Use Preset workspace
            client = SupSupersetClient.from_context(ctx, workspace_id=123)
            
            # Auto-detect from context
            client = SupSupersetClient.from_context(ctx)
        """
        # Determine which path to use
        
        # If instance_name explicitly provided, use self-hosted path
        if instance_name:
            return cls._from_instance(ctx, instance_name)
        
        # If workspace_id explicitly provided, use Preset path
        if workspace_id:
            return cls._from_preset_workspace(ctx, workspace_id)
        
        # Check context for instance (self-hosted)
        if ctx.get_instance_name():
            return cls._from_instance(ctx, ctx.get_instance_name())
        
        # Fall back to Preset path if workspace configured
        if ctx.get_workspace_id():
            return cls._from_preset_workspace(ctx, ctx.get_workspace_id())
        
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
        ctx,  # Type: SupContext
        instance_name: Optional[str] = None,
    ) -> "SupSupersetClient":
        """
        Create client for self-hosted Superset instance.
        
        Uses OAuth2/OIDC or other auth methods configured in superset_instances.
        """
        # Get instance name
        name = instance_name or ctx.get_instance_name()
        if not name:
            console.print(
                f"{EMOJIS['error']} No Superset instance configured",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup instance list[/] and [bold]sup instance use <NAME>[/]",
                style=RICH_STYLES["info"],
            )
            raise ValueError("No instance configured")
        
        # Get instance configuration
        instance_config = ctx.get_superset_instance_config(name)
        if not instance_config:
            console.print(
                f"{EMOJIS['error']} Instance '{name}' not found",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup instance list[/] to see available instances",
                style=RICH_STYLES["info"],
            )
            raise ValueError(f"Instance '{name}' not configured")
        
        # Create auth handler via factory (handles OAuth2, JWT, username/password)
        try:
            auth = create_superset_auth(instance_config)
        except ValueError as e:
            console.print(
                f"{EMOJIS['error']} Authentication configuration error:",
                style=RICH_STYLES["error"],
            )
            console.print(f"  {e}", style=RICH_STYLES["error"])
            raise
        
        # Create and return client
        client = cls(instance_config.url, auth)
        client.is_self_hosted = True
        return client

    @classmethod
    def _from_preset_workspace(
        cls,
        ctx,  # Type: SupContext
        workspace_id: Optional[int] = None,
    ) -> "SupSupersetClient":
        """
        Create client for Preset workspace.
        
        This is the existing implementation - kept unchanged for backward compatibility.
        """
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

        # Check if we have cached hostname for this specific workspace
        hostname = None
        current_workspace_id = ctx.get_workspace_id()
        if current_workspace_id == workspace_id:
            hostname = ctx.get_workspace_hostname()

        if not hostname:
            # No cached hostname, fetch from Preset API
            preset_client = SupPresetClient.from_context(ctx, silent=True)
            workspaces = preset_client.get_all_workspaces(silent=True)

            # Find our workspace
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

            # Cache the hostname for future use
            ctx.set_workspace_context(workspace_id, hostname=hostname)

        workspace_url = f"https://{hostname}/"

        auth = SupPresetAuth.from_sup_config(ctx, silent=True)
        client = cls(workspace_url, auth)
        client.is_self_hosted = False
        return client

    # ... rest of existing methods unchanged ...
```

---

## Testing

### Create `tests/clients/test_superset_self_hosted.py`

```python
"""Tests for self-hosted Superset client path."""

import pytest
from unittest.mock import MagicMock, patch
from yarl import URL

from sup.clients.superset import SupSupersetClient
from sup.config.settings import SupContext, SupersetInstanceConfig


@pytest.fixture
def context_with_instance():
    """Create a context with self-hosted instance configured."""
    ctx = MagicMock(spec=SupContext)
    instance_config = SupersetInstanceConfig(
        url="https://superset.example.com",
        auth_method="oauth",
        oauth_token_url="https://auth.example.com/oauth2/token",
        oauth_client_id="test-client",
        oauth_client_secret="test-secret",
        oauth_username="service@example.com",
        oauth_password="password",
    )
    
    ctx.get_instance_name.return_value = "test-instance"
    ctx.get_workspace_id.return_value = None
    ctx.get_superset_instance_config.return_value = instance_config
    
    return ctx


def test_from_context_with_instance_name(context_with_instance):
    """Test from_context uses instance when provided."""
    with patch("sup.clients.superset.create_superset_auth") as mock_auth:
        mock_auth.return_value = MagicMock()
        
        client = SupSupersetClient.from_context(
            context_with_instance,
            instance_name="test-instance",
        )
        
        assert client.is_self_hosted is True
        assert client.workspace_url == "https://superset.example.com"


def test_from_context_falls_back_to_workspace(context_with_instance):
    """Test from_context falls back to workspace if no instance."""
    context_with_instance.get_instance_name.return_value = None
    context_with_instance.get_workspace_id.return_value = 123
    
    with patch.object(
        SupSupersetClient, "_from_preset_workspace"
    ) as mock_preset:
        mock_preset.return_value = MagicMock(is_self_hosted=False)
        
        SupSupersetClient.from_context(context_with_instance)
        
        mock_preset.assert_called_once()


def test_from_context_no_config_raises_error(context_with_instance):
    """Test from_context raises helpful error when nothing configured."""
    context_with_instance.get_instance_name.return_value = None
    context_with_instance.get_workspace_id.return_value = None
    
    with pytest.raises(ValueError) as exc_info:
        SupSupersetClient.from_context(context_with_instance)
    
    assert "instance" in str(exc_info.value).lower()
    assert "workspace" in str(exc_info.value).lower()


def test_from_instance_missing_config(context_with_instance):
    """Test _from_instance raises error if instance not found."""
    context_with_instance.get_superset_instance_config.return_value = None
    
    with pytest.raises(ValueError) as exc_info:
        SupSupersetClient._from_instance(context_with_instance, "missing")
    
    assert "missing" in str(exc_info.value).lower()
```

---

## Summary of Changes

| File | Lines | Changes |
|------|-------|---------|
| `settings.py` | +40 | Add instance tracking fields + 4 methods |
| `superset.py` | +180 | Refactor from_context + add 2 helpers |
| `test_superset_self_hosted.py` | +90 | NEW - Unit tests |
| **Total** | **+310** | **Core Phase 1** |

## Next: Integration Testing

Once Phase 1 code is in, test against real environment:

```bash
# 1. Set up config
export SUPERSET_OAUTH_CLIENT_SECRET="<secret>"
export SUPERSET_OAUTH_SERVICE_PASSWORD="<password>"

# 2. Create instance in config
sup config set instance-name superset-qa  # TODO: implement in Phase 2

# 3. Test client creation
python -c "
from sup.config.settings import SupContext
from sup.clients.superset import SupSupersetClient

ctx = SupContext()
ctx.set_instance_context('superset-qa')

client = SupSupersetClient.from_context(ctx)
datasets = client.get_datasets()
print(f'Found {len(datasets)} datasets')
"
```

If all datasets print successfully, Phase 1 is complete! ✅
