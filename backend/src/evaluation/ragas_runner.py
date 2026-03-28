"""
RAGAs evaluation runner for FinBot.

Measures RAG pipeline quality across 5 metrics using an LLM judge.
Runs an ablation study comparing 4 pipeline configurations.

Ablation configurations:
    1. baseline    — basic RAG, no routing, no guardrails
    2. with_router — adds semantic routing
    3. with_rbac   — adds RBAC filtering (always on in our system)
    4. full_system — routing + RBAC + guardrails (production config)

Usage:
    cd backend/
    uv run --active python -m scripts.run_evals
"""

import os
os.environ["RAGAS_DO_NOT_TRACK"] = "true"  # disables analytics that crashes on fastembed

import sys
import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass

# ── Must set before any ragas/openai imports ─────────────────
# RAGAs tries to init OpenAI embeddings at import time.
# These must be set BEFORE importing ragas or langchain
from src.config import GROQ_API_KEY, GROQ_BASE_URL
os.environ["OPENAI_API_KEY"]  = GROQ_API_KEY
os.environ["OPENAI_BASE_URL"] = GROQ_BASE_URL

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    context_precision,
    context_recall,
    # answer_correctness,
)
from ragas.llms import LangchainLLMWrapper
# from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from langchain_openai import ChatOpenAI
# from langchain_community.embeddings import FastEmbedEmbeddings

from src.retrieval.retriever import search
from src.rag.prompts import build_prompt
from src.config import GROQ_BASE_URL, GROQ_MODEL

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"
RESULTS_PATH      = Path(__file__).parent / "results"
RESULTS_PATH.mkdir(exist_ok=True)


# ── Data classes ─────────────────────────────────────────────
@dataclass
class EvalSample:
    question:     str
    ground_truth: str
    answer:       str
    contexts:     list[str]
    role:         str
    collection:   str


# ── Judge LLM + embeddings ────────────────────────────────────
def _get_llm() -> LangchainLLMWrapper:
    """Groq via OpenAI-compatible endpoint, wrapped for RAGAs."""
    llm = ChatOpenAI(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        temperature=0.0,
        max_tokens=1024,
        max_retries=6,
    )
    return LangchainLLMWrapper(llm)


# def _get_embeddings() -> LangchainEmbeddingsWrapper:
#     """Local fastembed — no API key, no network calls."""
#     return LangchainEmbeddingsWrapper(
#         FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
#     )


# ── Ground truth ─────────────────────────────────────────────
def load_ground_truth(n: int | None = None) -> list[dict]:
    with open(GROUND_TRUTH_PATH) as f:
        data = json.load(f)
    return data[:n] if n else data


# ── Pipeline runner ───────────────────────────────────────────
def _run_one_sample(sample: dict, use_full_pipeline: bool) -> EvalSample | None:
    """
    Run the RAG pipeline on one ground-truth sample.
    Returns None if something fails — caller skips that sample.
    """
    question = sample["question"]
    role     = sample["role"]

    try:
        if use_full_pipeline:
            from src.rag.chain import run_rag_chain
            response = run_rag_chain(query=question, role=role)
            answer   = response.answer
            # Re-fetch contexts so RAGAs has the raw text
            results  = search(query=question, role=role, top_k=5)
            contexts = [r.text for r in results] or ["No context retrieved"]

        else:
            # Baseline: direct retrieval, no routing, no guardrails
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage

            results  = search(query=question, role=role, top_k=5)
            contexts = [r.text for r in results] or ["No context retrieved"]

            if not results:
                answer = "No relevant documents found."
            else:
                messages = build_prompt(question, results, role)
                llm = ChatOpenAI(
                    model=GROQ_MODEL,
                    api_key=GROQ_API_KEY,
                    base_url=GROQ_BASE_URL,
                    temperature=0.1,
                    max_tokens=1024,
                    max_retries=6,
                )
                lc_msgs = [
                    SystemMessage(content=messages[0]["content"]),
                    HumanMessage(content=messages[1]["content"]),
                ]
                resp   = llm.invoke(lc_msgs)
                answer = resp.content

        return EvalSample(
            question=question,
            ground_truth=sample["ground_truth"],
            answer=answer,
            contexts=contexts,
            role=role,
            collection=sample["collection"],
        )

    except Exception as e:
        logger.error(f"  ✗ Failed: {question[:60]} — {e}")
        return None


def _collect_samples(
    ground_truth: list[dict],
    use_full_pipeline: bool,
    delay: float = 2.0,
) -> list[EvalSample]:
    """Run pipeline on all samples, sleeping between each to avoid rate limits."""
    samples = []
    for i, gt in enumerate(ground_truth, 1):
        logger.info(
            f"  [{i}/{len(ground_truth)}] "
            f"role={gt['role']} | {gt['question'][:55]}..."
        )
        sample = _run_one_sample(gt, use_full_pipeline)
        if sample:
            samples.append(sample)
        if i < len(ground_truth):
            time.sleep(delay)
    return samples


