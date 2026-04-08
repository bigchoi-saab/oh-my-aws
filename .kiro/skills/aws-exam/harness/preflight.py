"""
preflight.py — HALT-ON-DKR-READ preamble generator (US-11)

Generates the verbatim preflight preamble that must be prepended to every
agent prompt spawned in exam simulation mode. The preamble is the PRIMARY
(fail-closed) DKR-blind enforcement layer.

Usage:
    from harness.preflight import build_preamble, pre_write_dkr_log
    preamble = build_preamble(dkr_log_path)
    pre_write_dkr_log(dkr_log_path)

Exit contract: this module has no side effects at import time.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Verbatim HALT-ON-DKR-READ preamble text (US-11 AC#1)
# This exact string must appear in every agent system prompt in exam mode.
# ---------------------------------------------------------------------------

_HALT_PREAMBLE_TEMPLATE = """\
HALT-ON-DKR-READ: If you are about to Read any path matching \
.claude/skills/aws-incident-response/references/scenarios/*.yaml, \
STOP immediately. Write {{violated: true, attempted_path: <path>}} to \
{dkr_log_path} and return. Do not read the file. Do not continue the task.\
"""


def build_preamble(dkr_log_path: str | Path) -> str:
    """Return the verbatim HALT-ON-DKR-READ preamble for agent prompt injection.

    Args:
        dkr_log_path: Path to _dkr_access_log.yaml (run-relative or absolute).
                      Included verbatim so the agent knows exactly where to write.

    Returns:
        Multi-line string to prepend to the agent's system prompt.

    US-11 AC#1 compliance: returned string contains the exact directive text.
    """
    return _HALT_PREAMBLE_TEMPLATE.format(dkr_log_path=str(dkr_log_path))


def pre_write_dkr_log(dkr_log_path: str | Path) -> None:
    """Pre-write _dkr_access_log.yaml with violated=false BEFORE agent spawn.

    This is the fail-closed setup step. Any subsequent agent write of
    violated=true signals a DKR-blind violation and aborts the run.

    US-11 AC#2 compliance.

    Args:
        dkr_log_path: Absolute path where _dkr_access_log.yaml will be written.
    """
    dkr_log_path = Path(dkr_log_path)
    dkr_log_path.parent.mkdir(parents=True, exist_ok=True)

    log_data = {
        "violated": False,
        "attempted_path": None,
        "written_by": "aws-exam-harness/preflight.py",
        "written_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Pre-written by harness before agent spawn. "
            "If violated=true appears here, a DKR-blind invariant violation occurred — "
            "run must be invalidated (US-11 AC#2)."
        ),
    }

    with open(dkr_log_path, "w", encoding="utf-8") as fh:
        yaml.dump(log_data, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)


def check_dkr_log(dkr_log_path: str | Path) -> tuple[bool, str | None]:
    """Read _dkr_access_log.yaml and return (violated, attempted_path).

    Used by the harness post-run to trigger invalidation if needed.

    US-11 AC#4 compliance.

    Returns:
        (violated: bool, attempted_path: str | None)
    """
    dkr_log_path = Path(dkr_log_path)
    if not dkr_log_path.exists():
        # Log missing entirely — treat as violation (fail-closed)
        return True, "<log_file_missing>"

    with open(dkr_log_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    violated = bool(data.get("violated", False))
    attempted_path = data.get("attempted_path")
    return violated, attempted_path


def handle_invalidation(
    run_dir: str | Path,
    invalidated_dir: str | Path,
    attempted_path: str | None,
) -> None:
    """Move run artifacts to _invalidated/ and raise RuntimeError.

    US-11 AC#4 compliance: entire run (Track A + Track B) is invalidated.
    Caller is responsible for notifying user (AskUserQuestion — US-11 AC#5).

    Args:
        run_dir: The run directory to move (e.g. .ops/exam-results/run-{ts}/).
        invalidated_dir: Root of invalidated runs (.ops/exam-results/_invalidated/).
        attempted_path: The DKR path the agent attempted to read (for error message).
    """
    import shutil

    run_dir = Path(run_dir)
    invalidated_dir = Path(invalidated_dir)
    invalidated_dir.mkdir(parents=True, exist_ok=True)

    dest = invalidated_dir / run_dir.name
    if run_dir.exists():
        shutil.move(str(run_dir), str(dest))

    raise RuntimeError(
        f"DKR-blind invariant violated: agent attempted to read '{attempted_path}'. "
        f"Run '{run_dir.name}' moved to '{dest}'. "
        "Investigate before rerun. (US-11 AC#4)"
    )
