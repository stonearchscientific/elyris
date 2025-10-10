"""
Evaluation framework for document parsing
Tests documents and generates detailed reports for development iteration
"""
import sys
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.services.document_parser import DocumentParser


class DocumentEvaluator:
    """Evaluates document parsing quality with detailed metrics and reports"""
    
    def __init__(self, use_llm: bool = True):
        self.parser = DocumentParser(use_llm=use_llm)
        self.results = []
    
    def evaluate_document(self, file_path: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single document against expected results
        
        Args:
            file_path: Path to document
            expected: Expected parsing results with keys:
                - sender: {first_name, last_name, organization_name, address, city, state, zip}
                - recipient: {first_name, last_name, address, city, state, zip}
                - doc_type: "letter", "receipt", "quote", etc.
        
        Returns:
            Evaluation result with metrics
        """
        print(f"\n{'='*80}")
        print(f"Evaluating: {Path(file_path).name}")
        print(f"Expected type: {expected.get('doc_type', 'unknown')}")
        print(f"{'='*80}")
        
        # Parse document
        try:
            result = self.parser.parse_document(file_path)
        except Exception as e:
            return {
                "file": file_path,
                "status": "error",
                "error": str(e)
            }
        
        # Compare results
        evaluation = {
            "file": file_path,
            "doc_type": expected.get('doc_type'),
            "status": "evaluated",
            "timestamp": datetime.now().isoformat(),
            "extracted": {
                "sender": result.get('parsed_sender'),
                "recipient": result.get('parsed_recipient')
            },
            "expected": expected,
            "metrics": {}
        }
        
        # Calculate accuracy metrics
        sender_expected = expected.get('sender', {})
        sender_extracted = result.get('parsed_sender', {})
        evaluation['metrics']['sender'] = self._calculate_field_accuracy(
            sender_expected, sender_extracted
        )
        
        recipient_expected = expected.get('recipient', {})
        recipient_extracted = result.get('parsed_recipient', {})
        evaluation['metrics']['recipient'] = self._calculate_field_accuracy(
            recipient_expected, recipient_extracted
        )
        
        # Print summary
        self._print_evaluation(evaluation)
        
        self.results.append(evaluation)
        return evaluation
    
    def _calculate_field_accuracy(self, expected: Dict, extracted: Dict) -> Dict[str, Any]:
        """Calculate precision, recall, and F1 for extracted fields"""
        if not expected:
            return {"note": "No expected data to compare"}
        
        correct = 0
        total_expected = len([v for v in expected.values() if v])
        total_extracted = len([v for v in extracted.values() if v])
        
        for key, expected_value in expected.items():
            if not expected_value:
                continue
            extracted_value = extracted.get(key)
            if extracted_value:
                # Normalize for comparison (case-insensitive, whitespace-tolerant)
                exp_norm = str(expected_value).lower().replace(' ', '')
                ext_norm = str(extracted_value).lower().replace(' ', '')
                if exp_norm == ext_norm or exp_norm in ext_norm or ext_norm in exp_norm:
                    correct += 1
        
        precision = correct / total_extracted if total_extracted > 0 else 0
        recall = correct / total_expected if total_expected > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "correct": correct,
            "total_expected": total_expected,
            "total_extracted": total_extracted,
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "f1": round(f1, 2)
        }
    
    def _print_evaluation(self, eval_result: Dict[str, Any]):
        """Print human-readable evaluation summary"""
        print(f"\n📊 RESULTS:")
        print(f"  Sender:")
        sender_metrics = eval_result['metrics']['sender']
        if 'note' in sender_metrics:
            print(f"    {sender_metrics['note']}")
        else:
            print(f"    Precision: {sender_metrics['precision']:.0%}")
            print(f"    Recall: {sender_metrics['recall']:.0%}")
            print(f"    F1: {sender_metrics['f1']:.2f}")
            print(f"    Extracted: {eval_result['extracted']['sender']}")
        
        print(f"  Recipient:")
        recipient_metrics = eval_result['metrics']['recipient']
        if 'note' in recipient_metrics:
            print(f"    {recipient_metrics['note']}")
        else:
            print(f"    Precision: {recipient_metrics['precision']:.0%}")
            print(f"    Recall: {recipient_metrics['recall']:.0%}")
            print(f"    F1: {recipient_metrics['f1']:.2f}")
            print(f"    Extracted: {eval_result['extracted']['recipient']}")
    
    def generate_report(self, output_file: str = None):
        """Generate comprehensive evaluation report"""
        if not self.results:
            print("No evaluation results to report")
            return
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_documents": len(self.results),
            "results": self.results,
            "summary": {
                "avg_sender_f1": sum(r['metrics']['sender'].get('f1', 0) for r in self.results) / len(self.results),
                "avg_recipient_f1": sum(r['metrics']['recipient'].get('f1', 0) for r in self.results) / len(self.results)
            }
        }
        
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n✅ Report saved to: {output_path}")
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total documents: {report['total_documents']}")
        print(f"Average Sender F1: {report['summary']['avg_sender_f1']:.2f}")
        print(f"Average Recipient F1: {report['summary']['avg_recipient_f1']:.2f}")
        
        return report


if __name__ == "__main__":
    """
    Example usage:
    python -m backend.testing.document_eval
    """
    
    # Define test cases
    test_cases = [
        {
            "file": "backend/data/uploads/spencer_benefits.pdf",
            "doc_type": "letter",
            "expected": {
                "sender": {
                    "organization_name": "Minnesota Department of Human Services",
                    "department": "Legislative Mailing",
                    "address": "PO Box 64989",
                    "city": "St. Paul",
                    "state": "MN",
                    "zip": "55164-0989"
                },
                "recipient": {
                    "first_name": "Spencer",
                    "last_name": "Kennedy",
                    "address": "1085 WILLOW VIEW DR",
                    "city": "ORONO",
                    "state": "MN",
                    "zip": "55356-4304"
                }
            }
        },
        {
            "file": "backend/data/uploads/caleb_receipt.pdf",
            "doc_type": "receipt",
            "expected": {
                "sender": {},  # Receipts typically have no sender
                "recipient": {
                    "first_name": "Caleb",
                    "last_name": "Kennedy",
                    "address": "1085 WILLOW VIEW DR",
                    "city": "ORONO",
                    "state": "MN",
                    "zip": "55356-4304"
                }
            }
        },
        {
            "file": "backend/data/uploads/heather_quote.pdf",
            "doc_type": "quote",
            "expected": {
                "sender": {
                    "first_name": "James",
                    "last_name": "Ostlie",
                    "phone": "(763) 200-4653",
                    "email": "James.Ostlie@davey.com"
                },
                "recipient": {
                    "first_name": "Heather",
                    "last_name": "Holcombe"
                }
            }
        }
    ]
    
    # Run evaluation
    evaluator = DocumentEvaluator(use_llm=True)
    
    for test_case in test_cases:
        file_path = test_case['file']
        if Path(file_path).exists():
            evaluator.evaluate_document(file_path, test_case['expected'])
        else:
            print(f"⚠️ File not found: {file_path}")
    
    # Generate report
    report_path = Path("backend/testing/reports") / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    evaluator.generate_report(str(report_path))

