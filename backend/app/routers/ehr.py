from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from backend.app.models import EhrEncounter
from backend.app.db import get_session

router = APIRouter(prefix="/api/v1/ehr", tags=["ehr"])

@router.get("/encounters", response_model=List[EhrEncounter])
def list_encounters(person_id: str = None, session: Session = Depends(get_session)):
    q = select(EhrEncounter)
    if person_id:
        q = q.where(EhrEncounter.person_id == person_id)
    return session.exec(q).all()
