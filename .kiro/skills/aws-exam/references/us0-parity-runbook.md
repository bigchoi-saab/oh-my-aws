# US-0 Parity Test Runbook

**Status**: SCAFFOLD — awaiting user live-incident baseline  
**Phase**: 2A entry gate  
**Related plan section**: aws-exam-skill-chain-v2.md §5 US-0

---

## Overview

US-0 is a **blocking gate for Phase 2A kickoff**. It validates that sparse-evidence fixtures are a valid proxy for real `observe.yaml` output from live CloudWatch/CLI. Until this test passes (exit 0), Phase 2A simulation-mode runs are blocked.

This runbook documents the preconditions, execution steps, pass criteria, and fail response.

---

## Precondition: Live-Incident Bootstrap

**The user must complete the live-incident bootstrap guide before running US-0.**

Guide location: `.claude/skills/aws-exam/references/live-incident-bootstrap-guide.md`

That guide instructs the user to:
1. Execute one real `/aws-incident` in live mode (real or staging AWS environment).
2. Copy the resulting incident artifacts into `.ops/incidents/_parity-baseline/`.

**Required files in `.ops/incidents/_parity-baseline/`:**
- `observe.yaml` — produced by aws-diagnostician in live mode
- `diagnosis.yaml` — produced by aws-diagnostician in live mode

Until these files exist, `run_us0_parity.py` exits with code **42** ("baseline not ready"). This is NOT a failure — it is an expected pre-condition state signaling that Phase 2A implementation work should continue in parallel.

> **REGRESSION NOTE**: The harness (US-1, Task #4) MUST NOT touch `_parity-baseline/` at any point. The harness creates sim-incident fixtures under `.ops/exam-results/run-{ts}/sim-incidents/` only. Any harness write to `_parity-baseline/` is a regression that would corrupt the baseline. If you observe unexpected writes to `_parity-baseline/`, file it as a bug against Task #4 (worker-1).

---

## How to Run

### Step 1: Verify baseline exists

```bash
ls .ops/incidents/_parity-baseline/observe.yaml
ls .ops/incidents/_parity-baseline/diagnosis.yaml
```

If either is missing, complete the live-incident bootstrap guide first.

### Step 2: Generate fixture-run diagnosis

The harness (US-1) must generate a sim-incident fixture from the `_us0-parity-fixture` question:

```bash
# Via aws-exam harness (after US-1 ships)
# This produces: .ops/exam-results/_us0-fixture-run/sim-incidents/_us0-parity-fixture/diagnosis.yaml
/aws-exam run --question _us0-parity-fixture --track skill-chain-only --run-id _us0-fixture-run
```

### Step 3: Run the parity check

```bash
python .claude/skills/aws-exam/scripts/run_us0_parity.py
```

Optional: specify custom paths:

```bash
python .claude/skills/aws-exam/scripts/run_us0_parity.py \
  --baseline-dir .ops/incidents/_parity-baseline \
  --fixture-diagnosis .ops/exam-results/_us0-fixture-run/sim-incidents/_us0-parity-fixture/diagnosis.yaml \
  --report-out .ops/exam-results/_parity-test-$(date -u +%Y-%m-%dT%H-%M-%S).yaml
```

---

## Pass Criteria (US-0 AC#5, AC#6, AC#8)

`run_us0_parity.py` exits **0** when:

1. `root_cause_code` in real `diagnosis.yaml` **exactly matches** `root_cause_code` in fixture `diagnosis.yaml`.
2. Top-3 `recommended_actions` overlap between real and fixture is **≥ 2 out of 3** (order-independent).

The structured report is written to `.ops/exam-results/_parity-test-{timestamp}.yaml` and must be linked from `regression-tracker.yaml` (see US-6).

---

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0    | PASS — parity criteria met | Phase 2A may proceed |
| 1    | FAIL — criteria not met | See Fail Response below |
| 2    | ERROR — file not found or parse error | Fix and re-run |
| 42   | BASELINE NOT READY | Complete bootstrap guide first |

---

## Fail Response (US-0 AC#7)

If `run_us0_parity.py` exits **1** (parity fail), **Phase 2A is BLOCKED**. Two remediation paths:

### Path A — Fix harness fixture fidelity

1. Inspect the structured diff in the parity report (`.ops/exam-results/_parity-test-*.yaml`).
2. Identify which evidence items in `_us0-parity-fixture.yaml` produce the divergence.
3. Update evidence items in the fixture to better match the real CloudWatch signals.
4. Re-generate fixture-run diagnosis (Step 2 above).
5. Re-run `run_us0_parity.py`.
6. Repeat until exit 0.

### Path B — Explicit re-scope (requires user approval)

If the mismatch is structural (e.g., sparse fixtures fundamentally cannot reproduce real diagnosis results), the measurement must be explicitly re-scoped:

- Admit that `collection_fidelity` is untestable in simulation mode.
- Drop `collection_fidelity` from the rubric with explicit user approval.
- Document the decision in `regression-tracker.yaml` and the plan's ADR section.

**Path B requires user decision — do not proceed unilaterally.**

---

## Files Involved

| File | Role |
|------|------|
| `.ops/incidents/_parity-baseline/observe.yaml` | Real live-mode observation (user provides) |
| `.ops/incidents/_parity-baseline/diagnosis.yaml` | Real live-mode diagnosis (user provides) |
| `.claude/skills/aws-incident-response/references/exam-bank/_us0-parity-fixture.yaml` | Fixture question (NOT in _index.yaml) |
| `.ops/exam-results/_us0-fixture-run/sim-incidents/_us0-parity-fixture/diagnosis.yaml` | Sim-mode diagnosis (harness generates) |
| `.claude/skills/aws-exam/scripts/run_us0_parity.py` | This runbook's runner |
| `.claude/skills/aws-exam/scripts/parity_check.py` | Core diff logic (US-13) |
| `.ops/exam-results/_parity-test-{timestamp}.yaml` | Structured report output |

---

## Status

**US-0: NOT RUN — awaiting user live-incident baseline.**

The scaffold is in place. All scripts are verified functional (smoke tests pass).  
Phase 2A implementation work continues in parallel pending baseline capture.
