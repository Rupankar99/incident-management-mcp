/// Queue listener

import asyncio
import json

import os
import sys
from pathlib import Path


# Add models directory (parent of database folder) to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))



from incident_db.db.connection import get_connection
from mcp_agent.main import Transporter 
from incident_db.models.queue import QueueModel

POLL_INTERVAL = 5  # seconds between checks

def get_model():
    conn = get_connection()
    queue_model = QueueModel(conn)

    return queue_model

def get_pending_message():
    queue_model = get_model()
    row = queue_model.get_first_pending_item()
    if row:
        return {"id": row['id'], "data": json.loads(row['data'])}

    return None

def mark_message_processed(message_id):
    queue_modal = get_model()
    queue_modal.set_processed(message_id)

async def watch_queue():
    """Continuously poll the queue for new messages."""
    print("🚀 Queue watcher started. Waiting for messages...\n")

    while True:
        message = get_pending_message()
        if(message['data']['task'] == 'get_llm_corrective_action'):
            transporter = Transporter()
            await transporter.process(message['data']['data'])
        
        ### llm invoke
        elif(message['data']['task'] == 'sourav-producer1'):
            print("Sourav Block 1")
    
        elif(message['data']['task'] == 'sourav-producer2'):
            print("Sourav Block 2")

        else:
            mark_message_processed(message["id"])
        # mark_message_processed(message["id"])
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(watch_queue())


///// Transport Agent


from dotenv import load_dotenv
import httpx
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from datetime import datetime

from langchain_openai import ChatOpenAI
from incident_db.db.connection import get_connection
from mcp_agent.models import IncidentContext
from typing import Any, Dict, List
import json

from datetime import datetime
from .utils import build_incident_prompt_context
from incident_db.models.classifier_output import ClassifierOutputsModel



from mcp_agent.tools import create_jira_issue, post_slack_alert, trigger_pagerduty_incident
import json

client = httpx.Client(verify=False) 

load_dotenv()

