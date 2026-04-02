# oh-my-aws

An agent-based AWS operations automation harness

## Project Goal

`oh-my-aws` is a project to build a harness that helps AI agents perform AWS operational tasks more safely and consistently.

The goal is not to build a simple bot that calls AWS APIs. The goal is to build an operational execution foundation with the following properties:

- operational context collection
- policy and guardrail enforcement
- pre-change validation and post-change verification
- execution history and auditability

## Problem Statement

AWS operations still depend heavily on human experience and manual procedures. Incident response, configuration changes, deployment verification, cost anomaly checks, and security reviews are repetitive tasks, but the cost of mistakes is high.

`oh-my-aws` aims to structure these workflows in an agent-friendly way so that humans keep final control while moving faster and operating more safely.

## Target Harness Flow

This project is broadly designed around the following flow:

1. `Observe`  
   Collect AWS resources, metrics, logs, configuration state, topology, tags, and account or region context.
2. `Reason`  
   Build an action plan based on runbooks, skills, operational policies, previous execution history, and the current system state.
3. `Act`  
   Execute operational actions through AWS CLI, SDKs, CDK, or other approved interfaces.
4. `Verify`  
   Compare before and after state and validate outcomes through diff, plan, synth, and checks.
5. `Audit`  
   Record what was executed, why it was executed, and what evidence supported the decision.

## Expected Use Cases

- automated first-pass AWS incident investigation
- converting operational runbooks into agent-executable workflows
- CDK-based infrastructure change proposal and validation
- drift, cost anomaly, security, and compliance checks
- semi-automated or automated execution of low-risk operational tasks

## Current Repository State

At the moment, this repository is centered more on research assets than implementation code.

- `docs/research`  
  Research documents on AWS CDK, AI agent skills, incident response cases, and infrastructure management patterns
- `cdk-research`  
  Reference repositories for AWS CDK and related open-source projects

In other words, the repository is currently in a research-first stage, gathering inputs and references for the harness implementation.

## Research Documents

The main documents currently included are:

- `docs/research/01-aws-cdk-ai-agent-infra.md`  
  Research on using AWS CDK for agent-driven infrastructure management
- `docs/research/02-ai-agent-cdk-skill-best-practices.md`  
  Research on designing and operating CDK skills for AI agents
- `docs/research/03-aws-incident-ai-agent-case-studies.md`  
  Research on AI agent use cases for AWS incident response
- `docs/research/04-cdk-infra-management-cases.md`  
  Research on practical CDK infrastructure patterns and organization models

## MVP Direction

An initial MVP should focus on part of the following scope:

- an AWS operations context collector
- a safe execution adapter layer
- an agent-facing operations skill or runbook registry
- a validation and execution-recording pipeline
- automation for one or two representative operational scenarios

Example early scenarios:

- Lambda throttling or timeout diagnosis
- RDS performance degradation checks
- root-cause tracing for post-deployment 5xx spikes
- automated `synth` and `diff` validation before CDK changes

## Next Steps

The natural next sequence is:

1. define the first harness architecture draft
2. select the first operational scenario
3. choose the execution approach  
   Python SDK-first or a mixed CDK and CLI model
4. define guardrails and approval policies
5. implement the minimum viable agent workflow

## Vision

Long term, `oh-my-aws` aims to become an agent execution layer that brings AWS operational knowledge, execution tools, and safety policies into one place.

Its core value is turning operational work that is currently manual, experience-driven, and hard to reproduce into automation flows that are repeatable, verifiable, and safe to operate.
