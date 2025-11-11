from langchain_core.tools import tool
import requests

PAGERDUTY_MCP = "http://localhost:8002/pagerduty"  # PagerDuty MCP server endpoint


@tool
def trigger_pagerduty_incident(
    title: str,
    urgency: str = "high",
    service_id: str = None,
    escalation_policy: str = None,
    assigned_to: str = None
) -> dict:
    """
    Trigger a PagerDuty incident through the PagerDuty MCP microservice.
    Mirrors the FastAPI server's 'pagerduty_event' signature exactly.
    """

    payload = {
        "title": title,
        "urgency": urgency,
        "service_id": service_id,
        "escalation_policy": escalation_policy,
        "assigned_to": assigned_to
    }

    try:
        # Use params to match FastAPI's query parameter parsing
        response = requests.post(PAGERDUTY_MCP, params=payload)
        response.raise_for_status()
        print("✅ Sent PagerDuty incident to PagerDuty MCP.")
        return response.json()
    except Exception as e:
        print("❌ PagerDuty MCP Error:", e)
        return {"status": "error", "message": str(e)}
