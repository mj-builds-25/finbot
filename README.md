# FinBot — Advanced RAG System for FinSolve Technologies

> Production-grade internal Q&A assistant with Role-Based Access Control,
> semantic routing, guardrails, and automated RAGAs evaluation.


---

## Architecture
```
User Query + JWT Role
       ↓
Input Guardrails (injection / PII / off-topic / rate limit)
       ↓
Semantic Router (5 routes — finance / engineering / marketing / hr / cross)
       ↓
Role Intersection (route ∩ user role → allowed collections)
       ↓
RBAC Retrieval (Qdrant filter applied at DB level)
       ↓
LLM Generation (Groq Llama 3.1 8B via LangChain)
       ↓
Output Guardrails (citation check / grounding check)
       ↓
Cited Response
```

## Tech Stack

| Layer | Technology |
|---|---|
| Document Parsing | Docling (hierarchical chunking) |
| Embeddings | fastembed (BAAI/bge-small-en-v1.5, 384-dim) |
| Vector Store | Qdrant Cloud |
| LLM | Groq (Llama 3.1 8B via OpenAI-compatible endpoint) |
| Orchestration | LangChain (LCEL) |
| Routing | semantic-router (cosine similarity) |
| Evaluation | RAGAs |
| Backend | FastAPI + JWT auth |
| Frontend | Next.js + Tailwind CSS |

## User Roles & Access

| Role | Collections Accessible |
|---|---|
| `employee` | General (HR policies, handbook) |
| `finance` | General + Finance |
| `engineering` | General + Engineering |
| `marketing` | General + Marketing |
| `c_level` | All collections |

## RBAC Security

Access is enforced **at the Qdrant retrieval layer** — not at the UI level.
Restricted chunks never reach the application or LLM context.
Verified with 18 adversarial tests including prompt injection attempts.

## Setup
```bash
# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/finbot-rag
cd finbot-rag

# 2. Install backend dependencies
cd backend && uv sync

# 3. Configure environment
cp .env.example .env
# Fill in: QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY

# 4. Run ingestion pipeline
make ingest

# 5. Start backend
make dev

# 6. Start frontend
cd ../frontend && npm install && npm run dev
```

## Demo Credentials

| Name | Email | Password | Role |
|---|---|---|---|
| Alice Johnson | alice@finsolve.com | demo123 | Employee |
| Bob Mitchell | bob@finsolve.com | demo123 | Finance |
| Carol Stevens | carol@finsolve.com | demo123 | Engineering |
| Dave Anderson | dave@finsolve.com | demo123 | Marketing |
| Eve Martinez | eve@finsolve.com | demo123 | C-Level |

## RAGAs Evaluation Results

See [docs/ragas-results.md](docs/ragas-results.md)

## Key Technical Decisions

- **fastembed over sentence-transformers** — avoids PyTorch (~2GB) in Codespaces
- **langchain-openai pointed at Groq** — bypasses langchain-groq proxies bug
- **RBAC at retrieval layer** — prompt injection cannot bypass DB-level filters
- **Docling table structure disabled for PDF** — libGL unavailable in Codespaces
- **qdrant-client v1.x** — uses query_points().points not client.search()
