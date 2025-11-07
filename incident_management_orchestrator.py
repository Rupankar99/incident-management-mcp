from models import Incident, IncidentReport, IncidentContext, Ticket
from reporting_agent import ReportingAgent
from ticketing_agent import IntelligentTicketingAgent
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List
import asyncio, json


class IncidentManagementSystem:
    def __init__(self):
        # ❌ REMOVE these (FastMCP handles Jira, Slack, PagerDuty tools internally)
        # self.jira_tool = JiraMCPTool()
        # self.slack_tool = SlackMCPTool()
        # self.pagerduty_tool = PagerDutyMCPTool()

        self.reporting_agent = ReportingAgent()

        # ✅ Just initialize normally — no need to pass tools anymore
        self.ticketing_agent = IntelligentTicketingAgent()

        self.incidents: Dict[str, Incident] = {}
        self.reports: Dict[str, IncidentReport] = {}
        self.tickets: Dict[str, List[Ticket]] = {}
        self.decisions: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        print("=" * 80)
        print("🚀 Intelligent Incident Management System (FastMCP-enabled)")
        print("=" * 80)
        print("✓ MCP tools registered (Jira, Slack, PagerDuty, etc.)")
        print("✓ LLM-driven decision engine ready\n")

    async def process_incident(self, incident: Incident, context: IncidentContext) -> Dict[str, Any]:
        """Process incident with LLM intelligence"""

        print(f"\n{'=' * 80}")
        print(f"📊 Processing: {incident.id}")
        print(f"{'=' * 80}")
        print(f"Title: {incident.title}")
        print(f"Severity: {incident.severity.value.upper()}")
        print(f"Region: {incident.region}")
        print(f"Context: {self._format_context(context)}")
        print(f"{'=' * 80}\n")

        self.incidents[incident.id] = incident

        # Step 1: Generate Report
        print("📝 Step 1: Generating Report...")
        print("-" * 80)

        try:
            report = self.reporting_agent.generate_report(incident)
            self.reports[incident.id] = report
            print(f"✅ Report Generated")
            print(f"   Report: {report}\n")
        except Exception as e:
            print(f"❌ Error generating report: {e}\n")
            return {"status": "error", "message": str(e)}

        # Step 2: LLM Decision + MCP Execution
        print("🎯 Step 2: LLM Making Decision via MCP...")
        print("-" * 80)

        try:
            decision = await self.ticketing_agent.make_decision_and_execute(incident, context)

            print("------------- Decision Output -------------")
            print(decision)

            # ✅ FastMCP returns JSON already — no need to parse manually
            if decision.get("key_factors"):
                print("🔑 Key Factors:")
                for factor in decision["key_factors"]:
                    print(f"   • {factor}")
                print()

            print(f"🎯 Decision (Confidence: {decision.get('confidence_level', 'medium')}):")
            print(f"   • PagerDuty: {'YES' if decision.get('use_pagerduty') else 'NO'}")
            print(f"   • Slack: {decision.get('slack_channel', 'NO') if decision.get('use_slack') else 'NO'}")
            print(f"   • Jira: {decision.get('jira_priority', 'MEDIUM')}")
            print()

            # ✅ If your MCP agent triggers Jira/Slack/PagerDuty directly, 
            # you might not need execute_decision anymore.
            result = {
                "tickets": [],
                "actions": decision.get("actions_taken", []),
                "reasoning": decision.get("reasoning", ""),
                "decision_summary": {
                    "pagerduty": decision.get("use_pagerduty", False),
                    "jira": decision.get("create_jira", False),
                    "slack": decision.get("use_slack", False),
                },
                "llm_decision": decision,
            }

            self.decisions[incident.id] = result

            print("✅ Decision Executed via MCP Tools")
            print("\nActions:")
            for action in result["actions"]:
                print(f"   {action}")
            print()

            return {
                "status": "success",
                "incident_id": incident.id,
                "severity": incident.severity.value,
                "region": incident.region,
                "context": asdict(context),
                "report": asdict(report),
                "tickets": [asdict(t) for t in result["tickets"]],
                "decision": result["decision_summary"],
                "actions": result["actions"],
                "reasoning": result["reasoning"],
                "llm_decision": result["llm_decision"],
            }

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
