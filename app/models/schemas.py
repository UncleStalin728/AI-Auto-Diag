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


# ── VIN Decoding ─────────────────────────────────────────

class VINDecodeResponse(BaseModel):
    """Response from VIN decoding."""

    vin: str = Field(..., description="The 17-character VIN")
    year: Optional[int] = Field(None, description="Model year")
    make: Optional[str] = Field(None, description="Vehicle manufacturer")
    model: Optional[str] = Field(None, description="Vehicle model")
    engine: Optional[str] = Field(None, description="Engine description (e.g., 2.4L I4)")
    displacement_l: Optional[float] = Field(None, description="Engine displacement in liters")
    cylinders: Optional[int] = Field(None, description="Number of cylinders")
    drive_type: Optional[str] = Field(None, description="Drive type (FWD, RWD, AWD, 4WD)")
    transmission: Optional[str] = Field(None, description="Transmission type")
    torque_specs_available: bool = Field(False, description="Whether torque specs exist for this vehicle")
    success: bool = Field(..., description="Whether VIN decode was successful")
    error: Optional[str] = Field(None, description="Error message if decode failed")


# ── Torque Specs ─────────────────────────────────────────

class TorqueStage(BaseModel):
    """A single stage in a multi-stage tightening procedure."""

    stage: int = Field(..., description="Stage number (1-based)")
    value: float = Field(..., description="Torque value or angle")
    unit: str = Field(..., description="ft-lbs, Nm, or degrees")


class TorqueSpec(BaseModel):
    """Torque specification for a fastener/component."""

    id: str = Field(..., description="Unique ID: make_model_engine_component slug")
    vehicle: str = Field(..., description="Human-readable vehicle description")
    year_range: list[int] = Field(..., description="[start_year, end_year] inclusive")
    make: str
    model: str
    engine: str
    component: str = Field(..., description="Fastener/component name (e.g., Cylinder Head Bolt)")
    category: str = Field(..., description="engine, brakes, suspension, drivetrain, general")
    torque_ft_lbs: float | None = Field(None, description="Primary torque in ft-lbs")
    torque_nm: float | None = Field(None, description="Primary torque in Nm")
    torque_sequence: str = Field("", description="Tightening sequence/pattern description")
    stages: list[TorqueStage] = Field(default_factory=list, description="Multi-stage procedure")
    tty: bool = Field(False, description="Torque-to-yield fastener")
    reusable: bool = Field(True, description="Whether the fastener can be reused")
    thread_size: str = Field("", description="Thread size (e.g., M12x1.75)")
    lubrication: str = Field("", description="Thread lubrication requirements")
    notes: str = Field("", description="Additional notes or warnings")
    verified: bool = Field(False, description="Whether spec has been verified by shop management")


class TorqueSpecResponse(BaseModel):
    """Response for torque spec lookup."""

    query: str
    found: bool
    specs: list[TorqueSpec] = Field(default_factory=list)
    source: str = Field("local_database", description="local_database or ai_knowledge")
    disclaimer: str = Field(
        default="Always verify torque specifications against the OEM service manual for your specific application."
    )


class TorqueSpecCreateRequest(BaseModel):
    """Request to add a new torque spec."""

    vehicle: str
    year_range: list[int]
    make: str
    model: str
    engine: str
    component: str
    category: str = "general"
    torque_ft_lbs: float | None = None
    torque_nm: float | None = None
    torque_sequence: str = ""
    stages: list[TorqueStage] = Field(default_factory=list)
    tty: bool = False
    reusable: bool = True
    thread_size: str = ""
    lubrication: str = ""
    notes: str = ""
    verified: bool = False
