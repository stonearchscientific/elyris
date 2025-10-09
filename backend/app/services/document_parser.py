"""Document parsing service with OCR and text extraction"""
import re
import os
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

# Lazy imports for optional OCR dependencies
_PIL_AVAILABLE = None
_PYTESSERACT_AVAILABLE = None
_PDF2IMAGE_AVAILABLE = None

def _check_pil():
    global _PIL_AVAILABLE
    if _PIL_AVAILABLE is None:
        try:
            from PIL import Image
            _PIL_AVAILABLE = True
        except ImportError:
            _PIL_AVAILABLE = False
    return _PIL_AVAILABLE

def _check_pytesseract():
    global _PYTESSERACT_AVAILABLE
    if _PYTESSERACT_AVAILABLE is None:
        try:
            import pytesseract
            _PYTESSERACT_AVAILABLE = True
        except ImportError:
            _PYTESSERACT_AVAILABLE = False
    return _PYTESSERACT_AVAILABLE

def _check_pdf2image():
    global _PDF2IMAGE_AVAILABLE
    if _PDF2IMAGE_AVAILABLE is None:
        try:
            from pdf2image import convert_from_path
            _PDF2IMAGE_AVAILABLE = True
        except ImportError:
            _PDF2IMAGE_AVAILABLE = False
    return _PDF2IMAGE_AVAILABLE

def _check_pypdf2():
    """Check if PyPDF2 is available for text extraction"""
    try:
        import PyPDF2
        return True
    except ImportError:
        return False

