import json
import logging
from typing import Dict, List

from services.grok_service import call_grok

logger = logging.getLogger(__name__)

# Keywords that automatically trigger a fact-check flag (heuristic pre-filter)
CONSPIRACY_KEYWORDS = [
    "flat earth",
    "fake moon landing",
    "microchips in vaccines",
    "chemtrails",
    "5g causes covid",
]

_FACT_CHECK_SYSTEM_PROMPT = (
    "You are a rigorous fact-checker for an education-only platform. "
    "Given a claim, determine if it is verifiable and factually supported. "
    "Respond ONLY in JSON with no markdown."
)


def _heuristic_flags(text: str) -> List[str]:
    """Simple keyword-based pre-filter for obviously unverifiable claims."""
    flags: List[str] = []
    text_lower = text.lower()
    for kw in CONSPIRACY_KEYWORDS:
        if kw in text_lower:
            flags.append(f"Potential unverified claim related to: {kw}")
    return flags


def verify_facts(text: str) -> dict:
    """
    Fact-check a piece of text using the Grok API.

    Returns:
        {
            "verified": bool,
            "flags": List[str],
            "analysis": str,
            "source": "grok" | "heuristic",
        }
    """
    if not text or not text.strip():
        return {"verified": True, "flags": [], "analysis": "No content provided.", "source": "heuristic"}

    # 1. Heuristic pre-filter
    flags = _heuristic_flags(text)

    # 2. Grok follow-up analysis
    prompt = (
        "Analyze the following educational claim. Return ONLY JSON: "
        '{"verified": true|false, "analysis": "one or two sentences explaining your assessment", "confidence": 0-100}.\n\n'
        f"Claim:\n{text}"
    )

    try:
        output = call_grok(
            prompt,
            system_prompt=_FACT_CHECK_SYSTEM_PROMPT,
            temperature=0.0,
        )

        clean = output.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]

        result = json.loads(clean)
        verified = bool(result.get("verified", False))
        analysis = result.get("analysis", "")
        confidence = int(result.get("confidence", 0))

        if confidence < 50:
            flags.append("Low confidence in fact-check result.")

        return {
            "verified": verified,
            "flags": flags,
            "analysis": analysis,
            "confidence": confidence,
            "source": "grok",
        }

    except Exception as e:
        logger.error(f"Fact-check API error: {e}")
        return {
            "verified": len(flags) == 0,
            "flags": flags,
            "analysis": f"Fact-check unavailable (API error: {e}). Based on heuristic checks only.",
            "source": "heuristic",
        }


def verify_facts_heuristic(text: str) -> dict:
    """Heuristic-only fact check (no API call). Kept for offline/fallback use."""
    flags = _heuristic_flags(text)
    return {
        "verified": len(flags) == 0,
        "flags": flags,
        "analysis": "Heuristic check only.",
        "source": "heuristic",
    }

