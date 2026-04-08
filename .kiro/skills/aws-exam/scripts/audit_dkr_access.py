#!/usr/bin/env python3
"""
audit_dkr_access.py — Post-run DKR access audit for aws-exam skill (US-13, US-11 AC#3)

EXIT CODE CONTRACT:
  0  = PASS — no `violated: true` found in any _dkr_access_log.yaml under the run directory
  1  = FAIL — at least one _dkr_access_log.yaml has violated: true; details printed to stderr
  2  = ERROR — run directory not found

USAGE:
  python audit_dkr_access.py <run_dir>

  <run_dir> is the path to a single exam run, e.g.:
    .ops/exam-results/run-2026-04-05T14-30/

  Walks <run_dir> recursively and finds every _dkr_access_log.yaml.
  For each log, checks `violated` field. If true, records the agent name
  (inferred from directory path) and `attempted_path`.

  This script is the BACKUP (Layer 2) detection mechanism. The PRIMARY
  defense is the fail-closed HALT-ON-DKR-READ preflight directive (Layer 1).
  A non-zero exit here means the run must be invalidated even if Layer 1
  did not halt the agent.

  Called by: aws-exam harness post-run verification step.
  Non-zero exit marks run invalid with chain_status: dkr_blind_violation.

DEPENDENCIES: Python stdlib + PyYAML
"""

import sys
import os
import yaml


def find_dkr_logs(run_dir: str) -> list[str]:
    """Recursively find all _dkr_access_log.yaml files under run_dir."""
    matches = []
    for root, _dirs, files in os.walk(run_dir):
        for fname in files:
            if fname == "_dkr_access_log.yaml":
                matches.append(os.path.join(root, fname))
    return sorted(matches)


def check_log(log_path: str) -> dict | None:
    """
    Parse a _dkr_access_log.yaml. Return a violation record if violated=true,
    else None.
    """
    with open(log_path, "r", encoding="utf-8") as fh:
        try:
            data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            # Treat parse failures as a potential violation (conservative)
            return {
                "log_path": log_path,
                "violated": True,
                "attempted_path": None,
                "parse_error": str(exc),
            }

    if not isinstance(data, dict):
        return None

    violated = data.get("violated", False)
    if violated:
        return {
            "log_path": log_path,
            "violated": True,
            "attempted_path": data.get("attempted_path"),
            "agent": data.get("agent"),
        }
    return None


def infer_agent_name(log_path: str) -> str:
    """Best-effort: derive agent name from the sim-incident directory path."""
    # Expected path structure:
    #   <run_dir>/sim-incidents/<question-id>/_dkr_access_log.yaml
    parts = log_path.replace("\\", "/").split("/")
    # Look for 'sim-incidents' segment
    try:
        idx = parts.index("sim-incidents")
        return parts[idx + 1] if idx + 1 < len(parts) - 1 else "unknown"
    except ValueError:
        return "unknown"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: audit_dkr_access.py <run_dir>", file=sys.stderr)
        return 2

    run_dir = sys.argv[1]
    if not os.path.isdir(run_dir):
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 2

    log_files = find_dkr_logs(run_dir)
    if not log_files:
        # No access logs found — pass (harness may not have created them yet)
        return 0

    violations = []
    for lf in log_files:
        result = check_log(lf)
        if result is not None:
            if result.get("agent") is None:
                result["agent"] = infer_agent_name(lf)
            violations.append(result)

    if not violations:
        return 0

    # FAIL — print structured report to stderr
    print(
        f"FAIL: {len(violations)} DKR access violation(s) detected.",
        file=sys.stderr,
    )
    print(f"Run directory: {run_dir}", file=sys.stderr)
    print("Violations:", file=sys.stderr)
    for v in violations:
        parse_note = f"  (parse_error: {v['parse_error']})" if v.get("parse_error") else ""
        print(
            f"  agent={v['agent']}  attempted_path={v['attempted_path']!r}"
            f"  log={v['log_path']}{parse_note}",
            file=sys.stderr,
        )
    print(
        "\nchain_status: dkr_blind_violation — mark entire run invalid.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
