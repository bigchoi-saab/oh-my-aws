# Live Incident Bootstrap Guide — Phase 2A Parity Baseline

**Audience**: You (the user) — this is the only step in the `aws-exam-skill-chain-v2` plan that requires a human action against real AWS.
**Purpose**: Produce a single real-execution artifact set that US-0 can compare against the fixture-based diagnostician output. Without this baseline, `collection_fidelity` scoring has nothing to score against.
**When to run**: Any time before US-0 is executed. All other Phase 2A user stories (US-0.5, US-1, US-2, US-3, US-4, US-5, US-6, US-11, US-12, US-13) proceed in parallel without blocking on this step.
**Time budget**: ~30–45 minutes including scenario setup, team-leader execution, and artifact copy.

---

## 1. Why this exists

The Phase 2A `collection_fidelity` rubric (US-3) measures whether the fixture-based diagnostician, running in simulation mode against `exam-bank` fixtures, collects the **same evidence** a real diagnostician would collect against a real AWS environment. To score this, the grader needs a ground-truth observation trace produced by a real pipeline run. That trace is the **parity baseline**.

The baseline is a one-time artifact. Once captured, US-0 replays the same scenario through the fixture harness and computes similarity against this baseline. You do not need to re-run this step for every exam round — only if the scenario or the diagnostician agent materially changes.

If you decide not to run the live incident at all, the fallback per Executor Handoff Note #1 in `.omc/plans/aws-exam-skill-chain-v2.md` is to scope `collection_fidelity` out of the Phase 2A rubric with your explicit approval. That reduces the rubric back to 1 dimension (`reasoning_fidelity` only) and partially defeats the iteration-2 measurement-validity fix, so the live-incident path is preferred.

---

## 2. Prerequisites (verify before step 3)

- [ ] **AWS CLI configured** with a profile that has read access to CloudWatch Metrics, CloudWatch Logs, CloudTrail, and the service you are going to exercise (Lambda or DynamoDB recommended — see §3).
- [ ] **Sandbox account**, not production. The scenarios in §3 are low blast-radius, but this guide assumes isolation.
- [ ] **Region confirmed** — export `AWS_REGION` and `AWS_PROFILE` in your shell before running the incident.
- [ ] **`.ops/incidents/` directory writable** — the team-leader pipeline will create subdirectories here automatically; verify the path exists under `C:/dev/oh-my-aws/.ops/incidents/` (create it manually if missing).
- [ ] **aws-team-leader skill and aws-incident-response skill** are both present at `.kiro/skills/` — they are the orchestrator and domain-knowledge skills the pipeline needs.

---

## 3. Pick your scenario (recommendation: `lambda-throttle`)

Any single DKR scenario works as long as it produces all 5 artifacts (`observe.yaml`, `diagnosis.yaml`, `execution.yaml`, `verification.yaml`, `audit-report.yaml`). You only need **one** real incident — not all 20. Pick the one you can reproduce most cheaply and reversibly.

### Recommended: `lambda-throttle-concurrency-exhaustion`

**Why**: Reversible (concurrency config rollback), low cost (no sustained data plane load), high signal (CloudWatch throttle metrics appear within 1–2 minutes), and one of the most complete DKR entries in `exam-bank`.

**Setup sketch** (not exhaustive — adapt to your account):
1. Deploy a throwaway Lambda (any handler — e.g., a 100ms sleep).
2. Set reserved concurrency to `2`.
3. Fire 50 concurrent invocations via `aws lambda invoke` in a loop or a small load generator.
4. Wait ~60 seconds for CloudWatch `Throttles` metric to register.
5. You now have a real incident. Proceed to step 4.

### Alternative: `dynamodb-throttle-provisioned-capacity`

**Why**: Also reversible (capacity adjustment), produces clean ProvisionedThroughputExceededException signals in CloudTrail and CloudWatch.

**Setup sketch**:
1. Create a throwaway DynamoDB table in provisioned mode with `1` RCU / `1` WCU.
2. Run a small parallel write loop (`aws dynamodb put-item` ×20) to exceed capacity.
3. Throttling appears within seconds.

### Not recommended for bootstrap

Scenarios involving `iam-compromise`, `region-outage`, `cascade-failure`, `az-failure`, or anything requiring multi-service orchestration. These are either unsafe to reproduce or too expensive. Stick to single-service throttling.

---

## 4. Run the incident through aws-team-leader

Invoke the Kiro-side team-leader flow with an incident description that matches your scenario. The team-leader routes to the appropriate DKR entry in `aws-incident-response` and may use the `aws-incident-responder` quick path or the `aws-diagnostician -> aws-executor -> aws-reporter` chain when the full pipeline is needed.

### 4a. Trigger the pipeline

Open Kiro CLI in `C:/dev/oh-my-aws/` and describe the incident in plain language so the `aws-team-leader` skill can classify it. Example prompts:

```text
Lambda 함수 throttle 발생. CloudWatch Throttles 메트릭 급증. aws-team-leader workflow로 triage해줘.
```

or

```text
DynamoDB 테이블 ProvisionedThroughputExceededException 에러 다발. aws-team-leader workflow로 대응해줘.
```

The Kiro workflow should run the full `scenario-detect -> diagnose -> remediate -> verify -> audit` pipeline and write artifacts under `.ops/incidents/...`. **Let it run end-to-end.** Do not interrupt. When it asks for approval on a remediation step, approve it or decline it explicitly.

**Important — this is live mode, not simulation.** The diagnostician will make real AWS API calls (`describe-*`, `get-metric-data`, `filter-log-events`, `lookup-events`, etc.) against your sandbox account. The executor may execute real remediation commands if you approve. Keep your sandbox account isolated.

