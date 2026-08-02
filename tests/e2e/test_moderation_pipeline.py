"""
End-to-end moderation pipeline tests.

These tests exercise the real moderation pipeline:
  - Basic quality rules (heuristic pre-filter)
  - Grok-based content classification (via xAI API) when a VALID XAI_API_KEY is set
  - Fallback deterministic behavior when no/invalid API key is configured (CI-safe)

IMPORTANT — Real AI classification behavior:
  - test_classify_educational_text_real_grok and test_classify_junk_content_real_grok
    call the REAL `classify_content()` function (NOT mocked) from services.grok_service.
  - If a valid XAI_API_KEY is present in the environment/.env file, they hit the live
    Grok API and assert STRICT results (approved / rejected / confidence thresholds).
  - If the key is missing, a placeholder, or INVALID (does not start with `xai-` or is
    rejected by the API), these tests are SKIPPED with a clear message. This prevents
    false confidence: the fallback returns `pending_review` for everything, which would
    otherwise make permissive assertions pass silently.

To enable real AI verification, set a valid key in your local `.env`:
    XAI_API_KEY=xai-...
Then run:
    python -m pytest tests/e2e/test_moderation_pipeline.py -v -s
"""
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from services.moderation.policy_rules import passes_basic_rules
from services.grok_service import classify_content

# Fast, deterministic check of the configured key's plausibility.
# xAI API keys are prefixed with "xai-". Anything else (empty, placeholder,
# or a different format) is treated as invalid WITHOUT making a network call.
def _configured_key_is_plausible() -> bool:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        return False
    if key in {"your_xai_key_here", "your_xai_api_key_here"}:
        return False
    return key.startswith("xai-")


def _live_grok_works() -> bool:
    """
    Performs a single live sanity call to the Grok API to confirm the configured
    XAI_API_KEY is genuinely valid and the account has credits/licenses.
    Only called when the key format is plausible.
    Returns True only if the API responds successfully (no error/timeout reason).
    """
    if not _configured_key_is_plausible():
        return False
    try:
        result = classify_content(content_type="text", text="The sky is blue.")
        reason = (result.get("reason") or "").lower()
        # A genuine response has a real reason; the fallback path reports an
        # "api error" / "timeout" / "failed to parse" reason.
        return not any(flag in reason for flag in ("api error", "timeout", "failed to parse"))
    except Exception:
        return False


# Evaluate ONCE at module load so the same decision applies to all tests.
_REAL_API_AVAILABLE = _live_grok_works()

