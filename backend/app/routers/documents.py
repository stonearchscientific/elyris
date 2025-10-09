"""Document upload and processing endpoints"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlmodel import Session
from typing import Dict, Any, Optional
from pathlib import Path
import shutil
import json
from datetime import datetime, timezone

from backend.app.db import get_session
from backend.app.models import Document, DocumentParse, ReviewQueueItem
from backend.app.services.document_parser import DocumentParser
from backend.app.services.smart_query import SmartQueryService

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Directory to store uploaded files
UPLOAD_DIR = Path("backend/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
    manual_data: Optional[str] = Form(None),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Upload and process a document with Smart Query
    
    Steps:
    1. Save uploaded file
    2. Extract text via OCR
    3. Parse into sender/recipient/body blocks
    4. Use Smart Query to match entities
    5. Create Document and DocumentParse records
    6. Return processing results
    """
    try:
        # 1. Save uploaded file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Parse manual data if provided
        manual_parsed = None
        if manual_data:
            try:
                manual_parsed = json.loads(manual_data)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid manual_data JSON")
        
        # 3. Parse document (OCR/LLM)
        parser = DocumentParser(use_llm=True)  # Enable LLM parsing
        parsed_data = parser.parse_document(str(file_path))
        
        # 4. Override parsed data with manual data if provided
        if manual_parsed:
            if 'sender' in manual_parsed:
                parsed_data['parsed_sender'] = {**parsed_data['parsed_sender'], **manual_parsed['sender']}
            if 'recipient' in manual_parsed:
                parsed_data['parsed_recipient'] = {**parsed_data['parsed_recipient'], **manual_parsed['recipient']}
        
        # 5. Create Document record
        document = Document(
            doc_type=doc_type,
            file_path=str(file_path),
            raw_text=parsed_data['raw_text']
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        
        # 6. Create DocumentParse record
        doc_parse = DocumentParse(
            document_id=document.id,
            sender_text=parsed_data['sender_text'],
            recipient_text=parsed_data['recipient_text'],
            body_text=parsed_data['body_text'],
            parsed_sender=parsed_data['parsed_sender'],
            parsed_recipient=parsed_data['parsed_recipient']
        )
        session.add(doc_parse)
        session.commit()
        session.refresh(doc_parse)
        
        # 7. Use Smart Query to match entities
        smart_query = SmartQueryService(session)
        
        # Match sender location
        sender_location_id = None
        if parsed_data['parsed_sender']:
            sender_location_id = smart_query.match_location(
                parsed_data['parsed_sender'],
                doc_parse.id
            )
            if sender_location_id:
                document.location_id = sender_location_id
        
        # Match recipient person
        recipient_person_id = None
        if parsed_data['parsed_recipient']:
            recipient_person_id = smart_query.match_person(
                parsed_data['parsed_recipient'],
                doc_parse.id
            )
            if recipient_person_id:
                document.person_id = recipient_person_id
        
        # Update document with matched entities
        session.add(document)
        session.commit()
        session.refresh(document)
        
        # 8. Check for pending reviews
        pending_reviews = session.query(ReviewQueueItem).filter(
            ReviewQueueItem.document_parse_id == doc_parse.id,
            ReviewQueueItem.status == "pending"
        ).all()
        
        return {
            "success": True,
            "document_id": document.id,
            "document_parse_id": doc_parse.id,
            "matched_entities": {
                "sender_location_id": sender_location_id,
                "recipient_person_id": recipient_person_id
            },
            "pending_reviews": len(pending_reviews),
            "parsed_data": {
                "sender": parsed_data['parsed_sender'],
                "recipient": parsed_data['parsed_recipient'],
                "body_preview": parsed_data['body_text'][:200] + "..." if len(parsed_data['body_text']) > 200 else parsed_data['body_text']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/{document_id}")
def get_document(document_id: str, session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Get document details"""
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get associated parse data
    doc_parse = session.query(DocumentParse).filter(
        DocumentParse.document_id == document_id
    ).first()
    
    return {
        "document": document.dict(),
        "parse_data": doc_parse.dict() if doc_parse else None
    }


@router.get("/")
def list_documents(
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """List all documents"""
    documents = session.query(Document).offset(skip).limit(limit).all()
    total = session.query(Document).count()
    
    return {
        "documents": [doc.dict() for doc in documents],
        "total": total,
        "skip": skip,
        "limit": limit
    }

