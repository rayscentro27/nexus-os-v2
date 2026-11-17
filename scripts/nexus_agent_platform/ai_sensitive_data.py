"""Fail-closed redaction for sensitive values at Nexus AI context boundaries."""
from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY = re.compile(
    r"(?i)(^|[_\- ])(ssn|social.?security|ein|tax.?id|bank.?account|account.?number|"
    r"routing.?number|password|passphrase|api.?secret|secret.?key|access.?token|"
    r"refresh.?token|auth.?cookie|cookie|session.?token)([_\- ]|$)"
)
_PATTERNS = (
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b\d{2}-\d{7}\b"), "[REDACTED_EIN]"),
    (re.compile(r"(?i)\b(?:routing|bank account|account number)\s*(?:number|no\.?|#|:|=)?\s*\d{6,17}\b"), "[REDACTED_BANK_IDENTIFIER]"),
    (re.compile(r"(?i)\b(?:password|api[_ -]?secret|secret[_ -]?key|access[_ -]?token|refresh[_ -]?token)\s*[:=]\s*[^\s,;]+"), "[REDACTED_SECRET]"),
)


def redact_ai_context(value: Any) -> Any:
    """Recursively redact named sensitive fields and recognizable raw values."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                result[key] = "[REDACTED_SENSITIVE_FIELD]"
            else:
                result[key] = redact_ai_context(item)
        return result
    if isinstance(value, list):
        return [redact_ai_context(item) for item in value]
    if isinstance(value, tuple):
        return [redact_ai_context(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern, replacement in _PATTERNS:
            result = pattern.sub(replacement, result)
        return result
    return value
