"""
RBAC-enforced retriever for FinBot.

This is the main retrieval interface used by the RAG chain.
Every search goes through RBAC — there is no way to search
without a role filter applied.

Usage:
    results = search(query="what is the leave policy?", role="employee")
    for r in results:
        print(r.text, r.source_document, r.score)
"""

import logging
from dataclasses import dataclass

from qdrant_client import QdrantClient

from src.retrieval.rbac import build_rbac_filter, get_accessible_collections
from src.retrieval.qdrant_store import get_client
from src.ingestion.embedder import embed_query
from src.config import COLLECTION_NAME

logger = logging.getLogger(__name__)

# Number of chunks to retrieve per query
# Higher = more context for LLM but uses more tokens
TOP_K = 5


@dataclass
class RetrievalResult:
    """
    One retrieved chunk with its metadata.
    This is what gets passed to the RAG chain.
    """
    text: str               # The chunk text — goes into LLM context
    source_document: str    # e.g. "financial_summary.docx"
    section_title: str      # e.g. "Q3 Revenue Breakdown"
    page_number: int        # For citations in the response
    collection: str         # Which collection this came from
    chunk_type: str         # text / table / code
    score: float            # Cosine similarity score (0-1)


def search(
    query: str,
    role: str,
    top_k: int = TOP_K,
    client: QdrantClient | None = None,
) -> list[RetrievalResult]:
    """
    Search for relevant chunks — RBAC filter always applied.

    This is the ONLY way to retrieve chunks in FinBot.
    The RBAC filter is not optional and cannot be bypassed.

    Args:
        query:  The user's natural language question
        role:   The authenticated user's role (enforces access control)
        top_k:  Number of results to return (default: 5)
        client: Optional QdrantClient (creates one if not provided)

    Returns:
        List of RetrievalResult objects, sorted by relevance score

    Example:
        # Engineering user — gets engineering + general chunks only
        results = search("what is the payment service SLA?", "engineering")

        # Finance user asking about engineering — gets ZERO results
        # because finance role has no access to engineering chunks
        results = search("what is the payment service SLA?", "finance")
        # → returns [] — RBAC enforced at database level
    """
    if client is None:
        client = get_client()

    # Step 1: Embed the query
    query_vector = embed_query(query)

    # Step 2: Build the RBAC filter for this user's role
    rbac_filter = build_rbac_filter(role)

    accessible = get_accessible_collections(role)
    logger.info(
        f"Search | role={role} | "
        f"collections={accessible} | "
        f"query='{query[:60]}...'"
    )

    # Step 3: Search Qdrant with the filter applied
    # The filter runs INSIDE Qdrant — restricted chunks
    # are never returned to this application at all
    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=rbac_filter,
        limit=top_k,
        with_payload=True,
    ).points

    # Step 4: Convert Qdrant hits to RetrievalResult objects
    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append(RetrievalResult(
            text=payload.get("text", ""),
            source_document=payload.get("source_document", "unknown"),
            section_title=payload.get("section_title", ""),
            page_number=payload.get("page_number", 0),
            collection=payload.get("collection", ""),
            chunk_type=payload.get("chunk_type", "text"),
            score=round(hit.score, 4),
        ))

    logger.info(f"  → {len(results)} chunks retrieved")
    return results


def search_with_collections(
    query: str,
    role: str,
    target_collections: list[str],
    top_k: int = TOP_K,
    client: QdrantClient | None = None,
) -> list[RetrievalResult]:
    """
    Search within specific collections — still RBAC enforced.

    Used by the semantic router to target specific collections
    after query intent classification. Even with targeted
    collections, the user's role is still validated first.

    Args:
        query:               User's question
        role:                User's role (RBAC enforced)
        target_collections:  Collections the router identified
        top_k:               Number of results

    Returns:
        RetrievalResult list filtered to target_collections
        AND authorized by role — both conditions must be true
    """
    # Get all results with RBAC enforced
    all_results = search(query, role, top_k=top_k * 2, client=client)

    # Further filter to only the targeted collections
    filtered = [
        r for r in all_results
        if r.collection in target_collections
    ]

    # Return top_k of the filtered results
    return filtered[:top_k]
