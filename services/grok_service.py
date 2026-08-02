import os
import json
import logging
from typing import Optional

from openai import OpenAI, APIError, APITimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# xAI (Grok) configuration
XAI_API_KEY = os.environ.get("XAI_API_KEY")
XAI_BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "grok-4.5")


def get_client() -> OpenAI:
    """Initialize and return the xAI compatible OpenAI client."""
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY is not set in the environment.")
    return OpenAI(
        api_key=XAI_API_KEY or "dummy",
        base_url=XAI_BASE_URL,
        timeout=15.0,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, APITimeoutError)),
    reraise=True,
)
def _call_grok_chat_completion(prompt: str, system_prompt: str, temperature: float = 0.1) -> str:
    """
    Calls the Grok API using chat completions with automatic retries.

    The xAI API is OpenAI-compatible, exposed at:
      POST https://api.x.ai/v1/chat/completions
    """
    client = get_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,  # Low temperature for more deterministic JSON output
    )

    return response.choices[0].message.content


def call_grok(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    temperature: float = 0.1,
    max_retries: int = 3,
) -> str:
    """
    Generic wrapper around the Grok API. Returns the raw text response.

    Can be used by any service that needs a Grok call (moderation, fact-checking, etc.).
    """
    return _call_grok_chat_completion(prompt, system_prompt, temperature)


_MODERATION_SYSTEM_PROMPT = (
    "You are a strict content moderator for an education-only social platform. "
    "Approve ONLY genuine educational content: tutorials, academic explanations, "
    "skill-building, exam prep, how-to learning content, verified facts explained clearly. "
    "REJECT: memes, promotional/marketing content, pure entertainment, lifestyle posts, "
    "and anything that mentions a topic without actually teaching something. "
    "You must ALWAYS return valid JSON only, with no markdown wrapping."
)


def classify_content(content_type: str, text: str = None, **kwargs) -> dict:
    """
    Classify the content using the Grok API (xAI, OpenAI-compatible).

    Returns: {
        "status": "approved" | "rejected" | "pending_review",
        "subject_tag": str,
        "confidence": int,
        "reason": str,
        "difficulty": str,
    }

    Thresholds:
      - confidence > 75  -> approved
      - 40 <= confidence <= 75 -> pending_review
      - confidence < 40  -> rejected
    """
    # Multimodal extraction (image/video) happens in the caller layer
    # (services/moderation/auto_classifier/inference.py). Here we handle
    # the common text-based classification used by the content router.
    extracted_text = (text or "").strip()

    if not extracted_text:
        return {
            "status": "pending_review",
            "subject_tag": "Other",
            "confidence": 0,
            "reason": "No readable content extracted.",
            "difficulty": "intermediate",
        }

    prompt = (
        "Return ONLY this JSON shape: "
        '{"status":"approved|rejected|pending_review",'
        '"subject_tag":"Math|Science|Coding|Language|History|ExamPrep|Health|Finance|LifeSkills|Other",'
        '"confidence":0-100,'
        '"reason":"one sentence",'
        '"difficulty":"beginner|intermediate|advanced"}. '
        "Rules: confidence>75 means approved, 40-75 means pending_review, below 40 means rejected.\n\n"
        f"Content to classify:\n{extracted_text}"
    )

    try:
        output_text = _call_grok_chat_completion(prompt, _MODERATION_SYSTEM_PROMPT)
        return _parse_classification_response(output_text)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Grok JSON response: {e}")
        return _fallback_result(f"Failed to parse JSON from AI: {e}")

    except Exception as e:
        logger.error(f"Grok API error: {e}")
        return _fallback_result(f"API error or timeout: {e}")


def _parse_classification_response(output_text: str) -> dict:
    """Clean markdown-wrapped JSON and parse it into a classification dict."""
    clean_text = output_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]

    result = json.loads(clean_text.strip())

    required = ("status", "subject_tag", "confidence", "reason")
    if not all(k in result for k in required):
        raise ValueError("Missing keys in JSON")

    # Normalize status
    status = str(result.get("status", "pending_review")).strip().lower()
    if status not in {"approved", "rejected", "pending_review"}:
        status = "pending_review"

    confidence = int(result.get("confidence", 0))

    # Apply threshold logic as a safety net on top of the model's own status
    if confidence > 75:
        status = "approved"
    elif confidence < 40:
        status = "rejected"
    else:
        status = "pending_review"

    return {
        "status": status,
        "subject_tag": result.get("subject_tag", "Other"),
        "confidence": confidence,
        "reason": result.get("reason", ""),
        "difficulty": result.get("difficulty", "intermediate"),
    }


def _fallback_result(reason: str) -> dict:
    """Never approve silently; send flagged content to human review."""
    return {
        "status": "pending_review",
        "subject_tag": "Other",
        "confidence": 0,
        "reason": reason,
        "difficulty": "intermediate",
    }

