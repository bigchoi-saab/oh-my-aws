# Ralplan Improvement Plan for Claude + Kiro Alignment

Date: 2026-04-10
Scope: `$ralplan` skill evolution and `.kiro/` runtime hardening
Status: Drafted and partially implemented in this repo

## Goal

Make `ralplan` reliable across two execution environments:

1. Codex/OMX-style orchestration, where planner/architect/critic loops and state files already exist.
2. Kiro CLI, where skills live under `.kiro/skills/` and custom agents must be JSON configs under `.kiro/agents/`.

The target is not "same wording everywhere." The target is one planning contract with thin runtime adapters.

## Current Gaps

### 1. `ralplan` is runtime-coupled

The current skill text assumes:

- `$plan --consensus`
- `AskUserQuestion`
- `.omx/context/...`
- `explore`
- downstream handoff to `$ralph` / `$team`

That works in the Codex/OMX stack, but it does not map cleanly onto Kiro CLI.

### 2. Planning and execution handoff are fused

`ralplan` currently combines:

- consensus planning rules
- ambiguity triage
- execution gate policy
- specific handoff targets

This makes reuse harder in Kiro, where the runtime can support different agent names and different approval UX.

### 3. `.kiro/` is not yet a self-consistent runtime surface

Before this change set:

- `.kiro/skills/aws-team-leader/` had no `SKILL.md`
- `.kiro/agents/` mixed valid JSON agents with markdown-only prompts
- many `.kiro` files still pointed at `.claude/...` paths

That meant Kiro could not treat `.kiro` as the canonical workspace runtime.

## Recommended Direction

### A. Split `ralplan` into a stable core plus runtime adapters

Keep one core planning contract:

- pre-context intake
- ambiguity gate
- planner -> architect -> critic order
- max-iteration loop
- ADR-style final plan output
- execution handoff only after approved plan

Then add runtime adapters:

- `ralplan-codex`: uses `$plan --consensus`, `.omx/context`, Codex agent roles
- `ralplan-kiro`: uses Kiro skills/agents, `.kiro/specs/`, Kiro approval flow

The alias `$ralplan` should detect or be told which adapter to use.

### B. Make context intake pluggable

Replace hardcoded intake assumptions with an adapter contract:

- `context store`: `.omx/context/` or `.kiro/specs/<task>/`
- `inspection tool`: `explore` or Kiro agent/resource lookup
- `interactive question tool`: `AskUserQuestion` when available, otherwise plain one-question turns

This removes most of the portability friction.

### C. Treat execution handoff as policy, not as hardcoded commands

Current handoff targets:

- `$ralph`
- `$team`

Proposed model:

- `sequential_executor`
- `parallel_executor`
- `manual_export`

Codex maps these to `$ralph` / `$team`.
Kiro maps them to project agents such as `aws-incident-responder`, `aws-infra-analyzer`, or future Kiro-native executor agents.

### D. Normalize artifact outputs

Every `ralplan` run should emit the same core artifacts regardless of runtime:

- context snapshot
- final consensus plan
- ADR summary
- verification strategy
- residual-risk note if consensus is incomplete

Recommended paths:

- Codex/OMX: `.omx/context/`, `.omx/specs/`
- Kiro: `.kiro/specs/<task>/requirements.md`, `design.md`, `tasks.md`

### E. Keep the skill small and move policy to references

The top-level `SKILL.md` should remain a router/contract, while detailed policy moves into references:

- `consensus-loop.md`
- `ambiguity-gate.md`
- `execution-handoff.md`
- `runtime-adapters.md`

This reduces context load and makes Kiro/Claude derivation easier.

## Repo Workstreams

### Workstream 1: `ralplan` runtime hardening

Targets:

- personal skill: `C:\Users\yhchoi\.agents\skills\ralplan\SKILL.md`
- supporting references under the same skill directory

Changes:

1. Introduce explicit runtime section: Codex vs Kiro.
2. Replace tool-specific assumptions with adapter language.
3. Keep consensus loop invariant unchanged.
4. Add artifact contract for Kiro specs output.
5. Add a portability note for interactive vs non-interactive mode.

### Workstream 2: `.kiro/` runtime normalization

Targets in this repo:

- `.kiro/skills/aws-team-leader/SKILL.md`
- `.kiro/agents/*.json`
- `.kiro/skills/**/*.md`
- `.kiro/skills/**/*.py`

Changes:

1. Add missing Kiro team-leader skill entrypoint.
2. Ensure every Kiro agent is a JSON config, not markdown only.
3. Keep markdown files as prompts, referenced from JSON configs.
4. Replace `.claude/...` path references with `.kiro/...` where the Kiro runtime should be authoritative.
5. Preserve `.claude` as a parallel runtime, not as a hidden dependency of `.kiro`.

## Success Criteria

### `ralplan`

- planning contract remains planner -> architect -> critic
- runtime-specific tool assumptions are isolated
- Kiro can consume the same plan intent without pretending to be Codex

### `.kiro/`

- Kiro sees a valid `aws-team-leader` skill
- Kiro sees valid JSON agents for the shipped specialist roles
- Kiro-facing docs and scripts resolve local `.kiro` paths
- no critical `.kiro` workflow depends on a missing `.claude`-only file

## Verification

1. Validate that `.kiro/skills/aws-team-leader/SKILL.md` exists.
2. Validate that each Kiro agent intended for use has a `.json` config.
3. Search `.kiro/` for remaining `.claude/` references and classify:
   - intentional cross-runtime reference
   - bug that should be converted to `.kiro/`
4. Re-open changed JSON and SKILL files to confirm internal path consistency.

## Deferred Items

- Full `ralplan` implementation rewrite in the personal skill directory
- Kiro-native planner/architect/critic agent trio
- Automatic golden-source -> Kiro derivation pipeline
- End-to-end Kiro CLI session validation against a live runtime
