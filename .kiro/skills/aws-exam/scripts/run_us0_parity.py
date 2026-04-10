#!/usr/bin/env python3
"""
run_us0_parity.py — US-0 parity test runner wrapper (scaffold)

EXIT CODE CONTRACT:
  0  = PASS — parity_check.py passed; Phase 2A may proceed
  1  = FAIL — parity_check.py failed; Phase 2A is BLOCKED (see US-0 AC#7)
  2  = ERROR — argument error or unexpected failure
  42 = BASELINE NOT READY — .ops/incidents/_parity-baseline/ lacks required files;
       US-0 cannot run yet; user must complete the live-incident bootstrap guide first.
       This is NOT a failure — it is an expected pre-condition state.

USAGE:
  python run_us0_parity.py [--baseline-dir <path>] [--fixture-diagnosis <path>] [--report-out <path>]

  Default baseline dir: .ops/incidents/_parity-baseline/
  Default fixture diagnosis: .ops/exam-results/_us0-fixture-run/sim-incidents/_us0-parity-fixture/diagnosis.yaml
  Default report out: .ops/exam-results/_parity-test-{timestamp}.md

PRECONDITION (US-0 AC#1):
  .ops/incidents/_parity-baseline/ must contain at minimum:
    - observe.yaml
    - diagnosis.yaml
  These are produced by the user running one real aws-team-leader incident flow in live mode
  and copying the resulting artifacts into _parity-baseline/. See:
    .kiro/skills/aws-exam/references/live-incident-bootstrap-guide.md

DO NOT RUN THIS SCRIPT UNTIL THE BASELINE EXISTS.
If baseline is absent, this script exits 42 — that is the expected behavior.

WHAT THIS SCRIPT DOES:
  1. Checks baseline directory for required files.
  2. If missing → prints TODO instructions → exits 42.
  3. If present → invokes parity_check.py with real vs fixture diagnosis.yaml.
  4. Writes structured report to --report-out path.
  5. Propagates parity_check.py exit code (0 = pass, 1 = fail).

NOTE: This script does NOT invoke aws-diagnostician. The fixture diagnosis.yaml
must have been produced separately by running aws-diagnostician against the
_us0-parity-fixture question in sim mode (via the aws-exam harness).
That step is part of US-0 execution, not US-0 scaffolding.

DEPENDENCIES: Python stdlib only (delegates to parity_check.py for PyYAML)

TODO [US-0 execution]: After user provides _parity-baseline/ artifacts AND
harness (US-1) generates fixture-run diagnosis.yaml, run this script and
verify exit 0 before marking US-0 passed.
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime, timezone

# Paths relative to project root
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", "..", "..", ".."))

DEFAULT_BASELINE_DIR   = os.path.join(PROJECT_ROOT, ".ops", "incidents", "_parity-baseline")
DEFAULT_FIXTURE_DIAG   = os.path.join(
    PROJECT_ROOT, ".ops", "exam-results", "_us0-fixture-run",
    "sim-incidents", "_us0-parity-fixture", "diagnosis.yaml"
)
PARITY_CHECK_SCRIPT    = os.path.join(SCRIPTS_DIR, "parity_check.py")
BOOTSTRAP_GUIDE        = ".kiro/skills/aws-exam/references/live-incident-bootstrap-guide.md"

EXIT_PASS              = 0
EXIT_FAIL              = 1
EXIT_ERROR             = 2
EXIT_BASELINE_NOT_READY = 42


def check_baseline(baseline_dir: str) -> tuple[bool, list[str]]:
    """
    Returns (ready, missing_files).
    ready=True if both observe.yaml and diagnosis.yaml are present.
    """
    required = ["observe.yaml", "diagnosis.yaml"]
    missing = [
        f for f in required
        if not os.path.isfile(os.path.join(baseline_dir, f))
    ]
    return (len(missing) == 0), missing


def default_report_path() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return os.path.join(PROJECT_ROOT, ".ops", "exam-results", f"_parity-test-{ts}.yaml")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="US-0 parity test runner — checks real-vs-fixture diagnosis parity."
    )
    parser.add_argument(
        "--baseline-dir",
        default=DEFAULT_BASELINE_DIR,
        help=f"Path to _parity-baseline/ directory (default: {DEFAULT_BASELINE_DIR})",
    )
    parser.add_argument(
        "--fixture-diagnosis",
        default=DEFAULT_FIXTURE_DIAG,
        help="Path to fixture-run diagnosis.yaml produced by sim-mode aws-diagnostician",
    )
    parser.add_argument(
        "--report-out",
        default=None,
        help="Path for structured YAML report (default: .ops/exam-results/_parity-test-{ts}.yaml)",
    )
    args = parser.parse_args()

    report_out = args.report_out or default_report_path()

    # --- Step 1: Check baseline ---
    if not os.path.isdir(args.baseline_dir):
        print(
            f"\nTODO: Baseline directory not found: {args.baseline_dir}",
            file=sys.stderr,
        )
        _print_bootstrap_instructions()
        return EXIT_BASELINE_NOT_READY

    ready, missing = check_baseline(args.baseline_dir)
    if not ready:
        print(
            f"\nTODO: Baseline directory exists but is missing required files: {missing}",
            file=sys.stderr,
        )
        print(f"Baseline dir: {args.baseline_dir}", file=sys.stderr)
        _print_bootstrap_instructions()
        return EXIT_BASELINE_NOT_READY

    # --- Step 2: Check fixture diagnosis exists ---
    if not os.path.isfile(args.fixture_diagnosis):
        print(
            f"\nTODO: Fixture diagnosis.yaml not found: {args.fixture_diagnosis}",
            file=sys.stderr,
        )
        print(
            "  The fixture diagnosis must be produced by running aws-diagnostician\n"
            "  against _us0-parity-fixture in sim mode (via aws-exam harness, US-1).\n"
            "  Complete US-1 (harness) first, then re-run this script.",
            file=sys.stderr,
        )
        return EXIT_BASELINE_NOT_READY

    # --- Step 3: Invoke parity_check.py ---
    real_diagnosis = os.path.join(args.baseline_dir, "diagnosis.yaml")
    cmd = [
        sys.executable, PARITY_CHECK_SCRIPT,
        real_diagnosis,
        args.fixture_diagnosis,
        "--report-out", report_out,
    ]

    print(f"Running parity check...")
    print(f"  real:    {real_diagnosis}")
    print(f"  fixture: {args.fixture_diagnosis}")
    print(f"  report:  {report_out}")

    result = subprocess.run(cmd, text=True)

    if result.returncode == 0:
        print(f"\nPARITY PASS — Phase 2A may proceed. Report: {report_out}")
    else:
        print(
            f"\nPARITY FAIL — Phase 2A is BLOCKED (US-0 AC#7). Report: {report_out}",
            file=sys.stderr,
        )
        print(
            "  Options:\n"
            "    (a) Correct harness fixture fidelity and re-run.\n"
            "    (b) Explicitly re-scope measurement with user approval (drop collection_fidelity).",
            file=sys.stderr,
        )

    return result.returncode


def _print_bootstrap_instructions() -> None:
    print(
        "\n" + "=" * 60,
        file=sys.stderr,
    )
    print(
        "US-0 PRECONDITION NOT MET — baseline not ready\n"
        "\n"
        "To establish the parity baseline:\n"
        "  1. Complete the live-incident bootstrap guide:\n"
        f"       {BOOTSTRAP_GUIDE}\n"
        "  2. Copy the resulting incident artifacts to:\n"
        f"       {DEFAULT_BASELINE_DIR}/\n"
        "     Required files: observe.yaml, diagnosis.yaml\n"
        "  3. Re-run this script.\n"
        "\n"
        "Exit code 42 = baseline not ready (not a failure — expected pre-condition).\n"
        "Phase 2A implementation work proceeds in parallel (non-blocking).",
        file=sys.stderr,
    )
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
