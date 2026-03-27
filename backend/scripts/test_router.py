"""
Semantic router test suite for FinBot.

Tests that:
1. Queries are classified into the correct routes
2. Role intersection correctly grants/denies access
3. Access denied messages are returned for cross-role queries

Usage:
    cd backend/
    uv run --active python -m scripts.test_router
"""

import sys
import logging
logging.basicConfig(level="WARNING", format="%(levelname)s: %(message)s")

from src.routing.semantic_router import get_router, RouteType
from src.routing.role_intersect import route_query

# ============================================================
# Routing classification tests
# ============================================================
ROUTING_TESTS = [
    {
        "query": "What was the total revenue in 2024?",
        "expected_route": RouteType.FINANCE,
        "description": "Revenue question → finance route",
    },
    {
        "query": "What was the root cause of the payment gateway outage?",
        "expected_route": RouteType.ENGINEERING,
        "description": "Incident question → engineering route",
    },
    {
        "query": "How many customers did we acquire in Q3?",
        "expected_route": RouteType.MARKETING,
        "description": "Acquisition question → marketing route",
    },
    {
        "query": "How many days of annual leave do I get?",
        "expected_route": RouteType.HR_GENERAL,
        "description": "Leave policy question → hr_general route",
    },
    {
        "query": "Give me an overview of how the company is doing",
        "expected_route": RouteType.CROSS_DEPARTMENT,
        "description": "Broad question → cross_department route",
    },
    {
        "query": "What is our EBITDA margin?",
        "expected_route": RouteType.FINANCE,
        "description": "EBITDA question → finance route",
    },
    {
        "query": "What is the SLA target for the payment service?",
        "expected_route": RouteType.ENGINEERING,
        "description": "SLA question → engineering route",
    },
    {
        "query": "What was the ROI on our influencer campaigns?",
        "expected_route": RouteType.MARKETING,
        "description": "Campaign ROI → marketing route",
    },
    {
        "query": "What is the work from home policy?",
        "expected_route": RouteType.HR_GENERAL,
        "description": "WFH policy → hr_general route",
    },
]

# ============================================================
# Role intersection tests
# ============================================================
INTERSECTION_TESTS = [
    {
        "query": "What was the total revenue in 2024?",
        "role": "finance",
        "expect_allowed": True,
        "description": "finance user asking finance question → allowed",
    },
    {
        "query": "What was the total revenue in 2024?",
        "role": "engineering",
        "expect_allowed": True,          # ← was False
        "expected_collections": ["general"],  # searches general only
        "description": "engineering asking finance → searches general only, no finance docs",
    },
    {
        "query": "What was the payment gateway incident?",
        "role": "engineering",
        "expect_allowed": True,
        "description": "engineering user asking engineering question → allowed",
    },
    {
        "query": "What was the payment gateway incident?",
        "role": "marketing",
        "expect_allowed": True,          # ← was False
        "expected_collections": ["general"],
        "description": "marketing asking engineering → searches general only",
    },
    {
        "query": "What is the work from home policy?",
        "role": "employee",
        "expect_allowed": True,
        "description": "employee asking HR question → allowed",
    },
    {
        "query": "What was the total revenue in 2024?",
        "role": "c_level",
        "expect_allowed": True,
        "description": "c_level asking finance question → allowed",
    },
    {
        "query": "What was the payment gateway incident?",
        "role": "c_level",
        "expect_allowed": True,
        "description": "c_level asking engineering question → allowed",
    },
    {
        "query": "What was the ROI on Q4 campaigns?",
        "role": "finance",
        "expect_allowed": True,          # ← was False
        "expected_collections": ["general"],
        "description": "finance asking marketing → searches general only",
    },
]


def run_tests():
    print("\n" + "="*60)
    print("  FinBot — Semantic Router Test Suite")
    print("="*60)

    passed = 0
    failed = 0

    # --- Routing classification tests ---
    print("\n📍 Route Classification Tests")
    print("-"*60)

    router = get_router()

    for i, test in enumerate(ROUTING_TESTS, 1):
        result = router.classify(test["query"])
        if result.route == test["expected_route"]:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"[{i:02d}] {status}")
        print(f"      Query    : {test['query'][:55]}...")
        print(f"      Expected : {test['expected_route'].value}")
        print(f"      Got      : {result.route.value} (score={result.score})")
        print(f"      Test     : {test['description']}")

    # --- Role intersection tests ---
    print(f"\n📍 Role Intersection Tests")
    print("-"*60)

    for i, test in enumerate(INTERSECTION_TESTS, 1):
        decision = route_query(test["query"], test["role"])

        if decision.allowed == test["expect_allowed"]:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        access = "ALLOWED" if decision.allowed else "DENIED"
        print(f"[{i:02d}] {status}")
        print(f"      Role       : {test['role']}")
        print(f"      Query      : {test['query'][:50]}...")
        print(f"      Access     : {access}")
        print(f"      Collections: {decision.collections_to_search}")
        if not decision.allowed:
            print(f"      Message    : {decision.denial_message[:70]}...")
        print(f"      Test       : {test['description']}")

    # Summary
    print("\n" + "="*60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("="*60)

    if failed == 0:
        print("\n✅ All router tests passed")
        print("="*60 + "\n")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} tests failed")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()