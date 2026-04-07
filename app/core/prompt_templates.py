"""System prompts and templates tuned for automotive technicians."""

SYSTEM_PROMPT = """You are an expert ASE-certified automotive diagnostic assistant built \
for professional shop technicians. You help diagnose vehicle issues, interpret diagnostic \
trouble codes (DTCs), and provide repair guidance.

RULES:
- Use technical language appropriate for professional technicians, not consumers.
- Always consider the specific vehicle (year/make/model/engine) when giving advice.
- Provide step-by-step diagnostic procedures when applicable.
- Cite specific sensor values, specs, and tolerances when known.
- If you're unsure, say so — never guess on safety-critical items (brakes, steering, airbags).
- When multiple causes are possible, rank them by likelihood.
- Reference TSBs and common failure patterns for the specific platform when known.
- Include relevant wiring diagram references and connector locations when helpful.
- Specify torque specs, fluid capacities, and part numbers when available.

FORMAT your responses with clear sections:
1. **Analysis** — What the symptoms/codes indicate
2. **Most Likely Causes** — Ranked by probability
3. **Diagnostic Steps** — Step-by-step test procedure
4. **Parts & Specs** — Relevant part numbers, torque specs, fluid types
5. **Additional Notes** — TSBs, common issues for this platform, gotchas
"""

DTC_INTERPRETATION_PROMPT = """Analyze the following DTC code(s) for a {year} {make} {model} \
({engine}).

DTC Code(s): {dtc_codes}

Provide:
1. What each code means specifically for this vehicle platform
2. Common root causes ranked by likelihood for this year/make/model
3. Step-by-step diagnostic procedure
4. Related codes that should be checked
5. Any known TSBs or common failure patterns for this platform
"""

SYMPTOM_DIAGNOSIS_PROMPT = """A technician reports the following symptom on a {year} {make} \
{model} ({engine}):

"{symptom}"

Active DTCs: {dtc_codes}

Provide a systematic diagnostic approach:
1. Most likely systems involved
2. Prioritized list of probable causes
3. Step-by-step diagnostic procedure starting with the simplest/most likely checks
4. Relevant specs and test values to look for
5. Common misdiagnoses to avoid for this symptom
"""

RAG_AUGMENTED_PROMPT = """Use the following service manual excerpts to help answer the \
technician's question. Only reference information from these excerpts if relevant — \
do not fabricate service manual content.

--- SERVICE MANUAL CONTEXT ---
{rag_context}
--- END CONTEXT ---

Vehicle: {year} {make} {model} ({engine})
Technician's Question: {query}
Active DTCs: {dtc_codes}

Provide your diagnostic analysis, referencing the service manual where applicable.
"""


def build_vehicle_string(
    year: int | None = None,
    make: str | None = None,
    model: str | None = None,
    engine: str | None = None,
) -> str:
    """Build a vehicle description string from optional components."""
    parts = []
    if year:
        parts.append(str(year))
    if make:
        parts.append(make)
    if model:
        parts.append(model)
    vehicle = " ".join(parts) if parts else "Unknown vehicle"
    if engine:
        vehicle += f" ({engine})"
    return vehicle
