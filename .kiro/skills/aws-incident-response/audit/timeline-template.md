# Incident Timeline: {incident-id}

> Auto-populated by oh-my-aws agent during the Audit phase. Human scribe should verify and annotate.
> Preserve this document as permanent artifact after incident closure.

---

## Summary

| Field | Value |
|-------|-------|
| Incident ID | `{incident-id}` (e.g., INC-2026-0403-001) |
| Start (UTC) | `{timestamp}` (e.g., 2026-04-03T05:05:00Z) |
| Detected by | `{alert-name}` (e.g., CheckoutAPI-5xx-SEV2 CloudWatch alarm) |
| Declared by | `{name}` |
| Severity | `{SEV1 / SEV2 / SEV3 / SEV4}` |
| Type | `{deployment / infrastructure / dependency / credential / cascading / unknown}` |
| Status | `{Investigating / Identified / Mitigating / Monitoring / Resolved}` |
| Resolved (UTC) | `{timestamp}` |
| Total duration | `{N hours M minutes}` |
| Customer impact | `{one-line quantified description}` |
| Incident Commander | `{name}` |
| Ops Lead | `{name}` |
| Comms Lead | `{name}` |
| Scribe | `{name / agent}` |

---

## Timeline

> Phase labels follow the oh-my-aws harness: Observe → Reason → Act → Verify → Audit.
> Actor: "Agent" = oh-my-aws automated action; "Human" = human operator decision or execution.
> Evidence column must link to a real artifact: CloudWatch URL, CLI output snippet, log query, or decision chat message.

| Time (UTC) | Phase | Actor | Action | Evidence |
|------------|-------|-------|--------|----------|
| `T+0:00` | Observe | Agent | Alarm triggered: CheckoutAPI p99 latency >3 s for 3 consecutive minutes | CW Alarm `CheckoutAPI-Latency-SEV2`, ARN: `{arn}` |
| `T+0:02` | Observe | Agent | Collected baseline metrics: error rate 22%, p95=4.1s, p50=1.8s, healthy host count=6/8 | CloudWatch Metrics snapshot `{link}` |
| `T+0:03` | Observe | Agent | Checked AWS Health Dashboard: no active events in ap-northeast-2 | Health API response `{link}` |
| `T+0:05` | Observe | Agent | Identified blast radius: ap-northeast-2 only; `/payments/authorize` endpoint; write path | `aws cloudwatch get-metric-data` output `{link}` |
| `T+0:06` | Reason | Agent | Correlated symptom onset with deploy `checkout-svc v2.4.1` at T-8 min (CodePipeline run ID `{id}`) | CodePipeline console `{link}` |
| `T+0:08` | Reason | Agent | Proposed options: (1) rollback to v2.4.0 — reversible, low risk; (2) continue investigating — higher customer cost | Reasoning log `{link}` |
| `T+0:09` | Reason | Human | IC approved rollback option (1). Deploy freeze activated for all services | Slack message `{link}` |
| `T+0:10` | Act | Human | Initiated rollback: CodePipeline re-deploy of `checkout-svc v2.4.0` | `aws codepipeline start-pipeline-execution` — run ID `{id}` |
| `T+0:18` | Verify | Agent | Rollback deployed. Error rate: 22% → 4%. p95 latency: 4.1s → 1.2s. Healthy hosts: 8/8 | CloudWatch dashboard `{link}` |
| `T+0:22` | Verify | Agent | Queue backlog age still elevated: 340s (normal <30s). Retry amplification suspected | SQS `ApproximateAgeOfOldestMessage` metric `{link}` |
| `T+0:25` | Reason | Agent | Identified retry storm: SQS consumer retrying failed messages from failure window at default rate | CloudWatch Logs Insights query `{link}` |
| `T+0:27` | Act | Human | Reduced SQS MaxReceiveCount 6→2, applied visibility timeout increase to 120s | `aws sqs set-queue-attributes` command `{link}` |
| `T+0:45` | Verify | Agent | Queue backlog drained: age 340s → 28s. Error rate <0.5% (baseline 0.2%) | CloudWatch metric snapshot `{link}` |
| `T+0:50` | Verify | Human | IC: sustained healthy window confirmed. IC released deploy freeze. Severity downgraded to SEV3 | Slack message `{link}` |
| `T+1:05` | Audit | Human | Incident declared Resolved. Postmortem scheduled for 2026-04-05 10:00 KST | Resolved notice posted `{link}` |

