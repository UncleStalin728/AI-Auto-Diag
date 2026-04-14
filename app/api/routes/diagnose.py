"""Main diagnostic endpoint — the core of AI Auto Diag."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import DiagnoseRequest, DiagnoseResponse
from app.core.claude_client import get_claude_client
from app.core.rag_pipeline import get_rag_pipeline

router = APIRouter()


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest):
    """Submit a diagnostic query to the AI assistant.

    Accepts vehicle info, symptoms, and/or DTC codes.
    Optionally retrieves relevant service manual context via RAG.
    """
    try:
        # Build RAG context if enabled and documents exist
        rag_context = None
        sources = []
        if request.use_rag:
            try:
                pipeline = get_rag_pipeline()
                if pipeline is not None:
                    rag_context = pipeline.build_context_string(request.query)
                    if rag_context:
                        results = pipeline.retrieve(request.query)
                        sources = list({r["source"] for r in results})
            except Exception:
                # RAG is optional — continue without it if ChromaDB isn't ready
                pass

        # Call Claude
        client = get_claude_client()
        response_text = await client.diagnose(
            query=request.query,
            year=request.vehicle_year,
            make=request.vehicle_make,
            model=request.vehicle_model,
            engine=request.vehicle_engine,
            dtc_codes=request.dtc_codes,
            rag_context=rag_context,
        )

        # Parse Claude's response into structured fields
        diagnosis_result = _parse_diagnosis(response_text, sources)
        return diagnosis_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


def _parse_diagnosis(response_text: str, sources: list[str]) -> DiagnoseResponse:
    """Parse Claude's text response into structured fields.

    Claude is prompted to use specific sections, so we extract them.
    Falls back to returning the full text as the diagnosis if parsing fails.
    """
    suggested_tests = []
    possible_causes = []
    related_dtcs = []

    lines = response_text.split("\n")
    current_section = None

    for line in lines:
        line_stripped = line.strip()
        lower = line_stripped.lower()

        # Detect sections
        if "likely cause" in lower or "probable cause" in lower or "possible cause" in lower:
            current_section = "causes"
            continue
        elif "diagnostic step" in lower or "test" in lower and "suggest" in lower:
            current_section = "tests"
            continue
        elif "related" in lower and ("dtc" in lower or "code" in lower):
            current_section = "dtcs"
            continue
        elif line_stripped.startswith("**") and line_stripped.endswith("**"):
            current_section = None  # New section header, reset

        # Extract items from bullet points or numbered lists
        if current_section and (line_stripped.startswith("-") or line_stripped.startswith("•") or
                                (len(line_stripped) > 2 and line_stripped[0].isdigit() and line_stripped[1] in ".)") ):
            item = line_stripped.lstrip("-•0123456789.) ").strip()
            if item:
                if current_section == "causes":
                    possible_causes.append(item)
                elif current_section == "tests":
                    suggested_tests.append(item)
                elif current_section == "dtcs":
                    related_dtcs.append(item)

    # Determine confidence based on response language
    confidence = "medium"
    lower_full = response_text.lower()
    if any(w in lower_full for w in ["most likely", "almost certainly", "strongly suggest", "clearly"]):
        confidence = "high"
    elif any(w in lower_full for w in ["could be", "might be", "hard to determine", "several possibilities"]):
        confidence = "low"

    return DiagnoseResponse(
        diagnosis=response_text,
        confidence=confidence,
        suggested_tests=suggested_tests[:10],
        possible_causes=possible_causes[:10],
        related_dtcs=related_dtcs[:10],
        sources=sources,
    )
