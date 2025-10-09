from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import Session, select
from backend.app.models import Person, Document, Event
from backend.app.db import get_session

router = APIRouter(prefix="/api/v1/common", tags=["common"])

@router.get("/persons", response_model=List[Person])
def list_persons(session: Session = Depends(get_session)):
    return session.exec(select(Person)).all()

@router.get("/persons/{person_id}", response_model=Person)
def get_person(person_id: str, session: Session = Depends(get_session)):
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="person not found")
    return person

@router.get("/events", response_model=List[Event])
def list_events(person_id: str = None, session: Session = Depends(get_session)):
    q = select(Event)
    if person_id:
        q = q.where(Event.person_id == person_id)
    return session.exec(q).all()
