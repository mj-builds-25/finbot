
"""
Step 1 verification script.
Run this to confirm Qdrant Cloud connection works and collection is ready.

Usage:
    cd backend/
    uv run --active python scripts/test_connection.py
"""

import sys
import logging
logging.basicConfig(level="INFO", format="%(levelname)s: %(message)s")

from src.retrieval.qdrant_store import get_client, create_collection_if_not_exists, verify_connection
from src.config import COLLECTION_NAME, QDRANT_URL, EMBEDDING_DIM

def main():
    print("\n" + "="*55)
    print("  FinBot — Qdrant Connection Test")
    print("="*55)
    print(f"  URL        : {QDRANT_URL[:40]}...")
    print(f"  Collection : {COLLECTION_NAME}")
    print(f"  Vector dim : {EMBEDDING_DIM}")
    print("="*55 + "\n")

    # Step 1: connect
    print("1. Connecting to Qdrant Cloud...")
    try:
        client = get_client()
        collections = client.get_collections().collections
        print(f"   ✅ Connected — {len(collections)} collection(s) found\n")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        sys.exit(1)

    # Step 2: create collection
    print("2. Setting up collection...")
    created = create_collection_if_not_exists(client)
    if created:
        print(f"   ✅ Collection '{COLLECTION_NAME}' created fresh\n")
    else:
        print(f"   ✅ Collection '{COLLECTION_NAME}' already exists\n")

    # Step 3: verify
    print("3. Verifying collection health...")
    result = verify_connection(client)
    if result["status"] == "ok":
        print(f"   ✅ Status       : {result['status']}")
        print(f"   ✅ Collection   : {result['collection']}")
        print(f"   ✅ Points count : {result['points_count']}")
        print(f"   ✅ Vector size  : {result['vector_size']}")
        print(f"   ✅ Distance     : {result['distance']}")
    else:
        print(f"   ❌ Health check failed: {result['error']}")
        sys.exit(1)

    print("\n" + "="*55)
    print("  ✅ Step 1 complete — Qdrant is ready")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
