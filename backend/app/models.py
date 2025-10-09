from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from datetime import datetime, date, timezone
import uuid

# Shared canonical models
class Person(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    first_name: str
    last_name: str
    dob: Optional[date] = None
    legal_flags: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GlobalPosition(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    lat: float
    lng: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Location(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    global_position_id: Optional[str] = Field(default=None, foreign_key="globalposition.id")
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Document(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    location_id: Optional[str] = Field(default=None, foreign_key="location.id")
    doc_type: Optional[str] = None
    file_path: Optional[str] = None
    raw_text: Optional[str] = None  # OCR extracted text
    extracted_fields: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DocumentParse(SQLModel, table=True):
    """Stores parsed data blocks from documents before mapping to entities"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="document.id")
    sender_text: Optional[str] = None  # Raw text of sender info
    recipient_text: Optional[str] = None  # Raw text of recipient info
    body_text: Optional[str] = None  # Main document text
    parsed_sender: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    parsed_recipient: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReviewQueueItem(SQLModel, table=True):
    """Tracks entities requiring manual review for Smart Query"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_parse_id: str = Field(foreign_key="documentparse.id")
    entity_type: str  # "person", "location"
    query_type: str  # "no_results", "multiple_results"
    candidate_matches: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    raw_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    status: str = "pending"  # pending, resolved, skipped
    resolved_entity_id: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Event(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id")
    title: str
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    location: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
