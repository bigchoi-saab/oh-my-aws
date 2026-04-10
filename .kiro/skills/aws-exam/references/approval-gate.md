# Approval Gate Protocol

**Version**: 1.0.0  
**Phase**: 2A  
**Owner**: aws-exam skill  
**Referenced by**: aws-exam SKILL.md Phase 6, aws-exam SKILL.md v0.2.0 (Task #8)

---

## 1. Purpose

After Phase 4 Reflect produces `reflection.yaml` with improvement proposals, Phase 6 presents the top-N proposals to the human for review. This document defines:
- The interactive approval flow (approve / defer / reject / view_details)
- The `/aws-exam improvements apply` command behavior
- The hard prohibition on auto-editing `.kiro/` files

**Core invariant**: Approval is a status marker, not an auto-edit trigger. The system records that a human approved a proposal; the human must make the actual file edits and commit them manually.

---

## 2. Phase 6 — Human Approval Gate

### 2.1 Trigger Conditions

Phase 6 runs after Phase 5 (Record & Track) completes, unless the run was invoked with `--no-approval`.

```
# Interactive approval gate (default)
/aws-exam run

# Skip interactive gate — proposals written but no prompt
/aws-exam run --no-approval
```

When `--no-approval` is used: all proposal files are written with `applied_by: null`, `applied_at: null`, `applied_commit: null`. The human can apply them later via `/aws-exam improvements apply <proposal-id>`.

### 2.2 Proposal Presentation

Read `reflection.yaml` from the current run directory. Extract `top_proposals[]` (top 3 by priority score). Present to user via `AskUserQuestion`:

```
AWS Exam Run Complete — Improvement Proposals

Run: {run_id}  |  mc_score: {score}  |  Proposals: {count}

Top proposals for review:

  [1] {proposal_id}
      Layer: {layer}  |  Target: {target_file}
      Summary: {one_line_summary}
      Impact: {impact_estimate}

  [2] {proposal_id}
      Layer: {layer}  |  Target: {target_file}
      Summary: {one_line_summary}
      Impact: {impact_estimate}

  [3] {proposal_id}
      Layer: {layer}  |  Target: {target_file}
      Summary: {one_line_summary}
      Impact: {impact_estimate}

Options:
  approve <N>     — Mark proposal N as approved (writes apply metadata stub; YOU edit the file)
  defer <N>       — Defer proposal N to next run
  reject <N>      — Reject proposal N (requires reason)
  view_details <N> — Show full proposal file for proposal N
  done            — Exit approval gate (remaining proposals stay pending)
```

### 2.3 Branch Behaviors

#### `approve <N>`

1. Read proposal file at `proposals/{proposal_id}.yaml`.
2. Verify `applied_by` is currently `null` (idempotency check — skip if already applied).
3. Write apply metadata stub to proposal file:
   ```yaml
   applied_by: null      # Human fills this in after making the edit
   applied_at: null      # Human fills this in after making the edit
   applied_commit: null  # Human fills this in after git commit
   status: approved
   approved_at: {ISO8601 timestamp}
   ```
4. Append proposal as a tracked follow-up to `.omc/plans/open-questions.md`:
   ```markdown
   ## [{proposal_id}] {one_line_summary}
   - **Source**: `{run_id}/proposals/{proposal_id}.yaml`
   - **Target**: `{target_file}`
   - **Layer**: {layer}
   - **Status**: approved — awaiting human edit + commit
   - **Apply command**: `/aws-exam improvements apply {proposal_id}`
   - **Backlink**: proposal_id={proposal_id}
   ```
5. Print confirmation:
   ```
   Proposal {proposal_id} approved.
   Next steps (YOU must do these):
     1. Edit: {target_file}
     2. Apply the change described in: {run_dir}/proposals/{proposal_id}.yaml
     3. git commit -m "apply proposal {proposal_id}: {one_line_summary}"
     4. Run: /aws-exam improvements apply {proposal_id} --commit <sha>
   ```
6. Re-prompt with remaining proposals.

<!-- HARD CONSTRAINT — AUTO-EDIT FORBIDDEN:
     The approve branch MUST NOT use Write, Edit, or any file-modification tool
     on any path under .kiro/. The only file written by approve is the proposal
     YAML itself (applying the status: approved + approved_at fields).
     Violation of this constraint corrupts the DKR ground truth and invalidates
     the measurement signal. There are no exceptions. -->

#### `defer <N>`

1. Write to proposal file:
   ```yaml
   status: deferred
   deferred_at: {ISO8601 timestamp}
   deferred_reason: "user deferred at Phase 6 review"
   ```
2. The proposal re-surfaces in the next run's Phase 6 if the same failure pattern persists (regression tracker identifies same `failure_pattern_id`).
3. Print confirmation and re-prompt.

#### `reject <N>`

1. Prompt user for a rejection reason (required — do not accept empty string).
2. Write to proposal file:
   ```yaml
   status: rejected
   rejected_at: {ISO8601 timestamp}
   rejected_reason: "{user-provided reason}"
   ```
3. The proposal is suppressed in future runs unless the underlying failure pattern changes (different `root_cause_code` or `failure_layer` in a future run's reflection).
4. Print confirmation and re-prompt.

<!-- HARD CONSTRAINT — AUTO-EDIT FORBIDDEN:
     The reject branch MUST NOT edit any .kiro/ file. The rejection reason
     is stored only in the proposal file. The DKR, scenarios, agents, and
     skill files are not touched. -->

#### `view_details <N>`

1. Read full proposal file from `proposals/{proposal_id}.yaml`.
2. Display the complete contents.
3. Re-prompt with the same option set (approve / defer / reject / view_details / done).

#### `done`

Exit the approval gate. Remaining proposals retain their current status (`pending`). They can be reviewed in a future run or via `/aws-exam improvements`.

---

## 3. `/aws-exam improvements apply` Command

### 3.1 Purpose

Allows the human to record, after the fact, that they have made the edit and committed it. This command writes **only apply metadata** to the proposal file. It does NOT edit any `.kiro/` file.

### 3.2 Usage

```bash
/aws-exam improvements apply <proposal-id>
/aws-exam improvements apply <proposal-id> --commit <git-sha>
```

### 3.3 Behavior

1. Locate proposal file: search `proposals/{proposal_id}.yaml` under all run directories in `.ops/exam-results/`.
2. Verify `status: approved` (only approved proposals can be applied; pending/deferred/rejected proposals are rejected with an error message).
3. Write apply metadata:
   ```yaml
   applied_by: {git user.name from `git config user.name`}
   applied_at: {ISO8601 timestamp}
   applied_commit: {--commit value, or null if not provided}
   status: applied
   ```
4. Print confirmation:
   ```
   Proposal {proposal_id} marked as applied.
   applied_by: {name}
   applied_at: {timestamp}
   applied_commit: {sha or "(not provided)"}

   The proposal file has been updated. No .kiro/ files were modified.
   ```
5. Update regression tracker entry for this proposal's `proposal_outcome` field to `applied`.

<!-- HARD CONSTRAINT — AUTO-EDIT FORBIDDEN:
     The apply command writes ONLY to the proposal YAML file:
       applied_by, applied_at, applied_commit, status: applied
     It does NOT:
       - Edit .kiro/agents/*.md
       - Edit .kiro/skills/*/references/scenarios/*.yaml  (DKR — inviolable)
       - Edit .kiro/skills/*/references/*.yaml
       - Edit .kiro/skills/*/SKILL.md
       - Edit any file outside .ops/exam-results/
     Violation of this constraint is a critical bug. The human is the only
     actor permitted to edit .kiro/ files. -->

### 3.4 Idempotency

Running `apply` on an already-applied proposal updates `applied_commit` if `--commit` is provided and the current value is null. Otherwise it is a no-op (prints "already applied" and exits 0).

---

## 4. Proposal File Structure

Every proposal file is created by Phase 4 (Reflect) with ownership metadata stubs present from creation. This is enforced by Task #7 (reflection protocol) and verified by Task #9.

```yaml
# proposals/{proposal_id}.yaml
proposal_id: prop-{run_id}-{question_id}-{sequence}
run_id: run-2026-04-05T14-30
question_id: exam-lambda-throttle-001
failure_layer: knowledge_gap          # knowledge_gap | reasoning_error | priority_error | procedural_error
target_file: ".kiro/skills/aws-incident-response/references/scenarios/lambda-throttle.yaml"
target_section: "root_causes[0].description"
summary: "Add missing concurrent execution limit root cause entry"
detail: |
  The diagnostician failed to identify reserved_concurrency=0 as the root cause.
  The DKR scenario's root_causes section does not explicitly list this as a
  distinct root cause code. Adding THROTTLE-RESV-ZERO with clear description
  would close the knowledge gap.
proposed_change: |
  + root_causes:
  +   - code: THROTTLE-RESV-ZERO
  +     description: "Reserved concurrency set to 0 blocks all invocations..."
impact_estimate: high
priority_score: 0.85
created_at: 2026-04-05T14:35:00Z

# Ownership metadata — stubs present from creation (Task #7 enforces; Task #9 verifies)
status: pending           # pending | approved | deferred | rejected | applied
applied_by: null          # filled by human after making the edit
applied_at: null          # filled by /aws-exam improvements apply
applied_commit: null      # filled by /aws-exam improvements apply --commit <sha>
approved_at: null         # filled at Phase 6 approve branch
rejected_at: null
rejected_reason: null
deferred_at: null
```

---

## 5. `/aws-exam improvements` Command (Status View)

```bash
/aws-exam improvements              # list all proposals from latest run
/aws-exam improvements --run <id>   # list proposals from specific run
/aws-exam improvements --status pending|approved|applied|deferred|rejected
```

Output format:
```
Improvement Proposals — {run_id}

PENDING (awaiting review):
  prop-run-2026-04-05T14-30-q001-1  lambda-throttle-001  knowledge_gap   high
  prop-run-2026-04-05T14-30-q003-1  ecs-crash-loop-001   reasoning_error medium

APPROVED (awaiting human edit):
  prop-run-2026-04-05T14-30-q002-1  dynamodb-throttle-001 priority_error  low
    → Apply: /aws-exam improvements apply prop-run-2026-04-05T14-30-q002-1

APPLIED:
  (none)
```

---

## 6. Mock Run — Branch Decision Table

| User action | Proposal status before | Writes to | Proposal status after | .kiro/ modified? |
|---|---|---|---|---|
| `approve 1` | pending | proposal YAML + open-questions.md | approved | **NO** |
| `defer 2` | pending | proposal YAML | deferred | **NO** |
| `reject 3` + reason | pending | proposal YAML | rejected | **NO** |
| `view_details 1` | any | none | unchanged | **NO** |
| `done` | any | none | unchanged | **NO** |
| `/aws-exam improvements apply <id>` | approved | proposal YAML only | applied | **NO** |
| `/aws-exam improvements apply <id>` | pending/deferred/rejected | none (error) | unchanged | **NO** |

**Every branch: `.kiro/` is never modified.** The human makes all edits to `.kiro/` files after approval.

---

## 7. Integration with Task #8 (SKILL.md v0.2.0)

Task #8 (aws-exam SKILL.md v0.2.0 rewrite) must add Phase 6 to the phase table referencing this document:

```markdown
### Phase 6: Human Approval Gate

See: `.kiro/skills/aws-exam/references/approval-gate.md`

If `--no-approval` flag was passed to `/aws-exam run`, skip this phase.

1. Read `reflection.yaml.top_proposals[]` from current run directory.
2. Present top-3 proposals via AskUserQuestion per approval-gate.md §2.2.
3. Process each user response per approval-gate.md §2.3 branch table.
4. `/aws-exam improvements apply <id>` is documented in approval-gate.md §3.
```
