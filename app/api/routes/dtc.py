"""DTC code lookup endpoint."""

from fastapi import APIRouter
from app.models.schemas import DTCLookupResponse
from app.core.dtc_database import lookup_dtc, get_all_codes

router = APIRouter()


@router.get("/dtc/{code}", response_model=DTCLookupResponse)
async def get_dtc(code: str):
    """Look up a diagnostic trouble code.

    Returns code description, common causes, symptoms, and diagnostic steps.
    Works for standard OBD-II codes and manufacturer-specific codes.
    """
    info = lookup_dtc(code)

    if info and "Unknown" not in info.description:
        return DTCLookupResponse(code=code.upper(), found=True, info=info)
    elif info:
        # We have a categorized but unknown code
        return DTCLookupResponse(code=code.upper(), found=False, info=info)
    else:
        return DTCLookupResponse(code=code.upper(), found=False, info=None)


@router.get("/dtc", response_model=list[str])
async def list_dtc_codes():
    """List all DTC codes in the local database."""
    return get_all_codes()
