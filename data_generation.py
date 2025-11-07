import random
from datetime import datetime
from typing import List, Optional, Tuple
from models import Incident, IncidentContext, IncidentSeverity, IncidentStatus


class SyntheticIncidentGenerator:
    """Generate realistic incident scenarios"""
    
    def __init__(self):
        self.incident_counter = 0
        self.regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-south-1"]
        
    def _get_time_context(self, force_hour: Optional[int] = None) -> tuple:
        hour = force_hour if force_hour is not None else datetime.now().hour
        day_of_week = datetime.now().weekday()
        
        business_hours = 9 <= hour < 18
        peak_traffic = (10 <= hour < 14) or (18 <= hour < 21)
        weekend = day_of_week >= 5
        
        return business_hours, peak_traffic, weekend
    
    def generate_scenarios(self, count: int = 8) -> List[tuple]:
        scenarios = []
        
        templates = [
            {
                "title": "Payment Gateway Complete Outage",
                "incident_text": "Payment processing service completely down. All payment attempts failing with 503 errors.",
                "service": "payment-gateway",
                "severity": IncidentSeverity.CRITICAL,
                "customer_facing": True,
                "revenue_impacting": True,
                "affected_components": ["payment-gateway", "payment-db"],
                "metrics": {"error_rate": 1.0, "requests_per_second": 0},
                "logs": ["[CRITICAL] Payment gateway unreachable", "[ERROR] Database connection pool exhausted"],
                "corrective_actions": ["Restart payment gateway service", "Scale up database"]
            },
            {
                "title": "Database Replication Lag - Internal Dashboard",
                "incident_text": "Analytics database replica experiencing 45-minute lag. Affecting internal dashboards only.",
                "service": "analytics-db",
                "severity": IncidentSeverity.HIGH,
                "customer_facing": False,
                "revenue_impacting": False,
                "affected_components": ["analytics-db-replica"],
                "metrics": {"replication_lag_seconds": 2700},
                "logs": ["[WARN] Replication lag exceeds threshold"],
                "corrective_actions": ["Investigate slow queries", "Promote new replica"]
            },
            {
                "title": "API Rate Limiting - Payment Service",
                "incident_text": "Third-party payment provider rate limiting our API calls. Affecting 25% of checkouts.",
                "service": "payment-integration",
                "severity": IncidentSeverity.MEDIUM,
                "customer_facing": True,
                "revenue_impacting": True,
                "affected_components": ["payment-integration"],
                "metrics": {"error_rate": 0.25},
                "logs": ["[ERROR] Partner API returned 429"],
                "corrective_actions": ["Implement exponential backoff"]
            },
        ]
        
        for i in range(count):
            template = random.choice(templates)
            self.incident_counter += 1
            
            force_hour = [3, 11, 19, 14][i % 4]
            business_hours, peak_traffic, weekend = self._get_time_context(force_hour)
            
            incident = Incident(
                id=f"INC-2025-{str(self.incident_counter).zfill(3)}",
                title=template["title"],
                description=template["incident_text"],
                severity=template["severity"],
                status=IncidentStatus.DETECTED,
                detected_at=datetime.now().isoformat(),
                service=template["service"],
                metrics=template["metrics"],
                logs=template["logs"],
                affected_components=template["affected_components"],
                region=random.choice(self.regions),
                incident_text=template["incident_text"],
                corrective_actions=template["corrective_actions"],
            )
            
            context = IncidentContext(
                business_hours=business_hours,
                peak_traffic_hours=peak_traffic,
                weekend=weekend,
                customer_facing=template["customer_facing"],
                revenue_impacting=template["revenue_impacting"]
            )
            
            scenarios.append((incident, context))
        
        return scenarios