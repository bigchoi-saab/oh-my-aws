"""Act pipeline tools - remediation execution with approval gates and dry-run."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from guardrails import assess_risk_level, check_approval_required, validate_pre_conditions


def register_act_tools(mcp: Any) -> None:
    """Register all act tools with the MCP server."""

    @mcp.tool()
    def dry_run_remediation(
        command: str,
        rollback_command: str = "",
        risk: str = "medium",
        action_name: str = "",
        estimated_impact: str = "",
        pre_conditions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Preview a remediation action without executing it.

        Returns the CLI command, rollback command, risk assessment, and
        pre-condition validation results. Does NOT execute anything.

        Args:
            command: AWS CLI command to preview
            rollback_command: Rollback CLI command if action needs reversal
            risk: Risk level (low/medium/high)
            action_name: Human-readable action name
            estimated_impact: Cost/performance impact description
            pre_conditions: List of pre-conditions to validate

        Returns:
            Dry-run preview with command, rollback, risk, and approval status.
        """
        action = {
            "name": action_name,
            "risk": risk,
            "requires_approval": risk.upper() != "LOW",
            "estimated_impact": estimated_impact,
        }

        approval = check_approval_required(action)

        pre_condition_results = []
        if pre_conditions:
            results = validate_pre_conditions(pre_conditions, {})
            pre_condition_results = [
                {"passed": r.passed, "message": r.message, "blocking": r.blocking}
                for r in results
            ]

        return {
            "mode": "DRY_RUN",
            "action_name": action_name,
            "command": command,
            "rollback_command": rollback_command,
            "risk_level": approval["risk_level"],
            "approval_required": approval["approval_required"],
            "estimated_impact": estimated_impact,
            "pre_condition_checks": pre_condition_results,
            "blocking_failures": [
                r for r in pre_condition_results if not r["passed"] and r["blocking"]
            ],
            "message": (
                f"DRY RUN: '{action_name}' (risk={approval['risk_level']}). "
                f"{'Approval required before execution.' if approval['approval_required'] else 'Auto-executable.'}"
            ),
        }

    @mcp.tool()
    def execute_remediation(
        command: str,
        rollback_command: str = "",
        risk: str = "medium",
        action_name: str = "",
        estimated_impact: str = "",
        pre_conditions: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Execute a remediation action with guardrail enforcement.

        Validates pre-conditions, checks approval requirements, then executes
        the AWS CLI command. HIGH risk actions require explicit approval.

        Args:
            command: AWS CLI command to execute
            rollback_command: Rollback command if action fails
            risk: Risk level (low/medium/high)
            action_name: Human-readable action name
            estimated_impact: Cost/performance impact description
            pre_conditions: Pre-conditions to validate before execution
            context: Current observation context for pre-condition evaluation
            approved: Whether human has explicitly approved this action

        Returns:
            Execution result with status, output, and rollback info.
        """
        action = {
            "name": action_name,
            "risk": risk,
            "requires_approval": risk.upper() != "LOW",
            "estimated_impact": estimated_impact,
        }

        # Step 1: Check approval requirement
        approval = check_approval_required(action)
        if approval["approval_required"] and not approved:
            return {
                "status": "BLOCKED",
                "reason": "approval_required",
                "approval_required": True,
                "risk_level": approval["risk_level"],
                "action_name": action_name,
                "command": command,
                "rollback_command": rollback_command,
                "estimated_impact": estimated_impact,
                "message": (
                    f"Action '{action_name}' (risk={approval['risk_level']}) requires explicit approval. "
                    f"Re-call with approved=true to execute."
                ),
            }

        # Step 2: Validate pre-conditions
        if pre_conditions:
            results = validate_pre_conditions(pre_conditions, context or {})
            blocking_failures = [r for r in results if not r.passed and r.blocking]
            if blocking_failures:
                return {
                    "status": "BLOCKED",
                    "reason": "pre_condition_failed",
                    "approval_required": False,
                    "action_name": action_name,
                    "blocking_failures": [
                        {"message": r.message} for r in blocking_failures
                    ],
                    "message": (
                        f"Action '{action_name}' blocked by {len(blocking_failures)} "
                        f"pre-condition failure(s). Resolve before retrying."
                    ),
                }

        # Step 3: Execute the command
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Try to parse JSON output
                try:
                    output = json.loads(result.stdout)
                except (json.JSONDecodeError, ValueError):
                    output = result.stdout.strip()

                return {
                    "status": "SUCCESS",
                    "action_name": action_name,
                    "command": command,
                    "rollback_command": rollback_command,
                    "output": output,
                    "message": f"Action '{action_name}' executed successfully.",
                }
            else:
                return {
                    "status": "FAILED",
                    "action_name": action_name,
                    "command": command,
                    "rollback_command": rollback_command,
                    "error": result.stderr.strip(),
                    "exit_code": result.returncode,
                    "message": (
                        f"Action '{action_name}' failed (exit={result.returncode}). "
                        f"Rollback available: {bool(rollback_command)}"
                    ),
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "action_name": action_name,
                "command": command,
                "rollback_command": rollback_command,
                "message": f"Action '{action_name}' timed out after 60 seconds.",
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "action_name": action_name,
                "error": str(e),
                "rollback_command": rollback_command,
                "message": f"Action '{action_name}' encountered an error: {str(e)}",
            }
