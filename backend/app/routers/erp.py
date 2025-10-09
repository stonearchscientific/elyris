from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from backend.app.models import ErpBenefit
from backend.app.db import get_session

router = APIRouter(prefix="/api/v1/erp", tags=["erp"])

@router.get("/benefits", response_model=List[ErpBenefit])
def list_benefits(person_id: str = None, session: Session = Depends(get_session)):
    q = select(ErpBenefit)
    if person_id:
        q = q.where(ErpBenefit.person_id == person_id)
    return session.exec(q).all()
