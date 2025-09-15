"""
Chart-specific filtering for sup CLI.

Extends universal filters with chart-specific options.
"""

import fnmatch
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sup.filters.base import UniversalFilters, apply_universal_filters


@dataclass
class ChartFilters(UniversalFilters):
    """Chart-specific filters extending universal filters."""

    # Chart-specific filters
    dashboard_id: Optional[int] = None
    viz_type: Optional[str] = None
    dataset_id: Optional[int] = None


def apply_chart_filters(
    charts: List[Dict[str, Any]],
    filters: ChartFilters,
    current_user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Apply chart-specific filters after universal filters.

    Args:
        charts: List of chart dictionaries from API
        filters: ChartFilters instance
        current_user_id: Current user ID for --mine filter

    Returns:
        Filtered list of charts
    """
    # Apply universal filters first
    filtered_charts = apply_universal_filters(charts, filters, current_user_id)

    # Apply chart-specific filters
    if filters.dashboard_id:
        filtered_charts = [
            item
            for item in filtered_charts
            # Charts can be in multiple dashboards, check if our dashboard_id is in the list
            if filters.dashboard_id in (item.get("dashboards") or [])
        ]

    if filters.viz_type:
        viz_pattern = filters.viz_type.lower()
        filtered_charts = [
            item
            for item in filtered_charts
            if item.get("viz_type") and fnmatch.fnmatch(item["viz_type"].lower(), viz_pattern)
        ]

    if filters.dataset_id:
        filtered_charts = [
            item for item in filtered_charts if item.get("datasource_id") == filters.dataset_id
        ]

    return filtered_charts


def parse_chart_filters(
    # Universal filters
    id_filter: Optional[int] = None,
    ids_filter: Optional[str] = None,
    search_filter: Optional[str] = None,
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
    # Chart-specific filters
    dashboard_id: Optional[int] = None,
    viz_type: Optional[str] = None,
    dataset_id: Optional[int] = None,
) -> ChartFilters:
    """Parse all filter arguments into ChartFilters object."""
    from sup.filters.base import parse_universal_filters

    # Get universal filters first
    universal = parse_universal_filters(
        id_filter,
        ids_filter,
        name_filter=None,  # Chart command doesn't use legacy name patterns
        search_filter=search_filter,  # Chart command uses server-side search
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

    # Add chart-specific filters
    return ChartFilters(
        # Universal filters
        id=universal.id,
        ids=universal.ids,
        name=universal.name,
        search=universal.search,
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
        # Chart-specific
        dashboard_id=dashboard_id,
        viz_type=viz_type,
        dataset_id=dataset_id,
    )
