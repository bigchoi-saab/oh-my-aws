# Reflection Protocol — aws-exam Skill-Chain v2

**Version**: 1.0.0
**Phase**: 2A
**Schema reference**: `handoff-schemas.yaml > reflection/v1`
**Consumed by**: aws-exam Phase 4 Reflect (aws-exam-reflector subagent)
**Updated**: 2026-04-05

---

## 1. Purpose

This document defines how the aws-exam reflector classifies failures and generates improvement proposals after each dual-track exam run. It provides:

1. A **decision table** mapping (failure type, failure location, artifact content) → (layer)
2. **Allowed layer values** for `failure_attribution[].layer`
3. **Proposal file format** requirements including ownership metadata and target fields
4. **Unclassifiable case handling** (defaults to `layer: unclear`)
5. **DKR proposal policy** (requires human approval per ADR-2)

---

## 2. Allowed Layer Values

Every `failure_attribution[].layer` MUST be one of these enumerated values:

| Layer value | Meaning |
|---|---|
| `skill:aws-incident-response` | Skill-level protocol, ordering, or guardrail definition |
| `skill:aws-cdk-operations` | CDK operations skill content |
| `skill:aws-exam` | Exam skill orchestration or prompt logic |
| `agent:aws-diagnostician` | Diagnostician agent prompt, observe/diagnosis logic |
| `agent:aws-executor` | Executor agent prompt, execution logic |
| `agent:aws-reporter` | Reporter agent prompt, reporting logic |
| `agent:aws-cdk-analyzer` | CDK analyzer agent |
| `agent:aws-cdk-engineer` | CDK engineer agent |
| `agent:aws-grader` | Grader agent rubric logic |
| `dkr:scenarios/{name}` | DKR scenario file (specific scenario named) |
| `harness:fixture-mapping` | Evidence-injection harness fixture format or mapping |
| `rubric:grading-rubric` | Grading rubric dimension definition or scoring criteria |
| `unclear` | Cannot be classified — escalate to human review |

**Important**: `dkr:*` layers always require human approval (see Section 5).

---

## 3. Decision Table

Each row has a unique ID (`DT-{N}`) used in `failure_attribution[].decision_table_row_cited`.

Rows are evaluated in order. Use the FIRST matching row. If no row matches, apply the unclassifiable default (Section 4).

### How to use this table

For each failure in a run, determine:
- **Failure type**: What went wrong (wrong root_cause, wrong action order, etc.)
- **Failure location**: Which artifact contains the failure (diagnosis.yaml, observe.yaml, etc.)
- **Artifact content signals**: What does the artifact content tell us about WHY it failed

Then match against the table below.

---

### Decision Table Rows

#### DT-1: Wrong root_cause_code — evidence-consistent reasoning

| Field | Value |
|---|---|
| **Row ID** | `DT-1` |
| **Failure type** | `reasoning_fidelity` low: `diagnosis.yaml.root_cause_code` does not match DKR ground truth |
| **Failure location** | `diagnosis.yaml` |
| **Artifact content signal** | `decision_tree_trace` is logically consistent with the fixture evidence (agent followed the evidence correctly but reached wrong conclusion — DKR decision tree may be ambiguous or root_cause description insufficiently distinctive) |
| **Layer** | `dkr:scenarios/{scenario_id}` — section `root_causes[].description` |
| **Rationale** | If the agent reasoned correctly from the available evidence but still reached the wrong root_cause, the fault is in the DKR root_cause descriptions being insufficiently distinctive or the decision_tree branches being ambiguous. The agent cannot be blamed for following correct evidence to a wrong DKR mapping. |
| **Proposed action scope** | Clarify `root_causes[{wrong_code}].description` to differentiate it from `root_causes[{correct_code}].description`. Add distinguishing symptoms or metric thresholds. |
| **requires_human_approval** | `true` (DKR layer) |

---

#### DT-2: Wrong root_cause_code — reasoning inconsistent with evidence

