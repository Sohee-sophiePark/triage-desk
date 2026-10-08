import re
from typing import Optional

PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",  # email
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",                         # phone
    r"\b\d{3}-\d{2}-\d{4}\b",                                  # SSN
]

_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "system override",
    "set is_fraud=false",
    "as an aik hacker",
    "bypass security",
    "ignore all instructions",
    "disregard previous",
    "you are now",
    "act as",
]

# Pre-compile with IGNORECASE so capitalised variants are also replaced
_INJECTION_RE = [
    (re.compile(re.escape(p), re.IGNORECASE), f"[REDACTED_POTENTIAL_INJECTION: {p}]")
    for p in _INJECTION_PATTERNS
]


def sanitize_llm_output(output: str) -> str:
    """Regex-scan LLM output for accidentally leaked PII patterns and redact them."""
    for pattern in PII_PATTERNS:
        output = re.sub(pattern, "[PII_REDACTED]", output)
    return output


def sanitize_llm_input(input_text: str) -> str:
    """Detect and neutralize potential prompt injection patterns (case-insensitive)."""
    sanitized = input_text
    for regex, replacement in _INJECTION_RE:
        sanitized = regex.sub(replacement, sanitized)
    return sanitized


def check_canary_leakage(output: str, canary: Optional[str]) -> bool:
    """Return True if the canary token appears in the output (SC-03 Layer 3).

    A match means the LLM may have leaked the system prompt, which should be
    treated as a security violation by the compliance node.
    """
    if not canary:
        return False
    return canary in output
