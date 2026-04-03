# Post-Incident Report: {incident-id}

> Blameless postmortem. Focus: what did the system fail to prevent, detect, or contain — not who made a mistake.
> Draft: oh-my-aws agent auto-populates sections 1–3 from timeline-template.md. Human team completes sections 4–6.
> Due: within 72 hours of incident resolution for SEV1/SEV2; within 1 week for SEV3.

---

## 1. Executive Summary

| Field | Value |
|-------|-------|
| Incident ID | `{incident-id}` |
| Incident window | `{start UTC}` to `{end UTC}` |
| Total duration | `{N hours M minutes}` |
| Severity | `{SEV1 / SEV2 / SEV3}` |
| Incident type | `{deployment / infrastructure / dependency / credential / cascading}` |
| Root cause (one sentence) | `{e.g., A bad deploy introduced a connection pool leak that exhausted DB connections under normal load within 8 minutes of rollout.}` |
| Customer impact | `{quantified: e.g., ~22% of checkout requests failed for 57 minutes; estimated 4,200 affected sessions in ap-northeast-2}` |
| Revenue impact | `{$ estimate or N/A — include basis for estimate}` |
| Postmortem author(s) | `{names}` |
| Reviewed by | `{IC name, Ops Lead name}` |
| Review date | `{date}` |

---

## 2. Customer Impact Quantification

> Use actual metric values from the incident window. Do not estimate where real data exists.
> "Affected users" = distinct sessions or accounts that received errors, not total traffic.

| Metric | Baseline (pre-incident) | Peak (during incident) | After mitigation | After resolution |
|--------|------------------------|----------------------|-----------------|-----------------|
| Error rate (5xx) | `{%}` | `{%}` | `{%}` | `{%}` |
| Latency p50 | `{ms}` | `{ms}` | `{ms}` | `{ms}` |
| Latency p95 | `{ms}` | `{ms}` | `{ms}` | `{ms}` |
| Latency p99 | `{ms}` | `{ms}` | `{ms}` | `{ms}` |
| Successful transactions/min | `{N}` | `{N}` | `{N}` | `{N}` |
| Affected users (estimated) | — | `{N}` | — | — |
| Affected services | — | `{list}` | — | — |
| Affected regions/AZs | — | `{list}` | — | — |

**Impact narrative** (2–4 sentences explaining the customer experience):

> Example: Customers attempting to complete checkout in ap-northeast-2 received HTTP 503 errors. Approximately 22% of checkout requests failed between 05:05–06:02 UTC. Customers who retried immediately were more likely to succeed after the rollback completed at T+18 min. No data was lost; failed transactions were not charged.

---

## 3. Detailed Timeline

> Auto-populated from `timeline-template.md`. Paste completed timeline table here.
> Do not condense: every decision row must appear. Timeline is the evidence base for section 4.

*(paste full timeline from timeline-template.md)*

**Key timestamps summary:**

| Milestone | Time (UTC) | Duration from start |
|-----------|------------|---------------------|
| Symptom onset (estimated) | `{T}` | T-0 (reference) |
| First alarm fired | `{T}` | `+{N} min` |
| Incident declared | `{T}` | `+{N} min` |
| Blast radius confirmed | `{T}` | `+{N} min` |
| First mitigation executed | `{T}` | `+{N} min` |
| First measurable improvement | `{T}` | `+{N} min` — MTTM |
| Sustained healthy window | `{T}` | `+{N} min` — MTTR |
| Incident resolved | `{T}` | `+{N} min` |

---

## 4. Root Cause and Contributing Factors

> This section requires human analysis. Agent provides data; engineers provide interpretation.
> Use "5 Whys" to reach a systemic root cause, not just the proximate trigger.

### Root Cause

**Proximate cause** (what broke):
> Example: `checkout-svc v2.4.1` introduced a JDBC connection pool configuration with `maxPoolSize=2` (was 20), causing connection exhaustion within 8 minutes under production load.

