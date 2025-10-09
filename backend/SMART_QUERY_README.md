# Smart Query Feature Documentation

## Overview

The Smart Query feature implements intelligent document parsing and entity matching for the Elyris system. It follows a three-tier precedence system for matching entities:

1. **Deterministic SQL Query** - Exact matches based on fixed fields
2. **Semantic Vector Search** - Similarity-based matching using embeddings
3. **Manual Review Queue** - Human adjudication for ambiguous cases

## User Story: Upload Spencer's "Change In Benefits" Form

This implementation supports the complete workflow:

### Step 1: Document Upload

Upload a scanned document (PDF or image) via the API:

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@spencer_benefits_form.pdf" \
  -F "doc_type=benefits_change"
```

### Step 2: Automatic Processing

The system automatically:
1. Extracts text using OCR (pytesseract)
2. Parses document into blocks:
   - **Sender** (organization/location info - typically top left)
   - **Recipient** (person info)
   - **Body** (main document text)
3. Extracts structured data (names, addresses, phone, email)
4. Runs Smart Query to match entities

### Step 3: Smart Query Matching

For each extracted entity (sender Location, recipient Person):

#### Tier 1: Deterministic Match
- **Person**: Match on `first_name` + `last_name` + optional `dob`
- **Location**: Match on `address` + `zip` OR `name` + `city` + `state`
- Returns match only if single exact result

#### Tier 2: Semantic Search
- Computes vector embeddings using sentence-transformers
- Calculates cosine similarity with existing entities
- Returns matches above threshold (default: 0.75)
- If single match found, uses it automatically

#### Tier 3: Manual Review Queue
Triggered when:
- **No results**: Entity not found in system
- **Multiple results**: Ambiguous matches found

Review items are queued with:
- Raw extracted data
- Candidate matches (if any) with similarity scores
- Document context

### Step 4: Manual Review (if needed)

Check pending reviews:

```bash
curl http://localhost:8000/api/review-queue/pending
```

Get review item details:

```bash
curl http://localhost:8000/api/review-queue/{review_id}
```

Resolve by selecting existing entity:

```bash
curl -X POST "http://localhost:8000/api/review-queue/{review_id}/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "resolved_entity_id": "existing-person-id",
    "reviewed_by": "admin@example.com"
  }'
```

Or create new entity:

```bash
curl -X POST "http://localhost:8000/api/review-queue/{review_id}/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "create_new": true,
    "reviewed_by": "admin@example.com",
    "new_entity_data": {
      "first_name": "Spencer",
      "last_name": "Smith",
      "dob": "2010-05-15"
    }
  }'
```

## API Endpoints

### Documents

- `POST /api/documents/upload` - Upload and process document
- `GET /api/documents/{document_id}` - Get document details
- `GET /api/documents/` - List all documents

### Review Queue

- `GET /api/review-queue/pending` - Get pending review items
- `GET /api/review-queue/{review_id}` - Get review item details
- `POST /api/review-queue/{review_id}/resolve` - Resolve review item
- `GET /api/review-queue/stats` - Get queue statistics
- `DELETE /api/review-queue/{review_id}` - Delete review item

## Database Schema

### New Tables

#### DocumentParse
Stores parsed document blocks before entity mapping:
- `sender_text`, `recipient_text`, `body_text` (raw blocks)
- `parsed_sender`, `parsed_recipient` (structured JSON)

#### ReviewQueueItem
Tracks items requiring manual review:
- `entity_type`: "person" or "location"
- `query_type`: "no_results" or "multiple_results"
- `candidate_matches`: JSON with similarity scores
- `status`: "pending", "resolved", or "skipped"

#### Document (updated)
Added fields:
- `raw_text`: Full OCR extracted text
- `location_id`: Link to sender location

## Configuration

### OCR Setup

**Note**: Tesseract OCR must be installed separately:

**Windows**:
```bash
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH or set TESSDATA_PREFIX
```

**Mac/Linux**:
```bash
brew install tesseract  # Mac
sudo apt install tesseract-ocr  # Ubuntu
```

### Similarity Threshold

Adjust in `smart_query.py`:
```python
self.similarity_threshold = 0.75  # Default
```

Lower values = more lenient matching (more false positives)
Higher values = stricter matching (more manual reviews)

## Example Workflow

1. **Spencer's benefits form arrives by mail (4 pages, double-sided)**

2. **Scan using iPhone camera** → `spencer_benefits.pdf`

3. **Upload to system**:
   ```bash
   curl -X POST "http://localhost:8000/api/documents/upload" \
     -F "file=@spencer_benefits.pdf" \
     -F "doc_type=benefits_change"
   ```

4. **System response**:
   ```json
   {
     "success": true,
     "document_id": "abc-123",
     "matched_entities": {
       "sender_location_id": "loc-456",  // Found existing location
       "recipient_person_id": null       // Needs review
     },
     "pending_reviews": 1,
     "parsed_data": {
       "sender": {
         "organization_name": "State Benefits Office",
         "address": "123 Main St",
         "city": "Springfield",
         "state": "IL"
       },
       "recipient": {
         "first_name": "Spencer",
         "last_name": "Smith"
       }
     }
   }
   ```

5. **Review Spencer's record** (multiple matches found):
   ```bash
   curl http://localhost:8000/api/review-queue/pending
   ```
   
   Shows 2 candidates: Spencer Smith (DOB: 2010-05-15) vs Spencer Smith (DOB: 2012-03-20)

6. **Adjudicate** - Select correct Spencer:
   ```bash
   curl -X POST "http://localhost:8000/api/review-queue/{review_id}/resolve" \
     -H "Content-Type: application/json" \
     -d '{
       "resolved_entity_id": "spencer-2010",
       "reviewed_by": "case_worker_jane"
     }'
   ```

7. **Document now fully linked** - ready for querying in unified timeline!

## Future Enhancements

- [ ] Add confidence scores to deterministic matches
- [ ] Implement batch document upload
- [ ] Add webhook notifications for new review items
- [ ] Support for custom entity types
- [ ] Integration with LLM for advanced text extraction
- [ ] Auto-learning from manual review decisions

