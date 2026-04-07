# AI Auto Diag

AI-powered automotive diagnostic assistant for professional shop technicians. Uses Claude API + RAG pipeline to provide accurate, context-aware diagnostic help grounded in service manual data.

## Features

- **AI Diagnostics** — Describe symptoms or enter DTC codes and get expert-level diagnostic analysis
- **DTC Lookup** — Built-in OBD-II code database with causes, symptoms, and step-by-step diagnostic procedures
- **RAG Pipeline** — Upload service manual PDFs to get answers grounded in your actual documentation
- **Vehicle-Aware** — Responses tailored to the specific year/make/model/engine

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/UncleStalin728/AI-Auto-Diag.git
cd AI-Auto-Diag
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run the API

```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

### 4. Run the UI

```bash
streamlit run ui/streamlit_app.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/diagnose` | Submit a diagnostic query |
| GET | `/api/dtc/{code}` | Look up a DTC code |
| GET | `/api/dtc` | List all known codes |
| POST | `/api/documents/upload` | Upload a service manual PDF |
| GET | `/api/documents/stats` | Get indexing statistics |

### Example: Diagnose

```bash
curl -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Engine misfiring at idle, rough running, slight shake",
    "vehicle_year": 2018,
    "vehicle_make": "Ford",
    "vehicle_model": "F-150",
    "vehicle_engine": "5.0L V8",
    "dtc_codes": ["P0300", "P0301"]
  }'
```

## Project Structure

```
app/
  main.py              # FastAPI application
  config.py            # Environment settings
  api/routes/          # API endpoints
  core/
    claude_client.py   # Claude API integration
    rag_pipeline.py    # RAG: embed, retrieve, augment
    dtc_database.py    # DTC code database
    prompt_templates.py # Diagnostic prompts
  ingestion/           # PDF parsing and chunking
  models/              # Request/response schemas
data/
  dtc_codes/           # DTC definitions (JSON)
  manuals/             # Service manual PDFs (gitignored)
  chroma_db/           # Vector store (gitignored)
ui/
  streamlit_app.py     # Prototype UI
tests/                 # Test suite
```

## Tech Stack

- **Backend**: Python, FastAPI
- **AI**: Anthropic Claude API
- **RAG**: LangChain, ChromaDB, sentence-transformers
- **PDF Parsing**: PyMuPDF
- **UI**: Streamlit
- **Testing**: pytest

## Running Tests

```bash
pytest tests/ -v
```