**Systemic root cause** (why the system allowed it):

> Example 5 Whys:
> 1. Why did checkout fail? — DB connections exhausted.
> 2. Why were connections exhausted? — New deploy set maxPoolSize=2.
> 3. Why did that config ship? — Default value changed in a library upgrade; not caught in review.
> 4. Why was it not caught in review? — No automated check for connection pool config in PR pipeline.
> 5. Why is there no automated check? — Connection pool limits were assumed to be set only by infra team; no ownership defined in service config spec.
>
> Root cause: Connection pool ownership was unspecified between app and infra teams, so a library default change propagated undetected to production.

### Contributing Factors

> List conditions that made the incident worse or harder to respond to. These each map to action items.

| Factor | Impact on incident | Category |
|--------|-------------------|----------|
| `{e.g., No p95 latency alarm — only p99}` | `{Delayed detection by ~4 min; p95 crossed SLO threshold first}` | Detection |
| `{e.g., SQS consumer had no retry cap}` | `{Amplified impact: retry storm extended backlog drain by ~20 min}` | Response ergonomics |
| `{e.g., Deploy pipeline lacked canary stage}` | `{Full traffic exposed immediately; no graduated rollout to catch regression}` | Prevention |
| `{e.g., Runbook for SQS retry tuning was missing}` | `{Ops Lead had to improvise; added 5 min delay}` | Response ergonomics |

### What Worked

> Honest accounting of effective practices. Reinforce these in future incidents.

- `{e.g., Deploy freeze was activated at T+9 min before IC even asked — Ops Lead knew the protocol.}`
- `{e.g., Agent correlated deploy timestamp with symptom onset in <2 min, guiding the rollback decision.}`
- `{e.g., SQS backlog was caught during Verify phase rather than after close — prevented a silent second impact.}`
- `{e.g., All role assignments were in place within 6 minutes of alarm; no confusion about ownership.}`

### What Did Not Work

> Factual, not blame-assigning. Each item here should generate at least one action item in section 5.

- `{e.g., No alarm existed for connection pool saturation — we only saw the downstream symptom (5xx), not the cause.}`
- `{e.g., Canary was not enabled for this service; 100% of traffic received the bad config.}`
- `{e.g., SQS retry configuration was not in the runbook; operator had to look up CLI syntax during the incident.}`
- `{e.g., Postmortem for a similar event 6 months ago (INC-2025-1012-003) had an action item to add canary — it was never completed.}`

---

## 5. Action Items

> Every item must meet the quality bar from playbook section 9.2.
> Weak: "Improve monitoring." Strong: see examples below.
> Owner must be a named person or named on-call rotation, not a team name.

### Quality Bar Checklist (per item)

- [ ] Has a named owner (person, not team)
- [ ] Has a specific due date
- [ ] Has a measurable success criterion
- [ ] Has a defined verification method
- [ ] Is categorized as Prevention / Detection / Response Ergonomics

### Action Items Table

