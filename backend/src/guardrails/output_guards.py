"""
Output guardrails for FinBot.

Validates LLM answers BEFORE they are returned to the user.
These are non-blocking by design — they append warnings/disclaimers
rather than rejecting the answer entirely.

Guards implemented:
1. Citation check    — warn if no source document cited
2. Grounding check   — flag if answer contains figures not in context
"""

import re
import logging
from dataclasses import dataclass, field

from src.retrieval.retriever import RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class OutputGuardResult:
    """
    Result of output guardrail checks.
    Contains the (possibly modified) answer and any warnings.
    """
    answer: str                      # Final answer (may have warnings appended)
    passed: bool                     # True if all checks passed cleanly
    warnings: list[str] = field(default_factory=list)
    citation_present: bool = True
    grounding_flagged: bool = False


# ============================================================
# Citation check
# The LLM is instructed to cite sources.
# If it doesn't, we append a warning.
# ============================================================
CITATION_PATTERNS = [
    r"source[s]?\s*:",
    r"\[.*?\.(pdf|docx|md).*?\]",
    r"according to",
    r"from the",
    r"page\s+\d+",
    r"document",
]

CITATION_WARNING = (
    "\n\n⚠️ Note: This answer may not include complete source citations. "
    "Please verify the information against the original documents."
)


# ============================================================
# Grounding check
# If the answer contains specific financial figures, dates, or
# percentages, we verify they appear in the retrieved context.
# ============================================================
def _extract_numbers(text: str) -> set[str]:
    """Extract numeric values from text for grounding check."""
    # Match numbers like: ₹783, 28%, 99.99%, 2024, 12.3
    pattern = r"(?:₹|Rs\.?)?\s*[\d,]+(?:\.\d+)?(?:\s*(?:Crore|Lakh|%|cr|L))?"
    return set(re.findall(pattern, text, re.IGNORECASE))


GROUNDING_WARNING = (
    "\n\n⚠️ Disclaimer: This response contains specific figures or claims. "
    "Please verify against the cited source documents as some details "
    "may not be fully traceable to the retrieved context."
)


def check_citation(answer: str) -> tuple[bool, str]:
    """
    Check if the answer contains source citations.

    Returns:
        (citation_found, warning_message)
    """
    answer_lower = answer.lower()
    citation_found = any(
        re.search(pattern, answer_lower, re.IGNORECASE)
        for pattern in CITATION_PATTERNS
    )
    return citation_found, ("" if citation_found else CITATION_WARNING)


def check_grounding(
    answer: str,
    retrieved_chunks: list[RetrievalResult],
) -> tuple[bool, str]:
    """
    Check if specific figures in the answer appear in retrieved context.

    This is a heuristic check — not perfect but catches obvious
    hallucinations where the LLM invents numbers not in the context.

    Returns:
        (grounding_ok, warning_message)
    """
    if not retrieved_chunks:
        return True, ""

    # Extract numbers from the answer
    answer_numbers = _extract_numbers(answer)
    if not answer_numbers:
        return True, ""  # No specific figures to verify

    # Build a combined context string from all chunks
    full_context = " ".join(r.text for r in retrieved_chunks)

    # Check if answer numbers appear in the context
    ungrounded = []
    for num in answer_numbers:
        # Clean the number for comparison
        clean_num = re.sub(r'\s+', '', num)
        if clean_num and len(clean_num) > 2:  # Skip tiny numbers
            if clean_num not in re.sub(r'\s+', '', full_context):
                ungrounded.append(num)

    if len(ungrounded) > 2:  # Allow minor mismatches
        logger.warning(
            f"Grounding check: {len(ungrounded)} figures "
            f"not traceable to context"
        )
        return False, GROUNDING_WARNING

    return True, ""


def run_output_guards(
    answer: str,
    retrieved_chunks: list[RetrievalResult],
) -> OutputGuardResult:
    """
    Run all output guardrails on the LLM answer.

    Non-blocking — warnings are appended to the answer
    rather than rejecting it. The frontend displays these
    as warning banners.

    Args:
        answer:           The raw LLM-generated answer
        retrieved_chunks: Chunks that were fed to the LLM

    Returns:
        OutputGuardResult with final answer and any warnings
    """
    warnings = []
    final_answer = answer

    # Check 1: Citation presence
    citation_ok, citation_warning = check_citation(answer)
    if not citation_ok:
        warnings.append("No source citation detected")
        final_answer += citation_warning
        logger.info("Output guard: citation warning added")

    # Check 2: Grounding check
    grounding_ok, grounding_warning = check_grounding(answer, retrieved_chunks)
    if not grounding_ok:
        warnings.append("Grounding check flagged unverifiable figures")
        final_answer += grounding_warning
        logger.info("Output guard: grounding warning added")

    return OutputGuardResult(
        answer=final_answer,
        passed=len(warnings) == 0,
        warnings=warnings,
        citation_present=citation_ok,
        grounding_flagged=not grounding_ok,
    )