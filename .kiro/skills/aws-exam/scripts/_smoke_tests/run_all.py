#!/usr/bin/env python3
"""
_smoke_tests/run_all.py — Smoke test suite for US-13 verification scripts

EXIT CODE CONTRACT:
  0  = ALL smoke tests passed
  1  = ONE or more smoke tests failed (failures printed to stderr)

DEPENDENCIES: Python stdlib + PyYAML

USAGE:
  python _smoke_tests/run_all.py

  Must be run from any directory; uses __file__ to locate sibling scripts.

TESTS COVERED:
  audit_bash_calls.py:
    T1 — clean trace (no aws calls) → exit 0
    T2 — trace with `aws cloudwatch ...` call → exit 1
    T3 — missing run directory → exit 2
    T4 — empty agent-traces directory → exit 0

  audit_dkr_access.py:
    T5 — clean log (violated: false) → exit 0
    T6 — violated log (violated: true) → exit 1
    T7 — missing run directory → exit 2
    T8 — YAML parse error in log → exit 1

  parity_check.py:
    T9  — matching root_cause_code and ≥2/3 action overlap → exit 0
    T10 — mismatched root_cause_code → exit 1
    T11 — matching root_cause_code but only 1/3 action overlap → exit 1
    T12 — missing root_cause_code in real file → exit 2
    T13 — full match: all 3 actions overlap → exit 0
"""

import os
import sys
import json
import subprocess
import tempfile
import yaml

# Locate the scripts directory (parent of this file's directory)
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_BASH = os.path.join(SCRIPTS_DIR, "audit_bash_calls.py")
AUDIT_DKR  = os.path.join(SCRIPTS_DIR, "audit_dkr_access.py")
PARITY     = os.path.join(SCRIPTS_DIR, "parity_check.py")

PYTHON = sys.executable


# ---------------------------------------------------------------------------
# test runner infrastructure
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []  # (name, passed, detail)


def run_script(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, script] + args,
        capture_output=True,
        text=True,
    )


def expect(name: str, proc: subprocess.CompletedProcess, expected_exit: int) -> bool:
    passed = proc.returncode == expected_exit
    detail = (
        f"exit={proc.returncode} (expected {expected_exit})"
        + (f"\n    stderr: {proc.stderr.strip()[:200]}" if proc.stderr.strip() else "")
    )
    _results.append((name, passed, detail))
    return passed


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------