| Field | Value |
|---|---|
| **Row ID** | `DT-2` |
| **Failure type** | `reasoning_fidelity` low: `diagnosis.yaml.root_cause_code` does not match DKR ground truth |
| **Failure location** | `diagnosis.yaml` |
| **Artifact content signal** | `decision_tree_trace` shows a branch that contradicts the fixture evidence (e.g., evidence shows Init Duration=8200ms but agent concludes "memory insufficient" without checking SnapStart). Reasoning is internally inconsistent with available data. |
| **Layer** | `agent:aws-diagnostician` |
| **Rationale** | If the agent reasoning contradicts the evidence it already had, the fault is in the diagnostician decision-logic or prompt guidance, not in the DKR content. The DKR evidence would have led a correct reasoner to the right conclusion. |
| **Proposed action scope** | Improve `aws-diagnostician` prompt guidance for the specific decision branch that failed. Consider adding a step to `exam-simulation-protocol.md` requiring the agent to cross-check each decision_tree_trace step against the evidence before proceeding. |
| **requires_human_approval** | `false` |

---

#### DT-3: Correct root_cause but wrong action order

| Field | Value |
|---|---|
| **Row ID** | `DT-3` |
| **Failure type** | `action_appropriateness` or `procedure_compliance` low: `diagnosis.yaml.recommended_actions` are correct but ordered incorrectly |
| **Failure location** | `diagnosis.yaml.recommended_actions[].order` |
| **Artifact content signal** | `recommended_actions` items match DKR `remediation.actions` but the `order` values differ from DKR prescribed sequence (e.g., investigation steps placed before mitigation) |
| **Layer** | `dkr:scenarios/{scenario_id}` — section `remediation[].actions.order` (if ordering principle is scenario-specific) OR `skill:aws-incident-response` (if ordering principle is a general mitigation-first rule) |
| **Classification rule** | If the wrong order violates a general `mitigation-first` principle defined in the aws-incident-response skill → `skill:aws-incident-response`. If the wrong order is scenario-specific (only wrong for THIS incident type) → `dkr:scenarios/{scenario_id}`. |
| **Proposed action scope** | For `dkr:*`: clarify `remediation[].actions[].order` field with explicit ordering rationale. For `skill:*`: reinforce mitigation-first ordering in the skill guardrails section. |
| **requires_human_approval** | `true` if layer is `dkr:*`; `false` if layer is `skill:*` |

---

#### DT-4: Missing guardrail reference

| Field | Value |
|---|---|
| **Row ID** | `DT-4` |
| **Failure type** | `procedure_compliance` low: agent did not reference or apply a guardrail that DKR requires before an action |
| **Failure location** | `diagnosis.yaml.recommended_actions` or `execution.yaml` |
| **Artifact content signal** | A HIGH-risk action appears without a corresponding `pre_conditions` check, or rollback_command is not mentioned, or approval_required step is skipped. DKR `guardrails.pre_conditions` lists conditions that must be checked. |
| **Layer** | `dkr:scenarios/{scenario_id}` — section `guardrails.pre_conditions` (if the guardrail is scenario-specific and insufficiently prominent in DKR) OR `agent:aws-executor` (if the guardrail is clearly defined in DKR but the executor ignored it) |
| **Classification rule** | If the DKR guardrail exists but executor skipped it → `agent:aws-executor`. If the guardrail is missing or poorly specified in DKR → `dkr:scenarios/{scenario_id}`. |
| **Proposed action scope** | For `agent:*`: update executor prompt to explicitly enumerate guardrail checks before HIGH-risk actions. For `dkr:*`: add `block: true` to the missing pre_condition or add an explicit rollback_command field. |
| **requires_human_approval** | `true` if layer is `dkr:*`; `false` if layer is `agent:*` |

---

#### DT-5: Correct answer but rubric scored it low

