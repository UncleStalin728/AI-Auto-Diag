"""Seed the torque spec database using Claude API.

Run this once to generate initial torque specs for common vehicles.
All generated specs are marked as unverified — review and verify before
techs rely on them.

Usage:
    python -m scripts.seed_torque_db
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "torque_specs"

# ── Vehicle definitions to seed ─────────────────────────────
# Each entry: (make, model, engine, year_range)
VEHICLES = [
    # Ford
    ("Ford", "F-150", "5.0L V8 Coyote", [2015, 2020]),
    ("Ford", "F-150", "3.5L V6 EcoBoost", [2015, 2020]),
    ("Ford", "F-150", "2.7L V6 EcoBoost", [2015, 2020]),
    ("Ford", "Explorer", "3.5L V6", [2016, 2019]),
    ("Ford", "Mustang", "5.0L V8 Coyote", [2015, 2023]),
    ("Ford", "Mustang", "2.3L I4 EcoBoost", [2015, 2023]),
    ("Ford", "Escape", "1.5L I4 EcoBoost", [2017, 2022]),
    ("Ford", "F-250", "6.7L V8 Power Stroke", [2017, 2022]),
    # GM / Chevy
    ("Chevrolet", "Silverado 1500", "5.3L V8 L83/L84", [2014, 2023]),
    ("Chevrolet", "Silverado 1500", "6.2L V8 L87", [2019, 2023]),
    ("Chevrolet", "Equinox", "1.5L I4 Turbo", [2018, 2023]),
    ("Chevrolet", "Malibu", "1.5L I4 Turbo", [2016, 2023]),
    ("Chevrolet", "Camaro", "6.2L V8 LT1", [2016, 2023]),
    ("GMC", "Sierra 1500", "5.3L V8", [2014, 2023]),
    ("GMC", "Sierra 1500", "6.2L V8", [2019, 2023]),
    # Chrysler / Dodge / Jeep
    ("Dodge", "Ram 1500", "5.7L V8 Hemi", [2013, 2023]),
    ("Dodge", "Ram 1500", "3.6L V6 Pentastar", [2013, 2023]),
    ("Jeep", "Wrangler", "3.6L V6 Pentastar", [2012, 2023]),
    ("Jeep", "Grand Cherokee", "3.6L V6 Pentastar", [2014, 2023]),
    ("Jeep", "Grand Cherokee", "5.7L V8 Hemi", [2014, 2023]),
    ("Dodge", "Charger", "5.7L V8 Hemi", [2015, 2023]),
    # Toyota
    ("Toyota", "Camry", "2.5L I4", [2018, 2024]),
    ("Toyota", "Tacoma", "3.5L V6", [2016, 2023]),
    ("Toyota", "Tundra", "5.7L V8", [2014, 2021]),
    ("Toyota", "RAV4", "2.5L I4", [2019, 2024]),
    ("Toyota", "Corolla", "1.8L I4", [2019, 2024]),
    ("Toyota", "4Runner", "4.0L V6", [2010, 2024]),
    # Honda
    ("Honda", "Civic", "1.5L I4 Turbo", [2016, 2024]),
    ("Honda", "Civic", "2.0L I4", [2016, 2024]),
    ("Honda", "Accord", "1.5L I4 Turbo", [2018, 2024]),
    ("Honda", "CR-V", "1.5L I4 Turbo", [2017, 2024]),
    ("Honda", "Pilot", "3.5L V6", [2016, 2023]),
    # Nissan
    ("Nissan", "Altima", "2.5L I4", [2019, 2024]),
    ("Nissan", "Rogue", "2.5L I4", [2017, 2023]),
    ("Nissan", "Frontier", "3.8L V6", [2022, 2024]),
    ("Nissan", "Titan", "5.6L V8", [2016, 2023]),
    ("Nissan", "Pathfinder", "3.5L V6", [2017, 2023]),
]

# Components to generate specs for
COMPONENTS = [
    # Engine
    "Cylinder Head Bolt",
    "Intake Manifold Bolt",
    "Exhaust Manifold Bolt/Stud",
    "Oil Pan Bolt",
    "Valve Cover Bolt",
    "Main Bearing Cap Bolt",
    "Connecting Rod Bolt",
    "Spark Plug",
    "Flywheel/Flexplate Bolt",
    "Timing Cover Bolt",
    # Brakes & Suspension
    "Lug Nut",
    "Brake Caliper Bracket Bolt",
    "Brake Caliper Slide Pin",
    "Brake Hose Banjo Bolt",
    "Ball Joint Pinch Bolt/Nut",
    "Tie Rod End Nut",
    "Lower Control Arm Bolt",
    "Upper Strut Mount Nut",
    "Sway Bar End Link Nut",
    "Wheel Bearing/Hub Bolt",
    # Drivetrain
    "Axle Nut",
    "Transmission Pan Bolt",
    "Transmission Drain Plug",
    "Driveshaft Bolt/Strap",
    "Bellhousing Bolt",
    "Oil Drain Plug",
]

SEED_PROMPT = """Generate accurate torque specifications for a {year_start}-{year_end} {make} {model} with the {engine} engine.

