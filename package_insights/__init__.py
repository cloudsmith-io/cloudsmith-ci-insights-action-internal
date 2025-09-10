"""Utilities and CLI for Cloudsmith package insights.

Exposes key functions for easier importing in tests.
"""

from .package_insights.cli import package_insights  # noqa: F401
from .package_insights.utils import (  # noqa: F401
    extract_action_slug,
    find_package,
    fetch_policies,
    fetch_policy_of_action,
    parse_logs_for_all_details,
)

__all__ = [
    "extract_action_slug",
    "find_package", 
    "fetch_policies",
    "fetch_policy_of_action",
    "package_insights",
    "parse_logs_for_all_details",
]
