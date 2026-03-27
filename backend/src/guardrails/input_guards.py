"""
Input guardrails for FinBot.

Validates user queries BEFORE they reach the RAG chain.
All checks run in sequence — first failure blocks the query.

Guards implemented:
1. Rate limiting     — max 20 queries per session
2. Off-topic detection — must relate to FinSolve business domains
3. Prompt injection  — detect attempts to override system behavior
4. PII detection     — block queries containing personal data

Each guard returns a GuardResult with:
    passed  — True if query is safe to proceed
    blocked — True if query should be rejected
    reason  — Why it was blocked (shown to user)
    warning — Non-blocking concern (logged but not blocked)
"""

import re
import logging
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class GuardResult:
    """Result of a guardrail check."""
    passed: bool           # True = safe to proceed
    blocked: bool          # True = reject this query
    guard_name: str        # Which guard produced this result
    reason: str = ""       # User-facing message if blocked
    warning: str = ""      # Non-blocking warning (logged only)


@dataclass
class InputGuardResult:
    """
    Aggregated result of all input guardrail checks.
    Contains the final decision and all individual results.
    """
    allowed: bool                        # Overall: safe to proceed?
    blocked_by: str | None = None        # Which guard blocked it
    message: str = ""                    # User-facing message
    warning: str = ""                    # Non-blocking warning
    results: list[GuardResult] = field(default_factory=list)


# ============================================================
# In-memory session rate limiter
# In production this would use Redis — for now a simple dict
# ============================================================
_session_counts: dict[str, int] = defaultdict(int)
RATE_LIMIT_MAX = 20


def reset_session(session_id: str) -> None:
    """Reset query count for a session. Call on logout."""
    _session_counts.pop(session_id, None)


# ============================================================
# Off-topic detection
# Queries must relate to FinSolve business domains.
# We use keyword matching — fast and explainable.
# ============================================================
BUSINESS_KEYWORDS = [
    # Finance domain
    "revenue", "budget", "profit", "expense", "financial", "vendor",
    "payment", "invoice", "cost", "salary", "payroll", "tax", "audit",
    "ebitda", "margin", "cash flow", "quarter", "annual", "fiscal",

    # Engineering domain
    "system", "architecture", "api", "database", "deployment", "incident",
    "outage", "sla", "uptime", "latency", "sprint", "velocity", "bug",
    "pipeline", "kubernetes", "microservice", "service", "infrastructure",

    # Marketing domain
    "campaign", "customer", "acquisition", "roi", "marketing", "brand",
    "engagement", "conversion", "churn", "retention", "cac", "ltv",
    "influencer", "social media", "channel",

    # HR/General domain
    "leave", "policy", "employee", "onboarding", "benefit", "insurance",
    "work from home", "remote", "hybrid", "performance", "review",
    "promotion", "training", "reimbursement", "travel", "holiday",
    "resignation", "notice period", "handbook", "code of conduct",

    # Company domain
    "finsolve", "company", "department", "team", "manager", "role",
    "access", "document", "report", "data",
]

OFF_TOPIC_RESPONSE = (
    "I can only answer questions related to FinSolve Technologies' "
    "internal documentation — HR policies, financial reports, "
    "engineering systems, and marketing data. "
    "Please rephrase your question or contact the relevant department."
)


# ============================================================
# Prompt injection patterns
# Detect attempts to override system behavior or bypass RBAC
# ============================================================
INJECTION_PATTERNS = [
    r"ignore\s+(your|all|previous|the)\s+(instructions?|rules?|prompt|context)",
    r"disregard\s+(your|all|previous|the)\s+(instructions?|rules?|prompt)",
    r"forget\s+(your|all|previous|the)\s+(instructions?|rules?|training)",
    r"act\s+as\s+(a\s+)?(different|new|another|unrestricted)",
    r"you\s+are\s+now\s+(a\s+)?(different|new|another)",
    r"override\s+(rbac|access|security|restrictions?|controls?)",
    r"bypass\s+(rbac|access|security|restrictions?|controls?)",
    r"show\s+me\s+all\s+documents",
    r"no\s+restrictions?",
    r"without\s+restrictions?",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
]

INJECTION_RESPONSE = (
    "This query appears to contain instructions that attempt to override "
    "system behavior. Such requests are not permitted. "
    "Please ask a genuine question about FinSolve's business."
)


