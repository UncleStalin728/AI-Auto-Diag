"""VIN decoder using the free NHTSA vPIC API."""

import logging
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)

NHTSA_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevin"

# Cylinder count to engine layout mapping
ENGINE_LAYOUTS = {
    "3": "I3",
    "4": "I4",
    "5": "I5",
    "6": "V6",
    "8": "V8",
    "10": "V10",
    "12": "V12",
}

# In-memory cache for decoded VINs
_vin_cache: dict[str, dict] = {}


def decode_vin(vin: str) -> dict:
    """Decode a VIN using the NHTSA API.

    Returns a dict with: vin, year, make, model, engine, cylinders,
    displacement_l, drive_type, transmission, engine_description, success, error
    """
    vin = vin.strip().upper()

    # Check cache
    if vin in _vin_cache:
        return _vin_cache[vin]

    if len(vin) != 17:
        return {
            "vin": vin,
            "success": False,
            "error": "VIN must be exactly 17 characters",
        }

    try:
        resp = requests.get(
            f"{NHTSA_API_URL}/{vin}",
            params={"format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"NHTSA API error for VIN {vin}: {e}")
        return {
            "vin": vin,
            "success": False,
            "error": f"NHTSA API request failed: {str(e)}",
        }

    # Parse the results array into a flat dict
    raw = {}
    for item in data.get("Results", []):
        name = item.get("Variable", "") or item.get("VariableName", "")
        value = item.get("Value")
        if name and value and str(value).strip():
            raw[name] = str(value).strip()

    year = raw.get("Model Year")
    make = raw.get("Make")
    model = raw.get("Model")
    displacement = raw.get("Displacement (L)")
    cylinders = raw.get("Engine Number of Cylinders")
    drive_type = raw.get("Drive Type")
    transmission = raw.get("Transmission Style")

    if not make or not model:
        result = {
            "vin": vin,
            "success": False,
            "error": "Could not decode VIN — make/model not found",
        }
        _vin_cache[vin] = result
        return result

    # Build engine description string like "2.4L I4"
    engine = _build_engine_string(displacement, cylinders)

    result = {
        "vin": vin,
        "year": int(year) if year else None,
        "make": make,
        "model": model,
        "engine": engine,
        "displacement_l": float(displacement) if displacement else None,
        "cylinders": int(cylinders) if cylinders else None,
        "drive_type": drive_type,
        "transmission": transmission,
        "success": True,
        "error": None,
    }

    _vin_cache[vin] = result
    return result


def _build_engine_string(displacement: str | None, cylinders: str | None) -> str:
    """Build an engine description string like '2.4L I4' or '5.7L V8'."""
    parts = []

    if displacement:
        try:
            disp = float(displacement)
            parts.append(f"{disp:.1f}L")
        except ValueError:
            pass

    if cylinders:
        layout = ENGINE_LAYOUTS.get(cylinders, f"{cylinders}cyl")
        parts.append(layout)

    return " ".join(parts) if parts else "Unknown"
