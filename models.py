from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict

class IncidentSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(Enum):
    DETECTED = "detected"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    detected_at: str
    service: str
    metrics: Dict[str, Any]
    logs: List[str]
    affected_components: List[str]
    region: str
    incident_text: str
    corrective_actions: List[str]
    root_cause: Optional[str] = None
    resolution: Optional[str] = None


@dataclass
class IncidentContext:
    business_hours: bool
    peak_traffic_hours: bool
    weekend: bool
    customer_facing: bool
    revenue_impacting: bool


@dataclass
class IncidentReport:
    incident_id: str
    summary: str
    root_cause: str
    recommendations: List[str]
    generated_at: str


@dataclass
class Ticket:
    ticket_id: str
    incident_id: str
    platform: str
    title: str
    description: str
    priority: str
    assignee: Optional[str]
    created_at: str
    url: Optional[str] = None