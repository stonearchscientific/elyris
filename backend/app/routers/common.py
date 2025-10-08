from fastapi import APIRouter, Depends, HTTPException
from typing import List
from backend.app.models import Person, Document, Event
from backend.app.db import get_session
from sqlmodel import select

router = APIRouter(prefix="/api/v1/common", tags=["common"])

@router.get("/persons", response_model=List[Person])
def list_persons():
    with get_session() as s:
        return s.exec(select(Person)).all()

@router.get("/persons/{person_id}", response_model=Person)
def get_person(person_id: str):
    with get_session() as s:
        person = s.get(Person, person_id)
        if not person:
            raise HTTPException(status_code=404, detail="person not found")
        return person

@router.get("/events", response_model=List[Event])
def list_events(person_id: str = None):
    with get_session() as s:
        q = select(Event)
        if person_id:
            q = q.where(Event.person_id == person_id)
        return s.exec(q).all()
