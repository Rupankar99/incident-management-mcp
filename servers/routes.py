from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from model import IncidentCreate
import db_ops


router = APIRouter()


@router.post("/incidents", status_code=201)
def create_incident(payload: IncidentCreate):
    data = payload.dict()
    try:
        datetime.fromisoformat(payload.created_at.replace('Z', '+00:00'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid created_at timestamp")
    try:
        db_ops.add_incident(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "ok", "id": payload.id}


@router.post("/incidents/bulk", status_code=201)
def create_incidents_bulk(payload: List[IncidentCreate]):
    data = [p.dict() for p in payload]
    db_ops.add_bulk(data)
    return {"status": "ok", "count": len(data)}


@router.get("/incidents")
def list_incidents(limit: int = 100):
    return 
    #return db_ops.list_incidents(limit)