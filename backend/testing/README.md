# Document Parsing Evaluation Framework

This directory contains tools for evaluating and testing document parsing quality during development.

## Overview

The evaluation framework allows you to:
- Systematically test document parsing against expected results
- Generate detailed metrics (precision, recall, F1 scores)
- Track parsing quality across development iterations
- Identify regressions when making changes

## Usage

### Running Evaluations

```bash
# From the elyris directory
cd backend
python -m testing.document_eval
```

This will:
1. Test all documents in the `test_cases` list
2. Print detailed results for each document
3. Generate a JSON report in `testing/reports/`

### Adding Test Cases

Edit `testing/document_eval.py` and add to the `test_cases` list:

```python
{
    "file": "backend/data/uploads/your_document.pdf",
    "doc_type": "letter",  # or "receipt", "quote", "invoice", etc.
    "expected": {
        "sender": {
            "organization_name": "Organization Name",
            "address": "123 Main St",
            "city": "City",
            "state": "ST",
            "zip": "12345"
        },
        "recipient": {
            "first_name": "John",
            "last_name": "Doe",
            "address": "456 Oak St",
            "city": "Town",
            "state": "ST",
            "zip": "67890"
        }
    }
}
```

### Environment Variables for Testing

```bash
# Enable detailed debug output in logs
DEBUG_DOCUMENT_PARSING=true

# Disable LLM validation (allows hallucinations for testing)
VALIDATE_LLM_EXTRACTIONS=false
```

## Metrics

The evaluator calculates:
- **Precision**: Of the fields extracted, how many were correct?
- **Recall**: Of the expected fields, how many were found?
- **F1 Score**: Harmonic mean of precision and recall

## Report Format

Reports are saved as JSON with:
```json
{
  "timestamp": "2025-10-10T12:00:00",
  "total_documents": 3,
  "results": [
    {
      "file": "...",
      "doc_type": "letter",
      "extracted": {"sender": {...}, "recipient": {...}},
      "expected": {"sender": {...}, "recipient": {...}},
      "metrics": {
        "sender": {"precision": 1.0, "recall": 0.83, "f1": 0.91},
        "recipient": {"precision": 1.0, "recall": 1.0, "f1": 1.0}
      }
    }
  ],
  "summary": {
    "avg_sender_f1": 0.91,
    "avg_recipient_f1": 0.95
  }
}
```

## Logs

Detailed parsing logs are written to `backend/logs/document_parsing_YYYYMMDD.log` with:
- Text extraction steps
- LLM calls and responses
- Block detection logic
- Field extraction details
- Validation checks

## Best Practices

1. **Run before commits**: Verify parsing quality hasn't regressed
2. **Update test cases**: Add new document types as they're encountered
3. **Review logs**: Check `backend/logs/` for detailed traces
4. **Compare reports**: Track F1 scores across iterations


