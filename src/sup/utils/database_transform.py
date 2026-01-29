"""
Database UUID transformation utilities for cross-environment asset imports.

Enables assets exported from one environment to be imported to another
by automatically updating database UUID references to match target databases.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def get_target_databases(instance_url: str, auth: Any) -> Dict[str, str]:
    """
    Fetch all databases from target instance and return name->UUID mapping.

    Args:
        instance_url: Target Superset instance URL
        auth: Authentication handler

    Returns:
        Dict mapping database names to UUIDs (e.g., {"Trino": "abc-123-def"})
    """
    from preset_cli.api.clients.superset import SupersetClient

    superset_client = SupersetClient(instance_url, auth)

    # Fetch all databases from target
    databases = superset_client.get_databases()

    # Create name -> UUID mapping
    database_map = {}
    for db in databases:
        name = db.get("database_name")
        uuid = db.get("uuid")
        if name and uuid:
            database_map[name] = uuid

    return database_map


def transform_database_refs(
    assets_dir: str,
    instance_url: str,
    auth: Any,
    database_uuid: Optional[str] = None,
    database_name: Optional[str] = None,
    auto_map: bool = False,
) -> Optional[str]:
    """
    Create temporary copy of assets with transformed database UUIDs.

    Args:
        assets_dir: Source assets directory path
        instance_url: Target instance URL
        auth: Authentication handler
        database_uuid: Single UUID to use for all database references
        database_name: Database name to look up in target
        auto_map: Auto-map databases by matching names

    Returns:
        Path to temporary directory with transformed assets, or None if no transform
    """
    # No transformation requested
    if not database_uuid and not database_name and not auto_map:
        return None

    source_path = Path(assets_dir)
    if not source_path.exists():
        raise ValueError(f"Assets directory does not exist: {assets_dir}")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="superset_assets_")
    temp_path = Path(temp_dir)

    # Copy entire directory structure
    shutil.copytree(source_path, temp_path, dirs_exist_ok=True)

    # Build transformation mapping
    if database_uuid:
        # Replace all UUIDs with specified one
        _replace_all_database_uuids(temp_path, database_uuid)

    elif database_name:
        # Fetch target databases and find matching name
        target_dbs = get_target_databases(instance_url, auth)
        if database_name not in target_dbs:
            raise ValueError(f"Database '{database_name}' not found in target")
        target_uuid = target_dbs[database_name]
        _replace_all_database_uuids(temp_path, target_uuid)

    elif auto_map:
        # Auto-map by matching database names
        target_dbs = get_target_databases(instance_url, auth)
        _auto_map_database_uuids(temp_path, target_dbs)
        
        # Remove databases/ directory to prevent connection validation
        # When using bundle import, databases are referenced by UUID only
        databases_dir = temp_path / "databases"
        if databases_dir.exists():
            shutil.rmtree(databases_dir)

    return temp_dir


def _replace_all_database_uuids(assets_path: Path, target_uuid: str) -> None:
    """Replace all database_uuid references with target_uuid."""
    for yaml_file in assets_path.rglob("*.yaml"):
        try:
            _update_yaml_database_uuid(yaml_file, target_uuid)
        except Exception:
            # Skip files that can't be processed
            pass


def _auto_map_database_uuids(assets_path: Path, target_dbs: Dict[str, str]) -> None:
    """
    Auto-map database UUIDs by fetching database names from source assets
    and matching with target database names.
    
    Matches databases by name between source (from databases/ metadata) and target.
    Also updates the database config files themselves to have target UUIDs.
    """
    # First pass: collect all database UUIDs and their names from assets
    source_db_map = _collect_database_info_from_assets(assets_path)

    # Build UUID mapping: source UUID -> target UUID
    uuid_mapping = {}
    
    if source_db_map:
        # Have database metadata - map by name
        for source_uuid, db_name in source_db_map.items():
            if db_name in target_dbs:
                target_uuid = target_dbs[db_name]
                uuid_mapping[source_uuid] = target_uuid
    
    # Second pass: update all YAML files with mapping (datasets and charts)
    for yaml_file in assets_path.rglob("*.yaml"):
        # Skip database files - handle them separately
        if yaml_file.parent.name == "databases":
            continue
        try:
            _update_yaml_database_uuid_from_mapping(yaml_file, uuid_mapping)
        except Exception:
            pass
    
    # Third pass: update database config files to use target UUIDs
    # This allows them to be included in the import without password prompts
    databases_dir = assets_path / "databases"
    if databases_dir.exists():
        for db_file in databases_dir.glob("*.yaml"):
            try:
                with open(db_file) as f:
                    content = yaml.safe_load(f)
                
                if isinstance(content, dict):
                    db_name = content.get("database_name")
                    if db_name and db_name in target_dbs:
                        # Update UUID to match target
                        content["uuid"] = target_dbs[db_name]
                        
                        with open(db_file, "w") as f:
                            yaml.dump(content, f, default_flow_style=False, sort_keys=False)
            except Exception:
                pass


def _collect_database_info_from_assets(assets_path: Path) -> Dict[str, str]:
    """
    Collect database UUID -> name mapping from database YAML files.

    Returns:
        Dict mapping database UUIDs to names
    """
    db_info = {}

    # Look in databases subdirectory
    db_dir = assets_path / "databases"
    if db_dir.exists():
        for yaml_file in db_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    content = yaml.safe_load(f)

                if isinstance(content, dict):
                    uuid = content.get("uuid")
                    name = content.get("database_name")
                    if uuid and name:
                        db_info[uuid] = name
            except Exception:
                pass

    return db_info


def _update_yaml_database_uuid(yaml_file: Path, target_uuid: str) -> None:
    """Update database_uuid field in a YAML file."""
    with open(yaml_file) as f:
        content = yaml.safe_load(f)

    if not content or not isinstance(content, dict):
        return

    # Update database_uuid if present
    if "database_uuid" in content:
        content["database_uuid"] = target_uuid

        with open(yaml_file, "w") as f:
            yaml.dump(content, f, default_flow_style=False, sort_keys=False)


def _update_yaml_database_uuid_from_mapping(yaml_file: Path, mapping: Dict[str, str]) -> None:
    """Update database_uuid using provided UUID mapping."""
    with open(yaml_file) as f:
        content = yaml.safe_load(f)

    if not content or not isinstance(content, dict):
        return

    # Update database_uuid if it exists in mapping
    if "database_uuid" in content:
        old_uuid = content["database_uuid"]
        if old_uuid in mapping:
            content["database_uuid"] = mapping[old_uuid]

            with open(yaml_file, "w") as f:
                yaml.dump(content, f, default_flow_style=False, sort_keys=False)
