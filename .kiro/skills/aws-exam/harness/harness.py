"""
harness.py — Core evidence-injection harness for aws-exam simulation mode (US-1)

Usage (CLI smoke-test):
    cd .claude/skills/aws-exam
    python -m harness.harness \\
        --question .claude/skills/aws-incident-response/references/exam-bank/lambda-timeout-001.yaml \\
        --run-id smoke-test \\
        --ops-root .ops/exam-results

Programmatic usage:
    from harness.harness import Harness
    h = Harness(ops_root=".ops/exam-results", run_id="run-2026-04-05T16-00")
    sim_dir = h.build_sim_incident("path/to/question.yaml")
    preamble = h.get_agent_preamble(sim_dir)

Design constraints:
- NEVER reads .claude/skills/aws-incident-response/references/scenarios/*.yaml (US-1 AC#6)
- Idempotent: second run for same qid+run_id overwrites identically (US-1 AC#8)
- All fixture files carry provenance footer (US-1 AC#7)
- _dkr_access_log.yaml pre-written with violated=false BEFORE any agent spawn (US-11 AC#2)
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path
from typing import Any

import yaml

from harness.preflight import build_preamble, pre_write_dkr_log
from harness.sim_incident_writer import (
    write_exam_mode_flag,
    write_evidence_fixtures,
    write_symptoms,
)

# ---------------------------------------------------------------------------
# DKR path guard — never read these paths (US-1 AC#6)
# ---------------------------------------------------------------------------
_FORBIDDEN_PATH_PATTERN = (
    ".claude/skills/aws-incident-response/references/scenarios/"
)

# Parity baseline write guard — harness must never write into this directory.
# The baseline is a human-captured live-mode artifact; harness writes would
# poison it. See us0-parity-runbook.md regression note.
_PARITY_BASELINE_PATTERN = ".ops/incidents/_parity-baseline"


def _assert_not_dkr(path: str | Path) -> None:
    """Raise if path matches the DKR scenarios glob. Defensive guard."""
    p = str(path).replace("\\", "/")
    if _FORBIDDEN_PATH_PATTERN in p:
        raise PermissionError(
            f"Harness attempted to read DKR path '{path}'. "
            "This violates US-1 AC#6 and ADR-2. Halting."
        )


def _assert_not_parity_baseline(path: str | Path) -> None:
    """Raise if path resolves under _parity-baseline/. Harness must never write there."""
    p = str(path).replace("\\", "/")
    if _PARITY_BASELINE_PATTERN in p:
        raise PermissionError(
            f"Harness attempted to write to parity baseline path '{path}'. "
            "The _parity-baseline/ directory is a protected live-mode artifact. "
            "Harness writes are forbidden. See us0-parity-runbook.md."
        )


# ---------------------------------------------------------------------------
# Harness class
# ---------------------------------------------------------------------------

class Harness:
    """Evidence-injection harness — converts exam YAML evidence into agent-readable fixtures."""

    def __init__(self, ops_root: str | Path, run_id: str) -> None:
        """
        Args:
            ops_root: Root of exam results (e.g. .ops/exam-results).
            run_id:   Run identifier (e.g. run-2026-04-05T16-00 or smoke-test).
        """
        self.ops_root = Path(ops_root)
        self.run_id = run_id
        self.run_dir = self.ops_root / run_id
        self.sim_incidents_dir = self.run_dir / "sim-incidents"
        self.invalidated_dir = self.ops_root / "_invalidated"
        _assert_not_parity_baseline(self.run_dir)  # guard at construction time

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_sim_incident(self, question_yaml_path: str | Path) -> Path:
        """Build the sim-incident directory for one exam question.

        Reads the question YAML (never a DKR scenario), writes all fixture
        files, and pre-writes _dkr_access_log.yaml. Idempotent.

        US-1 AC#1-8 + US-11 AC#2.

        Args:
            question_yaml_path: Path to exam-bank/{qid}.yaml.

        Returns:
            Path to the sim-incident directory for this question.
        """
        question_yaml_path = Path(question_yaml_path)
        _assert_not_dkr(question_yaml_path)  # US-1 AC#6
        _assert_not_parity_baseline(question_yaml_path)  # parity baseline write guard

        question_data = self._load_question(question_yaml_path)
        question = question_data.get("question", question_data)  # handle top-level or nested
        question_id = question.get("id") or question_yaml_path.stem

        sim_dir = self.sim_incidents_dir / question_id
        sim_dir.mkdir(parents=True, exist_ok=True)
        evidence_dir = sim_dir / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        created_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. _exam_mode_flag.yaml — exactly 5 required fields (US-1 AC#2)
        write_exam_mode_flag(sim_dir, question_id, created_at)

        # 2. _dkr_access_log.yaml — pre-written {violated: false} (US-11 AC#2)
        dkr_log_path = sim_dir / "_dkr_access_log.yaml"
        pre_write_dkr_log(dkr_log_path)

        # 3. symptoms.md — human-readable scenario
        write_symptoms(sim_dir, question)

        # 4-5. evidence/ fixture files (metrics, logs, cli-outputs)
        evidence_list = question.get("scenario", {}).get("evidence", [])

        # Handle optional expanded_fixture (Q10 Hybrid resolution)
        expanded = question.get("expanded_fixture")
        if expanded:
            evidence_list = self._flatten_expanded_fixture(expanded)

        write_evidence_fixtures(evidence_dir, evidence_list, question_id)

        return sim_dir

    def get_agent_preamble(self, sim_dir: Path) -> str:
        """Return the HALT-ON-DKR-READ preamble to prepend to agent system prompts.

        US-11 AC#1 compliance. This returns ONLY the fail-closed HALT directive.
        For a complete orchestrator-ready spawn prompt, use get_full_spawn_prompt().

        Args:
            sim_dir: The sim-incident directory for this question.
        """
        dkr_log_path = sim_dir / "_dkr_access_log.yaml"
        return build_preamble(dkr_log_path)

    def get_full_spawn_prompt(self, sim_dir: Path) -> str:
        """Return a complete orchestrator-ready spawn prompt for aws-diagnostician in exam mode.

        Assembles the three pieces SKILL.md Phase 2 Track B step 3 requires:
          1. HALT-ON-DKR-READ preamble (verbatim, from get_agent_preamble)
          2. exam-simulation-protocol.md reference path
          3. sim-incident directory path + required fields reminder

        Using this single helper instead of hand-assembling at call-sites guarantees
        every agent spawn sees the full exam-mode context. SKILL.md Phase 2 Track B
        step 3 should call this method.

        Args:
            sim_dir: The sim-incident directory for this question.
        """
        sim_dir = Path(sim_dir)
        halt_preamble = self.get_agent_preamble(sim_dir)
        sim_dir_posix = sim_dir.as_posix()
        protocol_ref = (
            ".claude/skills/aws-exam/references/exam-simulation-protocol.md"
        )
        exam_flag_path = (sim_dir / "_exam_mode_flag.yaml").as_posix()

        return (
            f"{halt_preamble}\n"
            f"\n"
            f"EXAM SIMULATION MODE\n"
            f"====================\n"
            f"You are running against a pre-built sim-incident directory, not live AWS.\n"
            f"\n"
            f"1. FIRST, Read {exam_flag_path} to confirm mode: simulation and dkr_blind: true.\n"
            f"2. Read the simulation protocol at {protocol_ref} for behavior rules:\n"
            f"   - Rule A: read fixture files under {sim_dir_posix}/evidence/ instead of\n"
            f"     running aws CLI commands.\n"
            f"   - Rule B: populate observe.yaml.sources_read[] with every fixture you read\n"
            f"     (sim_mode_required per handoff-schemas.yaml R11 extension).\n"
            f"   - Rule D: populate observe.yaml.intended_commands[] with the aws CLI commands\n"
            f"     you would have run in live mode, keyed to fixture_key (collection_fidelity\n"
            f"     scoring target).\n"
            f"3. Run your normal Observe -> Diagnose phases. Write observe.yaml and diagnosis.yaml\n"
            f"   into {sim_dir_posix}/. Do NOT run any aws ... CLI command.\n"
            f"4. The HALT directive above is fail-closed: reading any scenarios/*.yaml file\n"
            f"   invalidates the entire run.\n"
        )

    def check_and_handle_violation(self, sim_dir: Path) -> None:
        """Post-run: check _dkr_access_log.yaml for violation; move run to _invalidated if found.

        US-11 AC#4 compliance. Raises RuntimeError on violation.
        Caller must catch and surface via AskUserQuestion (US-11 AC#5).
        """
        from harness.preflight import check_dkr_log, handle_invalidation

        dkr_log_path = sim_dir / "_dkr_access_log.yaml"
        violated, attempted_path = check_dkr_log(dkr_log_path)

        if violated:
            handle_invalidation(self.run_dir, self.invalidated_dir, attempted_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_question(self, path: Path) -> dict[str, Any]:
        """Load and return the question YAML. Asserts not DKR. US-1 AC#6."""
        _assert_not_dkr(path)
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def _flatten_expanded_fixture(self, expanded: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert expanded_fixture dict to evidence[] list format.

        Q10 Hybrid resolution: per-question opt-in to richer fixtures.
        """
        evidence = []
        for etype, entries in expanded.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                evidence.append({"type": etype, **entry})
        return evidence


# ---------------------------------------------------------------------------
# CLI entry point (smoke-test)
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="aws-exam-harness v1 — build sim-incident fixture bundle"
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Path to exam-bank/{qid}.yaml",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        dest="run_id",
        help="Run identifier (e.g. run-2026-04-05T16-00 or smoke-test)",
    )
    parser.add_argument(
        "--ops-root",
        default=".ops/exam-results",
        dest="ops_root",
        help="Root of exam results directory (default: .ops/exam-results)",
    )
    args = parser.parse_args()

    harness = Harness(ops_root=args.ops_root, run_id=args.run_id)

    try:
        sim_dir = harness.build_sim_incident(args.question)
    except PermissionError as exc:
        print(f"ERROR (DKR guard): {exc}", file=sys.stderr)
        sys.exit(1)

    preamble = harness.get_agent_preamble(sim_dir)

    print(f"Sim-incident directory: {sim_dir}")
    print(f"\nFiles written:")
    for f in sorted(sim_dir.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(sim_dir)}")

    print(f"\nAgent preamble (prepend to system prompt):\n{'─'*60}")
    print(preamble)
    print('─'*60)
    print("\nSmoke-test complete. Verify _exam_mode_flag.yaml and _dkr_access_log.yaml.")


if __name__ == "__main__":
    _main()
