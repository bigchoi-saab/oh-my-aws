# Exam Simulation Protocol

**Version**: 1.0.0  
**Phase**: 2A  
**Owner**: aws-exam skill  
**Referenced by**: aws-exam SKILL.md (Task #8), aws-exam-harness (Task #4)

---

## 1. Purpose

`aws-diagnostician.md` is **zero-diff in Phase 2A** — it must not be modified (plan baseline item #26, US-2 AC#4). All simulation-mode behavior is injected **out-of-band** at spawn time: the `aws-exam` skill orchestrator includes this document's instructions in the prompt it sends to aws-diagnostician when spawning it in exam mode.

This file is the **single authoritative source** for how agents behave in exam simulation mode. It defines:
- How to detect simulation mode
- Behavior rules replacing live AWS calls
- Required observability fields for grading
- The fixture-key-to-CLI-command reverse mapping table
- The HALT-ON-DKR-READ fail-closed directive

**What this file does NOT do**: modify aws-diagnostician.md, aws-executor.md, or any other agent definition. Those files remain untouched.

---

## 2. Simulation Mode Detection

An agent is in **simulation mode** when its incident directory contains `_exam_mode_flag.yaml`.

```yaml
# _exam_mode_flag.yaml (pre-written by aws-exam-harness)
mode: simulation
question_id: exam-lambda-throttle-001
dkr_blind: true
created_at: 2026-04-05T14:30:00Z
agents_operating_mode: simulation
```

**Detection rule**: Before beginning Observe phase, Read `_exam_mode_flag.yaml`. If `mode: simulation` is present, activate all rules in Section 3. If the file is absent, proceed with normal live-mode behavior.

---

## 3. Behavior Rules in Simulation Mode

### Rule A — Read fixtures instead of calling AWS CLI

Do **not** invoke any `aws ...` CLI command. The evidence has already been pre-collected and written to the `evidence/` subdirectory of your incident directory:

```
sim-incidents/{question-id}/
  evidence/
    metrics.yaml       ← replaces aws cloudwatch get-metric-data / get-metric-statistics
    logs.yaml          ← replaces aws logs filter-log-events / start-query
    cli-outputs.yaml   ← replaces aws lambda/ecs/rds describe/get/list commands + alarms
```

Read these fixture files instead of executing Bash tool AWS calls. Treat fixture contents as ground truth for the Observe phase — they represent what a real CloudWatch/CLI query would have returned.

### Rule B — Populate sources_read[] in observe.yaml

Record every fixture file path you read in `observe.yaml.sources_read[]`. This field is **REQUIRED in simulation mode** (sim_mode_required: true per handoff-schemas.yaml R11 extension). The grader will fail loud — not silently score 0 — if this field is absent.

```yaml
# observe.yaml (excerpt)
sources_read:
  - evidence/metrics.yaml
  - evidence/logs.yaml
  - evidence/cli-outputs.yaml
```

List only files you actually read. If a fixture file is present but irrelevant to this question, you may omit it from `sources_read`.

### Rule C — Refuse to read scenarios/*.yaml

You MUST NOT read any file matching `.kiro/skills/aws-incident-response/references/scenarios/*.yaml`. See Section 5 (HALT-ON-DKR-READ) for the fail-closed directive.

### Rule D — Populate intended_commands[] in observe.yaml

Record the `aws ...` CLI commands you **would have run in live mode** to obtain the same observations, along with the fixture key that provided the equivalent data. This field is **REQUIRED in simulation mode** and is the primary scoring target for the `collection_fidelity` rubric dimension.

```yaml
# observe.yaml (excerpt)
intended_commands:
  - command: "aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Throttles --dimensions Name=FunctionName,Value=payment-processor --start-time ... --end-time ... --period 60 --statistics Sum"
    fixture_key: "metrics.lambda_throttles"
  - command: "aws lambda get-function-concurrency --function-name payment-processor"
    fixture_key: "cli_outputs.get_function_concurrency"
  - command: "aws logs filter-log-events --log-group-name /aws/lambda/payment-processor --filter-pattern ThrottlingException"
    fixture_key: "logs.throttling_errors"
```

Use the fixture-key-to-CLI mapping table in Section 4 to determine the correct `command` for each fixture entry you read.

---

## 4. Fixture-Key-to-CLI-Command Reverse Mapping

This table covers all 5 fixture types currently in use in the exam-bank. When populating `observe.yaml.intended_commands[]`, use the command pattern matching the fixture type and source.

### fixture type: `metric`

Metric fixtures live in `evidence/metrics.yaml`. Each entry represents a CloudWatch metric query result.

| Fixture key pattern | Intended CLI command |
|---|---|
| `metrics.*` (any Lambda metric) | `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name <MetricName> --dimensions Name=FunctionName,Value=<fn-name> --period 60 --statistics <Sum\|Average\|Maximum>` |
| `metrics.*` (any ECS metric) | `aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name <MetricName> --dimensions Name=ServiceName,Value=<svc>` |
| `metrics.*` (multi-metric or time-series) | `aws cloudwatch get-metric-data --metric-data-queries file://query.json --start-time ... --end-time ...` |
| `metrics.*` (RDS metric) | `aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name <MetricName> --dimensions Name=DBInstanceIdentifier,Value=<id>` |

**Rule**: If the fixture `source` field contains a CloudWatch namespace (e.g., `AWS/Lambda`, `AWS/ECS`), use `get-metric-statistics`. If the source describes a multi-metric dashboard or cross-resource query, use `get-metric-data`.

### fixture type: `log`

Log fixtures live in `evidence/logs.yaml`. Each entry represents a CloudWatch Logs query result.

| Fixture key pattern | Intended CLI command |
|---|---|
| `logs.*` (filter by pattern) | `aws logs filter-log-events --log-group-name <group> --filter-pattern "<pattern>" --start-time <epoch> --end-time <epoch>` |
| `logs.*` (Logs Insights query) | `aws logs start-query --log-group-name <group> --start-time <epoch> --end-time <epoch> --query-string "fields @timestamp, @message \| filter @message like /<pattern>/ \| sort @timestamp desc \| limit 100"` followed by `aws logs get-query-results --query-id <id>` |

**Rule**: If the fixture `source` references "CloudWatch Logs Insights" or contains an `@` query syntax, use `start-query` + `get-query-results`. Otherwise use `filter-log-events`.

### fixture type: `cli_output`

CLI output fixtures live in `evidence/cli-outputs.yaml`. Each entry's `source` field IS the intended command (the fixture records what that command returned).

| Fixture source example | Intended CLI command |
|---|---|
| `aws lambda get-function-concurrency` | `aws lambda get-function-concurrency --function-name <fn-name>` |
| `aws lambda get-account-settings` | `aws lambda get-account-settings` |
| `aws ecs describe-services` | `aws ecs describe-services --cluster <cluster> --services <service>` |
| `aws rds describe-db-instances` | `aws rds describe-db-instances --db-instance-identifier <id>` |
| `aws iam get-role` | `aws iam get-role --role-name <role>` |

**Rule**: The fixture `source` field directly names the CLI command. Copy it verbatim and add required parameters (region, resource identifier) inferred from the incident context.

### fixture type: `alarm`

Alarm fixtures live in `evidence/cli-outputs.yaml` (under a `alarms:` section or alongside other CLI outputs). Each entry represents a CloudWatch alarm state.

| Fixture key pattern | Intended CLI command |
|---|---|
| `alarms.*` (single alarm) | `aws cloudwatch describe-alarms --alarm-names "<AlarmName>"` |
| `alarms.*` (by state) | `aws cloudwatch describe-alarms --state-value ALARM` |
| `alarms.*` (by prefix) | `aws cloudwatch describe-alarms --alarm-name-prefix "<prefix>"` |

**Rule**: If the fixture names a specific alarm, use `--alarm-names`. If it describes alarms in a state across a service, use `--state-value`.

### fixture type: `cloudtrail_event`

CloudTrail event fixtures live in `evidence/cli-outputs.yaml`. Each entry represents a CloudTrail event lookup result.

| Fixture key pattern | Intended CLI command |
|---|---|
| `cloudtrail.*` (by resource) | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=<resource> --start-time <ISO8601> --end-time <ISO8601>` |
| `cloudtrail.*` (by event name) | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=<EventName>` |
| `cloudtrail.*` (by username) | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=<user>` |

**Rule**: Match the lookup attribute to what the fixture describes (resource change, API call, or actor).

---

## 5. HALT-ON-DKR-READ Directive (US-11, fail-closed)

The following preamble is injected verbatim into every agent spawn prompt in exam mode. It is reproduced here so this document is self-contained and Task #8 can reference it without reading the harness code.

> **HALT-ON-DKR-READ**: If you are about to Read any path matching `.kiro/skills/aws-incident-response/references/scenarios/*.yaml`, STOP immediately. Write `{violated: true, attempted_path: <path>}` to `_dkr_access_log.yaml` and return. Do not read the file. Do not continue the task.

**Why fail-closed**: The DKR-blind invariant is the measurement integrity guarantee of the entire exam pipeline. Reading a scenario file during a run contaminates the measurement signal irreversibly. Prevention (halt before reading) is stronger than detection (post-run audit). The post-run `audit_dkr_access.py` scan remains as a defense-in-depth backup.

**How the log works**: The harness pre-writes `_dkr_access_log.yaml` with `{violated: false, attempted_path: null}` before spawning any agent. If an agent triggers the HALT, it overwrites the `violated` field to `true`. The harness checks this file after agent completion; any `violated: true` aborts the entire run (both Track A and Track B) and moves artifacts to `.ops/exam-results/_invalidated/`.

---

## 6. Worked Examples

### Key shape note (READ FIRST)

The harness (`sim_incident_writer.py`) writes fixture files with a specific structure that examples below reflect:

- **`metrics.yaml`**: top-level `metrics:` wrapper containing a **dict** keyed by a sanitized version of each entry's `source` field. Sanitization rule: `source.replace(" ", "_").replace("/", "_").replace(":", "").lower()`. So `source: "AWS/Lambda Throttles"` becomes the key `aws_lambda_throttles`.
- **`logs.yaml`**: top-level `logs:` wrapper containing a **list** of log entries (each with `source`, `query_summary`, `sample_entries`, `_original_type`). No stable string key — agents reference by list index or by matching the `source` field.
- **`cli-outputs.yaml`**: top-level `cli_outputs:` wrapper containing a **list** of entries (each with `source`, `command`, `mocked_output`, `_original_type`). Same asymmetry as logs.
- All three files also carry a sibling `_provenance:` block ({generated_by, source_question, generated_at}).

**`fixture_key` convention** for `observe.yaml.intended_commands[].fixture_key`:
- For metrics (map): `metrics.<sanitized_key>` (dotted path to the dict entry)
- For logs (list): `logs[<index>]` or `logs[?source=='<source_string>']` — either style is acceptable; grader matches on presence
- For cli_outputs (list): `cli_outputs[<index>]` or `cli_outputs[?source=='<source_string>']`

> **Known asymmetry**: metrics being a dict while logs/cli_outputs are lists is a US-1 design choice carried into Phase 2A. The grader tolerates both dotted paths and JMESPath-style filters. Phase 2B/2C may normalize all three to the same shape — see team-exec handoff risk list.

### Example 1 — lambda-throttle-001 (metric + cli_output + log)

**Question**: `exam-lambda-throttle-001` — payment-processor Lambda returning 429 Throttling after deployment.

**Fixture evidence** (actual shape written by harness, NOT a simplified illustration):

```yaml
# evidence/metrics.yaml
metrics:
  aws_lambda_throttles:           # sanitized from source: "AWS/Lambda Throttles"
    source: "AWS/Lambda Throttles"
    value: "payment-processor 함수만 Throttles.Sum > 0"
    _original_type: metric
_provenance:
  generated_by: aws-exam-harness/v1
  source_question: exam-lambda-throttle-001
  generated_at: "2026-04-05T..."

# evidence/cli-outputs.yaml
cli_outputs:
  - source: "aws lambda get-function-concurrency"
    command: "# cli_output: aws lambda get-function-concurrency"
    mocked_output: "ReservedConcurrentExecutions: 0"
    _original_type: cli_output
  - source: "aws lambda get-account-settings"
    command: "# cli_output: aws lambda get-account-settings"
    mocked_output: "AccountLimit.ConcurrentExecutions: 1000, UnreservedConcurrentExecutions: 950"
    _original_type: cli_output
_provenance: { ... }

# evidence/logs.yaml
logs:
  - source: "API Gateway access log"
    query_summary: "모든 요청이 429 TooManyRequestsException"
    sample_entries: []
    _original_type: log
_provenance: { ... }
```

**Expected observe.yaml output** (sim mode):

```yaml
sources_read:
  - evidence/metrics.yaml
  - evidence/cli-outputs.yaml
  - evidence/logs.yaml

intended_commands:
  - command: "aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Throttles --dimensions Name=FunctionName,Value=payment-processor --period 60 --statistics Sum"
    fixture_key: "metrics.aws_lambda_throttles"
  - command: "aws lambda get-function-concurrency --function-name payment-processor"
    fixture_key: "cli_outputs[?source=='aws lambda get-function-concurrency']"
  - command: "aws lambda get-account-settings"
    fixture_key: "cli_outputs[?source=='aws lambda get-account-settings']"
  - command: "aws logs filter-log-events --log-group-name /aws/apigateway/payment-processor --filter-pattern TooManyRequestsException"
    fixture_key: "logs[?source=='API Gateway access log']"
```

> **Integration test validated 2026-04-05**: A general-purpose subagent running under this protocol produced observe.yaml + diagnosis.yaml for lambda-throttle-001 with root_cause_code `THROTTLE-RESV-ZERO`, confidence high, mitigation-first action ordering, and `_dkr_access_log.yaml violated: false`. The subagent correctly adapted fixture_key style to the list-shaped logs/cli_outputs.

### Example 2 — ecs-crash-loop (metric + log + alarm)

**Question**: ECS task repeatedly restarting (OOMKilled).

**Expected intended_commands[] excerpt**:

```yaml
intended_commands:
  - command: "aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name MemoryUtilization --dimensions Name=ServiceName,Value=my-service Name=ClusterName,Value=prod-cluster --period 300 --statistics Maximum"
    fixture_key: "metrics.ecs_memory_utilization"
  - command: "aws logs start-query --log-group-name /ecs/my-service --start-time 1743000000 --end-time 1743003600 --query-string \"fields @timestamp, @message | filter @message like /OOMKilled/ | sort @timestamp desc\""
    fixture_key: "logs.oom_kill_events"
  - command: "aws cloudwatch describe-alarms --alarm-names \"ECS-MemoryUtilization-High\""
    fixture_key: "alarms.ecs_memory_alarm"
```

### Example 3 — iam-compromise (cloudtrail_event + cli_output)

**Question**: Unauthorized IAM role assumption detected.

**Expected intended_commands[] excerpt**:

```yaml
intended_commands:
  - command: "aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole --start-time 2026-04-04T00:00:00Z --end-time 2026-04-05T00:00:00Z"
    fixture_key: "cloudtrail.assume_role_events"
  - command: "aws iam get-role --role-name suspicious-role"
    fixture_key: "cli_outputs.get_role"
```

---

## 7. Zero-Diff Constraint

**`aws-diagnostician.md` MUST NOT be edited in Phase 2A.**

This is plan baseline item #26 and US-2 AC#4. The zero-diff constraint exists to ensure that simulation-mode behavior does not leak into the agent's live-mode behavior. All sim-mode instructions live here (in this protocol file) and are injected at spawn time by the aws-exam skill orchestrator.

When the aws-exam skill spawns aws-diagnostician in exam mode, it prepends the following to the agent's task prompt:

```
You are operating in EXAM SIMULATION MODE.

Read and follow all rules in:
  .kiro/skills/aws-exam/references/exam-simulation-protocol.md

Your incident directory is: {sim_incident_dir}
The _exam_mode_flag.yaml confirms: mode=simulation, dkr_blind=true

[HALT-ON-DKR-READ preamble — see Section 5 of exam-simulation-protocol.md]
```

The diagnostician then runs its normal Observe → Diagnose loop, but reads fixture files from `evidence/` instead of calling AWS, and populates the required `sources_read[]` and `intended_commands[]` fields per this protocol.

---

## 8. Grader Integration Notes

The `collection_fidelity` rubric dimension (US-3) scores based on:
1. `observe.yaml.sources_read[]` — did the agent read the relevant fixture files?
2. `observe.yaml.intended_commands[]` — would the agent have asked for the right AWS data?

The grader cross-references `intended_commands[].fixture_key` against the DKR's expected evidence set for the question. If `sources_read` or `intended_commands` are **missing entirely** from a sim-mode `observe.yaml`, the grader MUST fail loud with an explicit error (not silently score `collection_fidelity: 0`). This is enforced by the `sim_mode_required: true` flag in `handoff-schemas.yaml`.

**Audit backup**: After each run, `audit_bash_calls.py` parses `agent-traces/*.jsonl` and asserts zero `aws ...` Bash calls. Any detected live AWS call marks the run `chain_status: illegal_live_aws_call`.
