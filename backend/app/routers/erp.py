from fastapi import APIRouter
from typing import List
from backend.app.models import ErpBenefit
from backend.app.db import get_session
from sqlmodel import select

router = APIRouter(prefix="/api/v1/erp", tags=["erp"])

@router.get("/benefits", response_model=List[ErpBenefit])
def list_benefits(person_id: str = None):
    with get_session() as s:
        q = select(ErpBenefit)
        if person_id:
            q = q.where(ErpBenefit.person_id == person_id)
        return s.exec(q).all()