| Field | Value |
|---|---|
| **Row ID** | `DT-5` |
| **Failure type** | `mc_score` high (exact_match correct) but `reasoning_fidelity` or `diagnosis_accuracy` dimension low, OR `total_weighted_score < 0.7` despite correct answer selection |
| **Failure location** | `exam-result.yaml` dimension scores |
| **Artifact content signal** | `exam-result.exact_match.correct == true` but one or more rubric dimension scores are unexpectedly low. The agent selected the right answer but the reasoning trace, DKR section mapping, or artifact structure did not satisfy rubric criteria. |
| **Layer** | `rubric:grading-rubric` |
| **Rationale** | When the correct answer is selected but rubric disagrees, the rubric criteria may be over-restrictive, ambiguous, or the dimension weight may be miscalibrated. The agent answer is correct — the measurement is the suspect. |
| **Proposed action scope** | Review the specific dimension scoring criteria in `grading-rubric.yaml`. Clarify the `3`-point criterion to be less ambiguous. Consider whether the dimension weight reflects its actual importance. |
| **requires_human_approval** | `false` |

---

#### DT-6: Low collection_fidelity but correct diagnosis

| Field | Value |
|---|---|
| **Row ID** | `DT-6` |
| **Failure type** | `collection_fidelity` low: `observe.yaml.intended_commands` do not match DKR expected commands, BUT `reasoning_fidelity` is high (correct root_cause_code) |
| **Failure location** | `observe.yaml.intended_commands[]` |
| **Artifact content signal** | `intended_commands` are either absent (FAIL_LOUD not triggered — field exists but content wrong), wrong category, or missing key DKR-expected CLI commands. Despite this, `diagnosis.yaml.root_cause_code` matches DKR ground truth — agent got lucky on sparse fixture. `observe.yaml.sources_read` may be populated but `intended_commands` content is wrong. |
| **Layer** | `agent:aws-diagnostician` (observe phase) |
| **Rationale** | The diagnostician observe phase did not ask for the right evidence — it would have asked the wrong questions in live mode. Even though the diagnosis is correct (from sparse fixture), the collection strategy is flawed. The fault is in the diagnostician observe-phase logic/prompt, not in the DKR content. |
| **Proposed action scope** | Update `exam-simulation-protocol.md` `intended_commands` mapping guidance or add an explicit instruction in the diagnostician exam-mode prompt to consult `diagnosis.decision_tree[].check_command` when building `intended_commands`. |
| **requires_human_approval** | `false` |

---

#### DT-7: High collection_fidelity but wrong diagnosis

| Field | Value |
|---|---|
| **Row ID** | `DT-7` |
| **Failure type** | `reasoning_fidelity` low: `diagnosis.yaml.root_cause_code` does not match DKR ground truth, BUT `collection_fidelity` is high (intended_commands match DKR expected commands) |
| **Failure location** | `diagnosis.yaml.root_cause_code` and `decision_tree_trace` |
| **Artifact content signal** | `observe.yaml.intended_commands` correctly match DKR expected CLI commands — the agent asked the right questions. But `diagnosis.yaml.root_cause_code` is wrong despite having the right evidence. The decision_tree_trace shows the agent had the right data but drew the wrong conclusion. |
| **Layer** | `dkr:scenarios/{scenario_id}` — section `root_causes[].description` (if DKR decision tree is ambiguous given the evidence) OR `skill:aws-incident-response` (if the diagnosis logic violates a general diagnostic principle in the skill) |
| **Classification rule** | Inspect `decision_tree_trace` branches: if the DKR `diagnosis.decision_tree` branching conditions are ambiguous given the available evidence → `dkr:scenarios/{scenario_id}`. If the trace shows the agent violated a general diagnostic principle (e.g., jumped to conclusion without checking alternatives) → `skill:aws-incident-response`. |
| **Proposed action scope** | For `dkr:*`: sharpen `diagnosis.decision_tree[].branches[].condition` with specific metric thresholds or log patterns that unambiguously differentiate root causes. For `skill:*`: reinforce the relevant diagnostic principle in the skill observation/diagnosis phase guidance. |
| **requires_human_approval** | `true` if layer is `dkr:*`; `false` if layer is `skill:*` |

---

#### DT-8: FAIL_LOUD — missing sim-mode fields

