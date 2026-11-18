"""Small shared redaction boundary for Systems-generated diagnostics."""
from __future__ import annotations

import re
from typing import Any

_PATTERNS = [
    (re.compile(r"(?im)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/=]{12,}"), "Bearer [REDACTED]"),
    (re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"), "[REDACTED_TELEGRAM_TOKEN]"),
    # Accept both shell-style assignments and quoted JSON/YAML key-value pairs.
    (re.compile(r"(?im)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|service[_-]?role[_-]?key|password|passwd|secret)\s*[\"']?\s*[=:]\s*[\"']?)([^\"'\s,;}]+)"), r"\1[REDACTED]"),
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(?i)(postgres(?:ql)?://[^:/\s]+:)[^@/\s]+(@)"), r"\1[REDACTED]\2"),
]


def redact_text(value: str) -> str:
    output = str(value)
    for pattern, replacement in _PATTERNS:
        output = pattern.sub(replacement, output)
    return output


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, dict):
        return {redact_text(str(k)): redact(v) for k, v in value.items()}
    return value
