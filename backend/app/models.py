from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from datetime import datetime, date
import uuid

# Shared canonical models
class Person(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    first_name: str
    last_name: str
    dob: Optional[date] = None
    legal_flags: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Document(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    doc_type: Optional[str] = None
    file_path: Optional[str] = None
    extracted_fields: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class Event(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    title: str
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    location: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ERP: benefits example
class ErpBenefit(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    benefit_name: str
    status: str = "active"
    renewal_date: Optional[date] = None
    case_worker: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

# CRM: activity example
class CrmProvider(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    contact: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class CrmActivity(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    provider_id: Optional[str] = Field(default=None, foreign_key="crmprovider.id")
    activity_name: str
    recurring_rule: Optional[str] = None
    notes: Optional[str] = None

# EHR: clinical encounter example
class EhrEncounter(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    encounter_date: Optional[datetime] = None
    provider: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    summary: Optional[str] = None
    notes_doc_id: Optional[str] = Field(default=None, foreign_key="document.id")

# LMS: iep goals
class LmsIep(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    iep_year: Optional[int] = None
    team: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    next_review_date: Optional[date] = None
    doc_id: Optional[str] = Field(default=None, foreign_key="document.id")

class LmsGoal(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    iep_id: Optional[str] = Field(default=None, foreign_key="lmsiep.id")
    goal_text: str
    baseline: Optional[str] = None
    target_date: Optional[date] = None