| Field | Value |
|---|---|
| **Row ID** | `DT-8` |
| **Failure type** | `collection_fidelity` grading triggered FAIL_LOUD: `observe.yaml.sources_read` or `observe.yaml.intended_commands` field absent in sim mode |
| **Failure location** | `observe.yaml` |
| **Artifact content signal** | `skill-chain-result.grading_evidence.missing_sim_fields_error` is non-null. Run marked `chain_failure: missing_sim_mode_fields`. |
| **Layer** | `agent:aws-diagnostician` |
| **Rationale** | In sim mode, diagnostician MUST populate `sources_read` and `intended_commands` per US-2 AC#9 and `exam-simulation-protocol.md`. Missing fields mean the agent did not follow the protocol — fault is in the agent sim-mode compliance, not in the DKR or rubric. |
| **Proposed action scope** | Add a stronger enforcement note to the diagnostician exam-mode prompt preamble. Consider adding a post-observe validation step in the harness that checks for these fields before proceeding to diagnosis. |
| **requires_human_approval** | `false` |

---

#### DT-9: Correct action but wrong risk assessment

| Field | Value |
|---|---|
| **Row ID** | `DT-9` |
| **Failure type** | `procedure_compliance` low: agent selected correct remediation actions but assigned wrong risk level (e.g., marked a HIGH-risk action as LOW, bypassing approval gate) |
| **Failure location** | `diagnosis.yaml.recommended_actions[].risk` or `diagnosis.yaml.risk_level` |
| **Artifact content signal** | `recommended_actions` match DKR `remediation.actions` by name/command, but `risk` field value differs from DKR `estimated_risk`. Approval-gate check would pass when it should not (or vice versa). |
| **Layer** | `dkr:scenarios/{scenario_id}` — section `remediation[].actions[].estimated_risk` (if DKR risk labeling is missing or wrong) OR `agent:aws-diagnostician` (if DKR risk is clearly labeled but agent assigned a different value) |
| **Classification rule** | Compare agent risk assignment against DKR `remediation.actions[].estimated_risk`. If DKR is clear → `agent:aws-diagnostician`. If DKR lacks `estimated_risk` field → `dkr:scenarios/{scenario_id}`. |
| **requires_human_approval** | `true` if layer is `dkr:*`; `false` if layer is `agent:*` |

---

#### DT-10: Fixture format mismatch

| Field | Value |
|---|---|
| **Row ID** | `DT-10` |
| **Failure type** | `artifact_completeness` low OR `chain_coverage` low due to agent failing to parse fixture data (not a reasoning failure — agent could not extract evidence) |
| **Failure location** | `evidence/*.yaml` fixture files or `observe.yaml` |
| **Artifact content signal** | `observe.yaml.sources_read` shows fixture files were accessed, but `observe.yaml.metrics_snapshot` or `observe.yaml.recent_logs` is empty despite fixture having data. Suggests fixture YAML structure does not match the agent expected schema. |
| **Layer** | `harness:fixture-mapping` |
| **Rationale** | When an agent reads a fixture file but fails to extract data, the problem is in the fixture format or the harness evidence rendering, not in the agent reasoning capability. |
| **Proposed action scope** | Review the harness evidence rendering logic (`evidence/{metrics,logs,cli-outputs}.yaml` format). Ensure fixture keys match what the agent expects based on `exam-simulation-protocol.md` fixture-to-CLI mapping table. |
| **requires_human_approval** | `false` |

---

## 4. Unclassifiable Default

When NO row in Section 3 matches a failure, apply this default:

```yaml
layer: unclear
decision_table_row_cited: null
requires_human_review: true
human_review_reason: "Failure pattern does not match any canonical row in reflection-protocol.md. Manual classification required."
```

Additionally, append a note to `.omc/plans/open-questions.md` in the format:

