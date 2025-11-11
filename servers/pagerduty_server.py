from fastapi import FastAPI, HTTPException
from datetime import datetime
import requests

app = FastAPI(title="PagerDuty MCP Server")
CENTRAL_API = "http://localhost:8000/incidents"

@app.post("/pagerduty")
def pagerduty_event(title: str, urgency: str = "high", service_id: str = None, escalation_policy: str = None, assigned_to: str = None):
    """
    Handle PagerDuty incidents → transform → forward to central incident API.
    """
    inc_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    pd_id = f"PD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    payload = {
        # Common fields
        "id": inc_id,
        "source": "pagerduty",
        "title": title,
        "description": None,
        "priority": urgency,
        "urgency": urgency,
        "status": "triggered",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "reporter": None,
        "assigned_to": assigned_to,

        # PagerDuty-specific
        "pd_incident_id": pd_id,
        "pd_service_id": service_id,
        "pd_escalation_policy": escalation_policy,
        "pd_html_url": f"https://pagerduty.com/incidents/{pd_id}",

        # Jira fields (unused)
        "jira_ticket_id": None,
        "jira_project": None,
        "jira_issue_type": None,
        "jira_url": None,

        # Slack fields (unused)
        "slack_channel": None,
        "slack_thread_ts": None,
        "slack_user": None,
        "slack_permalink": None,
    }

    try:
        r = requests.post(CENTRAL_API, json=payload)
        r.raise_for_status()
        return {"status": "sent", "tool": "pagerduty", "central_response": r.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
