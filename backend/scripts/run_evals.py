"""
RAGAs evaluation runner script for FinBot.

Runs the ablation study and saves results to:
  - src/evaluation/results/ablation_results.json
  - docs/ragas-results.md  (for the README)

Usage:
    cd backend/
    uv run --active python -m scripts.run_evals

    # Quick test with 5 samples:
    uv run --active python -m scripts.run_evals --quick
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

from src.evaluation.ragas_runner import (
    run_ablation_study,
    format_ablation_table,
    RESULTS_PATH,
)

DOCS_PATH = Path(__file__).resolve().parent.parent.parent / "docs"


def main():
    # Quick mode for testing (5 samples per config)
    quick = "--quick" in sys.argv
    sample_size = 5 if quick else 40

    print("\n" + "="*55)
    print("  FinBot — RAGAs Evaluation Suite")
    print("="*55)
    print(f"  Mode        : {'Quick (5 samples)' if quick else 'Full (40 samples)'}")
    print(f"  Results dir : {RESULTS_PATH}")
    print("="*55 + "\n")

    if quick:
        print("⚡ Quick mode — using 5 samples per config\n")

    # Run ablation study
    results = run_ablation_study(sample_size=sample_size)

    # Save JSON results
    results_file = RESULTS_PATH / "ablation_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results saved: {results_file}")

    # Format and print table
    table = format_ablation_table(results)
    print("\n" + "="*55)
    print(table)
    print("="*55)

    # Save to docs/ragas-results.md
    docs_file = DOCS_PATH / "ragas-results.md"
    with open(docs_file, "w") as f:
        f.write("# FinBot — RAGAs Evaluation Results\n\n")
        f.write(table)
        f.write("\n\n## Notes\n\n")
        f.write("- Evaluation run against 40 ground truth QA pairs\n")
        f.write("- Judge LLM: Groq Llama 3.1 8B\n")
        f.write("- Scores range 0-1, higher is better\n")
    print(f"✅ Markdown saved: {docs_file}")

    print("\n✅ Evaluation complete")


if __name__ == "__main__":
    main()