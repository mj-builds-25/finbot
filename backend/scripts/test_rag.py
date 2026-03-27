"""
End-to-end RAG chain test for FinBot.

Tests the full pipeline: routing → retrieval → LLM → answer
Uses real questions grounded in actual FinSolve documents.

Usage:
    cd backend/
    uv run --active python -m scripts.test_rag
"""

import sys
import logging
logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

from src.rag.chain import run_rag_chain

# ============================================================
# Test queries — one per collection + access denial test
# Answers grounded in actual FinSolve documents
# ============================================================
TEST_QUERIES = [
    {
        "query": "What is the work from home policy at FinSolve?",
        "role":  "employee",
        "description": "General HR query — employee role",
    },
    {
        "query": "What was FinSolve total revenue in 2024?",
        "role":  "finance",
        "description": "Finance query — finance role",
    },
    {
        "query": "What was the root cause of the payment gateway outage?",
        "role":  "engineering",
        "description": "Engineering incident query — engineering role",
    },
    {
        "query": "How many customers did FinSolve acquire in Q3 2024?",
        "role":  "marketing",
        "description": "Marketing query — marketing role",
    },
    {
        "query": "Give me an overview of FinSolve performance in 2024",
        "role":  "c_level",
        "description": "Cross-department query — c_level role",
    },
    {
        "query": "What was FinSolve total revenue in 2024?",
        "role":  "engineering",
        "description": "Finance query with engineering role — should use general only",
    },
]


def run_tests():
    print("\n" + "="*65)
    print("  FinBot — End-to-End RAG Chain Test")
    print("="*65)

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'─'*65}")
        print(f"[{i}] {test['description']}")
        print(f"     Role  : {test['role']}")
        print(f"     Query : {test['query']}")
        print(f"{'─'*65}")

        try:
            response = run_rag_chain(
                query=test["query"],
                role=test["role"],
            )

            print(f"\n  Route      : {response.route} "
                  f"(confidence={response.route_score})")
            print(f"  Collections: {response.collections_searched}")
            print(f"  Chunks     : {response.chunks_retrieved}")
            print(f"  Allowed    : {response.allowed}")
            print(f"\n  ANSWER:\n")

            # Print answer with word wrap
            words = response.answer.split()
            line = "  "
            for word in words:
                if len(line) + len(word) > 75:
                    print(line)
                    line = "  " + word + " "
                else:
                    line += word + " "
            if line.strip():
                print(line)

            if response.sources:
                print(f"\n  SOURCES:")
                for s in response.sources:
                    print(f"    • {s['document']} "
                          f"(page {s['page']}, "
                          f"score={s['score']})")

        except Exception as e:
            print(f"\n  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*65}")
    print("  ✅ RAG chain test complete")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    run_tests()