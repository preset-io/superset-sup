"""
Server-side API parameter building for efficient filtering.

Converts sup filter objects into Superset API parameters.
"""

from typing import Any, Dict

from sup.filters.base import UniversalFilters


def build_api_params(filters: UniversalFilters, entity_type: str) -> Dict[str, Any]:
    """
    Build API parameters that align with Superset's get_resources method.

    Args:
        filters: Universal filter object
        entity_type: "chart", "dataset", "dashboard", etc.

    Returns:
        Dictionary of API parameters for server-side filtering
    """
    api_params = {}

    # Pagination (always use for performance)
    page_size = filters.limit if filters.limit else 50
    api_params["page_size"] = page_size

    if filters.page:
        api_params["page"] = filters.page - 1  # API uses 0-based pages
    elif filters.offset:
        api_params["page"] = filters.offset // page_size

    # Ordering (API format with entity-specific field mappings)
    if filters.order:
        order_mapping = {
            "chart": {
                "name": "slice_name",
                "created": "created_on",
                "modified": "changed_on",
                "id": "id",
            },
            "dataset": {
                "name": "table_name",
                "created": "created_on",
                "modified": "changed_on",
                "id": "id",
            },
            "dashboard": {
                "name": "dashboard_title",
                "created": "created_on",
                "modified": "changed_on",
                "id": "id",
            },
            "database": {
                "name": "database_name",
                "created": "created_on",
                "modified": "changed_on",
                "id": "id",
            },
        }
        field_map = order_mapping.get(entity_type, {})
        api_params["order_column"] = field_map.get(filters.order, filters.order)
        api_params["order_direction"] = "desc" if filters.desc else "asc"
    else:
        # Default ordering by modification date (most recent first)
        api_params["order_column"] = "changed_on"
        api_params["order_direction"] = "desc"

    return api_params


def needs_client_side_filtering(filters: UniversalFilters) -> bool:
    """
    Check if we need client-side filtering for complex operations.

    Server-side filtering handles: pagination, ordering, basic field matches
    Client-side needed for: pattern matching, mine filter, complex logic
    """
    return bool(
        filters.name
        or filters.mine  # Pattern matching with wildcards
        or filters.created_after  # Complex owner logic across multiple fields
        or filters.modified_after,  # Date parsing and comparison  # Date parsing and comparison
    )
