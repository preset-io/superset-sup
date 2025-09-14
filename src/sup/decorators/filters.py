"""
Filter decorators for sup CLI commands.

Provides decorators to automatically add universal and entity-specific filter parameters
to commands, eliminating the massive parameter duplication across entity commands.
"""

import functools
from typing import Any, Callable, Optional

import typer
from typing_extensions import Annotated


def with_universal_filters(func: Callable) -> Callable:
    """
    Decorator that adds all universal filter parameters to a command.

    This eliminates the need to manually specify the same 13+ parameters
    in every list command across all entity types.

    The decorated function will receive a `filters` parameter containing
    a UniversalFilters object with all the parsed filter values.
    """

    @functools.wraps(func)
    def wrapper(
        # Universal filters - consistent across ALL entities
        id_filter: Annotated[
            Optional[int],
            typer.Option("--id", help="Filter by specific ID"),
        ] = None,
        ids_filter: Annotated[
            Optional[str],
            typer.Option("--ids", help="Filter by multiple IDs (comma-separated)"),
        ] = None,
        name_filter: Annotated[
            Optional[str],
            typer.Option("--name", help="Filter by name pattern (supports wildcards)"),
        ] = None,
        mine_filter: Annotated[
            bool,
            typer.Option("--mine", "-m", help="Show only items you own"),
        ] = False,
        team_filter: Annotated[
            Optional[int],
            typer.Option("--team", help="Filter by team ID"),
        ] = None,
        created_after: Annotated[
            Optional[str],
            typer.Option(
                "--created-after",
                help="Show items created after date (YYYY-MM-DD)",
            ),
        ] = None,
        modified_after: Annotated[
            Optional[str],
            typer.Option(
                "--modified-after",
                help="Show items modified after date (YYYY-MM-DD)",
            ),
        ] = None,
        limit_filter: Annotated[
            Optional[int],
            typer.Option("--limit", "-l", help="Maximum number of results"),
        ] = None,
        offset_filter: Annotated[
            Optional[int],
            typer.Option("--offset", help="Skip first n results"),
        ] = None,
        page_filter: Annotated[
            Optional[int],
            typer.Option("--page", help="Page number (alternative to offset)"),
        ] = None,
        page_size_filter: Annotated[
            Optional[int],
            typer.Option("--page-size", help="Results per page (default: 100)"),
        ] = None,
        order_filter: Annotated[
            Optional[str],
            typer.Option("--order", help="Sort by field (name, created, modified, id)"),
        ] = None,
        desc_filter: Annotated[
            bool,
            typer.Option("--desc", help="Sort descending (default: ascending)"),
        ] = False,
        **kwargs: Any,
    ) -> Any:
        # Parse filters using the proper function
        from sup.filters.base import parse_universal_filters

        filters = parse_universal_filters(
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

        # Call the original function with filters object
        return func(filters=filters, **kwargs)

    return wrapper


def with_entity_specific_filters(**entity_filters: dict) -> Callable:
    """
    Decorator that adds entity-specific filter parameters to a command.

    Args:
        entity_filters: Dictionary mapping filter names to their typer.Option definitions

    Example:
        @with_entity_specific_filters(
            database_id=typer.Option("--database-id", help="Filter by database ID"),
            schema=typer.Option("--schema", help="Filter by schema name"),
        )
        def list_datasets(filters, database_id, schema, **kwargs):
            # Function receives both universal filters and entity-specific params
            pass
    """

    def decorator(func: Callable) -> Callable:
        # For now, this is a placeholder - entity-specific filters
        # will still be manually defined in each command until we
        # implement a more sophisticated parameter injection system
        return func

    return decorator
