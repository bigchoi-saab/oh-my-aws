# oh-my-aws Architecture Document

> Version: 1.0.0-draft
> Date: 2026-04-03
> Status: Architecture Draft — Research phase complete, implementation not started
> Authors: oh-my-aws project

---

## Table of Contents

1. [Project Overview & Goals](#1-project-overview--goals)
2. [System Architecture](#2-system-architecture)
3. [Harness Pipeline](#3-harness-pipeline)
4. [Knowledge Base Architecture](#4-knowledge-base-architecture)
5. [Guardrail & Approval Policy](#5-guardrail--approval-policy)
6. [Implementation Roadmap](#6-implementation-roadmap)
7. [Directory Structure & File Map](#7-directory-structure--file-map)
8. [Extension Points & Future Direction](#8-extension-points--future-direction)

---

## 1. Project Overview & Goals

### 1.1 What is oh-my-aws?

oh-my-aws is a **Claude Code extension project** that provides AI agents with AWS operational knowledge, execution tools, and safety policies for incident response and infrastructure management.

It is **NOT** a standalone application with its own tech stack. It is a collection of:

- **Skills** — `.claude/skills/` files that instruct the agent how to behave during AWS incidents
- **Knowledge Base** — YAML decision records (DKR) that encode "problem → diagnosis → action → verification" patterns
- **MCP Tools** (future) — An MCP server that wraps AWS CLI/SDK calls with safety checks
- **Commands** (future) — Slash commands for triggering incident workflows

### 1.2 Core Value Proposition

Transform AWS operational work that is currently **manual, experience-driven, and hard to reproduce** into agent-executable workflows that are **repeatable, verifiable, and safe to operate**.

### 1.3 Design Principles

| Principle | Description |
|-----------|-------------|
| **Mitigate before diagnose** | The #1 operational anti-pattern is "root-causing before stabilizing." The agent must propose reversible mitigations within 10 minutes. |
| **Human-in-the-loop for risk** | Low-risk actions (logs, metrics, diagnostics) auto-execute. High-risk actions (rollbacks, config changes) require human approval. |
| **Evidence before action** | Every remediation must cite the metric/log/query that justifies it. No blind actions. |
| **Reversible by default** | Every action has a rollback command. Non-reversible actions are blocked unless explicitly approved. |
| **Knowledge from official sources** | All decision knowledge comes from AWS official free documentation (Well-Architected, Troubleshooting Guides, re:Post, Prescriptive Guidance). No exam questions (copyright/NDA risk). |

### 1.4 Target Users

| Persona | How They Use oh-my-aws |
|---------|----------------------|
| **On-Call Engineer** | `/aws-incident --auto` → agent collects context, diagnoses, proposes mitigations |
| **SRE** | Agent as first-pass incident investigator, reducing MTTR by 60-80% |
| **Cloud Infrastructure Engineer** | CDK diff validation, drift detection, config compliance checks |
| **Platform Engineer** | Runbook-as-code, automated operational workflows |

### 1.5 Expected Use Cases

- Automated first-pass AWS incident investigation
- Converting operational runbooks into agent-executable workflows
- CDK-based infrastructure change proposal and validation
- Drift, cost anomaly, security, and compliance checks
- Semi-automated or automated execution of low-risk operational tasks

---

## 2. System Architecture

### 2.1 Extension Layer Model

oh-my-aws extends Claude Code (or any compatible AI agent runtime) through 4 progressive layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Layer 4: Commands (UX)                          │
│   /aws-incident <scenario>    /aws-observe    /aws-verify           │
├─────────────────────────────────────────────────────────────────────┤
│                     Layer 3: Agents (Roles)                         │
│   Incident Commander    Diagnostician    Executor                   │
├─────────────────────────────────────────────────────────────────────┤
│                     Layer 2: Skill (Instructions)                   │
│   SKILL.md → Decision pipeline, anti-patterns, scenario routing     │
├─────────────────────────────────────────────────────────────────────┤
│                     Layer 1: Knowledge Base + Tools                  │
│   DKR YAML files    Scenario Registry    MCP Server (aws-ops-tools) │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Descriptions

#### Layer 1: Knowledge Base + Tools (Foundation)

The agent's "brain" and "hands."

| Component | Format | Location | Purpose |
|-----------|--------|----------|---------|
| **DKR Files** | YAML | `.claude/skills/aws-incident-response/references/scenarios/` | Machine-readable decision records per incident scenario |
| **Scenario Registry** | YAML | `.claude/skills/aws-incident-response/references/scenario-registry.yaml` | Master index of all scenarios, categories, and pipeline mappings |
| **Log Source Map** | Markdown | `.claude/skills/aws-incident-response/references/log-source-map.md` | Service → log location → query method lookup |
| **Guardrails** | YAML | `.claude/skills/aws-incident-response/references/guardrails.yaml` | Global pre/post-action safety policies |
| **MCP Server** (Phase 3) | Python | `mcp-servers/aws-ops-tools/` | AWS API wrapper with safety checks, approval gates, audit logging |

#### Layer 2: Skill (Instructions)

The agent's "standard operating procedure."

- **File**: `.claude/skills/aws-incident-response/SKILL.md`
- **Content**: Core architecture (Observe→Reason→Act→Verify→Audit), scenario registry reference, observability signal map, human operator model, anti-patterns, implementation options
- **The agent reads this file** to understand how to respond to any AWS incident

#### Layer 3: Agents (Roles) — Phase 2

Multi-agent decomposition for complex incidents:

| Agent | Role | File |
|-------|------|------|
| **aws-incident-commander** | Orchestration, IC role, escalation decisions | `.claude/agents/aws-incident-commander.md` |
| **aws-incident-diagnostician** | Log/metric queries, decision tree traversal, root cause analysis | `.claude/agents/aws-incident-diagnostician.md` |
| **aws-incident-executor** | Remediation execution with approval gates, rollback management | `.claude/agents/aws-incident-executor.md` |

#### Layer 4: Commands (UX) — Phase 4

Slash commands for end-user interaction:

| Command | Description |
|---------|-------------|
| `/aws-incident <scenario-id>` | Execute incident response for a specific scenario |
| `/aws-incident --auto` | Auto-detect scenario and execute full pipeline |
| `/aws-incident --diagnose` | Run diagnosis only (Observe + Reason, no Act) |
| `/aws-incident --verify` | Run verification only for a previous action |

### 2.3 How the Layers Work Together

```
User: "/aws-incident lambda-throttle"
                │
                ▼
     ┌──── Layer 4: Command ────┐
     │ Parse args, route to     │
     │ appropriate skill         │
     └──────────┬───────────────┘
                │
                ▼
     ┌──── Layer 2: Skill ──────┐
     │ Read SKILL.md             │
     │ Load scenario-registry    │
     │ Find "lambda-throttle"    │
     │ Load scenarios/lambda-    │
     │ throttle.yaml (DKR)       │
     └──────────┬───────────────┘
                │
                ▼
     ┌──── Layer 3: Agents ─────┐   (Phase 2: single agent → multi-agent)
     │ Commander orchestrates:   │
     │  1. Diagnostician runs    │
     │     Observe + Reason      │
     │  2. Commander reviews     │
     │     diagnosis, requests   │
     │     human approval        │
     │  3. Executor runs Act     │
     │     + Verify + Audit      │
     └──────────┬───────────────┘
                │
                ▼
     ┌──── Layer 1: Tools ──────┐
     │ AWS CLI / SDK calls      │
     │ CW Logs Insights queries │
     │ Metric retrievals        │
     │ (via MCP server or Bash) │
     └──────────────────────────┘
```

---

## 3. Harness Pipeline

The core execution model follows a 5-stage pipeline: **Observe → Reason → Act → Verify → Audit**.

### 3.1 Pipeline Overview

```
[Observe]       [Reason]        [Act]           [Verify]        [Audit]
알람/메트릭/    증상 분류 →     가역적 완화     완화 효과 확인   타임라인 기록
로그/토폴로지   원인 진단 →     실행            메트릭 정상화    결정사항 추적
최근 변경 수집  조치 계획       (승인 필요시    안정성 윈도우    증거 보존
                                인간 확인)      유지 확인        후속 조치 생성
```

### 3.2 Stage Details

#### Stage 1: Observe

**Goal**: Collect operational context — what is happening, where, and since when.

| Action | Method | Output |
|--------|--------|--------|
| Detect alarm/metric anomaly | CloudWatch Metrics, Alarms | Trigger signal with scenario hint |
| Collect recent logs | CloudWatch Logs Insights | Error patterns, stack traces |
| Check recent changes | CloudTrail, deployment history | Change timeline |
| Assess resource state | AWS API (describe, get, list) | Current configuration snapshot |
| Check AWS Health | AWS Health API | Active events, scheduled changes |

**Key rule**: Collect everything relevant before making changes. Log snapshots preserve evidence.

#### Stage 2: Reason

**Goal**: Classify symptoms, traverse decision tree, identify root cause, build action plan.

| Action | Method | Output |
|--------|--------|--------|
| Classify symptom pattern | DKR triggers + symptoms matching | Scenario identification |
| Traverse diagnosis tree | DKR `diagnosis.decision_tree` steps | Root cause code |
| Build remediation plan | DKR `remediation` matching root cause | Ordered action list with risk levels |
| Check guardrails | DKR `guardrails.pre_conditions` | Block/warn/proceed decision |
| Prepare approval request | Risk-based escalation | Human approval request (if needed) |

**Key rule**: Propose reversible mitigations within 10 minutes. Root cause analysis can continue after stabilization.

#### Stage 3: Act

**Goal**: Execute remediation actions with safety checks.

| Risk Level | Behavior | Examples |
|------------|----------|----------|
| LOW | Auto-execute + notify | Log queries, metric collection, dashboard links |
| MEDIUM | Propose + execute after approval | Lambda timeout/memory change, DynamoDB capacity, CloudFront cache invalidation |
| HIGH | Analysis + explicit approval required | Deployment rollback, traffic shift (Zonal Shift), IAM credential disable, Reserved Concurrency change |

**Key rule**: Only one change at a time. Execute, verify, then proceed to the next.

#### Stage 4: Verify

**Goal**: Confirm the action had the intended effect without side effects.

| Check | Method | Success Criteria |
|-------|--------|-----------------|
| Primary metric | CloudWatch Metrics (DKR `verification.checks`) | Metric meets threshold |
| Side effects | Error rate, latency, other metrics | No degradation |
| Stability window | 5-minute observation | Metrics remain stable |
| Auto-rollback trigger | Post-condition monitoring | If degraded → restore previous state |

**Key rule**: Wait 5 minutes. If metrics worsen, auto-rollback.

#### Stage 5: Audit

**Goal**: Record what happened, why, and what evidence supported each decision.

| Record | Content |
|--------|---------|
| Timeline | Timestamped log of every action taken |
| Decisions | What was decided and why (evidence cited) |
| Evidence | Metric snapshots, log excerpts, API responses |
| Follow-ups | Post-mortem scheduling, runbook updates, capacity review |

---

## 4. Knowledge Base Architecture

### 4.1 Decision Knowledge Record (DKR) Schema

Each operational scenario is encoded as a **Decision Knowledge Record (DKR)** — a machine-readable YAML file that the agent can parse and execute.

**Full schema** (defined in `docs/research/05-decision-knowledge-base.md` §3):

```yaml
schema: decision-knowledge-record/v1

metadata:        # id, name, category, service, severity, tags, source_refs
triggers:        # alarm, metric_threshold, log_pattern, event_bridge
symptoms:        # detection methods, CW queries, API calls
diagnosis:       # decision_tree (step → question → check → branches)
root_causes:     # code, name, probability, related_symptoms
remediation:     # actions (aws_cli, cdk, ssm_automation), rollback, risk, approval
guardrails:      # pre_conditions (block/warn), post_conditions (auto_rollback)
verification:    # checks, stability_window, success_criteria
escalation:      # auto_remediate, approval_required, timeout, notify
```

### 4.2 Scenario Registry

The **Scenario Registry** (`scenario-registry.yaml`) is the master index that maps scenarios to categories, pipeline stages, and action types.

**Current state**: 20 scenarios registered across 7 categories:

| Category | Scenarios | DKR Status |
|----------|-----------|------------|
| Compute | lambda-timeout, lambda-throttle, ecs-crash-loop, ec2-unreachable | Lambda: normalized (3 DKR files). Others: draft |
| Database | rds-perf-degradation, rds-failover, dynamodb-throttle | Draft |
| Network | vpc-unreachable, cloudfront-issue | Draft |
| Storage | s3-access-denied | Draft |
| Deployment | post-deploy-5xx, cert-expiry | Draft |
| Platform | az-failure, region-outage, control-plane-failure, cascade-failure | Draft |
| Security | iam-compromise, s3-public-exposure, network-unauthorized | Draft |

### 4.3 DKR Status Definitions

| Status | Meaning |
|--------|---------|
| `normalized` | Full DKR YAML file exists with all schema fields populated, including CLI commands, rollback commands, guardrails, and verification checks |
| `draft` | Scenario registered in `scenario-registry.yaml` with root causes defined, but full DKR YAML not yet created |
| `planned` | Scenario identified but not yet registered |

### 4.4 Knowledge Sources (Copyright-Safe)

All DKR content is derived from AWS official free documentation:

| Source | URL Pattern | What It Provides |
|--------|------------|-----------------|
| AWS Well-Architected Framework | `docs.aws.amazon.com/wellarchitected/` | Decision questions, best practices |
| AWS Troubleshooting Guides | `docs.aws.amazon.com/*/latest/dg/troubleshooting-*` | Step-by-step diagnosis |
| AWS Prescriptive Guidance | `docs.aws.amazon.com/prescriptive-guidance/` | Patterns, anti-patterns |
| AWS re:Post Knowledge Center | `repost.aws/knowledge-center/` | Verified Q&A |
| AWS SSM Automation Runbooks | `docs.aws.amazon.com/systems-manager/` | Executable automation scripts |
| AWS Operational Readiness Reviews | `docs.aws.amazon.com/` | Operational checklists |

**Explicitly excluded**: AWS certification exam questions (copyright/NDA risk).

---

## 5. Guardrail & Approval Policy

### 5.1 Risk-Based Automation Levels

```
┌──────────────────────────────────────────────────────────────┐
│                    RISK CLASSIFICATION                        │
├──────────────┬──────────────┬───────────────────────────────┤
│   LOW RISK   │ MEDIUM RISK  │        HIGH RISK              │
│  Auto-execute│  Propose +   │  Analysis + Explicit          │
│  + Notify    │  Approval    │  Approval Required            │
├──────────────┼──────────────┼───────────────────────────────┤
│· Log queries │· Lambda      │· Deployment rollback          │
│· Metric      │  timeout/    │· Traffic shift (Zonal Shift,  │
│  collection  │  memory      │  Route 53 failover)           │
│· Dashboard   │  change      │· IAM credential disable       │
│  link gen    │· DynamoDB    │· Reserved Concurrency change  │
│· Timeline    │  capacity    │· VPC route/SG change          │
│  recording   │  adjust      │· RDS failover trigger         │
│· Evidence    │· CloudFront  │· Any non-reversible action    │
│  collection  │  cache       │                               │
│· AWS Health  │  invalidate  │                               │
│  check       │· ECS task    │                               │
│· CloudTrail  │  count       │                               │
│  query       │  adjust      │                               │
└──────────────┴──────────────┴───────────────────────────────┘
```

### 5.2 Pre-Action Guardrails

Before any remediation action, the agent MUST verify:

| # | Check | Behavior |
|---|-------|----------|
| 1 | **Evidence exists** — metric/log/query justifies the action | Block if no evidence |
| 2 | **Cost impact assessed** — if cost changes, display to user | Block if cost impact not shown |
| 3 | **Rollback prepared** — rollback command exists and tested | Block if no rollback |
| 4 | **Blast radius scoped** — other resources won't be affected | Warn if cross-resource impact |
| 5 | **No concurrent changes** — only one change at a time | Block if another action in progress |

### 5.3 Post-Action Verification

After any remediation action, the agent MUST:

| # | Check | Behavior |
|---|-------|----------|
| 1 | **Primary metric** — the metric that triggered the action | Verify it improves |
| 2 | **Side effects** — error rate, latency, other metrics | Auto-rollback if degraded |
| 3 | **Stability window** — 5-minute observation | Wait before declaring success |
| 4 | **Audit record** — log the action, evidence, and outcome | Always record |

### 5.4 Absolute Blocks (Never Auto-Execute)

| Action | Reason |
|--------|--------|
| Deleting resources | Irreversible data loss |
| Changing security groups in production | Blast radius too wide |
| Modifying IAM policies | Security implications |
| RDS instance class changes | Extended downtime possible |
| Route table modifications | Multi-AZ impact |

---

## 6. Implementation Roadmap

### Phase 1: Skill + DKR Scenarios (Immediate — No Code Required)

**Goal**: Make the agent immediately useful for AWS incident investigation using only skill files and knowledge base.

| Deliverable | Status | Location |
|-------------|--------|----------|
| SKILL.md | ✅ Complete | `.claude/skills/aws-incident-response/SKILL.md` |
| Scenario Registry | ✅ Complete | `.claude/skills/aws-incident-response/references/scenario-registry.yaml` |
| Implementation Guide | ✅ Complete | `.claude/skills/aws-incident-response/references/implementation-guide.md` |
| Lambda timeout DKR | ✅ Complete (in research) | `docs/research/05-decision-knowledge-base.md` §4.1 — needs YAML file extraction |
| Lambda throttle DKR | ✅ Complete (in research) | `docs/research/05-decision-knowledge-base.md` §4.2 — needs YAML file extraction |
| Lambda poison pill DKR | ✅ Complete (in research) | `docs/research/05-decision-knowledge-base.md` §4.3 — needs YAML file extraction |
| RDS perf degradation DKR | 🔲 Pending | Needs creation from `docs/research/06` + `07` |
| RDS failover DKR | 🔲 Pending | Needs creation |
| DynamoDB throttle DKR | 🔲 Pending | Needs creation |
| ECS crash loop DKR | 🔲 Pending | Needs creation |
| Post-deploy 5xx DKR | 🔲 Pending | Needs creation |
| VPC unreachable DKR | 🔲 Pending | Needs creation |
| CloudFront issue DKR | 🔲 Pending | Needs creation |
| S3 access denied DKR | 🔲 Pending | Needs creation |
| AZ failure DKR | 🔲 Pending | Needs creation |
| Cascade failure DKR | 🔲 Pending | Needs creation |
| IAM compromise DKR | 🔲 Pending | Needs creation |
| Log source map | 🔲 Pending | Extract from `docs/research/06` → `references/log-source-map.md` |
| Global guardrails | 🔲 Pending | Create `references/guardrails.yaml` |
| Message templates | 🔲 Pending | Create `references/message-templates.md` |

**Success criteria**: Agent can diagnose any of the 20 registered scenarios using `SKILL.md` + DKR files, propose mitigations with evidence, and respect guardrails.

### Phase 2: Agent Decomposition (Multi-Agent Orchestration)

**Goal**: Split the monolithic skill into specialized agents for complex incidents.

| Deliverable | Description |
|-------------|-------------|
| `aws-incident-commander.md` | IC role — orchestrates diagnostician and executor, manages escalation, human communication |
| `aws-incident-diagnostician.md` | Diagnosis specialist — runs Observe + Reason, traverses DKR decision trees |
| `aws-incident-executor.md` | Execution specialist — runs Act + Verify, manages approval gates and rollbacks |

### Phase 3: MCP Server (Tool Layer)

**Goal**: Provide a structured AWS tool layer with built-in safety checks.

```python
# MCP Server: aws-ops-tools
tools = [
    "query_cloudwatch_logs",      # CW Logs Insights with auto-time-window
    "get_cloudwatch_metrics",     # Metric retrieval with baseline comparison
    "describe_aws_health",        # AWS Health Dashboard events
    "get_recent_deployments",     # Deployment history (CodeDeploy, CloudFormation)
    "get_cloudtrail_events",      # Recent changes with time correlation
    "execute_remediation",        # Remediation with approval gate + rollback
    "get_resource_topology",      # Resource dependency mapping
    "check_guardrails",           # Pre/post-action safety verification
]
```

### Phase 4: Slash Commands (UX Integration)

**Goal**: Provide intuitive slash commands for common workflows.

| Command | Behavior |
|---------|----------|
| `/aws-incident <scenario-id>` | Full pipeline for a known scenario |
| `/aws-incident --auto` | Auto-detect from metrics/logs, run full pipeline |
| `/aws-incident --diagnose` | Observe + Reason only (no Act) |
| `/aws-incident --verify` | Verify a previous action |
| `/aws-observe <service>` | Collect context for a specific service |
| `/aws-audit` | View execution history and audit trail |

---

## 7. Directory Structure & File Map

### 7.1 Target Directory Structure

```
oh-my-aws/
├── README.md                                    # Project charter
├── docs/
│   ├── architecture.md                          # This document
│   └── research/                                # Research documents (completed)
│       ├── 01-aws-cdk-ai-agent-infra.md
│       ├── 02-ai-agent-cdk-skill-best-practices.md
│       ├── 03-aws-incident-ai-agent-case-studies.md
│       ├── 04-cdk-infra-management-cases.md
│       ├── 05-decision-knowledge-base.md        # DKR schema + Lambda DKR
│       ├── 06-aws-incident-log-reference.md     # Log source map
│       ├── 07-aws-human-incident-response-scenarios.md
│       ├── 07-human-aws-incident-operations-playbook.md
│       └── 08-aws-operator-roles-and-skills.md
├── .claude/
│   └── skills/
│       └── aws-incident-response/
│           ├── SKILL.md                          # Agent instructions (Layer 2)
│           └── references/
│               ├── scenario-registry.yaml        # Master scenario index
│               ├── implementation-guide.md       # Implementation roadmap
│               ├── scenarios/                     # DKR files (Layer 1)
│               │   ├── lambda-timeout-cold-start.yaml
│               │   ├── lambda-throttle-concurrency-exhaustion.yaml
│               │   ├── lambda-sqs-poison-pill-retry-storm.yaml
│               │   ├── rds-perf-degradation.yaml
│               │   ├── rds-failover.yaml
│               │   ├── dynamodb-throttle.yaml
│               │   ├── ecs-crash-loop.yaml
│               │   ├── post-deploy-5xx.yaml
│               │   ├── vpc-unreachable.yaml
│               │   ├── s3-access-denied.yaml
│               │   ├── cloudfront-issue.yaml
│               │   ├── az-failure.yaml
│               │   ├── region-outage.yaml
│               │   ├── cascade-failure.yaml
│               │   ├── iam-compromise.yaml
│               │   └── ...                        # Remaining scenarios
│               ├── log-source-map.md             # Service → log → query lookup
│               ├── guardrails.yaml               # Global safety policies
│               └── message-templates.md          # Communication templates
├── _research/                                    # Reference repositories
│   ├── aws-incident-response-playbooks-workshop/
│   └── aws-customer-playbook-framework/
├── cdk-research/                                 # CDK reference projects
└── .claude/                                      # (Phase 2)
    └── agents/
        ├── aws-incident-commander.md
        ├── aws-incident-diagnostician.md
        └── aws-incident-executor.md
```

### 7.2 File Inventory (Current State)

| Path | Status | Description |
|------|--------|-------------|
| `README.md` | ✅ Complete | Project charter, goals, MVP direction |
| `docs/architecture.md` | ✅ This doc | Architecture reference |
| `docs/research/01-*.md` through `08-*.md` | ✅ Complete (9 files) | Research documentation |
| `.claude/skills/aws-incident-response/SKILL.md` | ✅ Complete | Agent instructions |
| `.claude/skills/aws-incident-response/references/scenario-registry.yaml` | ✅ Complete | Scenario registry (20 scenarios) |
| `.claude/skills/aws-incident-response/references/implementation-guide.md` | ✅ Complete | Implementation roadmap |
| `.claude/skills/aws-incident-response/references/scenarios/*.yaml` | 🔲 Pending | DKR files (3 normalized, 17 to create) |
| `.claude/skills/aws-incident-response/references/log-source-map.md` | 🔲 Pending | Log lookup table |
| `.claude/skills/aws-incident-response/references/guardrails.yaml` | 🔲 Pending | Global guardrails |
| `.claude/skills/aws-incident-response/references/message-templates.md` | 🔲 Pending | Communication templates |

---

## 8. Extension Points & Future Direction

### 8.1 CDK Infrastructure Management

The current architecture focuses on **incident response**. The research docs (`01` through `04`) also cover CDK-based infrastructure management:

- **CDK skill** — Safe `synth`, `diff`, `deploy` workflows with guardrails
- **Drift detection** — Automated CloudFormation drift detection and remediation
- **Cost anomaly** — Proactive cost monitoring with automated investigation

These will become **additional skills** in `.claude/skills/` with their own DKR-like patterns.

### 8.2 AWS SSM Automation Runbook Integration

Many DKR remediation actions can be mapped directly to AWS-provided SSM Automation Runbooks:

```
DKR remediation.action.type: "ssm_automation"
    → aws ssm start-automation-execution --document-name <AWS-managed-runbook>
```

This integration point exists in the DKR schema but has no implementation yet.

### 8.3 Multi-Account / Multi-Region

Current design assumes a single account/region context. Future extensions:

- Cross-account role assumption for centralized incident response
- Region failover orchestration (DR scenarios)
- Multi-account cost/security compliance scanning

### 8.4 Observability Backends

Current design is AWS-native (CloudWatch, X-Ray). Future extensions could support:

- Datadog / New Relic / Grafana as observability backends
- OpenTelemetry for vendor-neutral trace collection
- Custom log aggregation (ELK, Splunk)

### 8.5 Agent Runtime Portability

While currently designed for Claude Code, the knowledge base (DKR YAML files) and pipeline design are runtime-agnostic:

- Same DKR files could power an AWS Lambda-based agent
- Same pipeline could run in Amazon Bedrock Agent
- Same guardrails could be enforced by any MCP-compatible runtime

---

## Appendix A: Research Document Cross-Reference

| Research Document | Key Content | Architecture Mapping |
|-------------------|-------------|---------------------|
| `01-aws-cdk-ai-agent-infra.md` | CDK + AI Agent investigation | Future CDK skill |
| `02-ai-agent-cdk-skill-best-practices.md` | Skill system design | §2.2 Layer 2: Skill |
| `03-aws-incident-ai-agent-case-studies.md` | Global case studies + exam topic coverage | §1.3 Design principles |
| `04-cdk-infra-management-cases.md` | CDK patterns | Future CDK skill |
| `05-decision-knowledge-base.md` | DKR schema + 3 Lambda DKR | §4 Knowledge Base |
| `06-aws-incident-log-reference.md` | Log source map + 7 scenario queries | §3.2 Stage 1: Observe |
| `07-aws-human-incident-response-scenarios.md` | 10 human operator scenarios | §3.2 Pipeline stages |
| `07-human-aws-incident-operations-playbook.md` | Golden timeline, comms templates | §3.2 Stage 5: Audit |
| `08-aws-operator-roles-and-skills.md` | 10 roles, personas, skills | §1.4 Target Users |

## Appendix B: Scenario Coverage Matrix

| Scenario | Registry | DKR File | Research Source |
|----------|----------|----------|-----------------|
| lambda-timeout (cold start) | ✅ | ✅ (normalized) | `05` §4.1 |
| lambda-throttle (concurrency) | ✅ | ✅ (normalized) | `05` §4.2 |
| lambda-sqs-poison-pill | ✅ | ✅ (normalized) | `05` §4.3 |
| ecs-crash-loop | ✅ | 🔲 draft | `06` §3.2, `07` |
| rds-perf-degradation | ✅ | 🔲 draft | `06` §3.3, `07` |
| rds-failover | ✅ | 🔲 draft | `07` |
| dynamodb-throttle | ✅ | 🔲 draft | `06` §3.4 |
| vpc-unreachable | ✅ | 🔲 draft | `06` §3.5, `07` |
| s3-access-denied | ✅ | 🔲 draft | `06` §3.6 |
| cloudfront-issue | ✅ | 🔲 draft | `06` §3.7 |
| post-deploy-5xx | ✅ | 🔲 draft | `07` |
| az-failure | ✅ | 🔲 draft | `07` |
| region-outage | ✅ | 🔲 draft | `07` |
| cascade-failure | ✅ | 🔲 draft | `07` |
| control-plane-failure | ✅ | 🔲 draft | `07` |
| cert-expiry | ✅ | 🔲 draft | — |
| iam-compromise | ✅ | 🔲 draft | `_research/` security playbooks |
| s3-public-exposure | ✅ | 🔲 draft | `_research/` security playbooks |
| ec2-unreachable | ✅ | 🔲 draft | `07` |
| network-unauthorized | ✅ | 🔲 draft | `_research/` security playbooks |
