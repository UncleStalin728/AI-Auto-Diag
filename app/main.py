from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import diagnose, dtc, documents

app = FastAPI(
    title="AI Auto Diag",
    description="AI-powered automotive diagnostic assistant using Claude API + RAG",
    version="0.1.0",
)

# CORS — allow Streamlit and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(diagnose.router, prefix="/api", tags=["Diagnostics"])
app.include_router(dtc.router, prefix="/api", tags=["DTC Codes"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])


@app.get("/")
async def root():
    return {
        "service": "AI Auto Diag",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
