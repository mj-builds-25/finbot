"""
RBAC filter builder for FinBot retrieval layer.

This module is the security enforcement point.
It translates a user's role into a Qdrant metadata filter
that restricts which chunks can ever be retrieved.

Key principle: the filter is applied AT THE DATABASE LEVEL.
Restricted chunks are never returned to the application layer,
so the LLM can never see or leak them — even with prompt injection.

Role → accessible collections mapping:
    employee    → general
    finance     → general, finance
    engineering → general, engineering
    marketing   → general, marketing
    c_level     → general, finance, engineering, marketing
"""

from qdrant_client.models import Filter, FieldCondition, MatchValue


# Single source of truth for role → collection access
# If this changes, only this file needs updating
ROLE_COLLECTIONS: dict[str, list[str]] = {
    "employee":    ["general"],
    "finance":     ["general", "finance"],
    "engineering": ["general", "engineering"],
    "marketing":   ["general", "marketing"],
    "c_level":     ["general", "finance", "engineering", "marketing"],
}

# All valid roles — used for input validation
VALID_ROLES = set(ROLE_COLLECTIONS.keys())


def get_accessible_collections(role: str) -> list[str]:
    """
    Returns the list of collections a role can access.

    Args:
        role: One of employee, finance, engineering, marketing, c_level

    Returns:
        List of collection names this role can search

    Raises:
        ValueError: if role is not recognized
    """
    role = role.lower().strip()
    if role not in ROLE_COLLECTIONS:
        raise ValueError(
            f"Unknown role: '{role}'. "
            f"Valid roles: {sorted(VALID_ROLES)}"
        )
    return ROLE_COLLECTIONS[role]


def build_rbac_filter(role: str) -> Filter:
    """
    Builds a Qdrant filter that enforces RBAC at the database level.

    The filter checks that the chunk's access_roles list
    contains the user's role — meaning the user is authorized
    to see that chunk.

    Why we filter on access_roles (not collection):
    - access_roles is the authoritative field set at ingestion time
    - It supports future fine-grained permissions (e.g. specific users)
    - Collection field is for routing; access_roles is for security

    Args:
        role: The authenticated user's role

    Returns:
        Qdrant Filter object ready to pass to search()

    Example:
        role = "engineering"
        → Filter: access_roles must contain "engineering"
        → Returns engineering + general chunks (both have "engineering"
          in their access_roles list)
        → Never returns finance or marketing chunks
    """
    role = role.lower().strip()
    if role not in ROLE_COLLECTIONS:
        raise ValueError(f"Unknown role: '{role}'")

    # Build filter: access_roles array must contain the user's role
    # This works because at ingestion time we stored:
    #   general docs    → access_roles: ["employee","finance","engineering","marketing","c_level"]
    #   finance docs    → access_roles: ["finance", "c_level"]
    #   engineering docs → access_roles: ["engineering", "c_level"]
    #   marketing docs  → access_roles: ["marketing", "c_level"]
    return Filter(
        must=[
            FieldCondition(
                key="access_roles",
                match=MatchValue(value=role),
            )
        ]
    )


def validate_role(role: str) -> bool:
    """
    Returns True if the role is valid, False otherwise.
    Use this for input validation before building filters.
    """
    return role.lower().strip() in VALID_ROLES
