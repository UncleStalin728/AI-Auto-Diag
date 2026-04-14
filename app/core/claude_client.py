"""Claude API client for automotive diagnostics."""

import anthropic
from app.config import get_settings
from app.core.prompt_templates import (
    SYSTEM_PROMPT,
    DTC_INTERPRETATION_PROMPT,
    SYMPTOM_DIAGNOSIS_PROMPT,
    RAG_AUGMENTED_PROMPT,
    TORQUE_SPEC_PROMPT,
    build_vehicle_string,
)
from app.core.torque_db import lookup_torque_spec, search_torque_specs, format_specs_for_prompt


TORQUE_KEYWORDS = [
    "torque", "ft-lb", "ft lb", "foot pound", "nm ", "newton",
    "tighten", "torque spec", "tightening", "bolt torque",
    "head bolt", "lug nut", "drain plug torque",
    "intake manifold bolt", "exhaust manifold bolt",
    "how tight", "torque to yield", "tty",
]


def _is_torque_query(query: str) -> bool:
    """Detect if a query is primarily about torque specifications."""
    lower = query.lower()
    return any(kw in lower for kw in TORQUE_KEYWORDS)


class ClaudeClient:
    """Wrapper around the Anthropic Claude API for diagnostic queries."""

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.max_tokens

    async def diagnose(
        self,
        query: str,
        year: int | None = None,
        make: str | None = None,
        model: str | None = None,
        engine: str | None = None,
        dtc_codes: list[str] | None = None,
        rag_context: str | None = None,
    ) -> str:
        """Send a diagnostic query to Claude with optional RAG context."""

        vehicle = build_vehicle_string(year, make, model, engine)
        dtc_str = ", ".join(dtc_codes) if dtc_codes else "None reported"

        # Choose the right prompt template
        if _is_torque_query(query) and not rag_context:
            # Search local torque DB first
            db_specs = []
            if make or model:
                db_specs = lookup_torque_spec(query, make=make, model=model, year=year, engine=engine)
            if not db_specs:
                db_specs = search_torque_specs(query)

            db_specs_text = format_specs_for_prompt(db_specs) if db_specs else ""

            user_message = TORQUE_SPEC_PROMPT.format(
                year=year or "Unknown",
                make=make or "Unknown",
                model=model or "Unknown",
                engine=engine or "Unknown",
                query=query,
                db_specs=db_specs_text,
            )
        elif rag_context:
            user_message = RAG_AUGMENTED_PROMPT.format(
                rag_context=rag_context,
                year=year or "Unknown",
                make=make or "Unknown",
                model=model or "Unknown",
                engine=engine or "Unknown",
                query=query,
                dtc_codes=dtc_str,
            )
        elif dtc_codes:
            user_message = DTC_INTERPRETATION_PROMPT.format(
                year=year or "Unknown",
                make=make or "Unknown",
                model=model or "Unknown",
                engine=engine or "Unknown",
                dtc_codes=dtc_str,
            )
        else:
            user_message = SYMPTOM_DIAGNOSIS_PROMPT.format(
                year=year or "Unknown",
                make=make or "Unknown",
                model=model or "Unknown",
                engine=engine or "Unknown",
                symptom=query,
                dtc_codes=dtc_str,
            )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text

    async def interpret_dtc(
        self,
        dtc_code: str,
        year: int | None = None,
        make: str | None = None,
        model: str | None = None,
        engine: str | None = None,
    ) -> str:
        """Get a detailed interpretation of a single DTC code."""

        user_message = DTC_INTERPRETATION_PROMPT.format(
            year=year or "Unknown",
            make=make or "Unknown",
            model=model or "Unknown",
            engine=engine or "Unknown",
            dtc_codes=dtc_code,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text


# Singleton
_client: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client
