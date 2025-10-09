from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from backend.app.models import LmsGoal, LmsIep
from backend.app.db import get_session

router = APIRouter(prefix="/api/v1/lms", tags=["lms"])

@router.get("/ieps", response_model=List[LmsIep])
def list_ieps(person_id: str = None, session: Session = Depends(get_session)):
    q = select(LmsIep)
    if person_id:
        q = q.where(LmsIep.person_id == person_id)
    return session.exec(q).all()

@router.get("/goals", response_model=List[LmsGoal])
def list_goals(iep_id: str = None, session: Session = Depends(get_session)):
    q = select(LmsGoal)
    if iep_id:
        q = q.where(LmsGoal.iep_id == iep_id)
    return session.exec(q).all()
