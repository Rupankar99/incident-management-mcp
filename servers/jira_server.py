from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel
import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
    
from database.db.connection import get_connection
from database.models.all_incident import AllIncidentModel

app = FastAPI(title="Jira MCP Server")


class JiraRequest(BaseModel):
    project: str
    summary: str
    description: str
    priority: str
    reporter: str | None = None
    assigned_to: str | None = None

@app.post("/jira")
def jira_event(request:JiraRequest):
    """
    Handle Jira issue creation → transform → forward to central incident API.
    """
    inc_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    jira_ticket_id = f"JIRA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    payload = {
        # Common fields
        "id": inc_id,
        "source": "jira",
        "title": request.summary,
        "description": request.description,
        "priority": request.priority,
        "urgency": None,
        "status": "open",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "reporter": "Jira Reporter",
        "assigned_to": "Jira Assigned to",

        # PagerDuty fields (unused here)
        "pd_incident_id": None,
        "pd_service_id": None,
        "pd_escalation_policy": None,
        "pd_html_url": None,

        # Jira fields
        "jira_ticket_id": jira_ticket_id,
        "jira_project": request.project,
        "jira_issue_type": "Incident",
        "jira_url": f"https://jira.example.com/browse/{jira_ticket_id}",

        # Slack fields (unused)
        "slack_channel": None,
        "slack_thread_ts": None,
        "slack_user": None,
        "slack_permalink": None,
    }
    try:
        conn = get_connection()
        all_incidents_model = AllIncidentModel(conn)
        all_incidents_model.insert(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

