"""Smart Query service for entity matching with precedence: SQL → Semantic → Manual Review"""
from typing import Dict, Any, List, Optional, Tuple
from sqlmodel import Session, select
from sqlalchemy import func
from datetime import date, datetime

from backend.app.models import Person, Location, ReviewQueueItem, DocumentParse
from .logging_config import setup_logger

logger = setup_logger(__name__)

def _parse_date(date_value: Any) -> Optional[date]:
    """
    Parse date from various formats to Python date object
    
    Args:
        date_value: String (YYYY-MM-DD), datetime, or date object
    
    Returns:
        Python date object or None if parsing fails
    """
    if date_value is None:
        return None
    
    if isinstance(date_value, date):
        return date_value
    
    if isinstance(date_value, datetime):
        return date_value.date()
    
    if isinstance(date_value, str):
        try:
            # Try parsing YYYY-MM-DD format
            return datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try parsing MM/DD/YYYY format
                return datetime.strptime(date_value, '%m/%d/%Y').date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_value}")
                return None
    
    return None

# Lazy import for optional dependencies
_SENTENCE_TRANSFORMER_AVAILABLE = None
_NUMPY_AVAILABLE = None

def _check_sentence_transformers():
    global _SENTENCE_TRANSFORMER_AVAILABLE
    if _SENTENCE_TRANSFORMER_AVAILABLE is None:
        try:
            import sentence_transformers
            _SENTENCE_TRANSFORMER_AVAILABLE = True
        except (ImportError, AttributeError) as e:
            print(f"Warning: sentence-transformers not available: {e}")
            _SENTENCE_TRANSFORMER_AVAILABLE = False
    return _SENTENCE_TRANSFORMER_AVAILABLE

def _check_numpy():
    global _NUMPY_AVAILABLE
    if _NUMPY_AVAILABLE is None:
        try:
            import numpy
            _NUMPY_AVAILABLE = True
        except ImportError:
            _NUMPY_AVAILABLE = False
    return _NUMPY_AVAILABLE