class IntelligentTicketingAgent:
    """Intelligent agent that autonomously decides which MCP tools to call"""

    def __init__(self):
        self.llm = ChatOpenAI( 
            base_url="https://genailab.tcs.in", 
            model = "azure/genailab-maas-gpt-4o", 
            api_key="sk-9UQtjXiE5yKquDZEtgCwxQ", 
            http_client = client
        )
        
        # Define the tools the LLM can use
        self.tools = [
            create_jira_issue,
            post_slack_alert,
            trigger_pagerduty_incident
        ]
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _describe_context(self, context: IncidentContext) -> str:
        parts = []
        if not context.business_hours:
            parts.append("⏰ OFF-HOURS (2-4 AM) - Engineers are asleep")
        elif context.peak_traffic_hours:
            parts.append("📈 PEAK TRAFFIC - Maximum user activity")
        else:
            parts.append("🕐 BUSINESS HOURS - Team available")
        
        if context.weekend:
            parts.append("📅 WEEKEND")
        
        if context.customer_facing:
            parts.append("👥 CUSTOMER-FACING")
        else:
            parts.append("🔧 INTERNAL ONLY")
        
        if context.revenue_impacting:
            parts.append("💰 REVENUE-IMPACTING")
        
        return "\n".join(parts)



    async def make_decision_and_execute(
        self,
        incident,
        context,
    ) -> dict:
        """Let the LLM autonomously decide which MCP tools to call and execute them."""

        incident_context = build_incident_prompt_context(incident)

        conn = get_connection()
        classifier_output_model = ClassifierOutputsModel(conn)

        payload_record = classifier_output_model.get_payload_from_db(incident['payload_id'])
        payload_str = dict(payload_record).get("payload", {})
        payload_data = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        payload_metadata = {
            k: v for k, v in payload_data.items() if k != "payload"
        }

        formatted_payload = json.dumps(payload_data, indent=2) if payload_data else "N/A"
        # 🧠 Step 3: Build prompt for LLM
        system_prompt = """You are an expert incident coordinator with 15+ years of SRE experience.

    You have access to tools for managing incidents. Analyze the incident carefully and decide which tools to call.

    DECISION GUIDELINES:
    - ALWAYS create a Jira ticket for tracking (choose appropriate priority)
    - Send Slack alerts for team visibility (choose channel based on severity)
    - ONLY create PagerDuty incidents for truly critical issues:
    * Customer-facing outages affecting many users
    * Revenue-impacting payment/checkout failures
    * Security breaches or data loss
    - DO NOT wake engineers for:
    * Internal tools during off-hours
    * Issues that can wait until business hours
    * Potential issues without confirmed customer impact

    Think: "Would I want to be woken at 3 AM for this?" If no, don't page.

    Analyze the incident, explain your reasoning, then call the appropriate tools.
    """

        user_prompt = f"""ANALYZE THIS INCIDENT:
        **Classifier Metadata:**
        - Severity ID: {payload_metadata.get("severity_id", "N/A")}
        - Matched Pattern: {payload_metadata.get("matched_pattern", "N/A")}
        - Is Incident: {payload_metadata.get("is_incident", "N/A")}

        **Environment & Context Summary:**
        {incident_context}

        **Context:**
        {self._describe_context(context)}

        **Payload (from classifier_outputs):**
        {formatted_payload}

        **Questions to Consider:**
        1. Would YOU want to be woken up for this at this time?
        2. How many customers are affected RIGHT NOW?
        3. Can this wait until business hours?
        4. Is this causing revenue loss or just potential issues?

        Think through your decision and call the appropriate tools now.
        """

        messages = [
            HumanMessage(content=system_prompt + "\n\n" + user_prompt)
        ]
        tool_calls_made = []
        reasoning_text = ""

        max_iterations = 10
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")

            try:
                # Get LLM response with tool binding
                response = self.llm_with_tools.invoke(messages)
               

                # Check if LLM wants to call tools
                if hasattr(response, "tool_calls") and response.tool_calls:
                    print(f"🎯 LLM decided to call {len(response.tool_calls)} tool(s)")

                    messages.append(response)

                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        tool_id = tool_call.get("id", "unknown")

                        print(f"\n  Tool: {tool_name}")
                        print(f"  Args: {json.dumps(tool_args, indent=4)}")

                        try:
                            # Run the correct tool
                            if tool_name == "create_jira_issue":
                                result = await self.tools[0].ainvoke(tool_args)
                            elif tool_name == "post_slack_alert":
                                result = await self.tools[1].ainvoke(tool_args)
                            elif tool_name == "trigger_pagerduty_incident":
                                result = await self.tools[2].ainvoke(tool_args)
                            else:
                                result = {"status": "error", "message": f"Unknown tool: {tool_name}"}

                            print(f"  Result: {result}")

                            tool_calls_made.append({
                                "tool": tool_name,
                                "arguments": tool_args,
                                "result": result
                            })

                            # Add response back to conversation
                            messages.append(ToolMessage(
                                content=json.dumps(result),
                                tool_call_id=tool_id
                            ))

                        except Exception as e:
                            print(f"  ❌ Error executing tool: {e}")
                            error_result = {"status": "error", "message": str(e)}
                            messages.append(ToolMessage(
                                content=json.dumps(error_result),
                                tool_call_id=tool_id
                            ))

                else:
                    # LLM finished decision-making
                    print("\n✅ LLM finished decision-making")
                    if hasattr(response, "content") and response.content:
                        reasoning_text = response.content
                        print(f"\nReasoning: {reasoning_text[:300]}...")
                    break

            except Exception as e:
                print(f"\n❌ Error in agent loop: {e}")
                import traceback
                traceback.print_exc()
                break
    
  
    //////main.py


import asyncio
import json
from .models import IncidentContext
from .orchestrator import IncidentManagementSystem

class Transporter:
    def __init__(self):
        self.ims = IncidentManagementSystem()

    async def process(self, classifier_item):
        try:
            context = IncidentContext(
                business_hours=classifier_item.get("business_hours", True),
                weekend=classifier_item.get("weekend", False),
                peak_traffic_hours=classifier_item.get("peak_traffic_hours", False),
                customer_facing=classifier_item.get("customer_facing", True),
                revenue_impacting=classifier_item.get("revenue_impacting", False)
            )

            await self.ims.process_incident(classifier_item, context)

        except Exception as e:
            print(f"❌ Error processing queue item: {e}\n")
            await asyncio.sleep(0.5)




