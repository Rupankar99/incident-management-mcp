from models import Incident, IncidentReport, IncidentContext, Ticket
from reporting import ReportingAgent
from transport import IntelligentTicketingAgent
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
