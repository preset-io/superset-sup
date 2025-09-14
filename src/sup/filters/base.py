"""
Universal filtering system for sup CLI.

Provides cohesive filtering across all entity types with consistent patterns.
"""

import fnmatch
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class UniversalFilters:
    """Universal filters that apply to all entity types."""

    # Identity filters
    id: Optional[int] = None
    ids: Optional[List[int]] = None
    name: Optional[str] = None
    mine: bool = False
    team_id: Optional[int] = None

    # Date filters
    created_after: Optional[datetime] = None
    modified_after: Optional[datetime] = None

    # Pagination
    limit: Optional[int] = 50  # Default limit for responsive UX
    offset: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None

    # Ordering
    order: Optional[str] = None
    desc: bool = False

    def copy(self, **updates) -> "UniversalFilters":
        """Create a copy of filters with optional updates."""
        # Only include valid UniversalFilters fields from updates
        valid_fields = {
            "id",
            "ids",
            "name",
            "mine",
            "team_id",
            "created_after",
            "modified_after",
            "limit",
            "offset",
            "page",
            "page_size",
            "order",
            "desc",
        }

        # Only update with valid fields
        filtered_updates = {k: v for k, v in updates.items() if k in valid_fields}

        # Create new instance with current values updated
        return UniversalFilters(
            id=filtered_updates.get("id", self.id),
            ids=filtered_updates.get("ids", self.ids),
            name=filtered_updates.get("name", self.name),
            mine=filtered_updates.get("mine", self.mine),
            team_id=filtered_updates.get("team_id", self.team_id),
            created_after=filtered_updates.get("created_after", self.created_after),
            modified_after=filtered_updates.get("modified_after", self.modified_after),
            limit=filtered_updates.get("limit", self.limit),
            offset=filtered_updates.get("offset", self.offset),
            page=filtered_updates.get("page", self.page),
            page_size=filtered_updates.get("page_size", self.page_size),
            order=filtered_updates.get("order", self.order),
            desc=filtered_updates.get("desc", self.desc),
        )

    @classmethod
    def parse_ids(cls, ids_str: str) -> List[int]:
        """Parse comma-separated IDs string into list of integers."""
        if not ids_str:
            return []
        try:
            return [int(id_str.strip()) for id_str in ids_str.split(",")]
        except ValueError as e:
            raise ValueError(f"Invalid ID format: {ids_str}") from e

    @classmethod
    def parse_date(cls, date_str: str) -> datetime:
        """Parse date string in YYYY-MM-DD format."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format (use YYYY-MM-DD): {date_str}") from e


def apply_universal_filters(
    items: List[Dict[str, Any]],
    filters: UniversalFilters,
    current_user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Apply universal filters to a list of items.

    Args:
        items: List of entity dictionaries from API
        filters: UniversalFilters instance
        current_user_id: Current user ID for --mine filter

    Returns:
        Filtered list of items
    """
    filtered_items = items

    # ID filters
    if filters.id is not None:
        filtered_items = [item for item in filtered_items if item.get("id") == filters.id]

    if filters.ids:
        filtered_items = [item for item in filtered_items if item.get("id") in filters.ids]

    # Name pattern matching
    if filters.name:
        pattern = filters.name.lower()
        filtered_items = [
            item
            for item in filtered_items
            if fnmatch.fnmatch(
                (
                    item.get("name") or item.get("table_name") or item.get("slice_name") or ""
                ).lower(),
                pattern,
            )
        ]

    # Mine filter - objects owned by current user
    if filters.mine and current_user_id is not None:
        filtered_items = [
            item
            for item in filtered_items
            if item.get("created_by_fk") == current_user_id
            or item.get("changed_by_fk") == current_user_id
            or item.get("owner_id") == current_user_id
        ]

    # Team filter
    if filters.team_id:
        filtered_items = [item for item in filtered_items if item.get("team_id") == filters.team_id]

    # Date filters
    if filters.created_after:
        filtered_items = [
            item
            for item in filtered_items
            if item.get("created_on")
            and datetime.fromisoformat(item["created_on"].replace("Z", "+00:00"))
            >= filters.created_after
        ]

    if filters.modified_after:
        filtered_items = [
            item
            for item in filtered_items
            if item.get("changed_on")
            and datetime.fromisoformat(item["changed_on"].replace("Z", "+00:00"))
            >= filters.modified_after
        ]

    # Pagination
    if filters.offset:
        filtered_items = filtered_items[filters.offset :]

    if filters.limit:
        filtered_items = filtered_items[: filters.limit]

    return filtered_items


# Typer option generators for consistent CLI interface
def get_universal_filter_options():
    """Get Typer options for universal filters - DRY for all commands."""
    import typer
    from typing_extensions import Annotated

    return {
        "id_filter": Annotated[
            Optional[int],
            typer.Option("--id", help="Filter by specific ID"),
        ],
        "ids_filter": Annotated[
            Optional[str],
            typer.Option("--ids", help="Filter by multiple IDs (comma-separated)"),
        ],
        "name_filter": Annotated[
            Optional[str],
            typer.Option("--name", help="Filter by name pattern (supports wildcards)"),
        ],
        "mine_filter": Annotated[
            bool,
            typer.Option("--mine", help="Show only objects you own"),
        ],
        "team_filter": Annotated[
            Optional[int],
            typer.Option("--team", help="Filter by team ID"),
        ],
        "created_after": Annotated[
            Optional[str],
            typer.Option(
                "--created-after",
                help="Show objects created after date (YYYY-MM-DD)",
            ),
        ],
        "modified_after": Annotated[
            Optional[str],
            typer.Option(
                "--modified-after",
                help="Show objects modified after date (YYYY-MM-DD)",
            ),
        ],
        "limit_filter": Annotated[
            Optional[int],
            typer.Option(
                "--limit",
                "-l",
                help="Maximum number of results (default: 50, use 0 for unlimited)",
            ),
        ],
        "offset_filter": Annotated[
            Optional[int],
            typer.Option("--offset", help="Skip first n results"),
        ],
        "page_filter": Annotated[
            Optional[int],
            typer.Option("--page", help="Page number (alternative to offset)"),
        ],
        "page_size_filter": Annotated[
            Optional[int],
            typer.Option("--page-size", help="Results per page (default: 100)"),
        ],
        "order_filter": Annotated[
            Optional[str],
            typer.Option("--order", help="Sort by field (name, created, modified, id)"),
        ],
        "desc_filter": Annotated[
            bool,
            typer.Option("--desc", help="Sort descending (default: ascending)"),
        ],
    }


def parse_universal_filters(
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
) -> UniversalFilters:
    """Parse filter arguments into UniversalFilters object."""

    # Parse IDs if provided
    ids_list = None
    if ids_filter:
        ids_list = UniversalFilters.parse_ids(ids_filter)

    # Parse dates if provided
    created_after_dt = None
    if created_after:
        created_after_dt = UniversalFilters.parse_date(created_after)

    modified_after_dt = None
    if modified_after:
        modified_after_dt = UniversalFilters.parse_date(modified_after)

    # Handle special case: limit=0 means unlimited
    final_limit = None if limit_filter == 0 else (limit_filter if limit_filter is not None else 50)

    return UniversalFilters(
        id=id_filter,
        ids=ids_list,
        name=name_filter,
        mine=mine_filter,
        team_id=team_filter,
        created_after=created_after_dt,
        modified_after=modified_after_dt,
        limit=final_limit,
        offset=offset_filter,
        page=page_filter,
        page_size=page_size_filter,
        order=order_filter,
        desc=desc_filter,
    )
