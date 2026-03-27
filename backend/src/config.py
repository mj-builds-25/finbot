"""
Central configuration loader for FinBot.
Reads all environment variables from .env in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env relative to this file's location
# Works whether you run from backend/ or anywhere else
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


# --- Qdrant ---
QDRANT_URL: str = os.environ["QDRANT_URL"]
QDRANT_API_KEY: str = os.environ["QDRANT_API_KEY"]
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "finbot_v1")

# --- Groq / LLM ---
GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# --- Embeddings ---
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))

# --- App ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
