# AWS Incident Operations Playbook for Human Operators

> Date: 2026-04-03
> Purpose: Document how real operators run incidents in AWS environments from first alert to postmortem closure.
> Scope: Availability and reliability incidents (not deep-forensics security incidents).

---

## 1) What This Playbook Optimizes

This document is intentionally operational, not theoretical.

- Minimize customer impact first, then diagnose root cause.
- Keep one decision-maker (Incident Commander) and many executors.
- Use fixed communication cadence to reduce panic and rumor loops.
- Favor reversible mitigations under uncertainty.
- Preserve evidence while restoring service.

---

## 2) Incident Command Model (Who Does What)

## 2.1 Core Roles

| Role | Primary owner behavior | Not responsible for |
|---|---|---|
| Incident Commander (IC) | Declares incident, sets severity, prioritizes options, approves risky actions, drives timeline | Deep debugging alone |
| Operations Lead | Executes mitigations, coordinates service owners, reports technical state to IC | Stakeholder broadcasting |
| Communications Lead | Posts internal and external updates on cadence, keeps message consistency | Technical root cause analysis |
| Subject Matter Expert (SME) | Investigates one subsystem deeply and proposes options with risk | Cross-team coordination |
| Scribe | Maintains timeline, decisions, owners, ETA, evidence links | Decision authority |

## 2.2 Minimum Staffing by Severity

| Severity | Minimum active roles |
|---|---|
| SEV1 | IC + Ops Lead + Comms Lead + Scribe + 2+ SMEs |
| SEV2 | IC + Ops Lead + Comms Lead + 1+ SME |
| SEV3 | On-call lead can combine IC/Ops, plus one SME |
| SEV4 | Normal ticket owner, IC not always required |

---

## 3) Severity Classification and Update Cadence

| Severity | Typical impact | Initial comm cadence | Escalation expectation |
|---|---|---|---|
| SEV1 | Broad outage, major revenue path down, data integrity/security risk | Every 15 min | Executive and cross-team immediate escalation |
| SEV2 | Major degradation or partial outage in core path | Every 30 min | Service owners and management escalation |
| SEV3 | Limited user segment impact, workaround exists | Every 60 min | Team-level escalation |
| SEV4 | Minor defect or local issue | Event-based | Ticket workflow |

Severity can move up fast when uncertainty is high and customer impact is active.

---

## 4) Golden Timeline (How Operators Actually Run Incidents)

## 4.1 Phase A (T+0 to T+5 min): Detect, Declare, Stabilize the Room

Objective: Create command structure faster than problem spread.

Mandatory actions:

1. Acknowledge alert or customer signal.
2. Open incident channel and assign temporary IC.
3. Freeze risky production changes (deploy, schema, infra) unless IC approves exceptions.
4. Start incident record (doc/ticket) with fixed fields:
   - start time (UTC and local),
   - initial symptom,
   - impacted service(s),
   - reporter,
   - current severity (provisional),
   - next update time.

Exit criteria:

- Incident has an IC.
- There is one canonical timeline document.
- Next communication timestamp is published.

## 4.2 Phase B (T+5 to T+15 min): Triage and Severity Lock

Objective: Quantify blast radius quickly enough to guide mitigation.

Mandatory actions:

1. Determine blast radius:
   - region(s), AZ(s), tenant segment, API/surface, write vs read path.
2. Confirm whether incident is:
   - application deployment issue,
   - infrastructure saturation,
   - dependency/provider event,
   - configuration/credential expiry,
   - mixed/cascading.
3. Set severity (SEV1-4) and incident type.
4. Assign role owners (Ops, Comms, SMEs, Scribe).
5. Publish first structured incident update.

Exit criteria:

- Severity agreed and timestamped.
- Roles assigned by name.
- One mitigation branch selected.

## 4.3 Phase C (T+15 to T+45 min): Mitigation Before Explanation

Objective: Reduce customer pain first through reversible actions.

Mitigation order of preference:

1. Roll back latest risky change.
2. Shift traffic (healthy region/cell/path) when available.
3. Disable non-critical feature flags causing pressure.
4. Apply backpressure/rate limits to prevent retry storms.
5. Scale critical bottlenecks only if it is likely to help quickly.

Operator rule:

- If a mitigation is reversible and can be executed safely in under 10 minutes, run it before perfect diagnosis.

Exit criteria:

- A measurable improvement exists (error rate, latency, queue age, success rate).
- Next mitigation or investigation decision is explicit.

## 4.4 Phase D (T+45 min onward): Contain, Recover, Verify

Objective: Confirm sustained recovery and prevent immediate relapse.

Mandatory actions:

1. Validate service health by customer segment and geography, not only aggregate metrics.
2. Keep guarded mode:
   - deploy freeze remains until IC release,
   - temporary limits remain until steady-state confidence.
3. Move from active response to monitoring only after sustained healthy window.
4. Prepare preliminary root cause statement with confidence level (low/medium/high).

Exit criteria:

