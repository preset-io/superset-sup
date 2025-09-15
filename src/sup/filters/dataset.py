"""
Dataset-specific filtering for sup CLI.

Extends universal filters with dataset-specific options.
"""

import fnmatch
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sup.filters.base import UniversalFilters, apply_universal_filters


@dataclass
class DatasetFilters(UniversalFilters):
    """Dataset-specific filters extending universal filters."""

    # Dataset-specific filters
    database_id: Optional[int] = None
    schema: Optional[str] = None
    table_type: Optional[str] = None  # table, view, etc.


def apply_dataset_filters(
    datasets: List[Dict[str, Any]],
    filters: DatasetFilters,
    current_user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Apply dataset-specific filters after universal filters.

    Args:
        datasets: List of dataset dictionaries from API
        filters: DatasetFilters instance
        current_user_id: Current user ID for --mine filter

    Returns:
        Filtered list of datasets
    """
    # Apply universal filters first
    filtered_datasets = apply_universal_filters(datasets, filters, current_user_id)

    # Apply dataset-specific filters
    if filters.database_id:
        filtered_datasets = [
            item
            for item in filtered_datasets
            if item.get("database", {}).get("id") == filters.database_id
        ]

    if filters.schema:
        schema_pattern = filters.schema.lower()
        filtered_datasets = [
            item
            for item in filtered_datasets
            if item.get("schema") and fnmatch.fnmatch(item["schema"].lower(), schema_pattern)
        ]

    if filters.table_type:
        filtered_datasets = [
            item
            for item in filtered_datasets
            if item.get("table_name")
            and filters.table_type.lower() in str(item.get("sql", "")).lower()
        ]

    return filtered_datasets


def get_dataset_filter_options():
    """Get Typer options for dataset-specific filters."""
    import typer
    from typing_extensions import Annotated

    return {
        "database_id": Annotated[
            Optional[int],
            typer.Option("--database-id", help="Filter by database ID"),
        ],
        "schema": Annotated[
            Optional[str],
            typer.Option("--schema", help="Filter by schema name pattern"),
        ],
        "table_type": Annotated[
            Optional[str],
            typer.Option(
                "--table-type",
                help="Filter by table type (table, view, etc.)",
            ),
        ],
    }


def parse_dataset_filters(
    # Universal filters
    id_filter: Optional[int] = None,
    ids_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    mine_filter: bool = False,
    team_filter: Optional[int] = None,
    created_after: Optional[str] = None,
    modified_after: Optional[str] = None,
    limit_filter: Optional[int] = None,
    offset_filter: Optional[int] = None,
    page_filter: Optional[int] = None,
    page_size_filter: Optional[int] = None,
    order_filter: Optional[str] = None,
    desc_filter: bool = False,
    # Dataset-specific filters
    database_id: Optional[int] = None,
    schema: Optional[str] = None,
    table_type: Optional[str] = None,
) -> DatasetFilters:
    """Parse all filter arguments into DatasetFilters object."""
    from sup.filters.base import parse_universal_filters

    # Get universal filters first
    universal = parse_universal_filters(
        id_filter=id_filter,
        ids_filter=ids_filter,
        name_filter=name_filter,
        search_filter=None,  # Dataset uses name_filter, not search_filter
        mine_filter=mine_filter,
        team_filter=team_filter,
        created_after=created_after,
        modified_after=modified_after,
        limit_filter=limit_filter,
        offset_filter=offset_filter,
        page_filter=page_filter,
        page_size_filter=page_size_filter,
        order_filter=order_filter,
        desc_filter=desc_filter,
    )

    # Add dataset-specific filters
    return DatasetFilters(
        # Universal filters
        id=universal.id,
        ids=universal.ids,
        name=universal.name,
        mine=universal.mine,
        team_id=universal.team_id,
        created_after=universal.created_after,
        modified_after=universal.modified_after,
        limit=universal.limit,
        offset=universal.offset,
        page=universal.page,
        page_size=universal.page_size,
        order=universal.order,
        desc=universal.desc,
        # Dataset-specific
        database_id=database_id,
        schema=schema,
        table_type=table_type,
    )
