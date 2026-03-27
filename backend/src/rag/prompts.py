"""
Prompt templates for FinBot RAG chain.

Two key prompts:
1. SYSTEM_PROMPT — sets the assistant's behavior and constraints
2. format_context() — formats retrieved chunks into the prompt

Design principles:
- Anti-hallucination: LLM must only use provided context
- Citation enforcement: every answer must cite source + page
- Role awareness: LLM knows who it's talking to
- Graceful degradation: clear message when context is empty
"""

from src.retrieval.retriever import RetrievalResult


SYSTEM_PROMPT = """You are FinBot, an internal knowledge assistant for \
FinSolve Technologies.

STRICT RULES — follow these without exception:
1. Answer ONLY using the information in the CONTEXT section below.
2. If the context does not contain enough information to answer \
the question, say exactly:
   "I don't have enough information in the available documents \
to answer this question."
3. NEVER make up facts, figures, dates, or statistics.
4. ALWAYS cite your sources at the end of your answer using this format:
   Sources: [document_name, page X] | [document_name, page Y]
5. Keep answers concise and professional.
6. If the user asks about something outside FinSolve's business \
(e.g. cricket scores, poems, general knowledge), politely decline.

You are talking to a FinSolve employee. Be helpful, accurate, and professional.
"""


def format_context(results: list[RetrievalResult]) -> str:
    """
    Format retrieved chunks into a structured context block
    for the LLM prompt.

    Each chunk is labeled with its source and section so the
    LLM can cite them accurately in its response.

    Args:
        results: List of RetrievalResult from the retriever

    Returns:
        Formatted string ready to inject into the prompt
    """
    if not results:
        return "No relevant documents found in your authorized collections."

    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(
            f"[{i}] Source: {result.source_document} | "
            f"Section: {result.section_title} | "
            f"Page: {result.page_number}\n"
            f"{result.text}"
        )

    return "\n\n---\n\n".join(context_parts)


def build_prompt(
    query: str,
    results: list[RetrievalResult],
    role: str,
) -> list[dict]:
    """
    Build the full message list for the LLM API call.

    Returns a list of messages in OpenAI chat format:
    [
        {"role": "system", "content": "..."},
        {"role": "user",   "content": "..."},
    ]

    Args:
        query:   User's question
        results: Retrieved chunks from RBAC retriever
        role:    User's role (included in context for transparency)

    Returns:
        Messages list ready for langchain or direct API call
    """
    context = format_context(results)

    user_message = f"""CONTEXT (from your authorized document collections):

{context}

---

QUESTION: {query}

Remember: Answer only from the context above. Cite your sources."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]