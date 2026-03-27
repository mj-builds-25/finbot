"""
Ingest pipeline orchestrator for FinBot.

Ties together parser → chunker → embedder → Qdrant upload.

This is the main entry point for document ingestion.
Call run_ingestion() with a list of documents to process.
"""

import logging
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.ingestion.parser import parse_file, ParsedDocument
from src.ingestion.chunker import chunk_document, Chunk
from src.ingestion.embedder import embed_texts
from src.retrieval.qdrant_store import get_client, create_collection_if_not_exists
from src.config import COLLECTION_NAME

logger = logging.getLogger(__name__)

# Upload to Qdrant in batches — avoids memory issues with large doc sets
BATCH_SIZE = 50


# ============================================================
# Document registry
# Maps each file to its collection and access_roles
# This is the single source of truth for RBAC in ingestion
# ============================================================
DOCUMENT_REGISTRY = [
    # --- GENERAL (all roles) ---
    {
        "path": "data/general/employee_handbook.pdf",
        "collection": "general",
        "access_roles": ["employee", "finance", "engineering", "marketing", "c_level"],
    },

    # --- FINANCE (finance + c_level only) ---
    {
        "path": "data/finance/financial_summary.docx",
        "collection": "finance",
        "access_roles": ["finance", "c_level"],
    },
    {
        "path": "data/finance/quarterly_financial_report.docx",
        "collection": "finance",
        "access_roles": ["finance", "c_level"],
    },
    {
        "path": "data/finance/department_budget_2024.docx",
        "collection": "finance",
        "access_roles": ["finance", "c_level"],
    },
    {
        "path": "data/finance/vendor_payments_summary.docx",
        "collection": "finance",
        "access_roles": ["finance", "c_level"],
    },

    # --- ENGINEERING (engineering + c_level only) ---
    {
        "path": "data/engineering/engineering_master_doc.md",
        "collection": "engineering",
        "access_roles": ["engineering", "c_level"],
    },
    {
        "path": "data/engineering/incident_report_log.md",
        "collection": "engineering",
        "access_roles": ["engineering", "c_level"],
    },
    {
        "path": "data/engineering/system_sla_report_2024.md",
        "collection": "engineering",
        "access_roles": ["engineering", "c_level"],
    },
    {
        "path": "data/engineering/sprint_metrics_2024.md",
        "collection": "engineering",
        "access_roles": ["engineering", "c_level"],
    },

    # --- MARKETING (marketing + c_level only) ---
    {
        "path": "data/marketing/marketing_report_2024.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
    {
        "path": "data/marketing/marketing_report_q1_2024.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
    {
        "path": "data/marketing/marketing_report_q2_2024.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
    {
        "path": "data/marketing/marketing_report_q3_2024.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
    {
        "path": "data/marketing/marketing_report_q4_2024.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
    {
        "path": "data/marketing/campaign_performance_data.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
    {
        "path": "data/marketing/customer_acquisition_report.docx",
        "collection": "marketing",
        "access_roles": ["marketing", "c_level"],
    },
]


def _upload_chunks(
    client: QdrantClient,
    chunks: list[Chunk],
    texts: list[str],
    vectors: list[list[float]],
) -> None:
    """Upload a batch of chunks with their vectors to Qdrant."""
    points = []
    for chunk, vector in zip(chunks, vectors):
        points.append(PointStruct(
            id=chunk.chunk_id,
            vector=vector,
            payload={
                # RBAC fields — used for metadata filtering
                "collection":       chunk.collection,
                "access_roles":     chunk.access_roles,

                # Citation fields — shown to user in responses
                "source_document":  chunk.source_document,
                "section_title":    chunk.section_title,
                "page_number":      chunk.page_number,
                "chunk_type":       chunk.chunk_type,

                # Hierarchy field — links child to parent
                "parent_chunk_id":  chunk.parent_chunk_id,

                # The actual text — returned with search results
                "text":             chunk.text,
            }
        ))

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )


def ingest_document(
    client: QdrantClient,
    doc_config: dict,
    base_path: Path,
) -> dict:
    """
    Run the full pipeline for one document.

    Returns a summary dict with counts and status.
    """
    file_path = base_path / doc_config["path"]

    if not file_path.exists():
        logger.warning(f"⚠️  File not found — skipping: {file_path}")
        return {"file": doc_config["path"], "status": "skipped", "chunks": 0}

    try:
        # Stage 1: Parse
        parsed = parse_file(
            file_path=file_path,
            collection=doc_config["collection"],
            access_roles=doc_config["access_roles"],
        )

        # Stage 2: Chunk
        chunks = chunk_document(parsed)
        if not chunks:
            logger.warning(f"  No chunks produced for {file_path.name}")
            return {"file": doc_config["path"], "status": "empty", "chunks": 0}

        # Stage 3: Embed + Upload in batches
        total_uploaded = 0
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i: i + BATCH_SIZE]
            texts = [c.text for c in batch]
            vectors = embed_texts(texts)
            _upload_chunks(client, batch, texts, vectors)
            total_uploaded += len(batch)
            logger.info(f"  Uploaded batch {i//BATCH_SIZE + 1} "
                       f"({total_uploaded}/{len(chunks)} chunks)")

        return {
            "file": doc_config["path"],
            "status": "success",
            "chunks": len(chunks),
            "collection": doc_config["collection"],
        }

    except Exception as e:
        logger.error(f"❌ Failed to ingest {doc_config['path']}: {e}")
        return {"file": doc_config["path"], "status": "error", "error": str(e)}


def run_ingestion(base_path: Path | None = None) -> list[dict]:
    """
    Run the full ingestion pipeline for all documents in the registry.

    Args:
        base_path: Root path for resolving document paths.
                   Defaults to backend/ directory.

    Returns:
        List of result dicts, one per document.
    """
    if base_path is None:
        # Default: backend/ is the parent of src/
        base_path = Path(__file__).resolve().parent.parent.parent

    logger.info("="*55)
    logger.info("  FinBot — Document Ingestion Pipeline")
    logger.info("="*55)
    logger.info(f"  Base path  : {base_path}")
    logger.info(f"  Collection : {COLLECTION_NAME}")
    logger.info(f"  Documents  : {len(DOCUMENT_REGISTRY)}")
    logger.info("="*55)

    # Connect and ensure collection exists
    client = get_client()
    create_collection_if_not_exists(client)

    results = []
    for i, doc_config in enumerate(DOCUMENT_REGISTRY, 1):
        logger.info(f"\n[{i}/{len(DOCUMENT_REGISTRY)}] {doc_config['path']}")
        result = ingest_document(client, doc_config, base_path)
        results.append(result)

    # Summary
    success = [r for r in results if r["status"] == "success"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors  = [r for r in results if r["status"] == "error"]
    total_chunks = sum(r.get("chunks", 0) for r in results)

    logger.info("\n" + "="*55)
    logger.info("  Ingestion Complete")
    logger.info("="*55)
    logger.info(f"  ✅ Success : {len(success)} documents")
    logger.info(f"  ⚠️  Skipped : {len(skipped)} documents")
    logger.info(f"  ❌ Errors  : {len(errors)} documents")
    logger.info(f"  📦 Total chunks uploaded: {total_chunks}")
    logger.info("="*55)

    return results