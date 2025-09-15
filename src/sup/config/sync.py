"""
Sync configuration models for sup CLI.

Defines the data structures for sync files that orchestrate multi-target
asset synchronization with Jinja templating support.
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, validator


class AssetSelection(BaseModel):
    """Configuration for selecting which assets to sync."""

    selection: Literal["all", "ids", "mine", "filter"] = Field(
        default="all",
        description="How to select assets: all, specific ids, mine, or by filter",
    )
    ids: Optional[List[int]] = Field(
        default=None,
        description="Specific asset IDs when selection='ids'",
    )
    include_dependencies: bool = Field(
        default=True,
        description="Whether to include related dependencies (datasets, databases)",
    )

    @validator("ids")
    def validate_ids_when_selection_ids(cls, v, values):
        """Ensure ids are provided when selection='ids'."""
        if values.get("selection") == "ids" and not v:
            raise ValueError("ids must be provided when selection='ids'")
        return v


class AssetTypes(BaseModel):
    """Configuration for different asset types to sync."""

    charts: Optional[AssetSelection] = Field(
        default=None,
        description="Chart selection configuration",
    )
    dashboards: Optional[AssetSelection] = Field(
        default=None,
        description="Dashboard selection configuration",
    )
    datasets: Optional[AssetSelection] = Field(
        default=None,
        description="Dataset selection configuration",
    )
    databases: Optional[AssetSelection] = Field(
        default=None,
        description="Database selection configuration",
    )

    @validator("charts", "dashboards", "datasets", "databases", pre=True)
    def convert_none_to_default(cls, v):
        """Convert None to default AssetSelection for convenience."""
        if v is None:
            return None
        if isinstance(v, dict):
            return AssetSelection(**v)
        return v


class SourceConfig(BaseModel):
    """Configuration for the source workspace to pull from."""

    workspace_id: int = Field(description="Source workspace ID to pull assets from")
    assets: AssetTypes = Field(description="Asset types and selection criteria")
    overwrite: bool = Field(
        default=True,
        description="Whether to overwrite existing files during pull",
    )


class TargetDefaults(BaseModel):
    """Default configuration that applies to all targets unless overridden."""

    overwrite: bool = Field(
        default=False,
        description="Default overwrite behavior for push operations",
    )
    include_dependencies: bool = Field(
        default=True,
        description="Default dependency inclusion behavior",
    )
    jinja_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default Jinja template variables",
    )


class TargetConfig(BaseModel):
    """Configuration for a specific target workspace."""

    workspace_id: int = Field(description="Target workspace ID to push assets to")
    name: Optional[str] = Field(default=None, description="Human-readable name for this target")
    overwrite: Optional[bool] = Field(
        default=None,
        description="Override default overwrite behavior (None = use defaults)",
    )
    jinja_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Target-specific Jinja template variables",
    )

    def get_effective_overwrite(self, defaults: TargetDefaults) -> bool:
        """Get the effective overwrite setting, considering defaults."""
        return self.overwrite if self.overwrite is not None else defaults.overwrite

    def get_effective_jinja_context(self, defaults: TargetDefaults) -> Dict[str, Any]:
        """Get the effective Jinja context, merging defaults with target-specific."""
        # Start with defaults, then overlay target-specific values
        context = defaults.jinja_context.copy()
        context.update(self.jinja_context)
        return context


class SyncConfig(BaseModel):
    """Complete sync configuration for multi-target asset synchronization."""

    source: SourceConfig = Field(description="Source workspace configuration")
    target_defaults: TargetDefaults = Field(
        default_factory=TargetDefaults,
        description="Default settings for all targets",
    )
    targets: List[TargetConfig] = Field(description="List of target workspace configurations")

    @validator("targets")
    def validate_targets_not_empty(cls, v):
        """Ensure at least one target is specified."""
        if not v:
            raise ValueError("At least one target must be specified")
        return v

    @validator("targets")
    def validate_unique_workspace_ids(cls, v):
        """Ensure target workspace IDs are unique."""
        workspace_ids = [target.workspace_id for target in v]
        if len(workspace_ids) != len(set(workspace_ids)):
            raise ValueError("Target workspace IDs must be unique")
        return v

    def get_target_by_name(self, name: str) -> Optional[TargetConfig]:
        """Get a target configuration by name."""
        for target in self.targets:
            if target.name == name:
                return target
        return None

    def get_target_by_workspace_id(self, workspace_id: int) -> Optional[TargetConfig]:
        """Get a target configuration by workspace ID."""
        for target in self.targets:
            if target.workspace_id == workspace_id:
                return target
        return None

    def sync_config_path(self, base_folder: Path) -> Path:
        """Get the path to the sync config file."""
        return base_folder / "sync_config.yml"

    def assets_folder(self, base_folder: Path) -> Path:
        """Get the path to the assets folder."""
        return base_folder / "assets"

    @classmethod
    def from_yaml(cls, file_path: Path) -> "SyncConfig":
        """Load sync configuration from a YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Sync config file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                raise ValueError("Sync config file is empty")

            return cls(**data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in sync config: {e}")
        except Exception as e:
            raise ValueError(f"Error loading sync config: {e}")

    def to_yaml(self, file_path: Path) -> None:
        """Save sync configuration to a YAML file."""
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and write YAML
        config_dict = self.dict(exclude_none=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    config_dict,
                    f,
                    default_flow_style=False,
                    indent=2,
                    sort_keys=False,  # Preserve field order
                )
        except Exception as e:
            raise RuntimeError(f"Error writing sync config: {e}")

    @classmethod
    def create_example(
        cls,
        source_workspace_id: int,
        target_workspace_ids: List[int],
    ) -> "SyncConfig":
        """Create an example sync configuration."""

        # Create targets with basic configuration
        targets = []
        for i, workspace_id in enumerate(target_workspace_ids):
            targets.append(
                TargetConfig(
                    workspace_id=workspace_id,
                    name=f"target_{i+1}",
                    jinja_context={
                        "environment": "production" if i == 0 else "staging",
                        "database_host": f"target-{i+1}.example.com",
                    },
                ),
            )

        return cls(
            source=SourceConfig(
                workspace_id=source_workspace_id,
                assets=AssetTypes(
                    charts=AssetSelection(selection="all", include_dependencies=True),
                    dashboards=AssetSelection(selection="all", include_dependencies=True),
                ),
            ),
            target_defaults=TargetDefaults(
                overwrite=False,
                jinja_context={"company": "Default Company", "region": "us-east-1"},
            ),
            targets=targets,
        )


def validate_sync_folder(folder_path: Path) -> bool:
    """Validate that a folder contains a valid sync configuration."""
    sync_config_path = folder_path / "sync_config.yml"

    if not sync_config_path.exists():
        return False

    try:
        SyncConfig.from_yaml(sync_config_path)
        return True
    except Exception:
        return False
