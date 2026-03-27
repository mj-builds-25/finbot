"""
Role intersection module for FinBot routing layer.

After the semantic router classifies a query's intent,
this module intersects the router's target collections
with the user's authorized collections.

This is the step that produces polite access-denied messages
when a user asks about a collection they can't access.

Example:
    User role: engineering
    Query: "What was Q3 revenue?"
    Router says: finance_route → target: ["finance", "general"]
    Engineering can access: ["engineering", "general"]
    Intersection: ["general"]
    → Search only "general" (not finance)
    → If intersection is empty → access denied message

    User role: c_level
    Query: "What was Q3 revenue?"
    Router says: finance_route → target: ["finance", "general"]
    C-level can access: ["general", "finance", "engineering", "marketing"]
    Intersection: ["finance", "general"]
    → Full access, search finance + general
"""

import logging
from dataclasses import dataclass

from src.routing.semantic_router import RouteMatch, RouteType
from src.retrieval.rbac import get_accessible_collections, ROLE_COLLECTIONS

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """
    Final routing decision after role intersection.
    This is what gets passed to the retriever.
    """
    allowed: bool                    # Can this user access this route?
    collections_to_search: list[str] # Authorized + relevant collections
    route: RouteType                 # What route was matched
    route_score: float               # Confidence of route match
    denial_message: str | None       # Polite message if access denied


# Friendly messages shown when access is denied
# These are shown in the frontend as informational banners
DENIAL_MESSAGES: dict[RouteType, str] = {
    RouteType.FINANCE: (
        "This question relates to financial information which is restricted "
        "to the Finance team and C-Level executives. Please contact your "
        "Finance department if you need this information."
    ),
    RouteType.ENGINEERING: (
        "This question relates to engineering systems and technical "
        "documentation which is restricted to the Engineering team and "
        "C-Level executives."
    ),
    RouteType.MARKETING: (
        "This question relates to marketing data and campaign performance "
        "which is restricted to the Marketing team and C-Level executives."
    ),
    RouteType.HR_GENERAL: (
        "This question relates to HR and general company policies "
        "which are accessible to all employees."
    ),
    RouteType.CROSS_DEPARTMENT: (
        "This is a broad company question. Showing results from "
        "collections you are authorized to access."
    ),
}


def intersect_route_with_role(
    route_match: RouteMatch,
    role: str,
) -> RoutingDecision:
    """
    Intersect the router's target collections with the user's role.

    Args:
        route_match: Output from semantic_router.classify()
        role:        The authenticated user's role

    Returns:
        RoutingDecision with allowed=True/False and collections to search
    """
    # What collections does this route want to search?
    route_collections = set(route_match.target_collections)

    # What collections is this user authorized to access?
    authorized_collections = set(get_accessible_collections(role))

    # Intersection = collections we can actually search
    allowed_collections = route_collections & authorized_collections

    logger.info(
        f"Role intersection | role={role} | "
        f"route={route_match.route.value} | "
        f"route_wants={sorted(route_collections)} | "
        f"authorized={sorted(authorized_collections)} | "
        f"intersection={sorted(allowed_collections)}"
    )

    # If the intersection is empty, the user has no access to
    # any of the collections this route needs
    if not allowed_collections:
        route = route_match.route
        denial = DENIAL_MESSAGES.get(route, "You don't have access to this information.")
        logger.info(f"  → Access denied: no authorized collections in intersection")
        return RoutingDecision(
            allowed=False,
            collections_to_search=[],
            route=route,
            route_score=route_match.score,
            denial_message=denial,
        )

    # Access granted — search the intersected collections
    logger.info(f"  → Access granted: searching {sorted(allowed_collections)}")
    return RoutingDecision(
        allowed=True,
        collections_to_search=sorted(allowed_collections),
        route=route_match.route,
        route_score=route_match.score,
        denial_message=None,
    )


def route_query(query: str, role: str) -> RoutingDecision:
    """
    Full routing pipeline: classify → intersect → decide.

    This is the main entry point used by the RAG chain.

    Args:
        query: User's natural language question
        role:  Authenticated user's role

    Returns:
        RoutingDecision ready for the retriever
    """
    from src.routing.semantic_router import classify_query

    # Step 1: Classify query intent
    route_match = classify_query(query)

    # Step 2: Intersect with user's role
    decision = intersect_route_with_role(route_match, role)

    return decision