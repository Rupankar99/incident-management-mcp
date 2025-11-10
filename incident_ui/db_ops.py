from datetime import datetime
from typing import List, Dict

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

    # Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add the formatter to the handler
ch.setFormatter(formatter)

    # Add the handler to the logger
logger.addHandler(ch)



INCIDENTS: List[Dict] = []


def add_incident(data: Dict):
    if any(i['id'] == data['id'] for i in INCIDENTS):
        raise ValueError("Incident already exists")
    if not data.get("last_updated"):
        data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        INCIDENTS.append(data)


def add_bulk(incidents: List[Dict]):
    for d in incidents:
        if not any(i['id'] == d['id'] for i in INCIDENTS):
            if not d.get("last_updated"):
                d["last_updated"] = datetime.utcnow().isoformat() + "Z"
            INCIDENTS.append(d)


def list_incidents(limit: int = 100):
    logger.info(f"Get call invoked")
    #return sorted(INCIDENTS, key=lambda x: x['created_at'], reverse=True)[:limit]