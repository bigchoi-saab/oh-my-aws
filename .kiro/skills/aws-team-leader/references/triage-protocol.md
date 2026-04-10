# Incident Triage Protocol

Use this protocol when the incoming request describes an AWS outage, degradation, alarm, or operational anomaly.

## Step 1: Extract signals

Pull out:

- service name
- error text
- metric or alarm names
- time scope
- recent change hints

## Step 2: Match a scenario

Use `.kiro/skills/aws-incident-response/SKILL.md` Section 9 to map the symptom to the best scenario.

Routing rules:

1. match by concrete signal first
2. if multiple scenarios match, prefer higher priority
3. if priority ties, prefer higher severity
4. if still ambiguous, ask for one clarifying symptom

## Step 3: Resolve the DKR path

Scenario files live at:

`.kiro/skills/aws-incident-response/references/scenarios/{scenario-id}.yaml`

## Step 4: Confirm the route

Summarize:

- extracted symptom
- matched scenario ID
- severity
- next specialist agent

## Step 5: Create the incident directory

Write outputs under:

`.ops/incidents/{YYYY-MM-DDTHH-MM}-{scenario-id}/`

This directory is the handoff root for observe, diagnosis, execution, verification, and audit artifacts.