////orchestrator.py

from .models import Incident, IncidentReport, IncidentContext, Ticket
from .reporting import ReportingAgent
from .transport import IntelligentTicketingAgent
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List
import asyncio, json


class IncidentManagementSystem:
    def __init__(self):
        self.reporting_agent = ReportingAgent()

        # ✅ Just initialize normally — no need to pass tools anymore
        self.ticketing_agent = IntelligentTicketingAgent()

        self.incidents: Dict[str, Incident] = {}
        self.reports: Dict[str, IncidentReport] = {}
        self.tickets: Dict[str, List[Ticket]] = {}
        self.decisions: Dict[str, Dict[str, Any]] = {}

    async def process_incident(self, payload, context: IncidentContext) -> Dict[str, Any]:
        """Process incident with LLM intelligence"""
        # try:
        #     report = self.reporting_agent.generate_report(incident)
        #     self.reports[incident.id] = report
        #     print(f"✅ Report Generated")
        #     print(f"   Report: {report}\n")
        # except Exception as e:
        #     print(f"❌ Error generating report: {e}\n")
        #     return {"status": "error", "message": str(e)}

        # Step 2: LLM Decision + MCP Execution
        print("🎯 Step 2: LLM Making Decision via MCP...")
        print("-" * 80)

        try:
            await self.ticketing_agent.make_decision_and_execute(payload,context)
        except Exception as e:
            print(f"❌ Error during decision phase: {e}\n")
            return {"status": "error", "message": str(e)}

    def _format_context(self, context: IncidentContext) -> str:
        parts = []
        if not context.business_hours:
            parts.append("Off-Hours")
        elif context.peak_traffic_hours:
            parts.append("Peak")
        else:
            parts.append("Business")

        if context.weekend:
            parts.append("Weekend")
        if context.customer_facing:
            parts.append("Customer-Facing")
        else:
            parts.append("Internal")
        if context.revenue_impacting:
            parts.append("Revenue-Impact")

        return " | ".join(parts)

    def print_summary(self):
        print("\n" + "=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)

        total = len(self.incidents)
        pagerduty_count = sum(
            1 for d in self.decisions.values() if d["decision_summary"]["pagerduty"]
        )

        print(f"\nTotal Incidents: {total}")
        print(f"PagerDuty Escalations: {pagerduty_count}")
        print(f"Jira Only (No Wake): {total - pagerduty_count}")
        print(f"\n{'=' * 80}\n")


//// transport agent

from dotenv import load_dotenv
import httpx
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from datetime import datetime

from langchain_openai import ChatOpenAI
from incident_db.db.connection import get_connection
from mcp_agent.models import IncidentContext
from typing import Any, Dict, List
import json

from datetime import datetime
from .utils import build_incident_prompt_context
from incident_db.models.classifier_output import ClassifierOutputsModel



from mcp_agent.tools import create_jira_issue, post_slack_alert, trigger_pagerduty_incident
import json

client = httpx.Client(verify=False) 

load_dotenv()

class IntelligentTicketingAgent:
    """Intelligent agent that autonomously decides which MCP tools to call"""

    def __init__(self):
        self.llm = ChatOpenAI( 
            base_url="https://genailab.tcs.in", 
            model = "azure/genailab-maas-gpt-4o", 
            api_key="sk-9UQtjXiE5yKquDZEtgCwxQ", 
            http_client = client
        )
        
        # Define the tools the LLM can use
        self.tools = [
            create_jira_issue,
            post_slack_alert,
            trigger_pagerduty_incident
        ]
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _describe_context(self, context: IncidentContext) -> str:
        parts = []
        if not context.business_hours:
            parts.append("⏰ OFF-HOURS (2-4 AM) - Engineers are asleep")
        elif context.peak_traffic_hours:
            parts.append("📈 PEAK TRAFFIC - Maximum user activity")
        else:
            parts.append("🕐 BUSINESS HOURS - Team available")
        
        if context.weekend:
            parts.append("📅 WEEKEND")
        
        if context.customer_facing:
            parts.append("👥 CUSTOMER-FACING")
        else:
            parts.append("🔧 INTERNAL ONLY")
        
        if context.revenue_impacting:
            parts.append("💰 REVENUE-IMPACTING")
        
        return "\n".join(parts)



    async def make_decision_and_execute(
        self,
        incident,
        context,
    ) -> dict:
        """Let the LLM autonomously decide which MCP tools to call and execute them."""

        incident_context = build_incident_prompt_context(incident)

        conn = get_connection()
        classifier_output_model = ClassifierOutputsModel(conn)

        payload_record = classifier_output_model.get_payload_from_db(incident['payload_id'])
        payload_str = dict(payload_record).get("payload", {})
        payload_data = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        payload_metadata = {
            k: v for k, v in payload_data.items() if k != "payload"
        }

        formatted_payload = json.dumps(payload_data, indent=2) if payload_data else "N/A"
        # 🧠 Step 3: Build prompt for LLM
        system_prompt = """You are an expert incident coordinator with 15+ years of SRE experience.

    You have access to tools for managing incidents. Analyze the incident carefully and decide which tools to call.

    DECISION GUIDELINES:
    - ALWAYS create a Jira ticket for tracking (choose appropriate priority)
    - Send Slack alerts for team visibility (choose channel based on severity)
    - ONLY create PagerDuty incidents for truly critical issues:
    * Customer-facing outages affecting many users
    * Revenue-impacting payment/checkout failures
    * Security breaches or data loss
    - DO NOT wake engineers for:
    * Internal tools during off-hours
    * Issues that can wait until business hours
    * Potential issues without confirmed customer impact

    Think: "Would I want to be woken at 3 AM for this?" If no, don't page.

    Analyze the incident, explain your reasoning, then call the appropriate tools.
    """

        user_prompt = f"""ANALYZE THIS INCIDENT:
        **Classifier Metadata:**
        - Severity ID: {payload_metadata.get("severity_id", "N/A")}
        - Matched Pattern: {payload_metadata.get("matched_pattern", "N/A")}
        - Is Incident: {payload_metadata.get("is_incident", "N/A")}

        **Environment & Context Summary:**
        {incident_context}

        **Context:**
        {self._describe_context(context)}

        **Payload (from classifier_outputs):**
        {formatted_payload}

        **Questions to Consider:**
        1. Would YOU want to be woken up for this at this time?
        2. How many customers are affected RIGHT NOW?
        3. Can this wait until business hours?
        4. Is this causing revenue loss or just potential issues?

        Think through your decision and call the appropriate tools now.
        """

        messages = [
            HumanMessage(content=system_prompt + "\n\n" + user_prompt)
        ]
        tool_calls_made = []
        reasoning_text = ""

        max_iterations = 10
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")

            try:
                # Get LLM response with tool binding
                response = self.llm_with_tools.invoke(messages)
               

                # Check if LLM wants to call tools
                if hasattr(response, "tool_calls") and response.tool_calls:
                    print(f"🎯 LLM decided to call {len(response.tool_calls)} tool(s)")

                    messages.append(response)

                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        tool_id = tool_call.get("id", "unknown")

                        print(f"\n  Tool: {tool_name}")
                        print(f"  Args: {json.dumps(tool_args, indent=4)}")

                        try:
                            # Run the correct tool
                            if tool_name == "create_jira_issue":
                                result = await self.tools[0].ainvoke(tool_args)
                            elif tool_name == "post_slack_alert":
                                result = await self.tools[1].ainvoke(tool_args)
                            elif tool_name == "trigger_pagerduty_incident":
                                result = await self.tools[2].ainvoke(tool_args)
                            else:
                                result = {"status": "error", "message": f"Unknown tool: {tool_name}"}

                            print(f"  Result: {result}")

                            tool_calls_made.append({
                                "tool": tool_name,
                                "arguments": tool_args,
                                "result": result
                            })

                            # Add response back to conversation
                            messages.append(ToolMessage(
                                content=json.dumps(result),
                                tool_call_id=tool_id
                            ))

                        except Exception as e:
                            print(f"  ❌ Error executing tool: {e}")
                            error_result = {"status": "error", "message": str(e)}
                            messages.append(ToolMessage(
                                content=json.dumps(error_result),
                                tool_call_id=tool_id
                            ))

                else:
                    # LLM finished decision-making
                    print("\n✅ LLM finished decision-making")
                    if hasattr(response, "content") and response.content:
                        reasoning_text = response.content
                        print(f"\nReasoning: {reasoning_text[:300]}...")
                    break

            except Exception as e:
                print(f"\n❌ Error in agent loop: {e}")
                import traceback
                traceback.print_exc()
                break
    
  
    ////jira_tool.py

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
        response = requests.post(JIRA_MCP, json=payload)
        response.raise_for_status()
        print("✅ Sent Jira issue to Jira MCP.")
        return response.json()
    except Exception as e:
        print("❌ Jira MCP Error:", e)
        return {"status": "error", "message": str(e)}


///jira server

from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from datetime import datetime
import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
    
from incident_db.db.connection import get_connection
from incident_db.models.all_incident import AllIncidentModel

app = FastAPI(title="Jira MCP Server")

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
    print(payload,"payload")
    try:
        conn = get_connection()
        all_incidents_model = AllIncidentModel(conn)
        print(payload,"payload inside")
        all_incidents_model.insert(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


///slack tool
from langchain_core.tools import tool
import requests

SLACK_MCP = "http://localhost:8003/slack"  # Slack MCP server endpoint


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


///// slack server


from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from datetime import datetime
import requests


BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from incident_db.db.connection import get_connection
from incident_db.models.all_incident import AllIncidentModel

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
    print(payload,"payload")
    try:
        conn = get_connection()
        all_incidents_model = AllIncidentModel(conn)
        all_incidents_model.insert(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



///pd_tool

from langchain_core.tools import tool
import requests

PAGERDUTY_MCP = "http://localhost:8002/pagerduty"  # PagerDuty MCP server endpoint


@tool
def trigger_pagerduty_incident(
    title: str,
    urgency: str = "high",
    service_id: str = None,
    escalation_policy: str = None,
    assigned_to: str = None
) -> dict:
    """
    Trigger a PagerDuty incident through the PagerDuty MCP microservice.
    Mirrors the FastAPI server's 'pagerduty_event' signature exactly.
    """

    payload = {
        "title": title,
        "urgency": urgency,
        "service_id": service_id,
        "escalation_policy": escalation_policy,
        "assigned_to": assigned_to
    }

    try:
        # Use params to match FastAPI's query parameter parsing
        response = requests.post(PAGERDUTY_MCP, json=payload)
        response.raise_for_status()
        print("✅ Sent PagerDuty incident to PagerDuty MCP.")
        return response.json()
    except Exception as e:
        print("❌ PagerDuty MCP Error:", e)
        return {"status": "error", "message": str(e)}


///pd_server.py

from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))


from incident_db.db.connection import get_connection
from incident_db.models.all_incident import AllIncidentModel

app = FastAPI(title="PagerDuty MCP Server")
    
@app.post("/pagerduty")
def pagerduty_event(title: str, urgency: str = "high", service_id: str = None, escalation_policy: str = None, assigned_to: str = None):
    """
    Handle PagerDuty incidents → transform → forward to central incident API.
    """
    inc_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    pd_id = f"PD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    payload = {
        # Common fields
        "id": inc_id,
        "source": "pagerduty",
        "title": title,
        "description": None,
        "priority": urgency,
        "urgency": urgency,
        "status": "triggered",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "reporter": None,
        "assigned_to": assigned_to,

        # PagerDuty-specific
        "pd_incident_id": pd_id,
        "pd_service_id": service_id,
        "pd_escalation_policy": escalation_policy,
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

    print(payload,"payload")
    try:
        conn = get_connection()
        all_incidents_model = AllIncidentModel(conn)
        all_incidents_model.insert(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
