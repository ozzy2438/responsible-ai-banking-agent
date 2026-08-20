from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    categories: tuple[str, ...]

    @property
    def redacted(self) -> bool:
        return bool(self.categories)


_LABELLED_PATTERNS = (
    ("PASSWORD", re.compile(r"(?i)\b(password|passcode)\s*(?:is|=|:)\s*\S+")),
    ("PIN", re.compile(r"(?i)\bpin\s*(?:is|=|:)\s*\d{3,8}\b")),
    ("CVV", re.compile(r"(?i)\b(cvv|cvc|security code)\s*(?:is|=|:)\s*\d{3,4}\b")),
    ("TOKEN", re.compile(r"(?i)\b(api[_ -]?key|bearer|token)\s*(?:is|=|:)\s*\S+")),
)
_CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def _luhn(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def redact_sensitive(text: str) -> RedactionResult:
    categories: list[str] = []
    redacted = text
    for category, pattern in _LABELLED_PATTERNS:
        if pattern.search(redacted):
            categories.append(category)
            redacted = pattern.sub(f"[REDACTED_{category}]", redacted)

    def replace_card(match: re.Match[str]) -> str:
        if _luhn(match.group(0)):
            categories.append("CARD")
            return "[REDACTED_CARD]"
        return match.group(0)

    redacted = _CARD_CANDIDATE.sub(replace_card, redacted)
    return RedactionResult(redacted, tuple(dict.fromkeys(categories)))
