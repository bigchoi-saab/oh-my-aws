#!/usr/bin/env python3
"""
parity_check.py — Real-vs-fixture diagnosis parity check for aws-exam skill (US-13, US-0 AC#5,6,8)

EXIT CODE CONTRACT:
  0  = PASS — root_cause_code matches AND top-3 recommended_actions overlap ≥ 2/3
  1  = FAIL — parity criteria not met; structured diff printed to stderr
  2  = ERROR — argument error, file not found, or YAML parse failure

USAGE:
  python parity_check.py <real_diagnosis_yaml> <fixture_diagnosis_yaml> [--report-out <path>]

  <real_diagnosis_yaml>    diagnosis.yaml from a real live-mode aws-diagnostician run
                           (lives under .ops/incidents/_parity-baseline/<id>/diagnosis.yaml)
  <fixture_diagnosis_yaml> diagnosis.yaml from a sim-mode aws-diagnostician run
                           (lives under .ops/exam-results/run-*/sim-incidents/<id>/diagnosis.yaml)
  --report-out <path>      (optional) write structured pass/fail report to this path
                           instead of (or in addition to) stderr

PARITY RULES (from US-0 AC#5 and AC#6):
  1. root_cause_code MUST be identical (string equality, stripped).
  2. Top-3 recommended_actions overlap MUST be ≥ 2 out of 3 (order-independent).
     - "Top-3" = first 3 items in the recommended_actions list.
     - Comparison is case-insensitive on the `action` or `code` sub-field
       (falls back to full-string comparison if neither sub-field present).

OUTPUT FORMAT (written to --report-out path and echoed to stdout on pass):
  A YAML document with the following structure:
    parity_check:
      result: pass | fail
      timestamp: <ISO8601>
      real_file: <path>
      fixture_file: <path>
      root_cause_code:
        real: <value>
        fixture: <value>
        match: true | false
      recommended_actions_overlap:
        real_top3: [...]
        fixture_top3: [...]
        overlap_count: <int>
        overlap_required: 2
        pass: true | false
      overall: pass | fail

DEPENDENCIES: Python stdlib + PyYAML
"""

import sys
import os
import argparse
import yaml
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path!r}, got {type(data).__name__}")
    return data


def extract_root_cause_code(diagnosis: dict) -> str | None:
    """
    Extract root_cause_code from a diagnosis.yaml.
    Supports top-level `root_cause_code` or nested under `diagnosis.root_cause_code`.
    """
    if "root_cause_code" in diagnosis:
        return str(diagnosis["root_cause_code"]).strip()
    nested = diagnosis.get("diagnosis", {})
    if isinstance(nested, dict) and "root_cause_code" in nested:
        return str(nested["root_cause_code"]).strip()
    return None


def extract_recommended_actions(diagnosis: dict) -> list[str]:
    """
    Extract top-3 recommended actions as comparable strings.
    Supports:
      - recommended_actions: [{action: "..."}, ...]
      - recommended_actions: [{code: "..."}, ...]
      - recommended_actions: ["...", ...]
      - diagnosis.recommended_actions: (same shapes)
    Returns list of normalized strings (lowercased, stripped).
    """
    raw = diagnosis.get("recommended_actions") or (
        diagnosis.get("diagnosis", {}) or {}
    ).get("recommended_actions", [])

    if not isinstance(raw, list):
        return []

    result = []
    for item in raw[:3]:
        if isinstance(item, dict):
            val = item.get("action") or item.get("code") or item.get("name") or str(item)
        else:
            val = str(item)
        result.append(val.strip().lower())
    return result


def overlap_count(a: list[str], b: list[str]) -> int:
    return len(set(a) & set(b))


