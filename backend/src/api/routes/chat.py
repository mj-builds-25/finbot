"""
Chat route for FinBot API.

POST /chat — run full RAG pipeline for authenticated user.

This is the main endpoint the frontend calls when a user
sends a message. It runs:
1. Input guardrails
2. Semantic routing
3. RBAC-filtered retrieval
4. LLM answer generation
5. Output guardrails
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.rag.chain import run_rag_chain
from src.retrieval.rbac import get_accessible_collections

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class SourceCitation(BaseModel):
    document:   str
    section:    str
    page:       int
    collection: str
    score:      float


class ChatResponse(BaseModel):
    answer:               str
    sources:              list[SourceCitation]
    route:                str
    route_score:          float
    collections_searched: list[str]
    chunks_retrieved:     int
    allowed:              bool
    input_blocked:        bool
    output_warnings:      list[str]
    user_role:            str
    accessible_collections: list[str]


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Process a chat message through the full FinBot RAG pipeline.

    RBAC is enforced inside run_rag_chain() — the user's role
    from their JWT token is passed through to the retrieval layer.
    """
    role = current_user["role"]
    query = request.message.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    logger.info(
        f"Chat request | user={current_user['email']} | "
        f"role={role} | query='{query[:60]}...'"
    )

    try:
        response = run_rag_chain(
            query=query,
            role=role,
        )
    except Exception as e:
        logger.error(f"RAG chain error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred processing your request: {str(e)}"
        )

    return ChatResponse(
        answer=response.answer,
        sources=[
            SourceCitation(
                document=s["document"],
                section=s["section"],
                page=s["page"],
                collection=s["collection"],
                score=s["score"],
            )
            for s in response.sources
        ],
        route=response.route,
        route_score=response.route_score,
        collections_searched=response.collections_searched,
        chunks_retrieved=response.chunks_retrieved,
        allowed=response.allowed,
        input_blocked=getattr(response, "input_blocked", False),
        output_warnings=getattr(response, "output_warnings", []),
        user_role=role,
        accessible_collections=get_accessible_collections(role),
    )