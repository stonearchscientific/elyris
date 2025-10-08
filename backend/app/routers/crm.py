from fastapi import APIRouter
from typing import List
from backend.app.models import CrmActivity
from backend.app.db import get_session
from sqlmodel import select

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])

@router.get("/activities", response_model=List[CrmActivity])
def list_activities(person_id: str = None):
    with get_session() as s:
        q = select(CrmActivity)
        if person_id:
            q = q.where(CrmActivity.person_id == person_id)
        return s.exec(q).all()