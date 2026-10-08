"""Check every exported demo case against evals/golden.json (one entry per demo.export SCENARIOS item, same order).

Usage (from backend/, after `uv run python -m demo.export`):  uv run python -m evals.golden
Exits 1 if any expectation fails.
"""
import json
import sys
from pathlib import Path

from demo.export import OUT, SCENARIOS

GOLDEN = json.loads((Path(__file__).parent / "golden.json").read_text())


def check(case: dict, want: dict) -> list[str]:
    """Return the failed expectations for one exported case."""
    e = case["ai_evaluation"]
    flags = {f["code"] for f in e["flags"]}
    return [msg for ok, msg in [
        (case["status"] == want["status"], f"status {case['status']}"),
        (e["severity"] == want["severity"], f"severity {e['severity']}"),
        (flags == set(want["flags"]), f"flags {sorted(flags)}"),
        (set(want["lanes"]) <= set(e["routed_agents"]), f"lanes {e['routed_agents']}"),
        (e["brief"]["disposition"] in want["dispositions"], f"disposition {e['brief']['disposition']}"),
        (flags <= set(e["brief"]["cited_flags"]), f"cited {e['brief']['cited_flags']}"),
        (bool(e["compliance_result"] and e["compliance_result"]["passed"] and e["verdict"] and e["verdict"]["passed"]),
         "gates or evaluator failed"),
    ] if not ok]


def main() -> int:
    by_text = {s["text"]: i for i, s in enumerate(SCENARIOS)}
    scenario = {inc["id"]: by_text[inc["description"]]
                for f in OUT.glob("customers/*/risk-incidents.json") for inc in json.loads(f.read_text())["data"]}
    cases = {scenario[c["incident_id"]]: c for c in map(json.loads, map(Path.read_text, OUT.glob("workflow/cases/*.json")))}
    failed = 0
    for i, want in enumerate(GOLDEN):
        fails = check(cases[i], want) if i in cases else ["case missing from export"]
        failed += bool(fails)
        print(f"{'PASS' if not fails else 'FAIL'}  {i}  {want['name']:28} {'; '.join(fails)}")
    print(f"{len(GOLDEN) - failed}/{len(GOLDEN)} golden cases pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