# Human-readable reason for the skip message.
def _skip_reason() -> str:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        return (
            "XAI_API_KEY is not set. Real Grok verification skipped.\n"
            "  Fix: set XAI_API_KEY in .env"
        )
    if key in {"your_xai_key_here", "your_xai_api_key_here"}:
        return (
            "XAI_API_KEY is the placeholder value. Real Grok verification skipped.\n"
            "  Fix: replace with a real key from https://console.x.ai/"
        )
    if not key.startswith("xai-"):
        return (
            f"XAI_API_KEY format looks invalid (expected prefix 'xai-', got {key[:6]}...).\n"
            "  Real Grok verification skipped."
        )
    # Key format is valid, but the API call failed.
    # We try to determine the specific failure reason by probing the API directly.
    # The most common cause: the xAI account has no credits/licenses.
    try:
        import urllib.request, json
        body = json.dumps({
            "model": "grok-4.5",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }).encode()
        req = urllib.request.Request(
            "https://api.x.ai/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        # If we get here, it worked — but _live_grok_works returned False, so this is unexpected.
        return "Grok API responded but test detected failure. See logs."
    except urllib.error.HTTPError as e:
        err_body = json.loads(e.read())
        err_msg = err_body.get("error", str(err_body))
        if "credits" in err_msg.lower() or "license" in err_msg.lower() or "quota" in err_msg.lower():
            return (
                f"Grok API returned 403: {err_msg}\n"
                "  Real Grok verification skipped.\n"
                "  Fix: purchase credits at https://console.x.ai/team/.../billing"
            )
        return (
            f"Grok API returned {e.code}: {err_msg}\n"
            "  Real Grok verification skipped."
        )
    except Exception as e:
        return (
            f"Grok API error: {e}\n"
            "  Real Grok verification skipped."
        )


REAL_GROK_SKIP_REASON = _skip_reason()


# ─────────────────────────────────────────────────────────────
# 1. Policy Rules (heuristic pre-filter) — pure, always run
# ─────────────────────────────────────────────────────────────
def test_policy_rules_reject_spam():
    """Spam content should fail the basic quality pre-filter."""
    spam_text = (
        "CONGRATULATIONS YOU HAVE BEEN SELECTED FOR A FREE IPHONE 15 PRO MAX "
        "CLICK THE LINK NOW TO CLAIM YOUR PRIZE LIMITED TIME OFFER"
    )
    assert passes_basic_rules(spam_text) is False


def test_policy_rules_reject_short_text():
    """Very short content should fail the basic quality pre-filter."""
    assert passes_basic_rules("Hi") is False


def test_policy_rules_reject_empty():
    """Empty / whitespace-only content should fail."""
    assert passes_basic_rules("   ") is False
    assert passes_basic_rules("") is False


def test_policy_rules_accept_educational_text():
    """Genuine educational text should pass the pre-filter."""
    educational = (
        "Photosynthesis is the process by which plants use sunlight, water, "
        "and carbon dioxide to create oxygen and energy in the form of sugar."
    )
    assert passes_basic_rules(educational) is True


# ─────────────────────────────────────────────────────────────
# 2. classify_content — empty content (no API call, always runs)
# ─────────────────────────────────────────────────────────────
def test_classify_empty_content():
    """Empty content should be routed to pending_review (never approved)."""
    result = classify_content(content_type="text", text="   ")
    assert result["status"] == "pending_review"
    assert "confidence" in result
    assert "reason" in result


# ─────────────────────────────────────────────────────────────
# 3. Real Grok classification (REQUIRES valid XAI_API_KEY)
#    These tests SKIP when the key is missing/invalid to avoid
#    false confidence from the fallback path.
# ─────────────────────────────────────────────────────────────
@pytest.mark.skipif(not _REAL_API_AVAILABLE, reason=REAL_GROK_SKIP_REASON)
def test_classify_educational_text_real_grok():
    """
    REAL Grok API: genuine educational content must be classified as APPROVED.
    (Strict assertion — no fallback permitted.)
    """
    educational = (
        "To find the derivative of x^2, we use the power rule. "
        "Bring the exponent down to multiply by the coefficient, "
        "and decrease the exponent by 1. So the derivative of x^2 is 2x."
    )
    result = classify_content(content_type="text", text=educational)
    assert result["status"] == "approved", f"Expected approved, got: {result}"
    assert result["subject_tag"], "Missing subject_tag"
    assert result["confidence"] > 75, f"Confidence too low: {result}"


@pytest.mark.skipif(not _REAL_API_AVAILABLE, reason=REAL_GROK_SKIP_REASON)
def test_classify_junk_content_real_grok():
    """
    REAL Grok API: pure meme/joke with engagement bait must be REJECTED.
    (Strict assertion — no fallback permitted.)
    """
    meme = (
        "Why did the chicken cross the road? To escape the 5G towers! "
        "Like and subscribe for more dank memes bro."
    )
    result = classify_content(content_type="text", text=meme)
    assert result["status"] == "rejected", f"Expected rejected, got: {result}"
    assert result["confidence"] < 40, f"Confidence too high: {result}"


# ─────────────────────────────────────────────────────────────
# 4. Fallback safety (always runs — verifies graceful degradation)
# ─────────────────────────────────────────────────────────────
def test_classify_api_failure_returns_safe_fallback(monkeypatch):
    """
    Simulates an API failure by forcing _call_grok_chat_completion to raise.
    classify_content must never crash and never silently approve; it must
    return a structured `pending_review` result with a reason.
    """
    def _boom(*args, **kwargs):
        raise RuntimeError("Simulated network failure")

    monkeypatch.setattr(
        "services.grok_service._call_grok_chat_completion", _boom
    )

    result = classify_content(content_type="text", text="Some random text here")
    assert result["status"] == "pending_review"
    assert "confidence" in result
    assert "reason" in result

