# AI Auto Diag

## 1. Purpose
AI-powered diagnostic assistant for shop techs. Takes symptoms and/or DTC codes for a specific year/make/model/engine and returns diagnostic analysis grounded in uploaded service manual PDFs via a RAG pipeline. Foundation for future shop-tools that need LLM + retrieval (wiring-diagram assistant, service-data lookup).

## 2. Stack
- Python 3, **FastAPI** + Uvicorn (API), **Streamlit** (prototype UI)
- Anthropic Claude API (via `anthropic` SDK)
- RAG: LangChain, ChromaDB, sentence-transformers
- PDF: PyMuPDF, pdfplumber
- Testing: pytest, pytest-asyncio, httpx
- Storage: JSON for DTCs, ChromaDB vector store on disk (gitignored)

## 3. How to run
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # add ANTHROPIC_API_KEY

uvicorn app.main:app --reload        # API → http://localhost:8000  (docs: /docs)
streamlit run ui/streamlit_app.py    # UI

pytest tests/ -v
```

## 4. AutoLeap integration
Not applicable yet. This is the AI infrastructure project; AutoLeap-driven data (vehicle history, recent DTCs) is a future integration point for the Service Data Lookup project that will build on top of this.

## 5. Key files
- `app/main.py` — FastAPI app entrypoint
- `app/config.py` — env settings (Pydantic Settings)
- `app/api/routes/` — endpoints: `/api/diagnose`, `/api/dtc/{code}`, `/api/dtc`, `/api/documents/upload`, `/api/documents/stats`
- `app/core/claude_client.py` — Claude API integration
- `app/core/rag_pipeline.py` — embed / retrieve / augment
- `app/core/dtc_database.py` — DTC lookup
- `app/core/prompt_templates.py` — diagnostic prompts
- `app/ingestion/` — PDF parsing + chunking
- `app/models/` — request/response schemas
- `data/dtc_codes/` — DTC JSON
- `data/manuals/` — service-manual PDFs (gitignored)
- `data/chroma_db/` — vector store (gitignored)
- `ui/streamlit_app.py` — prototype UI
- `scripts/seed_torque_db.py` — torque spec DB seeding

## 6. Conventions
- Claude SDK usage: **include prompt caching** on manual chunks + system prompts (big reduction in cost and latency once corpus grows)
- Prefer latest Claude model IDs (Opus `claude-opus-4-7`, Sonnet `claude-sonnet-4-6`, Haiku `claude-haiku-4-5-20251001`)
- Request/response schemas: Pydantic models in `app/models/`, no inline dicts in routes
- Keep ingestion code stream-friendly — manuals are large, don't hold full PDFs in memory
- Tests use `httpx` + `pytest-asyncio` against the FastAPI app

## 7. Don't touch
- `.env` (contains `ANTHROPIC_API_KEY`)
- `data/manuals/` and `data/chroma_db/` — gitignored, can be large; don't commit
- Streamlit UI is a prototype — don't build real features there; real UI goes in a React/Vite project later

## 8. Current state (refreshed by /revise-claude-md)
_As of 2026-04-21:_
- API + Streamlit UI operational; diagnose endpoint works against uploaded manuals
- **Next experiment**: test Claude vision on an actual wiring diagram (ALLDATA/Mitchell1 screenshot or service-manual PDF) before writing code for the Electrical Diagram Assistant — this project is the likely home for that extension
- No blockers known

---
## Git workflow
- Work on `main` — solo
- Commit + push before switching computers
- Remote: github.com/UncleStalin728/AI-Auto-Diag
