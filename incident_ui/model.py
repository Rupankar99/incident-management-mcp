from pydantic import BaseModel, Field
from typing import Optional


class IncidentCreate(BaseModel):
    id: str = Field(...)
    source: str
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = None
    created_at: str
    last_updated: Optional[str] = None
    reporter: Optional[str] = None
    assigned_to: Optional[str] = None
    pd_incident_id: Optional[str] = None
    pd_service_id: Optional[str] = None
    pd_escalation_policy: Optional[str] = None
    pd_html_url: Optional[str] = None
    jira_ticket_id: Optional[str] = None
    jira_project: Optional[str] = None
    jira_issue_type: Optional[str] = None
    jira_url: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    slack_user: Optional[str] = None
    slack_permalink: Optional[str] = None