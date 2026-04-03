"""Observe pipeline tools - CloudWatch Logs, Metrics, CloudTrail, AWS Health."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError


def register_observe_tools(mcp: Any) -> None:
    """Register all observe tools with the MCP server."""

    @mcp.tool()
    def query_cloudwatch_logs(
        log_group: str,
        query: str,
        start_minutes_ago: int = 30,
        end_minutes_ago: int = 0,
        limit: int = 100,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Query CloudWatch Logs using Logs Insights.

        Args:
            log_group: CloudWatch Log Group name (e.g., /aws/lambda/my-function)
            query: CloudWatch Logs Insights query string
            start_minutes_ago: Start of time range (minutes ago from now)
            end_minutes_ago: End of time range (minutes ago from now, 0 = now)
            limit: Maximum number of results
            region: AWS region (uses default if not specified)

        Returns:
            Query results with status, statistics, and matching log entries.
        """
        try:
            client = boto3.client("logs", region_name=region) if region else boto3.client("logs")
            now = datetime.now(timezone.utc)
            start_time = int((now - timedelta(minutes=start_minutes_ago)).timestamp())
            end_time = int((now - timedelta(minutes=end_minutes_ago)).timestamp())

            response = client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=query,
                limit=limit,
            )
            query_id = response["queryId"]

            # Poll for results (max 30 seconds)
            for _ in range(30):
                result = client.get_query_results(queryId=query_id)
                if result["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
                    break
                time.sleep(1)

            return {
                "status": result["status"],
                "statistics": result.get("statistics", {}),
                "results": [
                    {field["field"]: field["value"] for field in row}
                    for row in result.get("results", [])
                ],
                "result_count": len(result.get("results", [])),
                "query": query,
                "log_group": log_group,
                "time_range": f"{start_minutes_ago}m ago - {end_minutes_ago}m ago",
            }
        except ClientError as e:
            return {"error": str(e), "error_code": e.response["Error"]["Code"], "log_group": log_group}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "log_group": log_group}

    @mcp.tool()
    def get_cloudwatch_metrics(
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]] | None = None,
        statistic: str = "Average",
        period: int = 300,
        start_minutes_ago: int = 30,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Get CloudWatch metric statistics.

        Args:
            namespace: CloudWatch namespace (e.g., AWS/Lambda, AWS/RDS)
            metric_name: Metric name (e.g., Duration, Throttles, CPUUtilization)
            dimensions: List of dimension filters [{Name: str, Value: str}]
            statistic: Statistic type (Average, Sum, Maximum, Minimum, SampleCount)
            period: Aggregation period in seconds
            start_minutes_ago: How far back to query (minutes)
            region: AWS region

        Returns:
            Metric datapoints sorted by timestamp.
        """
        try:
            client = boto3.client("cloudwatch", region_name=region) if region else boto3.client("cloudwatch")
            now = datetime.now(timezone.utc)

            params: dict[str, Any] = {
                "Namespace": namespace,
                "MetricName": metric_name,
                "StartTime": now - timedelta(minutes=start_minutes_ago),
                "EndTime": now,
                "Period": period,
                "Statistics": [statistic],
            }
            if dimensions:
                params["Dimensions"] = [{"Name": d["Name"], "Value": d["Value"]} for d in dimensions]

            response = client.get_metric_statistics(**params)
            datapoints = sorted(response.get("Datapoints", []), key=lambda x: x["Timestamp"])

            return {
                "namespace": namespace,
                "metric_name": metric_name,
                "statistic": statistic,
                "datapoints": [
                    {
                        "timestamp": dp["Timestamp"].isoformat(),
                        "value": dp.get(statistic, 0),
                        "unit": dp.get("Unit", ""),
                    }
                    for dp in datapoints
                ],
                "datapoint_count": len(datapoints),
                "dimensions": dimensions or [],
            }
        except ClientError as e:
            return {"error": str(e), "error_code": e.response["Error"]["Code"], "namespace": namespace}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "namespace": namespace}

    @mcp.tool()
    def get_cloudtrail_events(
        event_name: str | None = None,
        resource_type: str | None = None,
        resource_name: str | None = None,
        start_minutes_ago: int = 60,
        max_results: int = 20,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Look up recent CloudTrail events for change tracking.

        Args:
            event_name: Filter by API event name (e.g., UpdateFunctionConfiguration)
            resource_type: Filter by resource type (e.g., AWS::Lambda::Function)
            resource_name: Filter by resource name
            start_minutes_ago: How far back to search
            max_results: Maximum events to return
            region: AWS region

        Returns:
            List of CloudTrail events with timestamps, actors, and resources.
        """
        try:
            client = boto3.client("cloudtrail", region_name=region) if region else boto3.client("cloudtrail")
            now = datetime.now(timezone.utc)

            params: dict[str, Any] = {
                "StartTime": now - timedelta(minutes=start_minutes_ago),
                "EndTime": now,
                "MaxResults": max_results,
            }

            lookup_attributes = []
            if event_name:
                lookup_attributes.append({"AttributeKey": "EventName", "AttributeValue": event_name})
            if resource_type:
                lookup_attributes.append({"AttributeKey": "ResourceType", "AttributeValue": resource_type})
            if resource_name:
                lookup_attributes.append({"AttributeKey": "ResourceName", "AttributeValue": resource_name})
            if lookup_attributes:
                params["LookupAttributes"] = lookup_attributes

            response = client.lookup_events(**params)

            return {
                "events": [
                    {
                        "event_time": evt["EventTime"].isoformat(),
                        "event_name": evt.get("EventName", ""),
                        "username": evt.get("Username", ""),
                        "event_source": evt.get("EventSource", ""),
                        "resources": [
                            {"type": r.get("ResourceType", ""), "name": r.get("ResourceName", "")}
                            for r in evt.get("Resources", [])
                        ],
                    }
                    for evt in response.get("Events", [])
                ],
                "event_count": len(response.get("Events", [])),
                "time_range": f"{start_minutes_ago}m ago - now",
                "filters": {"event_name": event_name, "resource_type": resource_type, "resource_name": resource_name},
            }
        except ClientError as e:
            return {"error": str(e), "error_code": e.response["Error"]["Code"]}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool()
    def describe_aws_health(
        services: list[str] | None = None,
        regions: list[str] | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Check AWS Health Dashboard for ongoing service events.

        Args:
            services: Filter by AWS service names (e.g., ["LAMBDA", "RDS"])
            regions: Filter by AWS regions (e.g., ["ap-northeast-2"])
            region: AWS region for the Health API client (us-east-1 recommended)

        Returns:
            Active and recent AWS Health events affecting specified services/regions.
        """
        try:
            client = boto3.client("health", region_name=region or "us-east-1")

            filter_params: dict[str, Any] = {
                "eventStatusCodes": ["open", "upcoming"],
            }
            if services:
                filter_params["services"] = services
            if regions:
                filter_params["regions"] = regions

            response = client.describe_events(filter=filter_params, maxResults=20)

            return {
                "events": [
                    {
                        "arn": evt.get("arn", ""),
                        "service": evt.get("service", ""),
                        "event_type": evt.get("eventTypeCode", ""),
                        "category": evt.get("eventTypeCategory", ""),
                        "region": evt.get("region", ""),
                        "start_time": evt["startTime"].isoformat() if evt.get("startTime") else None,
                        "status": evt.get("statusCode", ""),
                    }
                    for evt in response.get("events", [])
                ],
                "event_count": len(response.get("events", [])),
                "filters": {"services": services, "regions": regions},
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "SubscriptionRequiredException":
                return {
                    "error": "AWS Health API requires Business or Enterprise Support plan",
                    "error_code": error_code,
                    "fallback": "Check https://health.aws.amazon.com/health/status manually",
                }
            return {"error": str(e), "error_code": error_code}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
