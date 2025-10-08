from fastapi import APIRouter
from typing import List
from backend.app.models import LmsGoal, LmsIep
from backend.app.db import get_session
from sqlmodel import select

router = APIRouter(prefix="/api/v1/lms", tags=["lms"])

@router.get("/ieps", response_model=List[LmsIep])
def list_ieps(person_id: str = None):
    with get_session() as s:
        q = select(LmsIep)
        if person_id:
            q = q.where(LmsIep.person_id == person_id)
        return s.exec(q).all()

@router.get("/goals", response_model=List[LmsGoal])
def list_goals(iep_id: str = None):
    with get_session() as s:
        q = select(LmsGoal)
        if iep_id:
            q = q.where(LmsGoal.iep_id == iep_id)
        return s.exec(q).all()