> Add rows for every decision, mitigation attempt, and verification check.
> Do not summarize multiple actions into one row — granularity enables accurate MTTD/MTTM calculation.

---

## Decisions

> Record every fork in the road: what was chosen, what was rejected, and why.
> This section is the primary input for postmortem "What Worked / What Did Not Work."

| Time (UTC) | Decision | Options Considered | Rationale | Decided By |
|------------|----------|--------------------|-----------|------------|
| `T+0:09` | Rollback to v2.4.0 immediately | (1) Rollback — reversible, fast; (2) Investigate further — slower, more data | Symptom onset correlates with deploy within change window; rollback is safe and reversible | IC `{name}` |
| `T+0:22` | Throttle SQS retry rate | (1) Drain naturally — slower; (2) Reduce MaxReceiveCount — immediate | Queue backlog growing; natural drain would take >20 min under retry pressure | Ops Lead `{name}` |
| `T+0:50` | Release deploy freeze | (1) Release — metrics stable for 25 min; (2) Hold — risk of recurrence | All error and latency metrics within SLO for sustained 25-minute window | IC `{name}` |

---

## Evidence Snapshots

> Every artifact referenced in the timeline must appear here with a stable link or inline content.
> CloudWatch URLs expire — export graphs as PNG or save queries with results.

### Metrics Captured

- `{timestamp}` — CloudWatch: CheckoutAPI ErrorRate, p50, p95, p99 (30-min window) — `{link or filename}`
- `{timestamp}` — CloudWatch: ALB HealthyHostCount by AZ — `{link or filename}`
- `{timestamp}` — SQS: ApproximateAgeOfOldestMessage, NumberOfMessagesSent, NumberOfMessagesDeleted — `{link or filename}`

### Log Queries

- `{timestamp}` — CloudWatch Logs Insights: error pattern in `/aws/ecs/checkout-svc`, last 30 min
  ```
  fields @timestamp, @message
  | filter @message like /ERROR|5xx|exception/
  | stats count() by bin(1m)
  | sort @timestamp desc
  ```
  Result: `{link or inline output}`

- `{timestamp}` — CloudWatch Logs Insights: SQS consumer retry pattern
  ```
  fields @timestamp, requestId, statusCode
  | filter statusCode = "429" or statusCode = "503"
  | stats count() by bin(1m)
  ```
  Result: `{link or inline output}`

### Change Events

- Deploy `checkout-svc v2.4.1` at `{timestamp}` — CodePipeline run ID `{id}` — `{link}`
- Rollback to `checkout-svc v2.4.0` at `{timestamp}` — CodePipeline run ID `{id}` — `{link}`
- SQS attribute change at `{timestamp}` — CLI output: `{inline or link}`

### AWS Health

- Health Dashboard check at `{timestamp}` — result: `{no active events / event description}` — `{link}`

### Communication Log

- Incident declaration message: `{link to Slack/Teams message}`
- First status update: `{link}`
- Resolved notice: `{link}`
- Executive brief (if SEV1): `{link}`

---

## Metrics for Postmortem Calculation

> Populated automatically where agent has timestamps; human scribe fills gaps.

| Metric | Value | Notes |
|--------|-------|-------|
| MTTD (detect) | `{N min}` | Alarm fired at `{T}`, acknowledged at `{T}` |
| MTTA (acknowledge) | `{N min}` | Time from alarm to IC declared |
| MTTM (mitigate) | `{N min}` | Time from declaration to first measurable improvement |
| MTTR (recover) | `{N min}` | Time from declaration to sustained healthy window |
| Peak error rate | `{%}` | At `{timestamp}` |
| Affected regions | `{list}` | |
| Affected AZs | `{list}` | |
| Affected endpoints | `{list}` | |
| Estimated affected users | `{N}` | Based on `{metric / calculation}` |
| Estimated revenue impact | `{$ or N/A}` | |