- Recovery sustained for agreed window.
- Incident transitions to monitoring then resolved state.

## 4.5 Phase E (Closure): Resolve, Hand Off, Start Learning Loop

Objective: End the incident cleanly and start accountable follow-up.

Mandatory actions:

1. Publish resolved message with impact window and known scope.
2. Schedule postmortem within 24-72 hours.
3. Create follow-up actions with owner + due date + verification metric.
4. Preserve timeline and key artifacts (graphs, logs, chat decisions, rollout IDs).

---

## 5) Decision Trees Used During Live Response

## 5.1 Rollback vs Continue Investigating

Use rollback first when all are true:

- Symptom started within one change window.
- No data migration irreversibility is involved.
- Rollback can be done safely and quickly.

Avoid immediate rollback when any is true:

- Rollback may corrupt data consistency.
- System is already drifting and rollback adds more risk.
- Problem is clearly external (provider dependency event).

## 5.2 Suspected AWS or External Dependency Incident

Run provider branch in parallel:

1. Check AWS Health Dashboard and service status updates.
2. Correlate internal symptom onset with provider event timeline.
3. Shift to unaffected region/cell/dependency path if architecture allows.
4. Continue internal mitigation; do not wait passively for provider recovery.

## 5.3 Retry Storm or Queue Backlog Pattern

Indicators:

- Rapid rise in retries/timeouts.
- Queue age and depth grow while throughput drops.

Actions:

1. Reduce retry aggressiveness.
2. Introduce or tighten circuit breakers.
3. Shed non-critical workloads.
4. Drain backlog in controlled mode after downstream recovers.

---

## 6) Communication Operating Model

## 6.1 Internal War Room Rules

- One incident channel, one timeline document, one IC voice for decisions.
- Use explicit status labels: `Investigating`, `Identified`, `Mitigating`, `Monitoring`, `Resolved`.
- Every update includes next timestamp.

## 6.2 Stakeholder Cadence

| Severity | Internal update cadence | External status cadence |
|---|---|---|
| SEV1 | 15 min | 15-30 min |
| SEV2 | 30 min | 30-60 min |
| SEV3 | 60 min | Event-based if customer-facing |

## 6.3 Message Templates

### Incident Declaration (internal)

```text
[Incident Declared]
Severity: SEV2
Start: 2026-04-03 14:05 KST (05:05 UTC)
Impact: Elevated 5xx on checkout API (~22% failure)
Scope: ap-northeast-2, /payments/authorize
Roles: IC=@name, Ops=@name, Comms=@name, Scribe=@name
Current action: rollback to previous release
Next update: 14:20 KST
```

### Status Update (internal/external)

```text
[Status Update]
Time: 14:20 KST
Status: Mitigating
What changed: Rollback completed; 5xx reduced from 22% to 4%
Current risk: queue backlog and elevated latency remain
Next actions: retry limit reduction, controlled backlog drain
Next update: 14:35 KST
```

### Resolved Notice

```text
[Resolved]
Resolved at: 15:10 KST
Customer impact window: 14:05-15:02 KST
Summary: Service restored after rollback and retry tuning
Follow-up: Postmortem scheduled for 2026-04-05 10:00 KST
```

### Executive Brief (SEV1)

```text
SEV1 update @ 14:30 KST
- Customer impact: checkout unavailable for ~35% of traffic in two regions
- Business impact: payment conversion currently down ~18%
- Current strategy: traffic shift + rollback + dependency isolation
- Confidence: medium (restoration trend positive)
- Next hard decision point: 14:45 KST (full feature disable if not <5% errors)
```

---

## 7) Practical Workflow by Common Incident Pattern

## 7.1 Post-Deploy 5xx Spike

1. Freeze deploy pipeline.
2. Compare pre/post release error and latency by endpoint.
3. Roll back if reversible and high confidence of causality.
4. Validate rollback effect per endpoint and region.
5. Keep canary off until guardrails are updated.

Common operator mistake to avoid:

- Running broad speculative debugging before attempting safe rollback.

## 7.2 Regional Degradation (Cloud Dependency Suspected)

1. Confirm affected region(s) and control-plane vs data-plane symptoms.
2. Start parallel branch:
   - internal telemetry correlation,
   - provider-status verification.
3. Shift traffic/workloads from impacted region if failover exists.
4. Apply graceful degradation (disable heavy features, reduce non-critical jobs).
5. Recover region gradually after stability window.

Common operator mistake to avoid:

- Waiting for provider updates without local impact reduction.

## 7.3 Queue Backlog and Retry Amplification

1. Identify retry multipliers and timeout chains.
2. Temporarily reduce retry count and increase jitter.
3. Apply backpressure at edge and worker concurrency controls.
4. Protect downstream dependencies first.
5. Drain backlog in staged batches after core path normalizes.

Common operator mistake to avoid:

- Scaling workers before controlling retry pressure.

## 7.4 Certificate or Credential Expiry Incident

