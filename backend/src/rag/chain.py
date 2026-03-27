"""
RAG chain for FinBot — the full pipeline from query to answer.

Orchestrates:
1. Semantic routing  → classify query intent
2. RBAC retrieval    → fetch authorized chunks
3. Prompt building   → format context
4. LLM generation   → Groq via OpenAI-compatible endpoint
5. Response building → cited answer with metadata

This is the single entry point for the entire RAG pipeline.
The FastAPI routes call run_rag_chain() and return the result.
"""

import logging
from dataclasses import dataclass, field

from src.guardrails.input_guards import run_input_guards, InputGuardResult
from src.guardrails.output_guards import run_output_guards

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.routing.role_intersect import route_query, RoutingDecision
from src.retrieval.retriever import search_with_collections, RetrievalResult
from src.rag.prompts import build_prompt, format_context
from src.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """
    Complete response from the RAG chain.
    This is what the API returns to the frontend.
    """
    answer: str                          # The LLM-generated answer
    sources: list[dict]                  # Citation metadata
    route: str                           # Which route was matched
    route_score: float                   # Router confidence
    collections_searched: list[str]      # Which collections were queried
    chunks_retrieved: int                # How many chunks fed to LLM
    allowed: bool                        # Was access granted?
    denial_message: str | None = None    # If denied, the message
    input_blocked: bool = False          # Was input blocked by guardrails?
    output_warnings: list[str] = field(default_factory=list)  # Output warnings


def _get_llm() -> ChatOpenAI:
    """
    Returns a ChatOpenAI instance pointed at Groq's endpoint.

    Used langchain-openai (not langchain-groq) because
    langchain-groq has a known proxies bug in Codespaces.
    Groq's API is fully OpenAI-compatible so this works perfectly.
    """
    return ChatOpenAI(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        temperature=0.1,      # Low temp = factual, consistent answers
        max_tokens=1024,
    )


def _build_sources(results: list[RetrievalResult]) -> list[dict]:
    """
    Extract citation metadata from retrieved chunks.
    Deduplicated by source document + page number.
    """
    seen = set()
    sources = []

    for r in results:
        key = (r.source_document, r.page_number)
        if key not in seen:
            seen.add(key)
            sources.append({
                "document": r.source_document,
                "section":  r.section_title,
                "page":     r.page_number,
                "collection": r.collection,
                "score":    r.score,
            })

    return sources


def run_rag_chain(
    query: str,
    role: str,
) -> RAGResponse:
    """
    Run the full RAG pipeline for a user query.

    Args:
        query: User's natural language question
        role:  Authenticated user's role (enforces RBAC)

    Returns:
        RAGResponse with answer, sources, and metadata
    """
    logger.info(f"RAG chain | role={role} | query='{query[:60]}...'")

    # ── Step 0: Input guardrails ────────────────────────────
    guard_result = run_input_guards(query=query, session_id=role)

    if not guard_result.allowed:
        logger.info(f"  Input blocked by: {guard_result.blocked_by}")
        return RAGResponse(
            answer=guard_result.message,
            sources=[],
            route="blocked",
            route_score=0.0,
            collections_searched=[],
            chunks_retrieved=0,
            allowed=False,
            denial_message=guard_result.message,
            input_blocked=True,
        )

    # ── Step 1: Route the query ──────────────────────────────
    decision: RoutingDecision = route_query(query, role)

    logger.info(
        f"  Route: {decision.route.value} "
        f"(score={decision.route_score}) "
        f"→ collections: {decision.collections_to_search}"
    )

    # ── Step 2: Handle access denial ────────────────────────
    if not decision.allowed or not decision.collections_to_search:
        logger.info(f"  Access denied for role={role}")
        return RAGResponse(
            answer=decision.denial_message or "Access denied.",
            sources=[],
            route=decision.route.value,
            route_score=decision.route_score,
            collections_searched=[],
            chunks_retrieved=0,
            allowed=False,
            denial_message=decision.denial_message,
        )

    # ── Step 3: Retrieve authorized chunks ──────────────────
    results = search_with_collections(
        query=query,
        role=role,
        target_collections=decision.collections_to_search,
        top_k=5,
    )

    logger.info(f"  Retrieved {len(results)} chunks")

    if not results:
        return RAGResponse(
            answer=(
                "I don't have enough information in the available "
                "documents to answer this question."
            ),
            sources=[],
            route=decision.route.value,
            route_score=decision.route_score,
            collections_searched=decision.collections_to_search,
            chunks_retrieved=0,
            allowed=True,
        )

    # ── Step 4: Build prompt ─────────────────────────────────
    messages = build_prompt(query, results, role)

    # ── Step 5: Generate answer via Groq ────────────────────
    llm = _get_llm()

    langchain_messages = [
        SystemMessage(content=messages[0]["content"]),
        HumanMessage(content=messages[1]["content"]),
    ]

    logger.info(f"  Calling Groq ({GROQ_MODEL})...")
    response = llm.invoke(langchain_messages)
    answer = response.content

    logger.info(f"  Answer generated ({len(answer)} chars)")

    # ── Step 6: Output guardrails ────────────────────────────
    output_result = run_output_guards(
        answer=answer,
        retrieved_chunks=results,
    )

    # ── Step 7: Build final response ─────────────────────────
    return RAGResponse(
        answer=output_result.answer,
        sources=_build_sources(results),
        route=decision.route.value,
        route_score=decision.route_score,
        collections_searched=decision.collections_to_search,
        chunks_retrieved=len(results),
        allowed=True,
        output_warnings=output_result.warnings,
    )