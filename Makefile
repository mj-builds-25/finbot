.PHONY: help install ingest eval dev test clean

help:
	@echo ""
	@echo "FinBot RAG — Available Commands"
	@echo "================================"
	@echo "  make install   Install all Python dependencies via uv"
	@echo "  make ingest    Run full document ingestion pipeline"
	@echo "  make eval      Run RAGAs evaluation suite"
	@echo "  make dev       Start FastAPI dev server"
	@echo "  make test      Run all tests"
	@echo "  make clean     Remove cache and temp files"
	@echo ""

install:
	cd backend && uv sync

ingest:
	cd backend && uv run --active python scripts/ingest_all.py

eval:
	cd backend && uv run --active python scripts/run_evals.py

dev:
	cd backend && uv run --active uvicorn src.api.main:app --reload --port 8000

test:
	cd backend && uv run --active pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cache cleaned"
