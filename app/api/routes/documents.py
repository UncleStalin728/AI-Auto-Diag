"""Document upload and management endpoints for the RAG pipeline."""

import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import DocumentUploadResponse
from app.core.rag_pipeline import get_rag_pipeline

router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "data" / "manuals"


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a service manual PDF for indexing into the RAG pipeline.

    The PDF will be:
    1. Saved to data/manuals/
    2. Parsed and split into chunks
    3. Embedded and stored in ChromaDB

    Once indexed, the content will be used to augment diagnostic queries.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Save the uploaded file
    file_path = UPLOAD_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Ingest into RAG pipeline
    try:
        pipeline = get_rag_pipeline()
        if pipeline is None:
            raise HTTPException(status_code=503, detail="RAG pipeline unavailable — ChromaDB not installed")
        chunks_created = pipeline.ingest_pdf(
            file_path,
            metadata={"original_filename": file.filename},
        )
    except Exception as e:
        # Clean up saved file if ingestion fails
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")

    return DocumentUploadResponse(
        filename=file.filename,
        chunks_created=chunks_created,
        status="indexed",
    )


@router.get("/documents/stats")
async def document_stats():
    """Get statistics about indexed documents."""
    try:
        pipeline = get_rag_pipeline()
        if pipeline is None:
            return {"total_chunks": 0, "collection_name": "N/A", "note": "ChromaDB not installed"}
        return pipeline.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