I need specs for EACH of the following components. For each one, provide a JSON object with these fields:

- "component": exact component name as provided
- "category": one of "engine", "brakes", "suspension", "drivetrain", "general"
- "torque_ft_lbs": primary torque value in ft-lbs (number or null if only angle-based)
- "torque_nm": primary torque value in Nm (number or null if only angle-based)
- "torque_sequence": tightening sequence description (string, empty if N/A)
- "stages": array of stages if multi-stage, each with {{"stage": number, "value": number, "unit": "ft-lbs"|"Nm"|"degrees"}}. Empty array if single-stage.
- "tty": true if torque-to-yield fastener, false otherwise
- "reusable": true if bolt can be reused, false if one-time use
- "thread_size": bolt thread size (e.g., "M12x1.75") if known, empty string if unknown
- "lubrication": thread lubrication requirement (e.g., "Clean and dry", "Light engine oil on threads")
- "notes": any critical warnings, tips, or additional info

Components:
{components}

IMPORTANT:
- Return ONLY a JSON array of objects, no markdown formatting or code blocks.
- If you don't know a specific spec for this exact vehicle, use your best knowledge but add a note saying "Verify with OEM service manual for this specific application."
- Be as accurate as possible — these specs will be used by professional shop technicians.
- Include proper multi-stage tightening procedures where applicable (especially head bolts, main caps).
- Always specify if a bolt is TTY (torque-to-yield) since those CANNOT be reused.
"""


def generate_specs_for_vehicle(
    client: anthropic.Anthropic,
    make: str,
    model: str,
    engine: str,
    year_range: list[int],
) -> list[dict]:
    """Use Claude to generate torque specs for a single vehicle."""

    components_str = "\n".join(f"- {c}" for c in COMPONENTS)

    prompt = SEED_PROMPT.format(
        year_start=year_range[0],
        year_end=year_range[1],
        make=make,
        model=model,
        engine=engine,
        components=components_str,
    )

    print(f"  Generating specs for {make} {model} {engine}...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Strip markdown code blocks if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        specs = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Failed to parse JSON for {make} {model}: {e}")
        print(f"  Raw response (first 200 chars): {text[:200]}")
        return []

    # Enrich each spec with vehicle info
    for spec in specs:
        spec["vehicle"] = f"{year_range[0]}-{year_range[1]} {make} {model} {engine}"
        spec["year_range"] = year_range
        spec["make"] = make
        spec["model"] = model
        spec["engine"] = engine
        spec["verified"] = False

    return specs


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from .env
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found. Set it in .env or as environment variable.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Group vehicles by make
    makes: dict[str, list[tuple]] = {}
    for make, model, engine, year_range in VEHICLES:
        makes.setdefault(make, []).append((make, model, engine, year_range))

    total_specs = 0

    for make, vehicles in makes.items():
        print(f"\n{'='*60}")
        print(f"Generating specs for {make} ({len(vehicles)} vehicles)...")
        print(f"{'='*60}")

        make_specs = []

        for make_name, model, engine, year_range in vehicles:
            specs = generate_specs_for_vehicle(client, make_name, model, engine, year_range)
            make_specs.extend(specs)
            total_specs += len(specs)
            print(f"  ->{len(specs)} specs generated")

        # Write to JSON file
        filename = make.lower().replace(" ", "-") + ".json"
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w") as f:
            json.dump({"specs": make_specs}, f, indent=2)
        print(f"  Saved to {filepath} ({len(make_specs)} total specs)")

    print(f"\n{'='*60}")
    print(f"DONE! Generated {total_specs} torque specs across {len(makes)} makes.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nIMPORTANT: All specs are marked as UNVERIFIED.")
    print(f"Review and verify specs before technicians rely on them.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