class DocumentParser:
    """Handles OCR and structured text extraction from documents"""
    
    def __init__(self, use_llm: bool = True):
        # Common patterns for extracting structured data
        self.address_pattern = re.compile(
            r'(\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|blvd|boulevard|way|court|ct|place|pl))'
            r'[,\s]+([a-zA-Z\s]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)',
            re.IGNORECASE
        )
        self.phone_pattern = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.name_pattern = re.compile(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$', re.MULTILINE)
        
        # LLM parser (optional)
        self.llm_parser = None
        
        if use_llm:
            try:
                from backend.app.services.llm_parser import LLMDocumentParser
                self.llm_parser = LLMDocumentParser()
                if self.llm_parser.available:
                    print("✅ LLM-based parsing enabled", flush=True)
            except Exception as e:
                print(f"⚠️ Could not initialize LLM parser: {e}", flush=True)
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        if not _check_pil():
            raise ValueError("PIL/Pillow not installed. Install with: pip install pillow")
        if not _check_pytesseract():
            raise ValueError("pytesseract not installed. Install with: pip install pytesseract")
        
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            raise ValueError(f"Error extracting text from image: {str(e)}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF - tries direct text extraction first, falls back to OCR
        
        Strategy:
        1. Try PyPDF2 for direct text extraction (fast, works for text-based PDFs)
        2. If no text found or PyPDF2 unavailable, use OCR (slower, works for scanned PDFs)
        """
        # Try direct text extraction first
        if _check_pypdf2():
            try:
                import PyPDF2
                
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    
                    for i, page in enumerate(pdf_reader.pages):
                        page_text = page.extract_text()
                        if page_text.strip():  # If there's actual text
                            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                    
                    if text_parts:
                        extracted_text = "\n\n".join(text_parts)
                        print(f"✓ Extracted {len(extracted_text)} chars from PDF using direct text extraction")
                        return extracted_text
                    else:
                        print("⚠ No embedded text found in PDF, falling back to OCR...")
            except Exception as e:
                print(f"⚠ Direct PDF text extraction failed ({str(e)}), trying OCR...")
        
        # Fall back to OCR
        if not _check_pdf2image():
            raise ValueError("pdf2image not installed. Install with: pip install pdf2image")
        if not _check_pytesseract():
            raise ValueError("pytesseract not installed. Install with: pip install pytesseract")
        
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            print("🔍 Converting PDF to images for OCR...")
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            # Extract text from each page
            full_text = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                full_text.append(f"--- Page {i+1} ---\n{text}")
                print(f"  Processed page {i+1}/{len(images)}")
            
            result = "\n\n".join(full_text)
            print(f"✓ OCR complete: extracted {len(result)} chars")
            return result
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    def parse_document_blocks(self, text: str) -> Tuple[Optional[str], Optional[str], str]:
        """
        Parse document into sender, recipient, and body sections
        Uses LLM if available, falls back to heuristic parsing
        
        Returns:
            Tuple of (sender_text, recipient_text, body_text)
        """
        # Try LLM parsing first
        if self.llm_parser and self.llm_parser.available:
            sender, recipient, body = self.llm_parser.parse_document_with_llm(text)
            if sender or recipient:  # If LLM found something, use it
                return sender, recipient, body
            print("⚠️ LLM didn't find sender/recipient, falling back to heuristics")
        
        # Fall back to heuristic parsing
        lines = text.strip().split('\n')
        
        # Heuristic: First non-empty block (top ~10 lines) is often sender
        sender_text = None
        recipient_text = None
        body_start = 0
        
        # Extract first text block as potential sender (top left corner)
        first_block = []
        for i, line in enumerate(lines[:15]):
            line = line.strip()
            if line:
                first_block.append(line)
                if len(first_block) >= 5:  # Take first 5 non-empty lines
                    sender_text = '\n'.join(first_block)
                    body_start = i + 1
                    break
        
        # Look for recipient indicators ("To:", name followed by address)
        remaining_lines = lines[body_start:]
        recipient_block = []
        found_recipient = False
        
        for i, line in enumerate(remaining_lines[:20]):
            line = line.strip()
            if not found_recipient and ('to:' in line.lower() or 're:' in line.lower()):
                found_recipient = True
                continue
            
            if found_recipient and line:
                recipient_block.append(line)
                if len(recipient_block) >= 4:  # Take next 4 lines after indicator
                    recipient_text = '\n'.join(recipient_block)
                    body_start += i + 1
                    break
        
        # Rest is body text
        body_text = '\n'.join(lines[body_start:]).strip()
        
        return sender_text, recipient_text, body_text
    
    def extract_structured_data(self, text: str, block_type: str = "unknown") -> Dict[str, Any]:
        """
        Extract structured fields from text block
        Uses LLM if available for better accuracy
        
        Args:
            text: Raw text block
            block_type: "sender" or "recipient" for LLM context
        """
        # Try LLM extraction first
        if self.llm_parser and self.llm_parser.available and text:
            llm_data = self.llm_parser.extract_structured_with_llm(text, block_type)
            if llm_data:  # If LLM found fields, use them
                return llm_data
        
        # Fall back to regex patterns
        data = {}
        
        # Extract addresses
        addresses = self.address_pattern.findall(text)
        if addresses:
            # Take the first match: (street, city, state, zip)
            street, city, state, zip_code = addresses[0]
            data['address'] = street.strip()
            data['city'] = city.strip()
            data['state'] = state.strip()
            data['zip'] = zip_code.strip()
        
        # Extract phone numbers
        phones = self.phone_pattern.findall(text)
        if phones:
            data['phone'] = phones[0]
        
        # Extract emails
        emails = self.email_pattern.findall(text)
        if emails:
            data['email'] = emails[0]
        
        # Extract potential names (lines with capitalized words)
        names = self.name_pattern.findall(text)
        if names:
            # Try to parse first and last name
            name_parts = names[0].split()
            if len(name_parts) >= 2:
                data['first_name'] = name_parts[0]
                data['last_name'] = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                data['first_name'] = name_parts[0]
        
        # Extract organization name (heuristic: first line if no name found)
        if 'first_name' not in data:
            first_line = text.split('\n')[0].strip()
            if first_line and not any(char.isdigit() for char in first_line):
                data['organization_name'] = first_line
        
        return data
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        Main entry point: parse a document file
        
        Returns dictionary with:
            - raw_text: Full OCR text
            - sender_text: Raw sender block
            - recipient_text: Raw recipient block
            - body_text: Document body
            - parsed_sender: Structured sender data
            - parsed_recipient: Structured recipient data
        """
        path = Path(file_path)
        
        # Extract text based on file type
        if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            raw_text = self.extract_text_from_image(file_path)
        elif path.suffix.lower() == '.pdf':
            raw_text = self.extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        # Parse into blocks
        sender_text, recipient_text, body_text = self.parse_document_blocks(raw_text)
        
        # Extract structured data
        parsed_sender = self.extract_structured_data(sender_text, "sender") if sender_text else {}
        parsed_recipient = self.extract_structured_data(recipient_text, "recipient") if recipient_text else {}
        
        return {
            'raw_text': raw_text,
            'sender_text': sender_text,
            'recipient_text': recipient_text,
            'body_text': body_text,
            'parsed_sender': parsed_sender,
            'parsed_recipient': parsed_recipient
        }

