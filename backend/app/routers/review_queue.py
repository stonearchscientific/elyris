"""Review queue endpoints for Smart Query manual adjudication"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from backend.app.db import get_session
from backend.app.models import ReviewQueueItem, Person, Location
from backend.app.services.smart_query import SmartQueryService

router = APIRouter(prefix="/api/review-queue", tags=["review-queue"])


class ResolveReviewRequest(BaseModel):
    """Request model for resolving a review item"""
    resolved_entity_id: Optional[str] = None
    reviewed_by: str
    create_new: bool = False
    new_entity_data: Optional[Dict[str, Any]] = None


@router.get("/pending")
def get_pending_reviews(
    entity_type: Optional[str] = None,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get all pending review items
    
    Args:
        entity_type: Optional filter by 'person' or 'location'
    """
    query = select(ReviewQueueItem).where(ReviewQueueItem.status == "pending")
    
    if entity_type:
        query = query.where(ReviewQueueItem.entity_type == entity_type)
    
    items = session.exec(query).all()
    
    return {
        "pending_items": [
            {
                "id": item.id,
                "document_parse_id": item.document_parse_id,
                "entity_type": item.entity_type,
                "query_type": item.query_type,
                "raw_data": item.raw_data,
                "candidate_matches": item.candidate_matches,
                "created_at": item.created_at.isoformat()
            }
            for item in items
        ],
        "total": len(items)
    }


@router.get("/{review_id}")
def get_review_item(
    review_id: str,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get detailed information about a review item"""
    review_item = session.get(ReviewQueueItem, review_id)
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found")
    
    # Get related document parse data
    from backend.app.models import DocumentParse, Document
    doc_parse = session.get(DocumentParse, review_item.document_parse_id)
    document = None
    if doc_parse:
        document = session.get(Document, doc_parse.document_id)
    
    return {
        "review_item": {
            "id": review_item.id,
            "document_parse_id": review_item.document_parse_id,
            "entity_type": review_item.entity_type,
            "query_type": review_item.query_type,
            "raw_data": review_item.raw_data,
            "candidate_matches": review_item.candidate_matches,
            "status": review_item.status,
            "created_at": review_item.created_at.isoformat()
        },
        "document_context": {
            "document_id": document.id if document else None,
            "doc_type": document.doc_type if document else None,
            "sender_text": doc_parse.sender_text if doc_parse else None,
            "recipient_text": doc_parse.recipient_text if doc_parse else None,
        }
    }


@router.post("/{review_id}/resolve")
def resolve_review(
    review_id: str,
    request: ResolveReviewRequest,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Resolve a review queue item by selecting an entity or creating a new one
    
    Options:
    1. Select existing entity: provide resolved_entity_id
    2. Create new entity: set create_new=True and provide new_entity_data
    3. Skip/dismiss: just mark as resolved without entity
    """
    try:
        smart_query = SmartQueryService(session)
        
        entity_id = smart_query.resolve_review(
            review_id=review_id,
            resolved_entity_id=request.resolved_entity_id,
            reviewed_by=request.reviewed_by,
            create_new=request.create_new,
            new_entity_data=request.new_entity_data
        )
        
        return {
            "success": True,
            "review_id": review_id,
            "resolved_entity_id": entity_id,
            "message": "Review item resolved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving review: {str(e)}")


@router.get("/stats")
def get_review_stats(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Get statistics about the review queue"""
    
    # Count by status
    pending_count = session.exec(
        select(ReviewQueueItem).where(ReviewQueueItem.status == "pending")
    ).all()
    
    resolved_count = session.exec(
        select(ReviewQueueItem).where(ReviewQueueItem.status == "resolved")
    ).all()
    
    # Count by entity type (pending only)
    person_pending = sum(1 for item in pending_count if item.entity_type == "person")
    location_pending = sum(1 for item in pending_count if item.entity_type == "location")
    
    # Count by query type (pending only)
    no_results = sum(1 for item in pending_count if item.query_type == "no_results")
    multiple_results = sum(1 for item in pending_count if item.query_type == "multiple_results")
    
    return {
        "total_pending": len(pending_count),
        "total_resolved": len(resolved_count),
        "by_entity_type": {
            "person": person_pending,
            "location": location_pending
        },
        "by_query_type": {
            "no_results": no_results,
            "multiple_results": multiple_results
        }
    }


@router.delete("/{review_id}")
def delete_review_item(
    review_id: str,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Delete a review queue item (admin function)"""
    review_item = session.get(ReviewQueueItem, review_id)
    if not review_item:
        raise HTTPException(status_code=404, detail="Review item not found")
    
    session.delete(review_item)
    session.commit()
    
    return {
        "success": True,
        "message": f"Review item {review_id} deleted"
    }

