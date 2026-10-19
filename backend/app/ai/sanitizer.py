"""Sanitization and prompt injection defense for untrusted logs and job payloads."""

import re
from typing import Any, Dict


# Regex patterns for sensitive credentials
SECRET_PATTERNS = [
    (re.compile(r'(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{15,}'), r'\1[REDACTED_TOKEN]'),
    (re.compile(r'(?i)(password|secret|api_key|token|auth)\s*[:=]\s*["\']?[^"\',\s]{4,}["\']?'), r'\1=[REDACTED]'),
    (re.compile(r'ey[a-zA-Z0-9_-]{10,}\.ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}'), '[REDACTED_JWT]'),
]

# Prompt injection markers in untrusted input
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions'),
    re.compile(r'(?i)you\s+are\s+now\s+(an?\s+)?admin'),
    re.compile(r'(?i)disregard\s+(all\s+)?safety'),
    re.compile(r'(?i)system\s*:\s*execute'),
]


def sanitize_text(text: str) -> str:
    """Removes sensitive credentials and neutralizes potential prompt injections."""
    sanitized = text
    for pattern, repl in SECRET_PATTERNS:
        sanitized = pattern.sub(repl, sanitized)

    for inj_pattern in PROMPT_INJECTION_PATTERNS:
        if inj_pattern.search(sanitized):
            sanitized = inj_pattern.sub('[FILTERED_POTENTIAL_INJECTION]', sanitized)

    return sanitized


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redacts dictionary values."""
    sanitized = {}
    sensitive_keys = {"password", "secret", "token", "key", "authorization"}

    for k, v in payload.items():
        if any(s in k.lower() for s in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, str):
            sanitized[k] = sanitize_text(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_payload(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_payload(x) if isinstance(x, dict) else (sanitize_text(x) if isinstance(x, str) else x)
                for x in v
            ]
        else:
            sanitized[k] = v

    return sanitized
