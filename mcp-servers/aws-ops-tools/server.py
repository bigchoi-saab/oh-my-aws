"""AWS Operations Tools MCP Server.

Provides structured AWS API tools for the incident response pipeline:
- observe_*: CloudWatch Logs, Metrics, CloudTrail, AWS Health
- act_*: Remediation execution with approval gates
- verify_*: Metric recovery and stability validation
"""

from fastmcp import FastMCP

mcp = FastMCP(
    "aws-ops-tools",
    description="AWS operations tools for incident response. Observe-Reason-Act-Verify pipeline.",
)

# Register tool modules
from tools.observe import register_observe_tools
from tools.act import register_act_tools
from tools.verify import register_verify_tools

register_observe_tools(mcp)
register_act_tools(mcp)
register_verify_tools(mcp)

if __name__ == "__main__":
    mcp.run()
