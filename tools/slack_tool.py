from langchain_core.tools import tool
import requests

SLACK_MCP = "http://localhost:8002/slack"  # Slack MCP server endpoint


@tool
def post_slack_alert(
    channel: str,
    message: str,
    severity: str = "medium",
    user: str = None,
    thread_ts: str = None
) -> dict:
    """
    Post an incident alert through the Slack MCP microservice.
    Mirrors the FastAPI server's 'slack_event' signature exactly.
    """

    payload = {
        "channel": channel,
        "message": message,
        "severity": severity,
        "user": user,
        "thread_ts": thread_ts
    }

    try:
        print(payload,"payload")
        # Using params since FastAPI parses these from query parameters
        response = requests.post(SLACK_MCP, json=payload)
        response.raise_for_status()
        print("✅ Sent Slack alert to Slack MCP.")
        return response.json()
    except Exception as e:
        print("❌ Slack MCP Error:", e)
        return {"status": "error", "message": str(e)}

