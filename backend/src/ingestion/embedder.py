"""
Embedder for FinBot ingestion pipeline.

Uses fastembed (BAAI/bge-small-en-v1.5) to convert text chunks
into 384-dimensional vectors for semantic search.

Why fastembed over sentence-transformers:
- Runs without PyTorch (much smaller install)
- ONNX-based — fast CPU inference
- Same model quality for RAG use cases
"""

import logging
from fastembed import TextEmbedding
from src.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Module-level singleton — load model once, reuse across all calls
# Loading takes ~5 seconds; we don't want to do it per-chunk
_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    """
    Returns the embedding model, loading it on first call.
    Subsequent calls return the already-loaded model instantly.
    """
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = TextEmbedding(model_name=EMBEDDING_MODEL)
        logger.info("✅ Embedding model loaded")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of text strings into embedding vectors.

    Args:
        texts: List of text strings to embed

    Returns:
        List of 384-dimensional float vectors, one per input text
    """
    model = get_embedding_model()

    # fastembed.embed() returns a generator — we consume it into a list
    embeddings = list(model.embed(texts))

    return [emb.tolist() for emb in embeddings]


def embed_query(query: str) -> list[float]:
    """
    Embed a single search query.
    Used at retrieval time — separate from batch embedding at ingest time.

    Args:
        query: User's search query string

    Returns:
        384-dimensional float vector
    """
    model = get_embedding_model()
    embedding = list(model.embed([query]))[0]
    return embedding.tolist()