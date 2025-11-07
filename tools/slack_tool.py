from langchain_core.tools import tool

@tool
async def send_slack_alert(channel: str, severity: str, message: str) -> dict:
    """Send an alert to a Slack channel to notify the team about incidents.
    
    Args:
        channel: Slack channel - e.g. #incidents-critical, #incidents-high, or #incidents
        severity: Severity level of the incident
        message: The alert message to send to the team
    """
    print(f"🔧 [TOOL CALL] send_slack_alert: {channel} (Severity: {severity})")
    return {
        "status": "success",
        "channel": channel,
        "severity": severity
    }
