"""
Runner script for the full document ingestion pipeline.


"""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

from src.ingestion.ingest_pipeline import run_ingestion

if __name__ == "__main__":
    results = run_ingestion()

    # Exit with error code if any documents failed
    errors = [r for r in results if r["status"] == "error"]
    if errors:
        print("\n❌ Some documents failed to ingest:")
        for e in errors:
            print(f"   {e['file']}: {e.get('error', 'unknown error')}")
        sys.exit(1)
    else:
        print("\n✅ All documents ingested successfully")
        sys.exit(0)