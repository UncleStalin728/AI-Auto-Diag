"""VIN decoding endpoint."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import VINDecodeResponse
from app.core.vin_decoder import decode_vin
from app.core.torque_db import get_all_specs

router = APIRouter()


@router.get("/vin/{vin}", response_model=VINDecodeResponse)
async def decode_vehicle_vin(vin: str):
    """Decode a 17-character VIN using the NHTSA API.

    Returns vehicle year, make, model, engine, and whether torque specs
    are available in the local database.
    """
    result = decode_vin(vin)

    if not result.get("success"):
        return VINDecodeResponse(
            vin=vin,
            success=False,
            error=result.get("error", "Unknown error"),
        )

    # Check if we have torque specs for this vehicle
    specs_available = False
    make = result.get("make")
    model = result.get("model")
    if make:
        all_specs = get_all_specs(make=make)
        if model:
            specs_available = any(
                s.model.lower() == model.lower() for s in all_specs
            )
        else:
            specs_available = len(all_specs) > 0

    return VINDecodeResponse(
        vin=vin,
        year=result.get("year"),
        make=make,
        model=model,
        engine=result.get("engine"),
        displacement_l=result.get("displacement_l"),
        cylinders=result.get("cylinders"),
        drive_type=result.get("drive_type"),
        transmission=result.get("transmission"),
        torque_specs_available=specs_available,
        success=True,
    )
