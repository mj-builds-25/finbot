"""
Document parser for FinBot ingestion pipeline.

Uses Docling to parse PDF, DOCX, and Markdown files into
structured text while preserving document hierarchy.

Why Docling over simple text extraction:
- Understands headings, sections, tables, code blocks
- Preserves the parent-child relationship between sections
- Handles tables in finance/marketing docs as structured data
- Gives us section titles for metadata — critical for RAG quality
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

logger = logging.getLogger(__name__)

@dataclass
class ParsedSection:
    """
    Represents one section extracted from a document.
    A section = a heading + all its content underneath it.
    """
    section_title: str          # The heading text (e.g. "Leave Policies")
    text: str                   # Full text content under this heading
    page_number: int            # Page where this section starts
    level: int                  # Heading level: 1=H1, 2=H2, 3=H3
    chunk_type: str             # "text", "table", "code", "heading"
    parent_title: Optional[str] = None   # Parent section title if nested


@dataclass
class ParsedDocument:
    """
    Represents a fully parsed document ready for chunking.
    """
    file_path: str              # Original file path
    file_name: str              # Just the filename e.g. "employee_handbook.pdf"
    collection: str             # Which collection: general/finance/engineering/marketing
    access_roles: list[str]     # Who can access this document
    sections: list[ParsedSection] = field(default_factory=list)
    raw_text: str = ""          # Full document text as fallback


def _get_pdf_converter() -> DocumentConverter:
    """
    PDF converter for Codespaces environment.
    Table structure and OCR disabled — both require OpenCV (libGL)
    which is not available in Codespaces.
    Text extraction still works perfectly for the employee handbook.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = False  # disabled: requires libGL

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )


def _get_docx_converter() -> DocumentConverter:
    """DOCX converter — Docling handles these natively."""
    return DocumentConverter(
        format_options={
            InputFormat.DOCX: WordFormatOption()
        }
    )


def _get_md_converter() -> DocumentConverter:
    """Markdown converter — simplest case, already structured."""
    return DocumentConverter()


def parse_file(
    file_path: Path,
    collection: str,
    access_roles: list[str],
) -> ParsedDocument:
    """
    Parse a single document file into a ParsedDocument.

    Args:
        file_path:    Path to the file
        collection:   One of: general, finance, engineering, marketing
        access_roles: List of roles that can access this doc

    Returns:
        ParsedDocument with all sections extracted
    """
    suffix = file_path.suffix.lower()
    logger.info(f"Parsing {file_path.name} ({suffix}) → collection: {collection}")

    # Pick the right converter for the file type
    if suffix == ".pdf":
        converter = _get_pdf_converter()
    elif suffix == ".docx":
        converter = _get_docx_converter()
    elif suffix in (".md", ".markdown"):
        converter = _get_md_converter()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    # Run Docling conversion
    result = converter.convert(str(file_path))
    doc = result.document

    # Export to markdown — Docling's markdown output preserves
    # heading hierarchy which we use to extract sections
    md_text = doc.export_to_markdown()

    # Parse the markdown into sections
    sections = _extract_sections_from_markdown(md_text)

    return ParsedDocument(
        file_path=str(file_path),
        file_name=file_path.name,
        collection=collection,
        access_roles=access_roles,
        sections=sections,
        raw_text=md_text,
    )


def _extract_sections_from_markdown(md_text: str) -> list[ParsedSection]:
    """
    Walk through markdown text and split it into sections
    based on heading levels (# ## ###).

    Each heading becomes a section. The text under it
    becomes that section's content.
    """
    sections = []
    lines = md_text.split("\n")

    current_title = "Introduction"
    current_level = 1
    current_lines = []
    current_page = 1
    page_counter = 1

    for line in lines:
        # Detect page breaks (Docling inserts these)
        if "<!-- PageBreak -->" in line or "---" in line.strip():
            page_counter += 1
            continue

        # Detect headings
        if line.startswith("# "):
            _flush_section(sections, current_title, current_lines,
                          current_page, current_level)
            current_title = line[2:].strip()
            current_level = 1
            current_lines = []
            current_page = page_counter

        elif line.startswith("## "):
            _flush_section(sections, current_title, current_lines,
                          current_page, current_level)
            current_title = line[3:].strip()
            current_level = 2
            current_lines = []
            current_page = page_counter

        elif line.startswith("### "):
            _flush_section(sections, current_title, current_lines,
                          current_page, current_level)
            current_title = line[4:].strip()
            current_level = 3
            current_lines = []
            current_page = page_counter

        else:
            current_lines.append(line)

    # Don't forget the last section
    _flush_section(sections, current_title, current_lines,
                  current_page, current_level)

    # Filter out empty sections
    sections = [s for s in sections if len(s.text.strip()) > 30]

    logger.info(f"  Extracted {len(sections)} sections")
    return sections


def _flush_section(
    sections: list,
    title: str,
    lines: list[str],
    page: int,
    level: int,
) -> None:
    """Helper — saves current section buffer to sections list."""
    text = "\n".join(lines).strip()
    if not text:
        return

    # Detect chunk type from content
    if "```" in text or "    " in text[:100]:
        chunk_type = "code"
    elif "|" in text and "---" in text:
        chunk_type = "table"
    else:
        chunk_type = "text"

    sections.append(ParsedSection(
        section_title=title,
        text=text,
        page_number=page,
        level=level,
        chunk_type=chunk_type,
    ))