"""
Hierarchical chunker for FinBot ingestion pipeline.

Takes a ParsedDocument and produces a flat list of chunks,
where each chunk has:
  - The text content
  - Full RBAC metadata (collection, access_roles, etc.)
  - A parent_chunk_id linking it to its parent section

Why hierarchical chunking matters:
  A finance doc has sections like:
    "Q3 Financial Results"          ← parent chunk (summary)
      "Revenue Breakdown"           ← child chunk
      "Expense Analysis"            ← child chunk

  When a user asks "what were Q3 results?", the parent chunk
  gives a broad answer. When they ask "what was the expense
  breakdown?", the child chunk gives the precise answer.
  Storing both = better retrieval at both levels of specificity.
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional

from src.ingestion.parser import ParsedDocument, ParsedSection

logger = logging.getLogger(__name__)

# Max characters per leaf chunk before we split further
# ~400 tokens at ~4 chars/token — fits well in context window
MAX_CHUNK_SIZE = 1500


@dataclass
class Chunk:
    """
    One unit of text ready to be embedded and stored in Qdrant.
    Every field here becomes a Qdrant payload field.
    """
    chunk_id: str               # Unique ID for this chunk
    parent_chunk_id: str        # ID of parent section chunk ("" if top-level)
    text: str                   # The actual text content to embed

    # RBAC metadata — enforced at retrieval time
    collection: str             # general / finance / engineering / marketing
    access_roles: list[str]     # ["finance", "c_level"] etc.

    # Document metadata — shown in citations
    source_document: str        # e.g. "financial_summary.docx"
    section_title: str          # e.g. "Q3 Revenue Breakdown"
    page_number: int            # Page in source document
    chunk_type: str             # text / table / code / heading


def chunk_document(parsed_doc: ParsedDocument) -> list[Chunk]:
    """
    Convert a ParsedDocument into a flat list of Chunks.

    Strategy:
    1. Each top-level section (H1) becomes a parent chunk
       containing a summary of all its children's text
    2. Each subsection (H2/H3) becomes a child chunk
    3. Large sections are split into smaller leaf chunks
    4. Every chunk carries the full RBAC metadata

    Args:
        parsed_doc: Output from parser.parse_file()

    Returns:
        List of Chunk objects ready for embedding
    """
    chunks = []
    parent_id = ""
    parent_title = ""

    for section in parsed_doc.sections:
        # Generate a stable unique ID for this chunk
        chunk_id = str(uuid.uuid4())

        # Top-level sections (H1) become parents
        if section.level == 1:
            parent_id = chunk_id
            parent_title = section.section_title

        # Split large sections into smaller pieces
        text_pieces = _split_text(section.text, MAX_CHUNK_SIZE)

        for i, piece in enumerate(text_pieces):
            piece_id = chunk_id if i == 0 else str(uuid.uuid4())

            chunks.append(Chunk(
                chunk_id=piece_id,
                parent_chunk_id=parent_id if section.level > 1 else "",
                text=piece,
                collection=parsed_doc.collection,
                access_roles=parsed_doc.access_roles,
                source_document=parsed_doc.file_name,
                section_title=section.section_title,
                page_number=section.page_number,
                chunk_type=section.chunk_type,
            ))

    logger.info(
        f"  Chunked '{parsed_doc.file_name}' → {len(chunks)} chunks"
    )
    return chunks


def _split_text(text: str, max_size: int) -> list[str]:
    """
    Split a large text block into smaller pieces.

    Strategy: split on paragraph boundaries first (double newline),
    then on sentence boundaries if paragraphs are still too large.
    This preserves semantic coherence better than character splitting.
    """
    if len(text) <= max_size:
        return [text]

    pieces = []
    # Try splitting on paragraphs first
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_size:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                pieces.append(current.strip())
            # If single paragraph is too large, split on sentences
            if len(para) > max_size:
                pieces.extend(_split_on_sentences(para, max_size))
                current = ""
            else:
                current = para

    if current:
        pieces.append(current.strip())

    return [p for p in pieces if p.strip()]


def _split_on_sentences(text: str, max_size: int) -> list[str]:
    """Fallback splitter — splits on '. ' boundaries."""
    sentences = text.split(". ")
    pieces = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 2 <= max_size:
            current = current + ". " + sentence if current else sentence
        else:
            if current:
                pieces.append(current.strip())
            current = sentence

    if current:
        pieces.append(current.strip())

    return pieces