1. Confirm expiry scope (edge cert, internal cert, IAM key, token issuer).
2. Rotate/renew using the least disruptive path.
3. Validate all trust chains and dependent services.
4. Keep temporary monitoring for delayed handshake/auth failures.
5. Add expiry forecasting and ownership alerts.

Common operator mistake to avoid:

- Fixing one endpoint while missing downstream trust chain consumers.

---

## 8) Handoff Protocol (Shift Change During Active Incident)

Handoff must include:

1. Current severity and customer impact.
2. Timeline summary (what changed, when, and why).
3. Active hypotheses with confidence levels.
4. Executed mitigations and observed effects.
5. Open decisions and next timestamp commitments.

Handoff template:

```text
[Incident Handoff]
Time: 16:00 KST
Severity: SEV2
Current status: Monitoring
Impact now: <1% 5xx (baseline 0.2%)
What is done: rollback, traffic shift 20%, retry cap 3->1
What remains: backlog drain completion, region re-balance
Open risks: latent timeout spikes under peak load
Next decision point: 16:20 KST
New IC: @name
```

---

## 9) Postmortem Standard (Blameless, Actionable)

## 9.1 Minimum Sections

1. Executive summary (impact and duration).
2. Customer impact quantification.
3. Detailed timeline with decisions.
4. Root cause and contributing factors.
5. What worked, what did not.
6. Action items categorized by:
   - prevention,
   - detection,
   - response ergonomics.

## 9.2 Action Item Quality Bar

Each action item must include:

- owner,
- due date,
- measurable success criterion,
- verification method.

Weak action (avoid):

- "Improve monitoring"

Strong action (preferred):

- "Add p95 latency composite alert for checkout + downstream auth; owner: platform-oncall; due: 2026-04-18; success: alert fires in staging chaos test and in monthly game day."

## 9.3 Follow-up Cadence

- 48-hour review: verify immediate hardening actions.
- 2-week review: verify structural fixes.
- 6-week review: verify recurrence risk reduction.

---

## 10) Metrics That Reflect Operator Quality

Track both speed and quality:

- MTTD (mean time to detect)
- MTTA (mean time to acknowledge)
- MTTM (mean time to mitigate)
- MTTR (mean time to recover)
- percent of incidents with complete timeline
- percent of action items closed on time
- recurrence rate by incident class

Do not optimize MTTR alone if recurrence rises.

---

## 11) How This Connects to oh-my-aws Harness

Map incident operations to harness phases:

1. Observe: collect alarms, metrics, logs, topology, recent change events.
2. Reason: evaluate severity, blast radius, and mitigation options with risk.
3. Act: execute approved reversible actions (rollback, traffic shift, throttling).
4. Verify: confirm recovery by service, region, and user path.
5. Audit: write full timeline, decisions, evidence, and follow-up tasks.

Agent support should accelerate operators, not replace command discipline.

---

## 12) Real-World Reference Signals Used for This Playbook

The workflow above is aligned with recurring patterns from AWS and industry incident reports and guidance.

- AWS post-event summaries:
  - https://aws.amazon.com/message/12721/
  - https://aws.amazon.com/message/41926/
  - https://aws.amazon.com/message/11201/
  - https://aws.amazon.com/message/101925/
- AWS guidance:
  - https://docs.aws.amazon.com/security-ir/latest/userguide/what-is-security-incident-response.html
  - https://docs.aws.amazon.com/security-ir/latest/userguide/detect-and-analyze.html
  - https://docs.aws.amazon.com/security-ir/latest/userguide/post-incident-report.html
  - https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html
- Google SRE:
  - https://sre.google/sre-book/managing-incidents/
  - https://sre.google/workbook/incident-response/
  - https://sre.google/workbook/postmortem-culture/
- PagerDuty incident operations:
  - https://response.pagerduty.com/getting_started/
  - https://response.pagerduty.com/before/severity_levels/
  - https://response.pagerduty.com/training/incident_commander/
- Public operator examples:
  - https://shopify.engineering/that-old-certificate-expired-and-started-an-outage-this-is-what-happened-next
  - https://www.shopifystatus.com/incidents/tbtk2sk9d5tp
  - https://stripe.com/rcas/2019-07-10
  - https://github.blog/news-insights/company-news/addressing-githubs-recent-availability-issues-2/
  - https://github.blog/news-insights/company-news/github-availability-report-february-2026/
  - https://r.jina.ai/http://netflixtechblog.com/empowering-netflix-engineers-with-incident-management-ebb967871de4

---

## 13) Quick-Use One Page Checklist

```text
[First 15 Minutes]
1) Declare incident, assign IC, open timeline, set next update time.
2) Freeze risky changes.
3) Measure blast radius (region, feature, tenant, API, write/read path).
4) Set severity and role assignments.
5) Execute first reversible mitigation.
6) Publish update on fixed cadence.

[Before Resolve]
1) Confirm sustained recovery window.
2) Validate customer path, not only internal graphs.
3) Publish resolved notice with impact window.
4) Schedule postmortem and assign owners.
```