def build_report(
    real_path: str,
    fixture_path: str,
    rcc_real: str | None,
    rcc_fixture: str | None,
    actions_real: list[str],
    actions_fixture: list[str],
) -> dict:
    rcc_match = (rcc_real is not None and rcc_fixture is not None and rcc_real == rcc_fixture)
    ov = overlap_count(actions_real, actions_fixture)
    actions_pass = ov >= 2

    overall = "pass" if (rcc_match and actions_pass) else "fail"

    return {
        "parity_check": {
            "result": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "real_file": real_path,
            "fixture_file": fixture_path,
            "root_cause_code": {
                "real": rcc_real,
                "fixture": rcc_fixture,
                "match": rcc_match,
            },
            "recommended_actions_overlap": {
                "real_top3": actions_real,
                "fixture_top3": actions_fixture,
                "overlap_count": ov,
                "overlap_required": 2,
                "pass": actions_pass,
            },
            "overall": overall,
        }
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parity check between real and fixture diagnosis.yaml files."
    )
    parser.add_argument("real_diagnosis", help="Path to real (live-mode) diagnosis.yaml")
    parser.add_argument("fixture_diagnosis", help="Path to fixture (sim-mode) diagnosis.yaml")
    parser.add_argument(
        "--report-out",
        metavar="PATH",
        help="Write structured YAML report to this path (in addition to stderr output)",
    )
    args = parser.parse_args()

    # --- validate inputs ---
    for path in (args.real_diagnosis, args.fixture_diagnosis):
        if not os.path.isfile(path):
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 2

    try:
        real_data = load_yaml(args.real_diagnosis)
    except Exception as exc:
        print(f"ERROR: failed to parse {args.real_diagnosis!r}: {exc}", file=sys.stderr)
        return 2

    try:
        fixture_data = load_yaml(args.fixture_diagnosis)
    except Exception as exc:
        print(f"ERROR: failed to parse {args.fixture_diagnosis!r}: {exc}", file=sys.stderr)
        return 2

    # --- extract fields ---
    rcc_real = extract_root_cause_code(real_data)
    rcc_fixture = extract_root_cause_code(fixture_data)
    actions_real = extract_recommended_actions(real_data)
    actions_fixture = extract_recommended_actions(fixture_data)

    if rcc_real is None:
        print(
            f"ERROR: real diagnosis.yaml missing root_cause_code: {args.real_diagnosis}",
            file=sys.stderr,
        )
        return 2
    if rcc_fixture is None:
        print(
            f"ERROR: fixture diagnosis.yaml missing root_cause_code: {args.fixture_diagnosis}",
            file=sys.stderr,
        )
        return 2

    # --- build report ---
    report = build_report(
        args.real_diagnosis,
        args.fixture_diagnosis,
        rcc_real,
        rcc_fixture,
        actions_real,
        actions_fixture,
    )
    report_yaml = yaml.dump(report, default_flow_style=False, sort_keys=False)

    # --- write report file if requested ---
    if args.report_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.report_out)), exist_ok=True)
        with open(args.report_out, "w", encoding="utf-8") as fh:
            fh.write(report_yaml)

    # --- determine exit ---
    pc = report["parity_check"]
    overall = pc["overall"]

    if overall == "pass":
        print(report_yaml)
        return 0

    # FAIL — detailed diff to stderr
    print("FAIL: parity check did not pass.", file=sys.stderr)
    print(report_yaml, file=sys.stderr)

    if not pc["root_cause_code"]["match"]:
        print(
            f"  MISMATCH root_cause_code: real={rcc_real!r}  fixture={rcc_fixture!r}",
            file=sys.stderr,
        )
    ov = pc["recommended_actions_overlap"]["overlap_count"]
    if not pc["recommended_actions_overlap"]["pass"]:
        print(
            f"  INSUFFICIENT action overlap: {ov}/3 (need ≥2)",
            file=sys.stderr,
        )
        print(f"  real_top3:    {actions_real}", file=sys.stderr)
        print(f"  fixture_top3: {actions_fixture}", file=sys.stderr)

    print(
        "\nPhase 2A kickoff is BLOCKED until parity check passes.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