def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def write_yaml(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        yaml.dump(data, fh, default_flow_style=False)


def write_jsonl(path: str, records: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# audit_bash_calls tests
# ---------------------------------------------------------------------------

def test_audit_bash_calls(tmp: str) -> None:
    # T1 — clean trace (no aws calls) → exit 0
    run1 = os.path.join(tmp, "run-t1")
    write_jsonl(
        os.path.join(run1, "agent-traces", "aws-diagnostician.jsonl"),
        [
            {"tool": "Read", "input": {"file_path": "/some/file.yaml"}},
            {"tool": "Bash", "input": {"command": "cat /ops/incidents/foo/observe.yaml"}},
        ],
    )
    expect("T1 audit_bash_calls: clean trace → exit 0",
           run_script(AUDIT_BASH, [run1]), 0)

    # T2 — trace with `aws cloudwatch ...` call → exit 1
    run2 = os.path.join(tmp, "run-t2")
    write_jsonl(
        os.path.join(run2, "agent-traces", "aws-diagnostician.jsonl"),
        [
            {"tool": "Bash", "input": {"command": "aws cloudwatch get-metric-data --metric-name Duration"}},
            {"tool": "Read", "input": {"file_path": "/safe.yaml"}},
        ],
    )
    expect("T2 audit_bash_calls: aws call detected → exit 1",
           run_script(AUDIT_BASH, [run2]), 1)

    # T3 — missing run directory → exit 2
    expect("T3 audit_bash_calls: missing dir → exit 2",
           run_script(AUDIT_BASH, [os.path.join(tmp, "nonexistent")]), 2)

    # T4 — empty agent-traces directory → exit 0
    run4 = os.path.join(tmp, "run-t4")
    os.makedirs(os.path.join(run4, "agent-traces"), exist_ok=True)
    expect("T4 audit_bash_calls: empty traces dir → exit 0",
           run_script(AUDIT_BASH, [run4]), 0)


# ---------------------------------------------------------------------------
# audit_dkr_access tests
# ---------------------------------------------------------------------------

def test_audit_dkr_access(tmp: str) -> None:
    # T5 — clean log (violated: false) → exit 0
    run5 = os.path.join(tmp, "run-t5")
    write_yaml(
        os.path.join(run5, "sim-incidents", "q001", "_dkr_access_log.yaml"),
        {"violated": False, "attempted_path": None},
    )
    expect("T5 audit_dkr_access: clean log → exit 0",
           run_script(AUDIT_DKR, [run5]), 0)

    # T6 — violated log (violated: true) → exit 1
    run6 = os.path.join(tmp, "run-t6")
    write_yaml(
        os.path.join(run6, "sim-incidents", "q001", "_dkr_access_log.yaml"),
        {
            "violated": True,
            "attempted_path": ".kiro/skills/aws-incident-response/references/scenarios/lambda-timeout.yaml",
            "agent": "aws-diagnostician",
        },
    )
    expect("T6 audit_dkr_access: violation detected → exit 1",
           run_script(AUDIT_DKR, [run6]), 1)

    # T7 — missing run directory → exit 2
    expect("T7 audit_dkr_access: missing dir → exit 2",
           run_script(AUDIT_DKR, [os.path.join(tmp, "nonexistent")]), 2)

    # T8 — YAML parse error → exit 1 (treated as potential violation)
    run8 = os.path.join(tmp, "run-t8")
    write_file(
        os.path.join(run8, "sim-incidents", "q001", "_dkr_access_log.yaml"),
        "violated: [unclosed bracket\n  bad yaml here\n",
    )
    expect("T8 audit_dkr_access: parse error treated as violation → exit 1",
           run_script(AUDIT_DKR, [run8]), 1)


# ---------------------------------------------------------------------------
# parity_check tests
# ---------------------------------------------------------------------------

def make_diagnosis(tmp: str, name: str, root_cause_code: str, actions: list[str]) -> str:
    path = os.path.join(tmp, f"{name}.yaml")
    write_yaml(path, {
        "root_cause_code": root_cause_code,
        "recommended_actions": [{"action": a} for a in actions],
    })
    return path


def test_parity_check(tmp: str) -> None:
    # T9 — matching root_cause_code + ≥2/3 overlap → exit 0
    real9  = make_diagnosis(tmp, "real9",  "LAMBDA_COLD_START_TIMEOUT", ["increase-memory", "enable-provisioned-concurrency", "reduce-init-code"])
    fix9   = make_diagnosis(tmp, "fix9",   "LAMBDA_COLD_START_TIMEOUT", ["increase-memory", "enable-provisioned-concurrency", "set-reserved-concurrency"])
    expect("T9 parity_check: match rcc + 2/3 overlap → exit 0",
           run_script(PARITY, [real9, fix9]), 0)

    # T10 — mismatched root_cause_code → exit 1
    real10 = make_diagnosis(tmp, "real10", "LAMBDA_COLD_START_TIMEOUT", ["increase-memory", "enable-provisioned-concurrency", "reduce-init-code"])
    fix10  = make_diagnosis(tmp, "fix10",  "ECS_OOM_KILL",              ["increase-memory", "enable-provisioned-concurrency", "reduce-init-code"])
    expect("T10 parity_check: rcc mismatch → exit 1",
           run_script(PARITY, [real10, fix10]), 1)

    # T11 — matching root_cause_code but only 1/3 overlap → exit 1
    real11 = make_diagnosis(tmp, "real11", "LAMBDA_COLD_START_TIMEOUT", ["increase-memory", "enable-provisioned-concurrency", "reduce-init-code"])
    fix11  = make_diagnosis(tmp, "fix11",  "LAMBDA_COLD_START_TIMEOUT", ["set-reserved-concurrency", "configure-vpc-endpoint", "tune-timeout-setting"])
    expect("T11 parity_check: rcc match but 1/3 action overlap → exit 1",
           run_script(PARITY, [real11, fix11]), 1)

    # T12 — missing root_cause_code in real file → exit 2
    real12 = os.path.join(tmp, "real12.yaml")
    fix12  = make_diagnosis(tmp, "fix12", "LAMBDA_COLD_START_TIMEOUT", ["increase-memory"])
    write_yaml(real12, {"recommended_actions": [{"action": "increase-memory"}]})
    expect("T12 parity_check: missing rcc in real → exit 2",
           run_script(PARITY, [real12, fix12]), 2)

    # T13 — full 3/3 action overlap → exit 0
    real13 = make_diagnosis(tmp, "real13", "ECS_TASK_OOM", ["increase-memory-limit", "enable-ecs-exec", "check-container-insights"])
    fix13  = make_diagnosis(tmp, "fix13",  "ECS_TASK_OOM", ["check-container-insights", "increase-memory-limit", "enable-ecs-exec"])
    expect("T13 parity_check: rcc match + 3/3 overlap → exit 0",
           run_script(PARITY, [real13, fix13]), 0)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="us13_smoke_") as tmp:
        test_audit_bash_calls(tmp)
        test_audit_dkr_access(tmp)
        test_parity_check(tmp)

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)

    print(f"\n=== US-13 Smoke Tests: {passed}/{len(_results)} passed ===")
    for name, ok, detail in _results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if not ok:
            print(f"         {detail}", file=sys.stderr)

    if failed:
        print(f"\n{failed} test(s) FAILED.", file=sys.stderr)
        return 1

    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
