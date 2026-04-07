from pydantic import BaseModel, Field
from typing import Optional


# ── Diagnose ──────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    """Request for AI diagnostic assistance."""

    query: str = Field(..., description="Technician's question or symptom description")
    vehicle_year: Optional[int] = Field(None, description="Vehicle model year")
    vehicle_make: Optional[str] = Field(None, description="Vehicle manufacturer")
    vehicle_model: Optional[str] = Field(None, description="Vehicle model name")
    vehicle_engine: Optional[str] = Field(None, description="Engine type (e.g., 5.3L V8)")
    dtc_codes: Optional[list[str]] = Field(None, description="Active DTC codes from scan tool")
    use_rag: bool = Field(True, description="Whether to search service manuals for context")


class DiagnoseResponse(BaseModel):
    """AI diagnostic response."""

    diagnosis: str = Field(..., description="AI-generated diagnostic analysis")
    confidence: str = Field(..., description="Confidence level: high, medium, low")
    suggested_tests: list[str] = Field(default_factory=list, description="Recommended diagnostic tests")
    possible_causes: list[str] = Field(default_factory=list, description="Likely root causes")
    related_dtcs: list[str] = Field(default_factory=list, description="Related DTC codes to check")
    sources: list[str] = Field(default_factory=list, description="Source documents used")


# ── DTC ───────────────────────────────────────────────────

class DTCInfo(BaseModel):
    """Diagnostic Trouble Code information."""

    code: str = Field(..., description="DTC code (e.g., P0300)")
    description: str = Field(..., description="Code description")
    category: str = Field(..., description="Category: powertrain, chassis, body, network")
    severity: str = Field(..., description="Severity: critical, moderate, minor, informational")
    common_causes: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    diagnostic_steps: list[str] = Field(default_factory=list)


class DTCLookupResponse(BaseModel):
    """Response for DTC code lookup."""

    code: str
    found: bool
    info: Optional[DTCInfo] = None


# ── Documents ─────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Response after uploading a service manual."""

    filename: str
    chunks_created: int
    status: str = "indexed"


class RAGContext(BaseModel):
    """Retrieved context from RAG pipeline."""

    content: str
    source: str
    relevance_score: float
