from langchain_core.tools import tool
from datetime import datetime
import sqlite3

@tool
def create_jira_issue(project: str, summary: str, description: str, priority: str) -> dict:
    """Create a Jira ticket for incident tracking and push to DB."""

    ticket_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"🧰 Creating Jira issue: {ticket_id} | {summary} | Priority: {priority}")

    # Example DB insert (disabled for now)
    # try:
    #     conn = sqlite3.connect("incidents.db")
    #     cursor = conn.cursor()
    #     cursor.execute("""
    #         CREATE TABLE IF NOT EXISTS jira_tickets (
    #             id TEXT PRIMARY KEY,
    #             project TEXT,
    #             summary TEXT,
    #             description TEXT,
    #             priority TEXT,
    #             created_at TEXT
    #         )
    #     """)
    #     cursor.execute("""
    #         INSERT INTO jira_tickets (id, project, summary, description, priority, created_at)
    #         VALUES (?, ?, ?, ?, ?, ?)
    #     """, (ticket_id, project, summary, description, priority, datetime.now().isoformat()))
    #     conn.commit()
    #     conn.close()
    #     print("✅ Jira issue saved to DB.")
    # except Exception as e:
    #     print("❌ DB Error:", e)
    #     return {"status": "error", "message": str(e)}

    return {
        "status": "success",
        "ticket_id": ticket_id,
        "project": project,
        "priority": priority
    }


@tool
async def send_slack_alert(channel: str, severity: str, message: str) -> dict:
    """Send an alert to a Slack channel to notify the team about incidents."""
    print(f"🔧 [TOOL CALL] send_slack_alert: {channel} (Severity: {severity})")
    return {
        "status": "success",
        "channel": channel,
        "severity": severity
    }


@tool
async def create_pagerduty_incident(title: str, description: str, urgency: str, service_id: str) -> dict:
    """Create a PagerDuty incident to wake up the on-call engineer."""
    print(f"🔧 [TOOL CALL] create_pagerduty_incident: {title} (Urgency: {urgency})")
    return {
        "status": "success",
        "title": title,
        "urgency": urgency
    }
