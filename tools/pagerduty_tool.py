from langchain_core.tools import tool

@tool
async def create_pagerduty_incident(title: str, description: str, urgency: str, service_id: str) -> dict:
    """Create a PagerDuty incident to wake up the on-call engineer.
    
    ONLY use this for truly critical issues:
    - Customer-facing outages affecting many users
    - Revenue-impacting payment/checkout failures
    - Security breaches or data loss
    """
    print(f"🔧 [TOOL CALL] create_pagerduty_incident: {title} (Urgency: {urgency})")
    return {
        "status": "success",
        "title": title,
        "urgency": urgency
    }