```markdown
### Unclassifiable Reflection Case — {run_id} / {question_id}

- **Date**: {ISO8601 timestamp}
- **Run**: {run_id}
- **Question**: {question_id}
- **Failure type observed**: {brief description}
- **Artifact signals**: {what the artifact showed}
- **Why unclassifiable**: {which DT rows were considered and why they did not match}
- **Proposed new DT row**: {if the reviewer can identify a pattern, suggest a new row}
- **Action**: Human reviewer should classify and either (a) add a new DT row to reflection-protocol.md, or (b) confirm `layer: unclear` and propose a fix manually.
```

The reflector MUST NOT edit `.kiro/**/*` files. Only append to `.omc/plans/open-questions.md`.

---

## 5. DKR Proposal Policy (ADR-2 compliance)

When `layer` starts with `dkr:`, the proposal file MUST include:

```yaml
requires_human_approval: true
approval_reason: "DKR edits are governed by ADR-2; only human can modify ground truth"
```

The reflector writes the proposal file but does NOT edit the DKR file. The human applies the proposed change after review through the approval gate (Phase 6, `approval-gate.md`).

---

## 6. Proposal File Format

Each failure generates a proposal file at:
```
.ops/exam-results/run-{ts}/proposals/{question_id}-{seq}.md
```

### Required fields (YAML frontmatter)

```yaml
---
proposal_id: "{question_id}-{seq}"
run_id: "{run_id}"
created_at: "{ISO8601}"

# Target — required for US-6 outcome computation (Handoff Note #4)
target_question: "{question_id}"
target_dimension: "collection_fidelity | reasoning_fidelity | mc | chain_coverage | artifact_completeness"

# Classification
layer: "{layer value from Section 2}"
decision_table_row_cited: "{DT-N}"
failure_type: "{knowledge_gap | reasoning_error | priority_error | procedural_error | collection_gap | rubric_calibration}"

# File attribution
file_path: "{absolute or repo-relative path to target file}"
section: "{YAML path or markdown header — e.g., root_causes[THROTTLE-RESV-ZERO].description}"

# DKR policy
requires_human_approval: true | false
approval_reason: "{if requires_human_approval is true}"

# Ownership metadata stubs (populated when applied, NOT by reflector)
applied_by: null
applied_at: null
applied_commit: null
---
```

### Required body sections

```markdown
## Problem Summary
{1-3 sentence description of what went wrong and why it matters for measurement quality}

## File + Section
- **File**: `{file_path}`
- **Section**: `{section}`

## Before (current state)
{current content — quote the relevant lines/YAML keys}

## After (proposed change)
{proposed new content — may be a unified diff snippet}

## Justification
{Why this change would improve the score on target_dimension for target_question}

## Regression Risk
{LOW | MEDIUM | HIGH} — {brief rationale: what could break if this change is applied incorrectly}
```

---

## 7. Top Proposals Selection

After all per-question proposals are generated, the reflector selects `top_proposals[]` for `reflection.yaml` using this algorithm:

1. Group proposals by `target_dimension`.
2. Within each group, sort by `failure_type` priority: `reasoning_error` > `priority_error` > `procedural_error` > `knowledge_gap` > `collection_gap` > `rubric_calibration`.
3. Boost proposals that appear for multiple questions (frequency weight: +1 per additional question).
4. Select top-3 across all groups (frequency-weighted priority).
5. Mark each top proposal with `rank: 1|2|3` in `reflection.yaml.top_proposals[]`.

---

## 8. Reflector Constraints

The reflector MUST:
- Cite a `decision_table_row_cited` in every `failure_attribution` entry.
- Populate `target_question` and `target_dimension` in every proposal file at creation time.
- Include all ownership metadata stubs (`applied_by: null`, `applied_at: null`, `applied_commit: null`).
- Append to `.omc/plans/open-questions.md` for every unclassifiable case.
- Mark all `dkr:*` proposals with `requires_human_approval: true`.

The reflector MUST NOT:
- Edit any file under `.kiro/` or `.kiro/skills/` or `.kiro/agents/`.
- Edit any DKR scenario file directly.
- Delete or overwrite existing proposal files from prior runs.
- Apply its own proposals.
