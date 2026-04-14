"""Torque specification lookup endpoints."""

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    TorqueSpec,
    TorqueSpecResponse,
    TorqueSpecCreateRequest,
)
from app.core.torque_db import (
    lookup_torque_spec,
    search_torque_specs,
    get_all_specs,
    add_spec,
    update_spec,
    mark_verified,
    format_specs_for_prompt,
)
from app.core.claude_client import get_claude_client

router = APIRouter()


@router.get("/torque-specs/search", response_model=TorqueSpecResponse)
async def search_specs(
    q: str = Query(..., description="Search query (e.g., 'head bolt', 'lug nut')"),
    make: str | None = Query(None, description="Vehicle make"),
    model: str | None = Query(None, description="Vehicle model"),
    year: int | None = Query(None, description="Vehicle year"),
    engine: str | None = Query(None, description="Engine type"),
):
    """Search the local torque spec database."""
    specs = lookup_torque_spec(q, make=make, model=model, year=year, engine=engine)
    if not specs:
        specs = search_torque_specs(q)

    return TorqueSpecResponse(
        query=q,
        found=len(specs) > 0,
        specs=specs,
        source="local_database",
    )


@router.get("/torque-specs", response_model=list[TorqueSpec])
async def list_specs(
    make: str | None = Query(None, description="Filter by make"),
    category: str | None = Query(None, description="Filter by category"),
):
    """List all torque specs, optionally filtered."""
    return get_all_specs(make=make, category=category)


@router.get("/torque-specs/{spec_id}", response_model=TorqueSpec)
async def get_spec(spec_id: str):
    """Get a specific torque spec by ID."""
    all_specs = get_all_specs()
    for spec in all_specs:
        if spec.id == spec_id:
            return spec
    raise HTTPException(status_code=404, detail=f"Spec '{spec_id}' not found")


@router.post("/torque-specs", response_model=TorqueSpec, status_code=201)
async def create_spec(request: TorqueSpecCreateRequest):
    """Add a new torque spec to the database."""
    try:
        return add_spec(request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/torque-specs/{spec_id}", response_model=TorqueSpec)
async def patch_spec(spec_id: str, updates: dict):
    """Update a torque spec. Pass only the fields to change."""
    result = update_spec(spec_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Spec '{spec_id}' not found")
    return result


@router.post("/torque-specs/{spec_id}/verify", response_model=TorqueSpec)
async def verify_spec(spec_id: str):
    """Mark a torque spec as verified by shop management."""
    result = mark_verified(spec_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Spec '{spec_id}' not found")
    return result


@router.post("/torque-specs/ask", response_model=TorqueSpecResponse)
async def ask_torque_spec(
    q: str = Query(..., description="Natural language question about torque specs"),
    make: str | None = Query(None),
    model: str | None = Query(None),
    year: int | None = Query(None),
    engine: str | None = Query(None),
):
    """Natural language torque spec query.

    Searches the local database first. If no results, falls back to Claude AI.
    """
    # Try local DB first
    specs = lookup_torque_spec(q, make=make, model=model, year=year, engine=engine)
    if not specs:
        specs = search_torque_specs(q)

    if specs:
        return TorqueSpecResponse(
            query=q,
            found=True,
            specs=specs,
            source="local_database",
        )

    # Fall back to Claude
    try:
        client = get_claude_client()
        response_text = await client.diagnose(
            query=q,
            year=year,
            make=make,
            model=model,
            engine=engine,
        )
        # Return as a response with AI source indicator
        return TorqueSpecResponse(
            query=q,
            found=True,
            specs=[],  # No structured specs from AI — response is in diagnosis text
            source="ai_knowledge",
            disclaimer=f"AI-generated response. Verify with OEM service manual.\n\n{response_text}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Torque spec lookup failed: {str(e)}")
