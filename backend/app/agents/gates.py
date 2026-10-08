"""Deterministic gates: G0 intake, G4 specialist findings, G5 output (the Compliance Guardian)."""
import re

from app.agents.pii_hooks import PII_PATTERNS, check_canary_leakage, sanitize_llm_input
from app.agents.rules import ALLOWED_DISPOSITIONS, Flag
from app.agents.tools import Metric

MAX_ALERT_CHARS = 2000
INJECTION_MARKER = "REDACTED_POTENTIAL_INJECTION"
_PLACEHOLDER = re.compile(r"\{\{(m|t):([A-Za-z0-9_]+)\}\}")
_PII = [re.compile(p) for p in PII_PATTERNS]
_NUMBER_WORD = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                          r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
                          r"hundred|thousand|million|billion|dozen|twice|percent)\b", re.IGNORECASE)


def intake_gate(text: str | None) -> tuple[str, bool]:
    """G0: cap length, neutralise injection phrases, wrap as untrusted data; returns (wrapped, injection_suspected)."""
    clean = sanitize_llm_input((text or "No alert description.")[:MAX_ALERT_CHARS])
    return f"<untrusted_alert_text>{clean}</untrusted_alert_text>", INJECTION_MARKER in clean


def text_failures(texts: list[str], metrics: dict[str, Metric], refs: set[str], canary: str | None) -> list[str]:
    fails = []
    for t in texts:
        for kind, key in _PLACEHOLDER.findall(t):
            if kind == "m" and key not in metrics:
                fails.append(f"unknown metric placeholder {{{{m:{key}}}}}")
            if kind == "t" and key not in refs:
                fails.append(f"unknown evidence placeholder {{{{t:{key}}}}}")
        bare = _PLACEHOLDER.sub("", t)
        if re.search(r"\d", bare):
            fails.append(f"raw digits outside placeholders: {t[:80]!r}")
        if word := _NUMBER_WORD.search(bare):
            fails.append(f"number written as a word ({word.group(0)!r}): {t[:80]!r}")
        if any(p.search(t) for p in _PII):
            fails.append("PII pattern in output")
        if check_canary_leakage(t, canary):
            fails.append("canary token leaked")
        if INJECTION_MARKER in t:
            fails.append("echoed redacted injection text")
    return fails


def findings_gate(finding: dict, metrics: dict[str, Metric], refs: set[str], canary: str | None) -> list[str]:
    """G4: a specialist finding may only reference known metrics and evidence, with no raw numbers."""
    fails = text_failures([finding["summary"], *finding["concerns"]], metrics, refs, canary)
    fails += [f"unknown metric key {k}" for k in finding["metric_keys"] if k not in metrics]
    fails += [f"unknown evidence ref {r}" for r in finding["evidence"] if r not in refs]
    return fails


def output_gate(brief: dict, metrics: dict[str, Metric], refs: set[str], flags: list[Flag],
                severity: str, canary: str | None) -> list[str]:
    """G5: placeholders resolve, disposition allowed for the code-computed severity, every high flag cited."""
    fails = text_failures([brief["summary"], *brief["rationale"]], metrics, refs, canary)
    if not brief["rationale"]:
        fails.append("rationale is empty")
    if brief["disposition"] not in ALLOWED_DISPOSITIONS[severity]:
        fails.append(f"disposition {brief['disposition']!r} not allowed at {severity} severity; "
                     f"allowed: {ALLOWED_DISPOSITIONS[severity]}")
    codes = {f.code for f in flags}
    fails += [f"cited flag {c} was not raised" for c in brief["cited_flags"] if c not in codes]
    fails += [f"high flag {f.code} not cited" for f in flags if f.severity == "high" and f.code not in brief["cited_flags"]]
    fails += [f"unknown evidence ref {r}" for r in brief["evidence"] if r not in refs]
    return fails


def _fmt(m: Metric) -> str:
    v = m.value
    if m.unit == "text":
        return str(v)
    if m.unit == "usd":
        return f"${v:,.2f}"
    if m.unit == "ratio":
        return f"{v:.1f}x"
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}"


def render(text: str, metrics: dict[str, Metric], evidence: dict[str, dict]) -> str:
    """Fill placeholders with code-computed values (call only after the gates pass)."""
    def sub(m: re.Match) -> str:
        kind, key = m.groups()
        if kind == "m":
            return _fmt(metrics[key])
        e = evidence[key]
        return f"{key} (${e['amount']:,.2f} on {e['date']}, {e['merchant'] or e['channel']})"
    return _PLACEHOLDER.sub(sub, text)
