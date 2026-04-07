"""DTC (Diagnostic Trouble Code) database and lookup engine."""

import json
from pathlib import Path
from app.models.schemas import DTCInfo

DTC_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "dtc_codes"


# ── Standard OBD-II DTC definitions ──────────────────────
# This is a starter set — expand by loading JSON files from data/dtc_codes/

STANDARD_DTCS: dict[str, dict] = {
    # Misfires
    "P0300": {
        "description": "Random/Multiple Cylinder Misfire Detected",
        "category": "powertrain",
        "severity": "critical",
        "common_causes": [
            "Worn or fouled spark plugs",
            "Faulty ignition coil(s)",
            "Vacuum leak (intake manifold gasket, PCV, brake booster line)",
            "Low fuel pressure (weak fuel pump, clogged filter, leaking injector)",
            "Compression loss (head gasket, valve, piston ring)",
            "Mass airflow sensor contamination",
        ],
        "symptoms": [
            "Rough idle",
            "Engine shaking/vibration",
            "Loss of power",
            "Flashing check engine light under load",
            "Poor fuel economy",
        ],
        "diagnostic_steps": [
            "Check freeze frame data for RPM, load, and coolant temp at time of misfire",
            "Read misfire counters per cylinder — if one cylinder dominates, focus there",
            "Inspect spark plugs for fouling, wear, or cracking",
            "Swap ignition coil to different cylinder and check if misfire follows",
            "Perform fuel pressure test (key-on and running)",
            "Smoke test intake for vacuum leaks",
            "Compression test if above checks pass",
        ],
    },
    "P0301": {
        "description": "Cylinder 1 Misfire Detected",
        "category": "powertrain",
        "severity": "critical",
        "common_causes": [
            "Faulty spark plug (cylinder 1)",
            "Faulty ignition coil (cylinder 1)",
            "Leaking fuel injector (cylinder 1)",
            "Vacuum leak near cylinder 1 intake runner",
            "Low compression (cylinder 1)",
        ],
        "symptoms": ["Rough idle", "Misfire at specific RPM range", "Flashing CEL"],
        "diagnostic_steps": [
            "Swap coil from cylinder 1 to another cylinder — does misfire follow?",
            "Swap spark plug from cylinder 1 to another cylinder",
            "Check injector pulse with noid light",
            "Perform relative compression test",
            "If no ignition/fuel issue, do leak-down test on cylinder 1",
        ],
    },
    # Oxygen sensors
    "P0171": {
        "description": "System Too Lean (Bank 1)",
        "category": "powertrain",
        "severity": "moderate",
        "common_causes": [
            "Vacuum leak (intake manifold, PCV hose, brake booster line)",
            "Dirty or faulty MAF sensor",
            "Weak fuel pump / low fuel pressure",
            "Clogged fuel injector(s)",
            "Exhaust leak before O2 sensor",
            "Faulty O2 sensor (rare — usually a symptom, not a cause)",
        ],
        "symptoms": [
            "Rough idle",
            "Hesitation on acceleration",
            "Long-term fuel trim above +10%",
            "Poor fuel economy",
        ],
        "diagnostic_steps": [
            "Check short-term and long-term fuel trims at idle and 2500 RPM",
            "If LTFT high at idle but normalizes at RPM → vacuum leak",
            "If LTFT high at both → fuel delivery issue",
            "Smoke test intake system for leaks",
            "Clean MAF sensor with MAF-specific cleaner",
            "Check fuel pressure at rail",
            "Inspect intake boot and PCV system",
        ],
    },
    "P0172": {
        "description": "System Too Rich (Bank 1)",
        "category": "powertrain",
        "severity": "moderate",
        "common_causes": [
            "Leaking fuel injector(s)",
            "Faulty fuel pressure regulator (high pressure)",
            "Contaminated MAF sensor",
            "Stuck-open purge valve (EVAP system)",
            "Faulty coolant temperature sensor (reading cold)",
            "Saturated charcoal canister",
        ],
        "symptoms": [
            "Black smoke from exhaust",
            "Fuel smell",
            "Negative fuel trims (below -10%)",
            "Fouled spark plugs",
            "Poor fuel economy",
        ],
        "diagnostic_steps": [
            "Check fuel trims — negative LTFT indicates rich condition",
            "Inspect spark plugs for black sooty deposits",
            "Check fuel pressure (should drop with vacuum applied to regulator)",
            "Command purge valve closed and monitor fuel trims",
            "Check coolant temp sensor reading vs actual temp",
            "Inspect injectors for leaking (fuel pressure drop test with engine off)",
        ],
    },
    # Catalytic converter
    "P0420": {
        "description": "Catalyst System Efficiency Below Threshold (Bank 1)",
        "category": "powertrain",
        "severity": "moderate",
        "common_causes": [
            "Worn catalytic converter (most common)",
            "Engine misfire damaging the catalyst",
            "Oil or coolant contamination in exhaust",
            "Exhaust leak before downstream O2 sensor",
            "Faulty downstream O2 sensor",
        ],
        "symptoms": [
            "Check engine light",
            "Possible rotten egg smell",
            "May have reduced power at high load",
            "Failed emissions test",
        ],
        "diagnostic_steps": [
            "Compare upstream vs downstream O2 sensor waveforms",
            "Downstream should be relatively flat/steady — if it mirrors upstream, cat is failing",
            "Check for exhaust leaks before downstream sensor",
            "Check for misfires or other codes that could cause cat damage",
            "Measure catalyst inlet vs outlet temperature (should be 50-100F hotter at outlet)",
            "Rule out O2 sensor issues before condemning the cat",
        ],
    },
    # EVAP system
    "P0442": {
        "description": "EVAP System Small Leak Detected",
        "category": "powertrain",
        "severity": "minor",
        "common_causes": [
            "Loose or cracked gas cap",
            "Cracked EVAP hose or connector",
            "Faulty purge valve or vent valve",
            "Small crack in charcoal canister",
            "Leaking fuel tank pressure sensor seal",
        ],
        "symptoms": ["Check engine light (no driveability symptoms typically)"],
        "diagnostic_steps": [
            "Inspect gas cap seal — replace if cracked or worn",
            "Perform EVAP smoke test to locate the leak",
            "Inspect all EVAP hoses and connectors for cracks",
            "Check purge valve and vent valve for proper sealing",
            "Inspect charcoal canister for cracks",
        ],
    },
    # Transmission
    "P0700": {
        "description": "Transmission Control System Malfunction",
        "category": "powertrain",
        "severity": "critical",
        "common_causes": [
            "Accompanying transmission-specific DTC (P07xx-P09xx)",
            "Low or contaminated transmission fluid",
            "Faulty shift solenoid",
            "TCM communication issue",
            "Wiring issue to transmission sensors/solenoids",
        ],
        "symptoms": [
            "Check engine light",
            "Harsh or delayed shifts",
            "Transmission slipping",
            "Limp mode (stuck in one gear)",
        ],
        "diagnostic_steps": [
            "Read transmission-specific codes with a capable scan tool",
            "Check transmission fluid level and condition",
            "Check for other P07xx-P09xx codes — P0700 is a generic flag",
            "Monitor transmission data PIDs (line pressure, solenoid commands, slip)",
            "Check wiring and connectors at transmission",
        ],
    },
    # Coolant system
    "P0128": {
        "description": "Coolant Thermostat Below Thermostat Regulating Temperature",
        "category": "powertrain",
        "severity": "minor",
        "common_causes": [
            "Stuck-open thermostat",
            "Faulty coolant temperature sensor",
            "Low coolant level",
            "Faulty radiator fan (running constantly)",
        ],
        "symptoms": [
            "Engine slow to warm up",
            "Heater blows lukewarm air",
            "Slightly higher fuel consumption",
            "Check engine light",
        ],
        "diagnostic_steps": [
            "Check coolant level",
            "Monitor coolant temp with scan tool — should reach 195-220F within 5-10 minutes",
            "If temp plateaus below 180F, thermostat is likely stuck open",
            "Check if radiator fan is running when it shouldn't be (cold engine)",
            "Compare ECT sensor reading to actual temp with infrared thermometer",
        ],
    },
}


