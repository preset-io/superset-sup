"""
Pydantic configuration models for sup CLI.

Type-safe configuration management with YAML support.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sup.config.paths import (
    ensure_config_dir,
    get_env_var,
    get_global_config_file,
    get_project_state_file,
)


class OutputFormat(str, Enum):
    """Available output formats for sup commands."""

    table = "table"
    json = "json"
    csv = "csv"
    yaml = "yaml"


class SyncMode(str, Enum):
    """Asset synchronization modes."""

    export_only = "export_only"
    import_only = "import_only"
    bidirectional = "bidirectional"


class OutputOptions(BaseModel):
    """Output format options for commands."""

    model_config = ConfigDict(extra="forbid")

    json_output: bool = False
    yaml_output: bool = False
    porcelain: bool = False
    workspace_id: Optional[int] = None

    @property
    def format(self) -> OutputFormat:
        """Get the primary output format."""
        if self.porcelain:
            return OutputFormat.table  # Porcelain is still tabular, just plain
        elif self.json_output:
            return OutputFormat.json
        elif self.yaml_output:
            return OutputFormat.yaml
        else:
            return OutputFormat.table


class SupersetInstanceConfig(BaseModel):
    """Configuration for a Superset instance."""

    model_config = ConfigDict(extra="forbid")

    url: str
    auth_method: str = Field(
        default="username_password",
        description="Authentication method: username_password, jwt, or oauth",
        pattern="^(username_password|jwt|oauth)$",
    )

    # Username/password authentication (basic Superset auth)
    username: Optional[str] = Field(
        default=None,
        description="Username for Superset username/password authentication",
    )
    password: Optional[str] = Field(
        default=None,
        description="Password for Superset username/password authentication",
    )

    # JWT token authentication
    jwt_token: Optional[str] = Field(
        default=None,
        description="Pre-generated JWT token for Superset JWT authentication",
    )

    # OAuth2/OIDC authentication (NEW)
    oauth_token_url: Optional[str] = Field(
        default=None,
        description="OAuth2 token endpoint URL (e.g., https://auth.example.com/oauth2/token)",
    )
    oauth_client_id: Optional[str] = Field(
        default=None,
        description="OAuth2 client ID registered with OIDC provider",
    )
    oauth_client_secret: Optional[str] = Field(
        default=None,
        description="OAuth2 client secret. Use environment variables: ${ENV:SUPERSET_OAUTH_SECRET}",
    )
    oauth_username: Optional[str] = Field(
        default=None,
        description="Service account username for OAuth2 resource owner password grant",
    )
    oauth_password: Optional[str] = Field(
        default=None,
        description="Service account password. Use environment variables: ${ENV:SERVICE_PASSWORD}",
    )
    oauth_scope: str = Field(
        default="openid profile email roles",
        description="OAuth2 scopes to request (space-separated)",
    )
    oauth_token_type: str = Field(
        default="Bearer",
        description="Token type in Authorization header (usually Bearer)",
    )


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
    color_output: bool = True  # Set to False for monochrome output

    @property
    def monochrome(self) -> bool:
        """Alias for !color_output (monochrome mode)."""
        return not self.color_output

    def set_monochrome(self, enabled: bool) -> None:
        """Set monochrome mode (inverts color_output)."""
        self.color_output = not enabled

    # Asset management
    assets_folder: str = "./assets"  # Global default for asset operations

    # Current context (can be overridden by project state or env vars)
    current_workspace_id: Optional[int] = None
    current_database_id: Optional[int] = None

    # Push target (only needed when pushing to different workspace than source)
    target_workspace_id: Optional[int] = None

    @classmethod
    def load_from_file(cls) -> "SupGlobalConfig":
        """Load global configuration from ~/.sup/config.yml."""
        config_file = get_global_config_file()

        if not config_file.exists():
            return cls()

        try:
            with open(config_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            # If config is corrupted, return default config
            print(f"Warning: Could not load config from {config_file}: {e}")
            return cls()

    def save_to_file(self) -> None:
        """Save global configuration to ~/.sup/config.yml."""
        config_file = get_global_config_file()
        ensure_config_dir(config_file.parent)

        # Convert to dict and remove None values for cleaner YAML
        data = self.model_dump(exclude_none=True, exclude_defaults=True)

        with open(config_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, indent=2)


class SupProjectState(BaseSettings):
    """Project-specific state stored in .sup/state.yml."""

    model_config = SettingsConfigDict(extra="ignore")

    # Current context
    current_workspace_id: Optional[int] = None
    current_workspace_url: Optional[str] = None
    current_workspace_hostname: Optional[str] = None  # Cache hostname for efficiency
    current_database_id: Optional[int] = None
    current_team: Optional[str] = None

    # Push target (only needed when pushing to different workspace than source)
    target_workspace_id: Optional[int] = None

    # Asset sync settings
    assets_folder: str = "./assets"
    sync_mode: SyncMode = SyncMode.bidirectional
    last_sync: Optional[datetime] = None

    @classmethod
    def load_from_file(cls) -> "SupProjectState":
        """Load project state from .sup/state.yml."""
        state_file = get_project_state_file()

        if not state_file.exists():
            return cls()

        try:
            with open(state_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            print(f"Warning: Could not load project state from {state_file}: {e}")
            return cls()

    def save_to_file(self) -> None:
        """Save project state to .sup/state.yml."""
        state_file = get_project_state_file()
        ensure_config_dir(state_file.parent)

        # Convert to dict and remove None values
        data = self.model_dump(exclude_none=True, exclude_defaults=True)

        with open(state_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, indent=2)


class SupContext:
    """
    Context manager that combines global config, project state, and environment variables.

    Provides a unified interface for accessing configuration with proper precedence:
    1. CLI arguments (handled by commands)
    2. Environment variables (SUP_*)
    3. Project state (.sup/state.yml)
    4. Global config (~/.sup/config.yml)
    """

    def __init__(self):
        self.global_config = SupGlobalConfig.load_from_file()
        self.project_state = SupProjectState.load_from_file()

    def get_workspace_id(self, cli_override: Optional[int] = None) -> Optional[int]:
        """Get workspace ID with proper precedence."""
        env_workspace_id = get_env_var("workspace_id")
        return (
            cli_override
            or (int(env_workspace_id) if env_workspace_id is not None else None)
            or self.project_state.current_workspace_id
            or self.global_config.current_workspace_id
        )

    def get_database_id(self, cli_override: Optional[int] = None) -> Optional[int]:
        """Get database ID with proper precedence."""
        env_database_id = get_env_var("database_id")
        return (
            cli_override
            or (int(env_database_id) if env_database_id is not None else None)
            or self.project_state.current_database_id
            or self.global_config.current_database_id
        )

    def get_preset_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Preset API credentials."""
        token = get_env_var("preset_api_token") or self.global_config.preset_api_token
        secret = get_env_var("preset_api_secret") or self.global_config.preset_api_secret
        return token, secret

    def get_output_format(
        self,
        cli_override: Optional[OutputFormat] = None,
    ) -> OutputFormat:
        """Get output format preference."""
        if cli_override:
            return cli_override

        env_format = get_env_var("output_format")
        if env_format:
            try:
                return OutputFormat(env_format)
            except ValueError:
                pass

        return self.global_config.output_format

    def get_workspace_hostname(self) -> Optional[str]:
        """Get cached workspace hostname."""
        return self.project_state.current_workspace_hostname

    def get_assets_folder(self, cli_override: Optional[str] = None) -> str:
        """Get assets folder with proper precedence."""
        env_assets_folder = get_env_var("assets_folder")
        return (
            cli_override
            or env_assets_folder
            or self.project_state.assets_folder
            or self.global_config.assets_folder
        )

    def set_workspace_context(
        self,
        workspace_id: int,
        hostname: Optional[str] = None,
        persist: bool = False,
    ) -> None:
        """Set workspace context with optional hostname caching."""
        if persist:
            self.global_config.current_workspace_id = workspace_id
            self.global_config.save_to_file()
        else:
            self.project_state.current_workspace_id = workspace_id
            if hostname:
                self.project_state.current_workspace_hostname = hostname
            self.project_state.save_to_file()

    def set_database_context(self, database_id: int, persist: bool = False) -> None:
        """Set database context."""
        if persist:
            self.global_config.current_database_id = database_id
            self.global_config.save_to_file()
        else:
            self.project_state.current_database_id = database_id
            self.project_state.save_to_file()

    def get_target_workspace_id(self, cli_override: Optional[int] = None) -> Optional[int]:
        """
        Get import target workspace ID with proper precedence.

        Returns None if no explicit target is configured - imports should be blocked
        unless user explicitly sets target or uses --workspace-id override.
        """
        env_import_target = get_env_var("target_workspace_id")
        return (
            cli_override
            or (int(env_import_target) if env_import_target is not None else None)
            or self.project_state.target_workspace_id
            or self.global_config.target_workspace_id
            # NO fallback to main workspace - force explicit configuration
        )

    def set_target_workspace_id(self, workspace_id: int, persist: bool = False) -> None:
        """
        Set import target workspace for cross-workspace operations.

        Only needed when you want imports to go to different workspace than exports.
        """
        if persist:
            self.global_config.target_workspace_id = workspace_id
            self.global_config.save_to_file()
        else:
            self.project_state.target_workspace_id = workspace_id
            self.project_state.save_to_file()
