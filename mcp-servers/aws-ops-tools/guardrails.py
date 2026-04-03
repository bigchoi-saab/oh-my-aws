"""Execution guardrails - pre/post condition validation, cost estimation, auto-rollback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    passed: bool
    message: str
    blocking: bool = True


def validate_pre_conditions(
    pre_conditions: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[ValidationResult]:
    """Validate pre-conditions before executing a remediation action.

    Args:
        pre_conditions: List of pre-condition definitions from DKR guardrails.
            Each has: description, check, block (bool)
        context: Current observation context (metrics, logs, config values)
            used to evaluate conditions.

    Returns:
        List of ValidationResult for each pre-condition.
    """
    results: list[ValidationResult] = []

    for condition in pre_conditions:
        description = condition.get("description", "Unknown condition")
        blocking = condition.get("block", True)

        # Evaluate the condition against provided context
        check_key = condition.get("check_key")
        if check_key and check_key in context:
            passed = bool(context[check_key])
            results.append(ValidationResult(
                passed=passed,
                message=f"{'PASS' if passed else 'FAIL'}: {description}",
                blocking=blocking,
            ))
        else:
            # If no context available for this check, require manual verification
            results.append(ValidationResult(
                passed=False,
                message=f"MANUAL CHECK REQUIRED: {description}",
                blocking=blocking,
            ))

    return results


def assess_risk_level(action: dict[str, Any]) -> str:
    """Determine risk level of a remediation action.

    Args:
        action: Remediation action from DKR with risk and requires_approval fields.

    Returns:
        Risk level string: LOW, MEDIUM, or HIGH.
    """
    risk = action.get("risk", "medium").upper()
    if risk in ("LOW", "MEDIUM", "HIGH"):
        return risk
    return "MEDIUM"


def check_approval_required(action: dict[str, Any]) -> dict[str, Any]:
    """Check if an action requires human approval before execution.

    Args:
        action: Remediation action from DKR.

    Returns:
        Dict with approval_required flag, risk level, and message.
    """
    risk = assess_risk_level(action)
    requires_approval = action.get("requires_approval", risk != "LOW")

    return {
        "approval_required": requires_approval,
        "risk_level": risk,
        "action_name": action.get("name", "Unknown"),
        "message": (
            f"Action '{action.get('name', 'Unknown')}' (risk={risk}) "
            f"{'requires explicit approval before execution' if requires_approval else 'can be auto-executed'}"
        ),
    }


def estimate_cost_impact(action: dict[str, Any]) -> dict[str, Any]:
    """Estimate cost impact of a remediation action.

    Args:
        action: Remediation action with estimated_impact field.

    Returns:
        Cost impact summary.
    """
    return {
        "action_name": action.get("name", "Unknown"),
        "estimated_impact": action.get("estimated_impact", "Not estimated"),
        "has_cost_change": bool(action.get("estimated_impact")),
    }
