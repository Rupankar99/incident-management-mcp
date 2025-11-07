from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from datetime import datetime
from models import Incident, IncidentReport
import json

class ReportingAgent:
    """Generate incident reports using LangChain ChatOpenAI"""

    def __init__(self):
        self.llm = ChatOllama(
            model="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.7
        )

    def generate_report(self, incident: Incident) -> IncidentReport:
        # prompt = f"""
        # You are an experienced Site Reliability Engineer (SRE) analyzing an incident.

        # Incident ID: {incident.id}
        # Title: {incident.title}
        # Severity: {incident.severity.value}
        # Service: {incident.service}
        # Region: {incident.region}

        # Description:
        # {incident.incident_text}

        # Components: {', '.join(incident.affected_components)}
        # Metrics: {json.dumps(incident.metrics, indent=2)}

        # Logs:
        # {chr(10).join(incident.logs)}

        # Your task:
        # Generate a concise and professional incident report **in valid JSON format only** (no Markdown, no explanations).

        # The JSON must have this exact structure:

        # {{
        # "executive_summary": "2-3 sentences summarizing the incident impact and context.",
        # "root_cause": "A short hypothesis on what caused the incident.",
        # "recommendations": [
        #     "Recommendation 1",
        #     "Recommendation 2",
        #     "Recommendation 3"
        # ]
        # }}

        # Ensure it is valid JSON — do not include backticks or any text outside the JSON.
        # """


        # Correct LangChain call
        # response = self.llm([HumanMessage(content=prompt)])

        # response = self.llm.invoke([HumanMessage(content=prompt)])
        # print("---------report response---------")
        # print(response)
        # report_text = response.content

        # print("---------report response text---------")
        # print(json.loads(report_text))

        return IncidentReport(
            incident_id="123",
            summary="summary",
            generated_at=datetime.now().isoformat(),
            root_cause="root cause",
            recommendations=["text1"]
        )