### 4b. Confirm the incident directory

When the pipeline finishes, team-leader prints a final report pointing at:

```
.ops/incidents/{YYYY-MM-DDTHH-MM}-{scenario-id}/
```

Example:

```
.ops/incidents/2026-04-05T16-30-lambda-throttle/
```

List the directory and confirm **all five artifacts are present**:

```bash
ls -la .ops/incidents/2026-04-05T16-30-lambda-throttle/
```

Expected files:
- `observe.yaml` — sources_read, intended_commands, raw observations (**critical — this is what US-0 compares against**)
- `diagnosis.yaml` — decision tree traversal, root cause hypothesis
- `execution.yaml` — intended/executed remediation commands, approvals
- `verification.yaml` — post-remediation checks, stability window
- `audit-report.yaml` — timeline, evidence, follow-ups

If any file is missing, the pipeline aborted mid-run. Investigate the team-leader output, fix the cause, and re-run. Do NOT proceed with a partial artifact set — US-0 parity scoring requires all five.

---

## 5. Copy artifacts into the parity baseline directory

Once the incident directory contains all 5 files, copy it into the dedicated baseline location so US-0 can find it at a stable path:

```bash
mkdir -p .ops/incidents/_parity-baseline/
cp -r .ops/incidents/2026-04-05T16-30-lambda-throttle/* .ops/incidents/_parity-baseline/
```

(Substitute your actual incident directory name for `2026-04-05T16-30-lambda-throttle`.)

Then add a small `_parity-baseline/metadata.yaml` describing which scenario this baseline represents:

```yaml
schema: parity-baseline-metadata/v1
captured_at: "2026-04-05T16:30:00Z"
captured_by: user-live-incident
source_incident_dir: ".ops/incidents/2026-04-05T16-30-lambda-throttle/"
scenario_id: "lambda-throttle-concurrency-exhaustion"
dkr_yaml: ".kiro/skills/aws-incident-response/references/scenarios/lambda-throttle.yaml"
agents_operating_mode: "live"
notes: |
  Live-mode baseline capture for Phase 2A US-0 parity test.
  Captured via real aws-team-leader pipeline against sandbox AWS account.
```

The `agents_operating_mode: "live"` field is the key marker that this trace was produced in live mode and is therefore valid as ground truth for `collection_fidelity` scoring against a simulation-mode re-run.

---

## 6. Validate the baseline

Before handing off to US-0, confirm the baseline has the two fields US-0 will score against (R11 carry-forward):

```bash
grep -A2 "sources_read:" .ops/incidents/_parity-baseline/observe.yaml
grep -A2 "intended_commands:" .ops/incidents/_parity-baseline/observe.yaml
```

Both fields must be present and non-empty. These are the fields US-2 AC#9 will require the sim-mode diagnostician to also populate, and US-3 AC#3 will score the two against each other. If `observe.yaml` does NOT contain these fields, your team-leader version is pre-R11 and needs the R11 schema extension applied before the baseline is usable. Flag this to the executor — do NOT hand-edit `observe.yaml` to add them, because that would poison the baseline.

---

## 7. You are done

Tell the executor: **"Live-incident baseline captured at `.ops/incidents/_parity-baseline/`. US-0 can proceed."**

The executor will then run US-0, which replays your chosen scenario through the fixture harness in simulation mode and computes similarity against the baseline. If parity is below threshold, US-0 surfaces it for debugging before Phase 2A proceeds.

---

## 8. If you decide NOT to run this

Tell the executor: **"Skipping live-incident baseline. Scope `collection_fidelity` out of Phase 2A rubric."**

The executor will then:
- Drop `collection_fidelity` from the US-3 rubric weights
- Re-normalize `reasoning_fidelity` to 1.00 weight
- Log the fallback decision in the v2 rubric migration record
- Proceed with Phase 2A as a 1-dimensional skill_chain_score rubric

This is a supported fallback path but it partially undoes the iteration-2 measurement-validity fix. Prefer the live-incident path unless you have a strong reason not to.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pipeline stops after `observe.yaml` | Diagnostician couldn't match scenario | Provide a more specific incident description keyed to a routing-table entry in `aws-incident-response/SKILL.md` §9 |
| `execution.yaml` empty | You declined remediation approval | That's fine — US-0 only strictly requires `observe.yaml`. Continue to step 5. |
| `observe.yaml` missing `sources_read` / `intended_commands` | Team-leader is pre-R11 | Stop. Do not use this baseline. Ask executor to apply R11 schema extension first. |
| Incident directory has wrong scenario_id | Routing misfire | Re-run with clearer keywords matching the routing table |
| `.ops/incidents/` doesn't exist | First-ever incident run | `mkdir -p .ops/incidents/` and re-run |

---

## 10. References

- Plan: `.omc/plans/aws-exam-skill-chain-v2.md` — see Executive Summary pre-kickoff block, US-0 acceptance criteria, Section 13 Handoff Note #1
- Team-leader SKILL: `.kiro/skills/aws-team-leader/SKILL.md`
- Team-leader triage protocol: `.kiro/skills/aws-team-leader/references/triage-protocol.md` (defines the `.ops/incidents/{id}/` directory convention)
- DKR routing table: `.kiro/skills/aws-incident-response/SKILL.md` §9
- Handoff schemas: `.kiro/skills/aws-team-leader/references/handoff-schemas.yaml` (defines `observe.yaml` schema — look for R11 extensions `sources_read` and `intended_commands`)
