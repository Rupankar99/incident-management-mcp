from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from datetime import datetime
from models import Ticket, Incident, IncidentReport, IncidentContext
from typing import Any, Dict, List
import json

from datetime import datetime

from tools import create_jira_issue, post_slack_alert, trigger_pagerduty_incident
import sqlite3
import json

DB_PATH = "/Users/rupankarchakroborty/Documents/incident-management-2/data.db"


class IntelligentTicketingAgent:
    """Intelligent agent that autonomously decides which MCP tools to call"""

    def __init__(self):
        self.llm = ChatOllama(
            model="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.7
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

        print(incident['payload_id'])
        payload_record = self.get_payload_from_db(incident['payload_id'])
        payload_data = payload_record.get("payload", {})
        payload_metadata = {
            k: v for k, v in payload_record.items() if k != "payload"
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

    **Incident Details:**
    - ID: {incident.id}
    - Title: {incident.title}
    - Severity: {incident.severity.value}
    - Service: {incident.service}
    - Region: {incident.region}

    **Classifier Metadata:**
    - Severity ID: {payload_metadata.get("severity_id", "N/A")}
    - Matched Pattern: {payload_metadata.get("matched_pattern", "N/A")}
    - Is Incident: {payload_metadata.get("is_incident", "N/A")}

    **Context:**
    {self._describe_context(context)}

    **Technical Details:**
    - Error Rate: {incident.metrics.get('error_rate', 'N/A')}
    - Affected Components: {', '.join(incident.affected_components)}

    **Payload (from classifier_outputs):**
    {formatted_payload}

    **Recent Logs:**
    {chr(10).join(incident.logs[:3])}

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

        print("\n" + "=" * 80)
        print("🤖 LLM AGENT - Analyzing incident and deciding on actions...")
        print("=" * 80)
        print(f"\nIncident: {incident.title}")
        print(f"Severity: {incident.severity.value}")
        print(f"Context: {self._describe_context(context)}")
        print(f"Payload ID: {incident.payload_id}")

        # 🔁 Agent loop — let LLM autonomously decide and act
        max_iterations = 10
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")

            try:
                # Get LLM response with tool binding
                response = self.llm_with_tools.invoke(messages)
                print("-------------------res-----------")
                print(response)

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
    
  
    def get_payload_from_db(self, payload_id: str) -> dict:
        """Fetch payload JSON and metadata from classifier_outputs using payload_id."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT payload, severity_id, matched_pattern, is_incident
                FROM classifier_outputs
                WHERE payload_id = ?
                LIMIT 1
            """, (payload_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                print(f"⚠️ No record found in classifier_outputs for payload_id={payload_id}")
                return {}

            payload_json = row[0]
            metadata = {
                "severity_id": row[1],
                "matched_pattern": row[2],
                "is_incident": row[3],
            }

            try:
                parsed_payload = json.loads(payload_json)
            except json.JSONDecodeError:
                print(f"❌ Error parsing payload JSON for payload_id={payload_id}")
                parsed_payload = {}

            print(parsed_payload['category'])
            print("parsed payload")
            return {"payload": parsed_payload, **metadata}

        except Exception as e:
            print(f"❌ Database error while fetching payload for {payload_id}: {e}")
            return {}
        