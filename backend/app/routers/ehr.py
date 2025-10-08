from fastapi import APIRouter
from typing import List
from backend.app.models import EhrEncounter
from backend.app.db import get_session
from sqlmodel import select

router = APIRouter(prefix="/api/v1/ehr", tags=["ehr"])

@router.get("/encounters", response_model=List[EhrEncounter])
def list_encounters(person_id: str = None):
    with get_session() as s:
        q = select(EhrEncounter)
        if person_id:
            q = q.where(EhrEncounter.person_id == person_id)
        return s.exec(q).all()
