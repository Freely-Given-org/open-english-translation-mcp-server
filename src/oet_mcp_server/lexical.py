"""Source identifier handling shared by corpus construction and retrieval."""

import re
import unicodedata

SCHEMA_VERSION = 2


def normalize_alias(value: str) -> str:
    """Accept accent/case variants without guessing a different lexical entry."""
    return "".join(c for c in unicodedata.normalize("NFD", value.strip().casefold())
                   if not unicodedata.combining(c))


def greek_strongs(extended: str) -> tuple[str, str]:
    """SR-GNT appends a sense digit to the standard Strong's number."""
    digits = extended.removeprefix("G")
    if not digits.isdigit() or len(digits) < 2:
        return "", ""
    return f"G{int(digits[:-1])}", f"G{digits}"


def hebrew_strongs(component: str) -> str:
    """Prefixes/suffixes are morphology, not Strong's dictionary numbers."""
    m = re.fullmatch(r"H?(\d+)(?:\s*[a-z])?", component.strip())
    return f"H{int(m[1])}" if m else ""