def lookup_dtc(code: str) -> DTCInfo | None:
    """Look up a DTC code in the database."""
    code = code.upper().strip()

    # Check built-in database
    if code in STANDARD_DTCS:
        data = STANDARD_DTCS[code]
        return DTCInfo(code=code, **data)

    # Check JSON files in data directory
    json_result = _search_json_files(code)
    if json_result:
        return json_result

    # Auto-categorize unknown codes by prefix
    return _categorize_unknown_code(code)


def _search_json_files(code: str) -> DTCInfo | None:
    """Search for a DTC code in JSON data files."""
    if not DTC_DATA_DIR.exists():
        return None

    for json_file in DTC_DATA_DIR.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
            if code in data:
                return DTCInfo(code=code, **data[code])
        except (json.JSONDecodeError, KeyError):
            continue

    return None


def _categorize_unknown_code(code: str) -> DTCInfo | None:
    """Provide basic info for unknown codes based on their prefix."""
    if len(code) < 2:
        return None

    categories = {
        "P": ("powertrain", "Powertrain"),
        "C": ("chassis", "Chassis"),
        "B": ("body", "Body"),
        "U": ("network", "Network/Communication"),
    }

    prefix = code[0].upper()
    if prefix not in categories:
        return None

    category, category_name = categories[prefix]

    # Determine if manufacturer-specific
    try:
        second_digit = int(code[1])
        specificity = "Generic (SAE)" if second_digit == 0 else "Manufacturer-specific"
    except (ValueError, IndexError):
        specificity = "Unknown"

    return DTCInfo(
        code=code,
        description=f"Unknown {category_name} code — {specificity}. Use scan tool or service manual for details.",
        category=category,
        severity="informational",
        common_causes=["Code not in local database — consult service manual or OEM resources"],
        symptoms=[],
        diagnostic_steps=[
            f"Look up {code} in the vehicle-specific service manual",
            "Check for related codes that may provide more context",
            "Consult OEM technical resources or Identifix/Mitchell for this specific code",
        ],
    )


def get_all_codes() -> list[str]:
    """Return all known DTC codes."""
    return sorted(STANDARD_DTCS.keys())
