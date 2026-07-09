from __future__ import annotations


def sanitize_text(text: str) -> str:
    """Remove invalid Unicode such as lone surrogate characters.

    Some clients may send strings that contain surrogate-escaped bytes like
    ``\\udcaa``. Those are not valid Unicode scalar values, and pygame's font
    renderer will fail when it tries to encode them as UTF-8.
    """

    if not isinstance(text, str):
        text = str(text)

    cleaned = text.encode("utf-8", "replace").decode("utf-8", "replace")
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()
