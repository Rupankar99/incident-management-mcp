from fastapi import FastAPI, HTTPException
from datetime import datetime
import requests

app = FastAPI(title="Jira MCP Server")
CENTRAL_API = "http://localhost:8000/incidents"

@app.post("/jira")
def jira_event(project: str, summary: str, description: str, priority: str, reporter: str = None, assigned_to: str = None):
    """
    Handle Jira issue creation → transform → forward to central incident API.
    """
    inc_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    jira_ticket_id = f"JIRA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    payload = {
        # Common fields
        "id": inc_id,
        "source": "jira",
        "title": summary,
        "description": description,
        "priority": priority,
        "urgency": None,
        "status": "open",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "reporter": reporter,
        "assigned_to": assigned_to,

        # PagerDuty fields (unused here)
        "pd_incident_id": None,
        "pd_service_id": None,
        "pd_escalation_policy": None,
        "pd_html_url": None,

        # Jira fields
        "jira_ticket_id": jira_ticket_id,
        "jira_project": project,
        "jira_issue_type": "Incident",
        "jira_url": f"https://jira.example.com/browse/{jira_ticket_id}",

        # Slack fields (unused)
        "slack_channel": None,
        "slack_thread_ts": None,
        "slack_user": None,
        "slack_permalink": None,
    }

    try:
        r = requests.post(CENTRAL_API, json=payload)
        r.raise_for_status()
        return {"status": "sent", "tool": "jira", "central_response": r.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
