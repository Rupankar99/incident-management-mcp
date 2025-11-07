from fastmcp import FastMCP
import asyncio
from datetime import datetime

mcp = FastMCP("IncidentTools")

@mcp.tool()
async def create_jira_issue(project: str, summary: str, description: str, priority: str) -> dict:
    print("--------------Jira MCP Triggered---------------")
    ticket_id = f"INCIDENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {"status": "success", "ticket_id": ticket_id, "url": f"https://jira.company.com/browse/{ticket_id}", "priority": priority}

@mcp.tool()
async def send_slack_alert(channel: str, severity: str, message: str) -> dict:
    return {"status": "success", "channel": channel}

@mcp.tool()
async def create_pagerduty_incident(title: str, description: str, urgency: str, service_id: str) -> dict:
    incident_id = f"PD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {"status": "success", "incident_id": incident_id, "url": f"https://company.pagerduty.com/incidents/{incident_id}"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
