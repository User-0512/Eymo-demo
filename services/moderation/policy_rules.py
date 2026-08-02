import re
from typing import Set

# Allowed upload content types
ALLOWED_CONTENT_TYPES: Set[str] = {"text", "image", "video"}

# File extensions that are allowed for media uploads
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
ALLOWED_VIDEO_EXTENSIONS: Set[str] = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}

# Common spam / engagement-bait phrases (lowercase)
SPAM_PHRASES = [
    "click the link",
    "limited time offer",
    "free iphone",
    "claim your prize",
    "congratulations you have been selected",
    "like and subscribe",
    "follow for more",
    "link in bio",
    "dm me",
    "check my profile",
    "buy now",
    "order now",
    "act fast",
]


def passes_basic_rules(text: str) -> bool:
    """
    Pre-filter function to reject content that obviously violates basic quality
    rules, saving API costs before calling Grok.

    Rules enforced:
      1. Non-empty after stripping.
      2. Minimum 10 characters.
      3. Not an ALL-CAPS spam phrase (>=10 letters, >80% uppercase).
      4. No repeated punctuation (e.g. '!!!!!').
      5. Not mostly links / emojis / non-text.
      6. No known spam phrases.
    """
    if not text:
        return False

    text = text.strip()
    if not text:
        return False

    # 1. Reject content under 10 characters
    if len(text) < 10:
        return False

    # 2. Reject obvious spam patterns (ALL CAPS phrases)
    alpha_chars = [c for c in text if c.isalpha()]
    if alpha_chars:
        upper_chars = [c for c in alpha_chars if c.isupper()]
        if (len(upper_chars) / len(alpha_chars)) > 0.8 and len(alpha_chars) >= 10:
            return False

    # 3. Reject repeated punctuation like "!!!!!"
    if re.search(r"[!?.]{4,}", text):
        return False

    # 4. Reject if mostly links (or emojis/non-text)
    text_no_links = re.sub(r"https?://\S+|www\.\S+", "", text)
    alnum_chars = [c for c in text_no_links if c.isalnum()]
    if len(alnum_chars) < 10:
        return False

    # 5. Reject known spam / engagement-bait phrases
    text_lower = text.lower()
    for phrase in SPAM_PHRASES:
        if phrase in text_lower:
            return False

    return True


def validate_content_type(content_type: str) -> bool:
    """Returns True if the content_type is one of the allowed types."""
    return content_type in ALLOWED_CONTENT_TYPES


def validate_extension(filename: str, content_type: str) -> bool:
    """
    Validates that a filename's extension matches the declared content type.
    Returns False for disallowed file types.
    """
    if not filename or "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[-1].lower()

    if content_type == "image":
        return ext in ALLOWED_IMAGE_EXTENSIONS
    if content_type == "video":
        return ext in ALLOWED_VIDEO_EXTENSIONS
    # Text content has no file extension requirement
    return content_type == "text"

