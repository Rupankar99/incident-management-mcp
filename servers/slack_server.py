from fastapi import FastAPI, HTTPException
from datetime import datetime
import requests

app = FastAPI(title="Slack MCP Server")
CENTRAL_API = "http://localhost:8000/incidents"

@app.post("/slack")
def slack_event(channel: str, message: str, severity: str = "medium", user: str = None, thread_ts: str = None):
    """
    Handle Slack incident messages → transform → forward to central incident API.
    """
    inc_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    payload = {
        # Common fields
        "id": inc_id,
        "source": "slack",
        "title": message,
        "description": message,
        "priority": severity,
        "urgency": None,
        "status": "open",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "reporter": user,
        "assigned_to": None,

        # PagerDuty fields (unused)
        "pd_incident_id": None,
        "pd_service_id": None,
        "pd_escalation_policy": None,
        "pd_html_url": None,

        # Jira fields (unused)
        "jira_ticket_id": None,
        "jira_project": None,
        "jira_issue_type": None,
        "jira_url": None,

        # Slack-specific
        "slack_channel": channel,
        "slack_thread_ts": thread_ts,
        "slack_user": user,
        "slack_permalink": f"https://slack.com/app_redirect?channel={channel}&message_ts={thread_ts}" if thread_ts else None,
    }

    try:
        r = requests.post(CENTRAL_API, json=payload)
        r.raise_for_status()
        return {"status": "sent", "tool": "slack", "central_response": r.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
