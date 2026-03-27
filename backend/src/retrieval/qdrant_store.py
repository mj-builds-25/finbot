"""
Qdrant store — manages the vector database collection for FinBot.

Responsibilities:
- Create the finbot_v1 collection if it doesn't exist
- Define the vector configuration (dimensions, distance metric)
- Provide a shared QdrantClient instance to other modules
- Verify connection health

Collection schema:
  - Vector size: 384 (BAAI/bge-small-en-v1.5)
  - Distance: Cosine similarity
  - Payload (metadata) fields stored per chunk:
      source_document, collection, access_roles, section_title,
      page_number, chunk_type, parent_chunk_id, text
"""

import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
)

from src.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    EMBEDDING_DIM,
)

logger = logging.getLogger(__name__)


def get_client() -> QdrantClient:
    """
    Returns a connected QdrantClient instance.
    Call this wherever you need to interact with Qdrant.
    """
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )


def create_collection_if_not_exists(client: QdrantClient) -> bool:
    """
    Creates the finbot_v1 collection if it doesn't already exist.

    Returns:
        True  — collection was just created
        False — collection already existed, nothing changed
    """
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in existing:
        logger.info(f"Collection '{COLLECTION_NAME}' already exists — skipping creation")
        return False

    logger.info(f"Creating collection '{COLLECTION_NAME}' ...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,       # 384 for bge-small-en-v1.5
            distance=Distance.COSINE, # standard for semantic similarity
        ),
    )
    logger.info(f"✅ Collection '{COLLECTION_NAME}' created successfully")
    return True


def verify_connection(client: QdrantClient) -> dict:
    """
    Runs a health check against Qdrant Cloud.

    Returns a dict with:
        status       — 'ok' or 'error'
        collection   — collection name
        points_count — number of vectors currently stored
        error        — error message if status is 'error'
    """
    try:
        info = client.get_collection(COLLECTION_NAME)
        return {
            "status": "ok",
            "collection": COLLECTION_NAME,
            "points_count": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance": str(info.config.params.vectors.distance),
        }
    except Exception as e:
        return {
            "status": "error",
            "collection": COLLECTION_NAME,
            "error": str(e),
        }
