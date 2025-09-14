"""
Dashboard-specific filtering logic for sup CLI.

Extends universal filtering with dashboard-specific filters.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sup.filters.base import UniversalFilters, apply_universal_filters


@dataclass
class DashboardFilters(UniversalFilters):
    """Dashboard-specific filters extending universal filters."""

    # Dashboard-specific filters
    published: Optional[bool] = None  # Only published dashboards
    draft: Optional[bool] = None  # Only draft dashboards
    folder: Optional[str] = None  # Filter by folder path
    roles: Optional[List[str]] = None  # Filter by assigned roles


def parse_dashboard_filters(
    # Universal filter parameters (same as other entities)
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
    # Dashboard-specific filter parameters
    published: Optional[bool] = None,
    draft: Optional[bool] = None,
    folder: Optional[str] = None,
    roles_filter: Optional[str] = None,
) -> DashboardFilters:
    """Parse command line arguments into DashboardFilters object."""
    from sup.filters.base import parse_universal_filters

    # Parse universal filters first
    universal = parse_universal_filters(
        id_filter=id_filter,
        ids_filter=ids_filter,
        name_filter=name_filter,
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

    # Parse roles if provided
    roles_list = None
    if roles_filter:
        roles_list = [role.strip() for role in roles_filter.split(",")]

    # Create dashboard-specific filters
    return DashboardFilters(
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
        # Dashboard-specific filters
        published=published,
        draft=draft,
        folder=folder,
        roles=roles_list,
    )


def apply_dashboard_filters(
    dashboards: List[Dict[str, Any]],
    filters: DashboardFilters,
    current_user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Apply dashboard-specific filters to a list of dashboards."""

    # Apply universal filters first
    filtered_dashboards = apply_universal_filters(dashboards, filters, current_user_id)

    # Apply dashboard-specific filters
    if filters.published is not None:
        filtered_dashboards = [
            dashboard
            for dashboard in filtered_dashboards
            if dashboard.get("published") == filters.published
        ]

    if filters.draft is not None:
        # Draft is typically the opposite of published
        filtered_dashboards = [
            dashboard
            for dashboard in filtered_dashboards
            if (not dashboard.get("published", False)) == filters.draft
        ]

    if filters.folder:
        # Filter by dashboard folder/path (pattern matching)
        import fnmatch

        pattern = filters.folder.lower()
        filtered_dashboards = [
            dashboard
            for dashboard in filtered_dashboards
            if fnmatch.fnmatch((dashboard.get("folder_path") or "").lower(), pattern)
        ]

    if filters.roles:
        # Filter by assigned roles (if dashboard has roles info)
        filtered_dashboards = [
            dashboard
            for dashboard in filtered_dashboards
            if any(role in filters.roles for role in dashboard.get("roles", []))
        ]

    return filtered_dashboards
