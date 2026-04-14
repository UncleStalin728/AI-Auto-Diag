"""Torque specification database and lookup engine."""

import json
import re
from pathlib import Path
from app.models.schemas import TorqueSpec, TorqueStage

TORQUE_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "torque_specs"

# In-memory cache loaded from JSON files
_specs_cache: list[TorqueSpec] = []
_loaded: bool = False


def _slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _make_id(make: str, model: str, engine: str, component: str) -> str:
    """Generate a unique ID for a torque spec."""
    return _slugify(f"{make}_{model}_{engine}_{component}")


def load_specs() -> list[TorqueSpec]:
    """Load all torque specs from JSON files in data/torque_specs/."""
    global _specs_cache, _loaded

    _specs_cache = []

    if not TORQUE_DATA_DIR.exists():
        _loaded = True
        return _specs_cache

    for json_file in sorted(TORQUE_DATA_DIR.glob("*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)
            specs_list = data if isinstance(data, list) else data.get("specs", [])
            for entry in specs_list:
                # Generate ID if missing
                if "id" not in entry:
                    entry["id"] = _make_id(
                        entry.get("make", ""),
                        entry.get("model", ""),
                        entry.get("engine", ""),
                        entry.get("component", ""),
                    )
                # Parse stages if present
                if "stages" in entry:
                    entry["stages"] = [
                        TorqueStage(**s) if isinstance(s, dict) else s
                        for s in entry["stages"]
                    ]
                _specs_cache.append(TorqueSpec(**entry))
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Failed to load {json_file}: {e}")
            continue

    _loaded = True
    return _specs_cache


def _ensure_loaded():
    """Load specs if not already loaded."""
    global _loaded
    if not _loaded:
        load_specs()


def lookup_torque_spec(
    component: str,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    engine: str | None = None,
) -> list[TorqueSpec]:
    """Look up torque specs with progressive fallback.

    Priority: exact match > make+component+year > make+component > component-only
    """
    _ensure_loaded()
    component_lower = component.lower()
    results = []

    # Score each spec by match quality
    scored: list[tuple[int, TorqueSpec]] = []

    for spec in _specs_cache:
        spec_component = spec.component.lower()

        # Component must at least partially match
        if component_lower not in spec_component and spec_component not in component_lower:
            # Try keyword matching: split query into words and check overlap
            query_words = set(component_lower.split())
            spec_words = set(spec_component.split())
            if not query_words & spec_words:
                continue

        score = 0

        # Component match quality
        if component_lower == spec_component:
            score += 100
        elif component_lower in spec_component or spec_component in component_lower:
            score += 50
        else:
            score += 10  # keyword overlap

        # Make match
        if make and spec.make.lower() == make.lower():
            score += 40

        # Model match
        if model and spec.model.lower() == model.lower():
            score += 30

        # Engine match
        if engine and spec.engine.lower() == engine.lower():
            score += 20

        # Year range match
        if year and len(spec.year_range) == 2:
            if spec.year_range[0] <= year <= spec.year_range[1]:
                score += 25

        scored.append((score, spec))

    # Sort by score descending, return top matches
    scored.sort(key=lambda x: x[0], reverse=True)
    return [spec for _, spec in scored[:10]]


def search_torque_specs(query: str) -> list[TorqueSpec]:
    """Keyword search across all specs for natural language queries."""
    _ensure_loaded()
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored: list[tuple[int, TorqueSpec]] = []

    for spec in _specs_cache:
        score = 0
        searchable = f"{spec.vehicle} {spec.component} {spec.category} {spec.notes}".lower()

        for word in query_words:
            if len(word) < 3:
                continue
            if word in searchable:
                score += 10

        if score > 0:
            scored.append((score, spec))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [spec for _, spec in scored[:10]]


def get_all_specs(
    make: str | None = None,
    category: str | None = None,
) -> list[TorqueSpec]:
    """Return all specs, optionally filtered by make and/or category."""
    _ensure_loaded()
    results = _specs_cache

    if make:
        results = [s for s in results if s.make.lower() == make.lower()]
    if category:
        results = [s for s in results if s.category.lower() == category.lower()]

    return results


def add_spec(spec_data: dict) -> TorqueSpec:
    """Add a new torque spec to the database and persist to JSON."""
    _ensure_loaded()

    # Generate ID
    spec_data["id"] = _make_id(
        spec_data.get("make", ""),
        spec_data.get("model", ""),
        spec_data.get("engine", ""),
        spec_data.get("component", ""),
    )

    spec = TorqueSpec(**spec_data)
    _specs_cache.append(spec)
    _persist_spec(spec)
    return spec


def update_spec(spec_id: str, updates: dict) -> TorqueSpec | None:
    """Update an existing spec and persist changes."""
    _ensure_loaded()

    for i, spec in enumerate(_specs_cache):
        if spec.id == spec_id:
            updated_data = spec.model_dump()
            updated_data.update(updates)
            updated_spec = TorqueSpec(**updated_data)
            _specs_cache[i] = updated_spec
            _persist_make(updated_spec.make)
            return updated_spec

    return None


def mark_verified(spec_id: str) -> TorqueSpec | None:
    """Mark a spec as verified by shop management."""
    return update_spec(spec_id, {"verified": True})


def _persist_spec(spec: TorqueSpec):
    """Persist a single spec to its make's JSON file."""
    _persist_make(spec.make)


def _persist_make(make: str):
    """Write all specs for a given make back to its JSON file."""
    TORQUE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    make_specs = [s for s in _specs_cache if s.make.lower() == make.lower()]
    filename = _slugify(make) + ".json"
    filepath = TORQUE_DATA_DIR / filename

    data = {"specs": [s.model_dump() for s in make_specs]}
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def format_specs_for_prompt(specs: list[TorqueSpec]) -> str:
    """Format torque specs into a text block for injection into Claude prompts."""
    if not specs:
        return ""

    lines = ["--- LOCAL TORQUE SPEC DATABASE RESULTS ---"]
    for spec in specs:
        verified_tag = "[VERIFIED]" if spec.verified else "[UNVERIFIED - confirm with service manual]"
        lines.append(f"\n{spec.component} — {spec.vehicle} {verified_tag}")

        if spec.torque_ft_lbs is not None:
            lines.append(f"  Torque: {spec.torque_ft_lbs} ft-lbs ({spec.torque_nm} Nm)")
        if spec.stages:
            lines.append("  Procedure:")
            for stage in spec.stages:
                lines.append(f"    Stage {stage.stage}: {stage.value} {stage.unit}")
        if spec.torque_sequence:
            lines.append(f"  Sequence: {spec.torque_sequence}")
        if spec.tty:
            lines.append(f"  TTY: Yes — do NOT reuse bolt")
        if spec.thread_size:
            lines.append(f"  Thread: {spec.thread_size}")
        if spec.lubrication:
            lines.append(f"  Lubrication: {spec.lubrication}")
        if spec.notes:
            lines.append(f"  Notes: {spec.notes}")

    lines.append("--- END TORQUE SPECS ---")
    return "\n".join(lines)
