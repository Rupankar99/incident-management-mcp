from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from datetime import datetime

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))


from database.db.connection import get_connection
from database.models.all_incident import AllIncidentModel
class PagerDutyRequest(BaseModel):
        title: str
        priority: str
        urgency: str
        assigned_to:str

app = FastAPI(title="PagerDuty MCP Server")
    
@app.post("/pagerduty")
def pagerduty_event(request:PagerDutyRequest):
    """
    Handle PagerDuty incidents → transform → forward to central incident API.
    """
    inc_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    pd_id = f"PD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    service_id = f"PD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"    

    payload = {
        # Common fields
        "id": inc_id,
        "source": "pagerduty",
        "title": request.title,
        "description": None,
        "priority": request.urgency,
        "urgency": request.urgency,
        "status": "triggered",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "reporter": None,
        "assigned_to": request.assigned_to,

        # PagerDuty-specific
        "pd_incident_id": pd_id,
        "pd_service_id": service_id,
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
        conn = get_connection()
        all_incidents_model = AllIncidentModel(conn)
        all_incidents_model.insert(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))