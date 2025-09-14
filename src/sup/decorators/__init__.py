"""
Command decorators for sup CLI.

Provides decorators to eliminate parameter duplication across entity commands.
"""

from .filters import with_entity_specific_filters, with_universal_filters
from .output import with_output_options

__all__ = [
    "with_universal_filters",
    "with_entity_specific_filters",
    "with_output_options",
]