# ── RAGAs evaluation ─────────────────────────────────────────
def _to_dataset(samples: list[EvalSample]) -> Dataset:
    return Dataset.from_dict({
        "question":     [s.question     for s in samples],
        "answer":       [s.answer       for s in samples],
        "contexts":     [s.contexts     for s in samples],
        "ground_truth": [s.ground_truth for s in samples],
    })


METRICS = [faithfulness, context_precision, context_recall]


def _evaluate(dataset: Dataset, label: str) -> dict:
    """
    Run RAGAs evaluation.

    Key settings:
      - LLM set explicitly on every metric (required for ragas 0.2+)
      - max_workers=1  → sequential calls, avoids Groq 429 storms
      - max_wait=300   → up to 5 min wait per call (handles slow retries)
    """
    logger.info(f"Running RAGAs for: {label}")

    llm        = _get_llm()
    # embeddings = _get_embeddings()

    # Inject LLM into every metric explicitly
    for metric in METRICS:
        metric.llm = llm

    run_config = RunConfig(
        max_workers=1,
        max_wait=300,
        timeout=180,
    )

    try:
        result = evaluate(
            dataset=dataset,
            metrics=METRICS,
            llm=llm,
            # embeddings=embeddings,
            run_config=run_config,
            raise_exceptions=True,
        )

        import numpy as np

        def _safe_score(val) -> float:
            if isinstance(val, list):
                valid = [v for v in val if v is not None and not (isinstance(v, float) and np.isnan(v))]
                return round(float(np.mean(valid)) if valid else 0.0, 4)
            return round(float(val), 4) if val is not None else 0.0

        scores = {
            "faithfulness":      _safe_score(result["faithfulness"]),
            "context_precision": _safe_score(result["context_precision"]),
            "context_recall":    _safe_score(result["context_recall"]),
        }
        logger.info(f"Scores → {scores}")
        return scores

    except Exception as e:
        logger.error(f"RAGAs failed for {label}: {e}")
        return {
            "faithfulness": 0.0, "context_precision": 0.0,
            "context_recall": 0.0, 
            "error": str(e),
        }


# ── Ablation study ────────────────────────────────────────────
CONFIGS = [
    {
        "key":              "1_baseline",
        "label":            "Baseline RAG (no routing, no guardrails)",
        "use_full_pipeline": False,
    },
    {
        "key":              "2_full_system",
        "label":            "Full System (routing + RBAC + guardrails)",
        "use_full_pipeline": True,
    },
]


def run_ablation_study(sample_size: int = 40) -> dict:
    logger.info("=" * 55)
    logger.info("  FinBot — RAGAs Ablation Study")
    logger.info("=" * 55)
    logger.info(f"  Samples per config : {sample_size}")
    logger.info(f"  Metrics            : {[m.name for m in METRICS]}")
    logger.info("=" * 55)

    ground_truth = load_ground_truth(sample_size)
    results      = {}

    for cfg in CONFIGS:
        logger.info(f"\nConfig: {cfg['label']}")
        logger.info("-" * 40)

        samples = _collect_samples(
            ground_truth,
            use_full_pipeline=cfg["use_full_pipeline"],
            delay=3.0,          # 3 s between Groq calls
        )

        if not samples:
            logger.error("  No samples collected — skipping evaluation")
            results[cfg["key"]] = {
                "label": cfg["label"],
                "scores": {},
                "samples_evaluated": 0,
            }
            continue

        # Extra pause before firing RAGAs judge calls
        logger.info("  Pausing 10 s before RAGAs evaluation...")
        time.sleep(10)

        dataset = _to_dataset(samples)
        scores  = _evaluate(dataset, cfg["label"])

        results[cfg["key"]] = {
            "label":             cfg["label"],
            "scores":            scores,
            "samples_evaluated": len(samples),
        }

    return results


# ── Markdown table ────────────────────────────────────────────
def format_ablation_table(ablation_results: dict) -> str:
    metric_keys = [
        "faithfulness",
        "context_precision",
        "context_recall",
        # "answer_correctness",
    ]
    header = (
        "| Configuration | Faithfulness | "
        "Context Precision | Context Recall | "
    )
    sep = "|---|---|---|---|"

    rows = [
        "## RAGAs Ablation Study Results\n",
        header,
        sep,
    ]

    for cfg_result in ablation_results.values():
        label  = cfg_result["label"]
        scores = cfg_result.get("scores", {})
        row    = f"| {label} "
        for k in metric_keys:
            v = scores.get(k, 0.0)
            row += f"| {v:.4f} "
        row += "|"
        rows.append(row)

    rows.append(
        f"\n*Evaluated on {list(ablation_results.values())[0].get('samples_evaluated', 0)} "
        f"samples per configuration.*"
    )
    return "\n".join(rows)