# ============================================================
# PII patterns
# Detect personal data submitted in queries
# ============================================================
PII_PATTERNS = {
    "aadhaar_number":    r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "pan_card":          r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "email_address":     r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone_number":      r"\b(\+91|91|0)?[6-9]\d{9}\b",
    "bank_account":      r"\b\d{9,18}\b",
    "credit_card":       r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
}

PII_RESPONSE = (
    "Your query appears to contain personal information "
    "(such as an ID number, email, or phone number). "
    "Please remove any personal data from your query and try again."
)


# ============================================================
# Guard functions
# ============================================================

def check_rate_limit(session_id: str) -> GuardResult:
    """Block if session has exceeded the query limit."""
    _session_counts[session_id] += 1
    count = _session_counts[session_id]

    if count > RATE_LIMIT_MAX:
        return GuardResult(
            passed=False,
            blocked=True,
            guard_name="rate_limiter",
            reason=(
                f"You have exceeded the maximum of {RATE_LIMIT_MAX} "
                f"queries per session. Please start a new session."
            ),
        )

    if count > RATE_LIMIT_MAX * 0.8:
        return GuardResult(
            passed=True,
            blocked=False,
            guard_name="rate_limiter",
            warning=(
                f"Approaching rate limit: {count}/{RATE_LIMIT_MAX} queries used."
            ),
        )

    return GuardResult(passed=True, blocked=False, guard_name="rate_limiter")


def check_off_topic(query: str) -> GuardResult:
    """Block queries unrelated to FinSolve business domains."""
    query_lower = query.lower()

    # Check if any business keyword appears in the query
    has_business_context = any(
        keyword in query_lower for keyword in BUSINESS_KEYWORDS
    )

    if has_business_context:
        return GuardResult(
            passed=True,
            blocked=False,
            guard_name="off_topic_detector",
        )

    # Short queries might be follow-ups — be lenient
    if len(query.split()) <= 4:
        return GuardResult(
            passed=True,
            blocked=False,
            guard_name="off_topic_detector",
            warning="Short query — may be off-topic but allowing through",
        )

    return GuardResult(
        passed=False,
        blocked=True,
        guard_name="off_topic_detector",
        reason=OFF_TOPIC_RESPONSE,
    )


def check_prompt_injection(query: str) -> GuardResult:
    """Detect and block prompt injection attempts."""
    query_lower = query.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.warning(f"Prompt injection detected: '{query[:80]}'")
            return GuardResult(
                passed=False,
                blocked=True,
                guard_name="injection_detector",
                reason=INJECTION_RESPONSE,
            )

    return GuardResult(
        passed=True,
        blocked=False,
        guard_name="injection_detector",
    )


def check_pii(query: str) -> GuardResult:
    """Detect PII in the query and block if found."""
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"PII detected ({pii_type}) in query")
            return GuardResult(
                passed=False,
                blocked=True,
                guard_name="pii_detector",
                reason=PII_RESPONSE,
            )

    return GuardResult(
        passed=True,
        blocked=False,
        guard_name="pii_detector",
    )


# ============================================================
# Main entry point
# ============================================================

def run_input_guards(
    query: str,
    session_id: str = "default",
) -> InputGuardResult:
    """
    Run all input guardrails in sequence.

    Checks run in this order:
    1. Rate limit  — cheapest check, no regex
    2. Injection   — security critical, runs before off-topic
    3. PII         — privacy check
    4. Off-topic   — most lenient, runs last

    Args:
        query:      The user's raw query string
        session_id: Session identifier for rate limiting

    Returns:
        InputGuardResult — allowed=True means safe to proceed
    """
    results = []
    warnings = []

    # Run all guards in order
    guards = [
        lambda: check_rate_limit(session_id),
        lambda: check_prompt_injection(query),
        lambda: check_pii(query),
        lambda: check_off_topic(query),
    ]

    for guard_fn in guards:
        result = guard_fn()
        results.append(result)

        if result.warning:
            warnings.append(result.warning)

        if result.blocked:
            logger.info(
                f"Query blocked by {result.guard_name}: "
                f"'{query[:60]}'"
            )
            return InputGuardResult(
                allowed=False,
                blocked_by=result.guard_name,
                message=result.reason,
                warning=" | ".join(warnings),
                results=results,
            )

    return InputGuardResult(
        allowed=True,
        blocked_by=None,
        message="",
        warning=" | ".join(warnings),
        results=results,
    )