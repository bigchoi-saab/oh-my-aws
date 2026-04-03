"""Verify pipeline tools - metric recovery checks and stability validation."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError


def register_verify_tools(mcp: Any) -> None:
    """Register all verify tools with the MCP server."""

    @mcp.tool()
    def check_metric_recovery(
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]] | None = None,
        statistic: str = "Average",
        threshold: float = 0,
        comparison: str = "LessThanOrEqual",
        period: int = 60,
        lookback_minutes: int = 5,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Check if a CloudWatch metric has recovered to normal levels.

        Args:
            namespace: CloudWatch namespace (e.g., AWS/Lambda)
            metric_name: Metric name (e.g., Throttles, Errors)
            dimensions: Dimension filters
            statistic: Statistic type
            threshold: Expected normal threshold value
            comparison: How to compare (LessThanOrEqual, GreaterThanOrEqual, Equal)
            period: Aggregation period in seconds
            lookback_minutes: How far back to check
            region: AWS region

        Returns:
            Recovery status with current metric value and comparison result.
        """
        try:
            client = boto3.client("cloudwatch", region_name=region) if region else boto3.client("cloudwatch")
            now = datetime.now(timezone.utc)

            params: dict[str, Any] = {
                "Namespace": namespace,
                "MetricName": metric_name,
                "StartTime": now - timedelta(minutes=lookback_minutes),
                "EndTime": now,
                "Period": period,
                "Statistics": [statistic],
            }
            if dimensions:
                params["Dimensions"] = [{"Name": d["Name"], "Value": d["Value"]} for d in dimensions]

            response = client.get_metric_statistics(**params)
            datapoints = sorted(response.get("Datapoints", []), key=lambda x: x["Timestamp"])

            if not datapoints:
                return {
                    "recovered": None,
                    "message": f"No datapoints for {namespace}/{metric_name} in last {lookback_minutes}m",
                    "current_value": None,
                    "threshold": threshold,
                }

            latest = datapoints[-1]
            current_value = latest.get(statistic, 0)

            comparisons = {
                "LessThanOrEqual": current_value <= threshold,
                "LessThan": current_value < threshold,
                "GreaterThanOrEqual": current_value >= threshold,
                "GreaterThan": current_value > threshold,
                "Equal": current_value == threshold,
            }
            recovered = comparisons.get(comparison, current_value <= threshold)

            return {
                "recovered": recovered,
                "current_value": current_value,
                "threshold": threshold,
                "comparison": comparison,
                "metric": f"{namespace}/{metric_name}",
                "timestamp": latest["Timestamp"].isoformat(),
                "datapoint_count": len(datapoints),
                "message": (
                    f"{'RECOVERED' if recovered else 'NOT RECOVERED'}: "
                    f"{metric_name}={current_value} (threshold {comparison} {threshold})"
                ),
            }
        except ClientError as e:
            return {"error": str(e), "error_code": e.response["Error"]["Code"], "recovered": None}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "recovered": None}

    @mcp.tool()
    def validate_stability_window(
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]] | None = None,
        statistic: str = "Average",
        threshold: float = 0,
        comparison: str = "LessThanOrEqual",
        window_seconds: int = 300,
        check_interval_seconds: int = 30,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Validate metric stability over a time window.

        Polls a CloudWatch metric at regular intervals and checks that it
        remains within the threshold for the entire window. Returns early
        if the metric exceeds the threshold.

        Args:
            namespace: CloudWatch namespace
            metric_name: Metric name
            dimensions: Dimension filters
            statistic: Statistic type
            threshold: Normal threshold value
            comparison: Comparison operator
            window_seconds: Stability window duration in seconds
            check_interval_seconds: Polling interval in seconds
            region: AWS region

        Returns:
            Stability result with pass/fail, check history, and duration.
        """
        checks: list[dict[str, Any]] = []
        start_time = time.time()
        end_time = start_time + window_seconds
        all_passed = True

        try:
            client = boto3.client("cloudwatch", region_name=region) if region else boto3.client("cloudwatch")

            while time.time() < end_time:
                now = datetime.now(timezone.utc)
                params: dict[str, Any] = {
                    "Namespace": namespace,
                    "MetricName": metric_name,
                    "StartTime": now - timedelta(seconds=check_interval_seconds * 2),
                    "EndTime": now,
                    "Period": check_interval_seconds,
                    "Statistics": [statistic],
                }
                if dimensions:
                    params["Dimensions"] = [{"Name": d["Name"], "Value": d["Value"]} for d in dimensions]

                response = client.get_metric_statistics(**params)
                datapoints = response.get("Datapoints", [])

                if datapoints:
                    latest = max(datapoints, key=lambda x: x["Timestamp"])
                    value = latest.get(statistic, 0)

                    comparisons = {
                        "LessThanOrEqual": value <= threshold,
                        "LessThan": value < threshold,
                        "GreaterThanOrEqual": value >= threshold,
                        "GreaterThan": value > threshold,
                    }
                    passed = comparisons.get(comparison, value <= threshold)

                    checks.append({
                        "timestamp": now.isoformat(),
                        "value": value,
                        "passed": passed,
                    })

                    if not passed:
                        all_passed = False
                        break
                else:
                    checks.append({
                        "timestamp": now.isoformat(),
                        "value": None,
                        "passed": True,
                        "note": "No datapoints (assumed OK)",
                    })

                remaining = end_time - time.time()
                if remaining > check_interval_seconds:
                    time.sleep(check_interval_seconds)
                elif remaining > 0:
                    time.sleep(remaining)

            elapsed = time.time() - start_time

            return {
                "stable": all_passed,
                "metric": f"{namespace}/{metric_name}",
                "threshold": threshold,
                "comparison": comparison,
                "window_seconds": window_seconds,
                "elapsed_seconds": round(elapsed, 1),
                "check_count": len(checks),
                "checks": checks,
                "message": (
                    f"{'STABLE' if all_passed else 'UNSTABLE'}: "
                    f"{metric_name} {'held within' if all_passed else 'exceeded'} "
                    f"threshold over {round(elapsed, 0)}s ({len(checks)} checks)"
                ),
            }
        except ClientError as e:
            return {"error": str(e), "error_code": e.response["Error"]["Code"], "stable": None}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "stable": None}
