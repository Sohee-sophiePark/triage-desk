"""
Canary token tests (SC-03 Layer 3).

Covers:
- load_prompt injects canary token when provided
- check_canary_leakage returns False for clean output
- check_canary_leakage returns True when token appears in output
"""
from app.agents.pii_hooks import check_canary_leakage
from app.agents.prompt_loader import load_prompt

# ── prompt_loader ─────────────────────────────────────────────────────────────

def test_load_prompt_without_canary_has_no_canary_string():
    prompt = load_prompt("triage")
    assert "CANARY:" not in prompt


def test_load_prompt_with_canary_injects_token():
    prompt = load_prompt("triage", canary_token="abc123testtoken")
    assert "abc123testtoken" in prompt
    assert "CANARY:" in prompt


def test_load_prompt_canary_not_duplicated_on_second_call():
    """Each call returns a fresh load; no state is mutated."""
    p1 = load_prompt("transactions", canary_token="token_one")
    p2 = load_prompt("transactions", canary_token="token_two")
    assert "token_one" in p1
    assert "token_two" in p2
    assert "token_one" not in p2
    assert "token_two" not in p1


def test_load_prompt_none_canary_produces_no_canary_line():
    prompt = load_prompt("triage", canary_token=None)
    assert "CANARY:" not in prompt


# ── check_canary_leakage ──────────────────────────────────────────────────────

def test_canary_leakage_clean_output_returns_false():
    assert check_canary_leakage("This is a normal output with no secret.", "abc123") is False


def test_canary_leakage_output_contains_token_returns_true():
    assert check_canary_leakage("Here is my response. abc123 was in the output.", "abc123") is True


def test_canary_leakage_none_canary_returns_false():
    assert check_canary_leakage("output text with anything", None) is False


def test_canary_leakage_empty_canary_returns_false():
    assert check_canary_leakage("output text", "") is False
