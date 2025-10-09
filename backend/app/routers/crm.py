from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from backend.app.models import CrmActivity
from backend.app.db import get_session

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])

@router.get("/activities", response_model=List[CrmActivity])
def list_activities(person_id: str = None, session: Session = Depends(get_session)):
    q = select(CrmActivity)
    if person_id:
        q = q.where(CrmActivity.person_id == person_id)
    return session.exec(q).all()