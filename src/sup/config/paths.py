"""
Configuration file paths and directory management for sup CLI.

Follows modern CLI conventions for configuration storage.
"""

import os
from pathlib import Path
from typing import Optional


def get_global_config_dir() -> Path:
    """Get the global configuration directory (~/.sup/)."""
    return Path.home() / ".sup"


def get_global_config_file() -> Path:
    """Get the global configuration file (~/.sup/config.yml)."""
    return get_global_config_dir() / "config.yml"


def get_project_config_dir() -> Path:
    """Get the project-specific configuration directory (.sup/)."""
    return Path.cwd() / ".sup"


def get_project_state_file() -> Path:
    """Get the project-specific state file (.sup/state.yml)."""
    return get_project_config_dir() / "state.yml"


def ensure_config_dir(config_dir: Path) -> None:
    """Ensure configuration directory exists."""
    config_dir.mkdir(parents=True, exist_ok=True)


def find_project_root() -> Optional[Path]:
    """
    Find the project root by looking for .sup directory.

    Walks up the directory tree from current working directory.
    """
    current_dir = Path.cwd()

    while current_dir != current_dir.parent:
        sup_dir = current_dir / ".sup"
        if sup_dir.exists() and sup_dir.is_dir():
            return current_dir
        current_dir = current_dir.parent

    return None


def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with SUP_ prefix."""
    return os.getenv(f"SUP_{name.upper()}", default)
