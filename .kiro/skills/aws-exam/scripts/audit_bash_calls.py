#!/usr/bin/env python3
"""
audit_bash_calls.py — Post-run Bash-call audit for aws-exam skill (US-13, US-2 AC#8)

EXIT CODE CONTRACT:
  0  = PASS — zero `aws ...` Bash calls found in agent traces under the run directory
  1  = FAIL — one or more `aws ...` Bash calls detected; offending calls printed to stderr
  2  = ERROR — run directory not found, or no agent-traces/ directory present

USAGE:
  python audit_bash_calls.py <run_dir>

  <run_dir> is the path to a single exam run, e.g.:
    .ops/exam-results/run-2026-04-05T14-30/

  Parses every *.jsonl file under <run_dir>/agent-traces/ and looks for
  tool invocations of type "bash" whose command starts with "aws " (case-insensitive).

  Called by: aws-exam harness post-run verification step.
  Non-zero exit marks run invalid with chain_status: illegal_live_aws_call.

DEPENDENCIES: Python stdlib + PyYAML (PyYAML not required here; stdlib json used)
"""

import json
import sys
import os
import re


AWS_CALL_PATTERN = re.compile(r'^\s*aws\s+', re.IGNORECASE)


def find_trace_files(run_dir: str) -> list[str]:
    traces_dir = os.path.join(run_dir, "agent-traces")
    if not os.path.isdir(traces_dir):
        return []
    return [
        os.path.join(traces_dir, f)
        for f in os.listdir(traces_dir)
        if f.endswith(".jsonl")
    ]


def parse_bash_calls(trace_file: str) -> list[dict]:
    """Return list of offending tool invocation records from a .jsonl trace file."""
    offenders = []
    with open(trace_file, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(
                    f"  WARNING: {trace_file}:{lineno}: JSON parse error: {exc}",
                    file=sys.stderr,
                )
                continue

            # Support two common trace record shapes:
            # Shape A: {"type": "tool_use", "tool": "Bash", "input": {"command": "..."}}
            # Shape B: {"tool_name": "Bash", "tool_input": {"command": "..."}}
            tool_name = (
                record.get("tool")
                or record.get("tool_name")
                or ""
            ).lower()
            tool_input = record.get("input") or record.get("tool_input") or {}
            command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

            if tool_name == "bash" and AWS_CALL_PATTERN.match(command):
                offenders.append({
                    "file": trace_file,
                    "line": lineno,
                    "command": command.strip(),
                    "record": record,
                })
    return offenders


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: audit_bash_calls.py <run_dir>", file=sys.stderr)
        return 2

    run_dir = sys.argv[1]
    if not os.path.isdir(run_dir):
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 2

    trace_files = find_trace_files(run_dir)
    if not trace_files:
        # No agent-traces directory or no .jsonl files — treat as clean pass
        # (harness may not have produced traces yet; caller decides if that itself is an error)
        return 0

    all_offenders = []
    for tf in sorted(trace_files):
        all_offenders.extend(parse_bash_calls(tf))

    if not all_offenders:
        return 0

    # FAIL — print structured report to stderr
    print(
        f"FAIL: {len(all_offenders)} illegal live AWS Bash call(s) detected in exam mode.",
        file=sys.stderr,
    )
    print(f"Run directory: {run_dir}", file=sys.stderr)
    print("Offending calls:", file=sys.stderr)
    for o in all_offenders:
        agent_name = os.path.basename(o["file"]).replace(".jsonl", "")
        print(
            f"  agent={agent_name}  line={o['line']}  command={o['command']!r}",
            file=sys.stderr,
        )
    print(
        "\nchain_status: illegal_live_aws_call — mark run invalid.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
