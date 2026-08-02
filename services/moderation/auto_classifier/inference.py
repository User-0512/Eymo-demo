import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NOTE ON VISION SUPPORT
# ---------------------------------------------------------------------------
# Grok 4.5 via the xAI OpenAI-compatible endpoint currently supports text-based
# chat completions. Image understanding may be available through the vision
# model variants, but to keep this pipeline robust we follow this strategy:
#
#   - text  : send text directly to Grok.
#   - image : extract text via OCR (pytesseract), then classify the OCR text.
#   - video : extract audio (ffmpeg) -> transcribe (OpenAI Whisper, local),
#             extract 2 sample frames -> OCR each frame,
#             then combine transcript + frame OCR and classify.
# ---------------------------------------------------------------------------


def _classify_via_grok(content_text: str) -> dict:
    """
    Classify extracted text using the Grok API.

    Import is deferred to avoid a hard dependency on the OpenAI client
    when only local extraction utilities are being used.
    """
    from services.grok_service import classify_content

    return classify_content(content_type="text", text=content_text)


def _extract_text_from_image(image_path: str) -> str:
    """Run OCR on an image using pytesseract."""
    try:
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(image_path))
    except ImportError:
        logger.warning("pytesseract or Pillow not installed; skipping image OCR.")
        return ""
    except Exception as e:
        logger.error(f"OCR error for image {image_path}: {e}")
        return ""


def _extract_text_from_video(video_path: str) -> str:
    """
    Extract text from a video by:
      1. Extracting audio with ffmpeg.
      2. Transcribing with OpenAI Whisper (local, no API cost).
      3. Extracting 2 sample frames and running OCR on them.

    Returns the combined transcript + frame OCR text.
    """
    combined_text = ""
    audio_path = f"{video_path}.wav"
    frame1_path = f"{video_path}_frame1.jpg"
    frame2_path = f"{video_path}_frame2.jpg"

    try:
        import ffmpeg
        import pytesseract
        import whisper
        from PIL import Image

        # 1. Extract audio
        ffmpeg.input(video_path).output(
            audio_path, acodec="pcm_s16le", ac=1, ar="16k"
        ).run(quiet=True, overwrite_output=True)

        # 2. Transcribe with local Whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        combined_text += (result.get("text") or "") + "\n"

        # 3. Extract 2 sample frames and OCR them
        ffmpeg.input(video_path, ss="00:00:01").output(
            frame1_path, vframes=1
        ).run(quiet=True, overwrite_output=True)
        combined_text += "\n[Frame 1 OCR]: " + pytesseract.image_to_string(
            Image.open(frame1_path)
        )

        ffmpeg.input(video_path, ss="00:00:02").output(
            frame2_path, vframes=1
        ).run(quiet=True, overwrite_output=True)
        combined_text += "\n[Frame 2 OCR]: " + pytesseract.image_to_string(
            Image.open(frame2_path)
        )

    except ImportError:
        logger.warning(
            "ffmpeg-python / whisper / pytesseract not installed; "
            "video transcription unavailable."
        )
    except Exception as e:
        logger.error(f"Error processing video {video_path}: {e}")
    finally:
        # Cleanup temporary files
        for tmp_file in (audio_path, frame1_path, frame2_path):
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

    return combined_text


def classify_content(
    content_type: str,
    text: str = None,
    image_path: str = None,
    video_path: str = None,
) -> dict:
    """
    Classify content as educational or not using Grok (via xAI API).

    Args:
        content_type: "text", "image", or "video"
        text: raw text content (for text posts)
        image_path: path to an image file (for image posts)
        video_path: path to a video file (for video posts)

    Returns:
        {
            "status": "approved" | "rejected" | "pending_review",
            "subject_tag": str,
            "confidence": int,
            "reason": str,
            "difficulty": str,
        }
    """
    extracted_text = ""

    if content_type == "text":
        if text:
            extracted_text = text

    elif content_type == "image":
        if image_path:
            # If Grok 4.5 supports image input directly, that can be added later.
            # For now, OCR-text-only is the working path.
            extracted_text = _extract_text_from_image(image_path)

    elif content_type == "video":
        if video_path:
            extracted_text = _extract_text_from_video(video_path)

    else:
        logger.warning(f"Unsupported content_type: {content_type}")
        return {
            "status": "pending_review",
            "subject_tag": "Other",
            "confidence": 0,
            "reason": f"Unsupported content type: {content_type}",
            "difficulty": "intermediate",
        }

    if not extracted_text.strip():
        return {
            "status": "pending_review",
            "subject_tag": "Other",
            "confidence": 0,
            "reason": "No readable content extracted.",
            "difficulty": "intermediate",
        }

    return _classify_via_grok(extracted_text)

