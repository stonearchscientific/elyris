"""
Test runner for synthetic documents
Tests each document type and prints results
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables from .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print("Warning: .env file not found")

from backend.app.services.document_parser import DocumentParser

def test_document(file_path: str, expected_type: str) -> Dict[str, Any]:
    """
    Test a single document and print results
    
    Args:
        file_path: Path to test document
        expected_type: Expected doc_type (financial, health, education)
    
    Returns:
        Parsing results
    """
    print(f"\n{'='*80}")
    print(f"Testing: {Path(file_path).name}")
    print(f"Expected type: {expected_type}")
    print(f"{'='*80}")
    
    parser = DocumentParser(use_llm=True)
    
    try:
        result = parser.parse_document(file_path)
        
        # Print results
        print(f"\nRESULTS:")
        print(f"  Doc Type: {result.get('doc_type', 'None')}")
        print(f"\n  Sender (LOCATION):")
        sender = result.get('parsed_sender', {})
        for key, value in sender.items():
            print(f"    {key}: {value}")
        
        print(f"\n  Recipient (PERSON):")
        recipient = result.get('parsed_recipient', {})
        for key, value in recipient.items():
            print(f"    {key}: {value}")
        
        print(f"\n  Body preview: {result.get('body_text', '')[:200]}...")
        
        # Validate
        if result.get('doc_type') == expected_type:
            print(f"\n  ✓ PASS: Correct document type")
        else:
            print(f"\n  ✗ FAIL: Expected '{expected_type}', got '{result.get('doc_type')}'")
        
        return result
        
    except Exception as e:
        print(f"\n  ✗ ERROR: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    """
    Run all synthetic document tests
    """
    test_dir = Path(__file__).parent / "test_documents"
    
    tests = [
        {
            "file": test_dir / "financial_invoice.txt",
            "expected_type": "financial"
        },
        {
            "file": test_dir / "health_benefits_letter.txt",
            "expected_type": "health"
        },
        {
            "file": test_dir / "education_iep_notice.txt",
            "expected_type": "education"
        }
    ]
    
    print("\n" + "="*80)
    print("SYNTHETIC DOCUMENT TESTING")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test["file"].exists():
            result = test_document(str(test["file"]), test["expected_type"])
            if result.get('doc_type') == test["expected_type"]:
                passed += 1
            elif 'error' not in result:
                failed += 1
        else:
            print(f"\n⚠️ File not found: {test['file']}")
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print(f"{'='*80}\n")