| # | Category | Action | Owner | Due Date | Success Criterion | Verification Method |
|---|----------|--------|-------|----------|-------------------|---------------------|
| 1 | Prevention | Add connection pool config validation to PR pipeline: fail build if `maxPoolSize < 10` for services with RDS dependency | `{name}` | `{date}` | CI pipeline rejects a test PR with `maxPoolSize=2` | Run canary PR through pipeline; confirm FAIL result |
| 2 | Prevention | Enable canary deployment (10% → 100%) for all services in the `checkout` domain. Integrate with existing CodeDeploy config | `{name}` | `{date}` | Staging chaos test: bad config reaches only 10% of hosts before auto-rollback triggers | Inject bad config in staging; confirm rollback before 100% |
| 3 | Detection | Add p95 latency composite alarm for checkout-svc + downstream auth-svc. Threshold: >1.5s for 2 consecutive minutes → SEV2 | `{name}` | `{date}` | Alarm fires in monthly game day chaos test and in staging load test | Run staging load test past threshold; confirm alarm fires within 2 min |
| 4 | Detection | Add CloudWatch alarm for DB connection pool utilization (`HikariCP.connections.active / max`). Threshold: >80% for 1 min → Warning | `{name}` | `{date}` | Alarm fires before error rate rises in next pool-related incident (measurable in staging test) | Staging test: saturate pool; confirm alarm fires before 5xx appears |
| 5 | Response Ergonomics | Add SQS retry tuning runbook section to `scenarios/lambda-sqs-poison-pill.yaml` and `references/message-templates.md`. Include CLI commands for MaxReceiveCount and visibility timeout adjustment | `{name}` | `{date}` | Next on-call engineer can execute SQS tuning within 3 min using runbook without external lookup | Tabletop drill: on-call executes SQS tuning against staging queue using only runbook |
| 6 | Response Ergonomics | Close INC-2025-1012-003 action item AI-7 (canary for checkout). Verify completion or re-assign with escalation path | `{name}` | `{date}` | Canary enabled (see item 2 above) OR formal exception documented with risk acceptance | Canary pipeline check or exception ticket linked in INC-2025-1012-003 |

> Add rows as needed. Aim for 4–8 high-quality items over 10+ vague ones.
> Items 1–2 address prevention; items 3–4 address detection; items 5–6 address response ergonomics and process debt.

---

## 6. Follow-up Review Schedule

> IC is responsible for scheduling these reviews. If IC rotates, assign to a standing on-call lead.
> Reviews are not optional for SEV1/SEV2. Skip only with written exception from engineering director.

| Review | Date | Owner | Scope |
|--------|------|-------|-------|
| 48-hour review | `{date}` | `{IC name}` | Verify immediate hardening complete: items 3 and 5 above. Confirm deploy freeze lifted safely. Check for latent symptoms (elevated error rate, queue backlog residue). |
| 2-week review | `{date}` | `{Ops Lead}` | Verify structural fixes in progress: items 1, 2, 4. Review open PRs and staging test results. Re-date any slipping items. |
| 6-week review | `{date}` | `{Engineering Lead}` | Verify recurrence risk reduced: run game day scenario that mirrors this incident. Confirm all items closed or formally deferred with risk acceptance. Check if recurrence rate for this incident class has decreased. |

### Closure Criteria

This postmortem is closed when:

- [ ] All action items are marked Closed or formally deferred with owner sign-off
- [ ] 6-week review completed with no recurrence detected
- [ ] Relevant runbooks updated (link: `{runbook path}`)
- [ ] Learnings shared with broader team (link: `{meeting notes or wiki page}`)
- [ ] Incident record archived with all evidence links intact

---

## Appendix: Blameless Postmortem Guidance

> For facilitators. Remove this section before distributing the final report.

**Framing questions that keep discussion systemic:**
- "What did our system, process, or tooling fail to make visible?"
- "What would a reasonable engineer have needed to know to prevent this?"
- "If a new engineer had been on-call, would the outcome have been different? Why?"
- "Which of our action items from past incidents are still open? Why?"

**Signs the discussion is drifting toward blame:**
- Naming a person as the cause ("X pushed the bad config")
- Phrases like "should have known" or "obvious mistake"
- Action items that assign remedial training to individuals

**Redirect:** Every individual action happens inside a system. The system either caught it or it did not. Fix the system.

**5 Whys example for this template:**

| Why | Answer |
|-----|--------|
| Why did customers see errors? | checkout-svc returned 503s |
| Why did checkout-svc return 503s? | DB connections exhausted |
| Why were connections exhausted? | maxPoolSize misconfigured in new deploy |
| Why did the misconfiguration ship? | Library upgrade changed default; no automated guard |
| Why is there no automated guard? | Ownership of connection pool config between app/infra was undefined |

Root cause: configuration ownership gap, not human error.