class SmartQueryService:
    """
    Implements the Smart Query feature set with three-tier precedence:
    1. Deterministic SQL query
    2. Semantic vector similarity search
    3. Manual review queue for ambiguous cases
    """
    
    def __init__(self, session: Session):
        self.session = session
        # Initialize semantic model (lightweight model for speed)
        self.model = None  # Lazy load
        self.similarity_threshold = 0.75  # Configurable threshold
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize nested data structures to flat strings for SQL queries
        
        Handles cases where parsed data might have nested dicts like:
        {'address': {'street': '...', 'city': '...'}} → {'address': '...', 'city': '...'}
        
        Also handles remapping common variations:
        - 'street_address' → 'address'
        - 'organization_name' → used for 'name' field
        """
        normalized = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # Flatten nested dict - merge into parent
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, str):
                        # Remap street_address to address
                        if nested_key == 'street_address':
                            normalized['address'] = nested_value
                        else:
                            normalized[nested_key] = nested_value
            elif isinstance(value, str):
                # Handle key remapping
                if key == 'street_address':
                    normalized['address'] = value
                elif key == 'organization_name':
                    normalized['name'] = value  # Map to Location.name field
                else:
                    normalized[key] = value
            # Skip non-string, non-dict values
        
        return normalized
    
    def _get_model(self):
        """Lazy load the sentence transformer model"""
        if not _check_sentence_transformers():
            raise RuntimeError(
                "sentence-transformers not available. Install with: pip install sentence-transformers"
            )
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        return self.model
    
    def _compute_embedding(self, text: str):
        """Compute vector embedding for text"""
        if not _check_numpy():
            raise RuntimeError("numpy not available")
        model = self._get_model()
        return model.encode(text, convert_to_numpy=True)
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        if not _check_numpy():
            raise RuntimeError("numpy not available")
        import numpy as np
        
        emb1 = self._compute_embedding(text1)
        emb2 = self._compute_embedding(text2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    # ===== PERSON MATCHING =====
    
    def match_person_deterministic(self, data: Dict[str, Any]) -> Optional[Person]:
        """
        Deterministic SQL query for exact person match
        
        Args:
            data: Dict with keys like 'first_name', 'last_name', 'dob'
        
        Returns:
            Person object if exact match found, None otherwise
        """
        query = select(Person)
        
        # Build query based on available fields (case-insensitive)
        if 'first_name' in data and 'last_name' in data:
            # Use case-insensitive comparison via func.lower()
            from sqlalchemy import func
            query = query.where(
                func.lower(Person.first_name) == data['first_name'].lower(),
                func.lower(Person.last_name) == data['last_name'].lower()
            )
            
            # If DOB is available, use it for stronger match
            if 'dob' in data and data['dob']:
                query = query.where(Person.dob == data['dob'])
            
            results = self.session.exec(query).all()
            
            # Return only if single exact match
            if len(results) == 1:
                return results[0]
        
        return None
    
    def match_person_semantic(self, data: Dict[str, Any]) -> List[Tuple[Person, float]]:
        """
        Semantic search for person matches using vector similarity
        
        Returns:
            List of (Person, similarity_score) tuples above threshold
        """
        # Skip semantic search if dependencies not available
        if not _check_sentence_transformers() or not _check_numpy():
            print("Warning: Semantic search unavailable, skipping to manual review")
            return []
        
        # Create search text from available fields
        search_parts = []
        if 'first_name' in data:
            search_parts.append(data['first_name'])
        if 'last_name' in data:
            search_parts.append(data['last_name'])
        
        if not search_parts:
            return []
        
        search_text = ' '.join(search_parts)
        
        # Get all persons and compute similarity
        all_persons = self.session.exec(select(Person)).all()
        matches = []
        
        try:
            for person in all_persons:
                person_text = f"{person.first_name} {person.last_name}"
                similarity = self._compute_similarity(search_text, person_text)
                
                if similarity >= self.similarity_threshold:
                    matches.append((person, similarity))
            
            # Sort by similarity descending
            matches.sort(key=lambda x: x[1], reverse=True)
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
        
        return matches
    
    def match_person(self, data: Dict[str, Any], document_parse_id: str) -> Optional[str]:
        """
        Main entry point for person matching with full precedence system
        
        Returns:
            person_id if match found/created, None if queued for review
        """
        # Normalize data to flatten nested structures
        data = self._normalize_data(data)
        
        # Step 1: Try deterministic match
        person = self.match_person_deterministic(data)
        if person:
            return person.id
        
        # Step 2: Try semantic search
        semantic_matches = self.match_person_semantic(data)
        
        if len(semantic_matches) == 1:
            # Single semantic match - use it
            return semantic_matches[0][0].id
        elif len(semantic_matches) == 0:
            # No results - create new person
            if data.get('first_name') and data.get('last_name'):
                # Parse DOB if present (convert string to date object)
                dob_value = _parse_date(data.get('dob'))
                
                new_person = Person(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    dob=dob_value
                )
                self.session.add(new_person)
                self.session.commit()
                self.session.refresh(new_person)
                logger.info(f"[CREATE] New Person: {new_person.first_name} {new_person.last_name} (ID: {new_person.id})")
                return new_person.id
            else:
                # Insufficient data to create person - queue for review
                self._queue_for_review(
                    document_parse_id=document_parse_id,
                    entity_type="person",
                    query_type="no_results",
                    raw_data=data,
                    candidates=[]
                )
                return None
        else:
            # Multiple results - queue for manual review with candidates
            candidates = [
                {"id": p.id, "first_name": p.first_name, "last_name": p.last_name, "similarity": score}
                for p, score in semantic_matches[:5]  # Top 5 candidates
            ]
            self._queue_for_review(
                document_parse_id=document_parse_id,
                entity_type="person",
                query_type="multiple_results",
                raw_data=data,
                candidates=candidates
            )
            return None
    
    # ===== LOCATION MATCHING =====
    
    def match_location_deterministic(self, data: Dict[str, Any]) -> Optional[Location]:
        """
        Deterministic SQL query for exact location match
        
        Args:
            data: Dict with keys like 'name', 'address', 'city', 'state', 'zip'
        
        Returns:
            Location object if exact match found, None otherwise
        """
        query = select(Location)
        
        # Try matching on multiple fields for high confidence
        if 'address' in data and 'zip' in data:
            # Address + ZIP is a strong unique identifier
            query = query.where(
                Location.address == data['address'],
                Location.zip == data['zip']
            )
            results = self.session.exec(query).all()
            if len(results) == 1:
                return results[0]
        
        # Try name + city + state
        if 'organization_name' in data and 'city' in data and 'state' in data:
            query = select(Location).where(
                Location.name == data['organization_name'],
                Location.city == data['city'],
                Location.state == data['state']
            )
            results = self.session.exec(query).all()
            if len(results) == 1:
                return results[0]
        
        return None
    
    def match_location_semantic(self, data: Dict[str, Any]) -> List[Tuple[Location, float]]:
        """
        Semantic search for location matches using vector similarity
        
        Returns:
            List of (Location, similarity_score) tuples above threshold
        """
        # Skip semantic search if dependencies not available
        if not _check_sentence_transformers() or not _check_numpy():
            print("Warning: Semantic search unavailable, skipping to manual review")
            return []
        
        # Create search text from available fields
        search_parts = []
        if 'organization_name' in data:
            search_parts.append(data['organization_name'])
        if 'address' in data:
            search_parts.append(data['address'])
        if 'city' in data:
            search_parts.append(data['city'])
        if 'state' in data:
            search_parts.append(data['state'])
        
        if not search_parts:
            return []
        
        search_text = ' '.join(search_parts)
        
        # Get all locations and compute similarity
        all_locations = self.session.exec(select(Location)).all()
        matches = []
        
        try:
            for location in all_locations:
                location_parts = [location.name]
                if location.address:
                    location_parts.append(location.address)
                if location.city:
                    location_parts.append(location.city)
                if location.state:
                    location_parts.append(location.state)
                
                location_text = ' '.join(location_parts)
                similarity = self._compute_similarity(search_text, location_text)
                
                if similarity >= self.similarity_threshold:
                    matches.append((location, similarity))
            
            # Sort by similarity descending
            matches.sort(key=lambda x: x[1], reverse=True)
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
        
        return matches
    
    def match_location(self, data: Dict[str, Any], document_parse_id: str) -> Optional[str]:
        """
        Main entry point for location matching with full precedence system
        
        Returns:
            location_id if match found/created, None if queued for review
        """
        # Normalize data to flatten nested structures
        data = self._normalize_data(data)
        
        # Step 1: Try deterministic match
        location = self.match_location_deterministic(data)
        if location:
            return location.id
        
        # Step 2: Try semantic search
        semantic_matches = self.match_location_semantic(data)
        
        if len(semantic_matches) == 1:
            # Single semantic match - use it
            return semantic_matches[0][0].id
        elif len(semantic_matches) == 0:
            # No results - queue for manual review
            self._queue_for_review(
                document_parse_id=document_parse_id,
                entity_type="location",
                query_type="no_results",
                raw_data=data,
                candidates=[]
            )
            return None
        else:
            # Multiple results - queue for manual review with candidates
            candidates = [
                {
                    "id": loc.id,
                    "name": loc.name,
                    "address": loc.address,
                    "city": loc.city,
                    "state": loc.state,
                    "similarity": score
                }
                for loc, score in semantic_matches[:5]  # Top 5 candidates
            ]
            self._queue_for_review(
                document_parse_id=document_parse_id,
                entity_type="location",
                query_type="multiple_results",
                raw_data=data,
                candidates=candidates
            )
            return None
    
    # ===== REVIEW QUEUE MANAGEMENT =====
    
    def _queue_for_review(
        self,
        document_parse_id: str,
        entity_type: str,
        query_type: str,
        raw_data: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ):
        """Add item to manual review queue"""
        review_item = ReviewQueueItem(
            document_parse_id=document_parse_id,
            entity_type=entity_type,
            query_type=query_type,
            raw_data=raw_data,
            candidate_matches={"candidates": candidates} if candidates else None,
            status="pending"
        )
        self.session.add(review_item)
        self.session.commit()
    
    def get_pending_reviews(self) -> List[ReviewQueueItem]:
        """Get all pending review items"""
        return self.session.exec(
            select(ReviewQueueItem).where(ReviewQueueItem.status == "pending")
        ).all()
    
    def resolve_review(
        self,
        review_id: str,
        resolved_entity_id: Optional[str],
        reviewed_by: str,
        create_new: bool = False,
        new_entity_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Resolve a review queue item
        
        Args:
            review_id: ID of review item
            resolved_entity_id: ID of selected entity (if matched to existing)
            reviewed_by: User ID or name of reviewer
            create_new: Whether to create a new entity
            new_entity_data: Data for new entity if create_new=True
        
        Returns:
            Entity ID (existing or newly created)
        """
        review_item = self.session.get(ReviewQueueItem, review_id)
        if not review_item:
            raise ValueError(f"Review item {review_id} not found")
        
        entity_id = resolved_entity_id
        
        # Create new entity if requested
        if create_new and new_entity_data:
            if review_item.entity_type == "person":
                person = Person(**new_entity_data)
                self.session.add(person)
                self.session.commit()
                self.session.refresh(person)
                entity_id = person.id
            elif review_item.entity_type == "location":
                location = Location(**new_entity_data)
                self.session.add(location)
                self.session.commit()
                self.session.refresh(location)
                entity_id = location.id
        
        # Update review item
        from datetime import datetime, timezone
        review_item.status = "resolved"
        review_item.resolved_entity_id = entity_id
        review_item.reviewed_by = reviewed_by
        review_item.reviewed_at = datetime.now(timezone.utc)
        
        self.session.add(review_item)
        self.session.commit()
        
        return entity_id

