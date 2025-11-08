# from langchain_ollama import ChatOllama
from langchain_core.tools import tool
#from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from datetime import datetime
from models import Ticket, Incident, IncidentReport, IncidentContext
from typing import Any, Dict, List
from dotenv import load_dotenv
import json
from langchain_openai import ChatOpenAI 
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage,ToolMessage
import sqlite3
from datetime import datetime
import httpx

client = httpx.Client(verify=False) 

load_dotenv()

from tools import create_jira_issue, send_slack_alert, create_pagerduty_incident

class IntelligentTicketingAgent:
    """Intelligent agent that autonomously decides which MCP tools to call"""

    def __init__(self):
        self.llm = ChatOpenAI( 
            base_url="https://genailab.tcs.in", 
            model = "azure/genailab-maas-gpt-4o", 
            api_key="sk-vnedOvmLAuyelJh-X1G-tA", 
            http_client = client
        )
        
        # Define the tools the LLM can use
        self.tools = [
            create_jira_issue,
            send_slack_alert,
            create_pagerduty_incident
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
        incident: Incident, 
        context: IncidentContext, 

    ) -> Dict[str, Any]:
        """Let the LLM autonomously decide which MCP tools to call and execute them"""
        
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

Analyze the incident, explain your reasoning, then call the appropriate tools."""

        user_prompt = f"""ANALYZE THIS INCIDENT:

**Incident Details:**
- ID: {incident.id}
- Title: {incident.title}
- Severity: {incident.severity.value}
- Service: {incident.service}
- Region: {incident.region}

**Context:**
{self._describe_context(context)}

**Technical Details:**
- Error Rate: {incident.metrics.get('error_rate', 'N/A')}
- Affected Components: {', '.join(incident.affected_components)}

**Recent Logs:**
{chr(10).join(incident.logs[:3])}

**Questions to Consider:**
1. Would YOU want to be woken up for this at this time?
2. How many customers are affected RIGHT NOW?
3. Can this wait until business hours?
4. Is this causing revenue loss or just potential issues?

Think through your decision and call the appropriate tools now."""

        messages = [
            HumanMessage(content=system_prompt + "\n\n" + user_prompt)
        ]
        
        tickets = []
        actions = []
        tool_calls_made = []
        reasoning_text = ""
        
        print("\n" + "="*80)
        print("🤖 LLM AGENT - Analyzing incident and deciding on actions...")
        print("="*80)
        print(f"\nIncident: {incident.title}")
        print(f"Severity: {incident.severity.value}")
        print(f"Context: {self._describe_context(context)}")
        
        # Agent loop - let LLM make autonomous decisions
        max_iterations = 10
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")
            
            try:
                # Get LLM response with tool binding
                response = self.llm_with_tools.invoke(messages)
                print("-------------------res-----------")
                print(response)
                
                # Check if LLM wants to call tools
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    print(f"🎯 LLM decided to call {len(response.tool_calls)} tool(s)")
                    
                    # Add AI response to conversation
                    messages.append(response)
                    
                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        tool_id = tool_call.get("id", "unknown")
                        
                        print(f"\n  Tool: {tool_name}")
                        print(f"  Args: {json.dumps(tool_args, indent=4)}")
                        
                        # Execute the tool directly based on name
                        try:
                            # Call the actual MCP function
                            if tool_name == "create_jira_issue":
                                result = await create_jira_issue.ainvoke(tool_args)
                            elif tool_name == "send_slack_alert":
                                result = await send_slack_alert.ainvoke(tool_args)
                            elif tool_name == "create_pagerduty_incident":
                                result = await create_pagerduty_incident.ainvoke(tool_args)
                            else:
                                result = {"status": "error", "message": f"Unknown tool: {tool_name}"}
                            
                            print(f"  Result: {result}")
                            
                            # Track the tool call
                            tool_calls_made.append({
                                "tool": tool_name,
                                "arguments": tool_args,
                                "result": result
                            })
                            
                            # Build tickets and actions for response
                            if tool_name == "create_jira_issue" and result.get("status") == "success":
                                tickets.append(Ticket(
                                    ticket_id=result['ticket_id'],
                                    incident_id=incident.id,
                                    platform="Jira",
                                    title=tool_args["summary"],
                                    description=tool_args["description"],
                                    priority=tool_args["priority"],
                                    assignee=None,
                                    created_at=datetime.now().isoformat()
                                ))
                                actions.append(f"✅ Jira: {result['ticket_id']} (Priority: {tool_args['priority']})")
                            
                            elif tool_name == "create_pagerduty_incident" and result.get("status") == "success":
                                tickets.append(Ticket(
                                    ticket_id=result['incident_id'],
                                    incident_id=incident.id,
                                    platform="PagerDuty",
                                    title=tool_args["title"],
                                    description=tool_args["description"],
                                    priority=incident.severity.value,
                                    assignee="On-call Engineer",
                                    created_at=datetime.now().isoformat(),
                                    url=result['url']
                                ))
                                actions.append(f"🚨 PagerDuty: {result['incident_id']} (Urgency: {tool_args['urgency']})")
                            
                            elif tool_name == "send_slack_alert" and result.get("status") == "success":
                                actions.append(f"💬 Slack: {tool_args['channel']}")
                            
                            # Send tool result back to LLM
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
                    # No more tool calls - LLM is done
                    print("\n✅ LLM finished decision-making")
                    if hasattr(response, 'content') and response.content:
                        reasoning_text = response.content
                        print(f"\nReasoning: {reasoning_text[:300]}...")
                    break
            
            except Exception as e:
                print(f"\n❌ Error in agent loop: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print("\n" + "="*80)
        print(f"✅ EXECUTION COMPLETE - {len(tool_calls_made)} MCP tool(s) called")
        print("="*80)
        
        # Add a note if no tools were called
        if not actions:
            actions.append("⚠️ LLM decided no immediate action needed")
        
        return {
            "tickets": tickets,
            "actions": actions,
            "reasoning": [reasoning_text or f"LLM autonomously called {len(tool_calls_made)} tool(s)"],
            "tool_calls": tool_calls_made,
            "decision_summary": {
                "total_tools_called": len(tool_calls_made),
                "tools_used": [tc["tool"] for tc in tool_calls_made],
                "jira_created": any(tc["tool"] == "create_jira_issue" for tc in tool_calls_made),
                "pagerduty_created": any(tc["tool"] == "create_pagerduty_incident" for tc in tool_calls_made),
                "slack_sent": any(tc["tool"] == "send_slack_alert" for tc in tool_calls_made),
                "autonomous_decision": True
            }
        }
