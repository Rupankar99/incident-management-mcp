from langchain_core.tools import tool
import requests

JIRA_MCP = "http://localhost:8001/jira"  # Jira MCP server endpoint


@tool
def create_jira_issue(
    project: str,
    summary: str,
    description: str,
    priority: str,
    reporter: str = None,
    assigned_to: str = None
) -> dict:
    """
    Create a Jira issue and push it through the Jira MCP microservice.
    Mirrors the FastAPI server's 'jira_event' method signature exactly.
    """

    payload = {
        "project": project,
        "summary": summary,
        "description": description,
        "priority": priority,
        "reporter": reporter,
        "assigned_to": assigned_to
    }

    try:
        # Use params to match FastAPI query-style argument parsing
        response = requests.post(JIRA_MCP, params=payload)
        response.raise_for_status()
        print("✅ Sent Jira issue to Jira MCP.")
        return response.json()
    except Exception as e:
        print("❌ Jira MCP Error:", e)
        return {"status": "error", "message": str(e)}
