"""
Admin routes for FinBot API.

These endpoints are for the admin panel in the frontend.
In production these would require admin role verification.
For this demo, they're accessible to c_level users only.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_current_user
from src.retrieval.qdrant_store import get_client, verify_connection
from src.ingestion.ingest_pipeline import DOCUMENT_REGISTRY
from src.api.demo_users import DEMO_USERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def require_c_level(current_user: dict = Depends(get_current_user)):
    """Dependency — only c_level users can access admin endpoints."""
    if current_user["role"] != "c_level":
        raise HTTPException(
            status_code=403,
            detail="Admin access requires c_level role.",
        )
    return current_user


@router.get("/health")
def health_check():
    """Check Qdrant connection and collection status."""
    client = get_client()
    result = verify_connection(client)
    return {
        "status":   result["status"],
        "qdrant":   result,
        "api":      "online",
    }


@router.get("/collections")
def list_collections(current_user: dict = Depends(require_c_level)):
    """List all Qdrant collections with document counts."""
    client = get_client()
    collections = client.get_collections().collections

    result = []
    for col in collections:
        info = client.get_collection(col.name)
        result.append({
            "name":         col.name,
            "points_count": info.points_count,
            "vector_size":  info.config.params.vectors.size,
        })

    return {"collections": result}


@router.get("/documents")
def list_documents(current_user: dict = Depends(require_c_level)):
    """List all documents in the registry with their access roles."""
    return {
        "documents": [
            {
                "path":         doc["path"],
                "collection":   doc["collection"],
                "access_roles": doc["access_roles"],
            }
            for doc in DOCUMENT_REGISTRY
        ],
        "total": len(DOCUMENT_REGISTRY),
    }


@router.get("/users")
def list_users(current_user: dict = Depends(require_c_level)):
    """List all demo users (no passwords)."""
    return {
        "users": [
            {
                "email":      user.email,
                "name":       user.name,
                "role":       user.role,
                "department": user.department,
            }
            for user in DEMO_USERS.values()
        ]
    }