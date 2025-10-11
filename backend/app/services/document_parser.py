"""Document parsing service with OCR and text extraction"""
import re
import os
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from .logging_config import setup_logger

logger = setup_logger(__name__)

# Debug mode controlled by environment variable
DEBUG_PARSING = os.getenv('DEBUG_DOCUMENT_PARSING', 'false').lower() == 'true'

def extract_filename_hints(file_path: str) -> Dict[str, Any]:
    """
    Extract helpful context from filename for guiding LLM parsing
    
    Args:
        file_path: Path to document file
    
    Returns:
        Dict with keywords, suggested_type, and person_name hints
    """
    path = Path(file_path)
    filename = path.stem.lower()  # Remove extension
    
    # Common document type keywords
    financial_keywords = ['invoice', 'receipt', 'quote', 'bill', 'payment', 'transaction', 'purchase', 'financial']
    health_keywords = ['health', 'medical', 'insurance', 'benefits', 'care', 'claim', 'hospital', 'doctor', 'clinic']
    education_keywords = ['school', 'iep', 'education', 'academic', 'grade', 'student', 'class', 'elementary', 'learning']
    
    # Extract keywords from filename
    keywords = []
    suggested_type = None
    
    for keyword in financial_keywords:
        if keyword in filename:
            keywords.append(keyword)
            suggested_type = 'financial'
    
    for keyword in health_keywords:
        if keyword in filename:
            keywords.append(keyword)
            suggested_type = 'health'
    
    for keyword in education_keywords:
        if keyword in filename:
            keywords.append(keyword)
            suggested_type = 'education'
    
    # Try to extract person name (often first part before underscore)
    parts = filename.split('_')
    person_name = parts[0] if parts and len(parts[0]) > 2 else None
    
    return {
        'keywords': keywords,
        'suggested_type': suggested_type,
        'person_name': person_name.title() if person_name else None,
        'filename': path.name
    }

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
                    logger.info("[INIT] LLM-based parsing enabled")
            except Exception as e:
                logger.warning(f"Could not initialize LLM parser: {e}")
    
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
                        logger.info(f"[PDF] Extracted {len(extracted_text)} chars from PDF using direct text extraction")
                        return extracted_text
                    else:
                        logger.info("[PDF] No embedded text found in PDF, falling back to OCR...")
            except Exception as e:
                logger.warning(f"Direct PDF text extraction failed ({str(e)}), trying OCR...")
        
        # Fall back to OCR
        if not _check_pdf2image():
            raise ValueError("pdf2image not installed. Install with: pip install pdf2image")
        if not _check_pytesseract():
            raise ValueError("pytesseract not installed. Install with: pip install pytesseract")
        
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            logger.info("[OCR] Converting PDF to images for OCR...")
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            # Extract text from each page
            full_text = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                full_text.append(f"--- Page {i+1} ---\n{text}")
                logger.debug(f"Processed page {i+1}/{len(images)}")
            
            result = "\n\n".join(full_text)
            logger.info(f"[OCR] Complete: extracted {len(result)} chars")
            return result
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    def parse_document_blocks(self, text: str, filename_hints: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[str], str, Optional[str]]:
        """
        Parse document into sender, recipient, and body sections, plus document type
        Uses LLM if available, falls back to heuristic parsing
        
        Args:
            text: Document text to parse
            filename_hints: Optional hints from filename (keywords, suggested_type, person_name)
        
        Returns:
            Tuple of (sender_text, recipient_text, body_text, doc_type)
            doc_type will be None if heuristics are used (can't determine type)
        """
        # Try LLM parsing first
        detected_doc_type = None
        if self.llm_parser and self.llm_parser.available:
            sender, recipient, body, doc_type = self.llm_parser.parse_document_with_llm(text, filename_hints)
            detected_doc_type = doc_type  # Preserve doc_type even if blocks not found
            if sender or recipient:  # If LLM found blocks, use them
                return sender, recipient, body, doc_type
            logger.info(f"[FALLBACK] LLM found type={doc_type} but no blocks, using heuristics for blocks")
        
        # Fall back to heuristic parsing
        lines = text.strip().split('\n')
        
        sender_text = None
        recipient_text = None
        recipient_start_idx = None
        body_start = 0
        
        # PRE-CHECK: Detect if this is a quote/email format
        # Look for "Hi/Hello [Name]" in first 20 lines AND signature at end
        is_quote_format = False
        for i, line in enumerate(lines[:20]):
            line_stripped = line.strip()
            # Match patterns like "Hi Heather Holcombe," or "Hello John,"
            if re.match(r'^(hi|hello|hey)\s+([a-z]+(\s+[a-z]+)?)[,:]', line_stripped, re.IGNORECASE):
                # Extract recipient name from salutation
                match = re.match(r'^(hi|hello|hey)\s+([a-z\s]+)[,:]', line_stripped, re.IGNORECASE)
                if match:
                    recipient_text = match.group(2).strip()
                    is_quote_format = True
                    body_start = i + 1
                    
                    # Look for signature after the salutation (search forward in next 50 lines)
                    # Signatures typically appear after "Thank you," or similar closings
                    for j in range(i+1, min(i+50, len(lines))):
                        sig_line = lines[j].strip()
                        # Look for email pattern or phone pattern
                        if '@' in sig_line or re.search(r'\(\d{3}\)\s*\d{3}[-\s]*\d{4}', sig_line):
                            # Found email/phone, look backwards for closing phrase or name
                            sender_lines = []
                            sig_start = j - 3  # Default: 3 lines back (closing, name, phone/email)
                            
                            # Try to find a closing phrase ("Thank you,", "Sincerely,", etc.)
                            for k in range(j-1, max(j-10, i), -1):
                                check_line = lines[k].strip().lower()
                                if any(phrase in check_line for phrase in ['thank you', 'thanks', 'sincerely', 'best', 'regards']):
                                    sig_start = k
                                    break
                            
                            # Collect signature from closing/name to email/phone
                            for k in range(max(sig_start, i), j+2):  # Include line after phone (might be email)
                                potential_line = lines[k].strip()
                                if potential_line and not potential_line.startswith('---'):
                                    # Skip body text indicators
                                    if not any(word in potential_line.lower() for word in ['proposed', 'details', 'reply to this', 'services below']):
                                        sender_lines.append(potential_line)
                            if sender_lines:
                                sender_text = '\n'.join(sender_lines)
                            break
                    break
        
        # If not a quote format, use traditional letterhead detection
        if not is_quote_format:
            # FIRST: Look for "Dear..." to find where recipient/body starts
            dear_line_idx = None
            for i, line in enumerate(lines[:50]):
                if line.strip().lower().startswith('dear '):
                    dear_line_idx = i
                    break
            
            if dear_line_idx:
                # Found "Dear", now work backwards to find recipient block
                # Recipient typically appears just before "Dear" (name + address)
                recipient_lines = []
                for j in range(dear_line_idx - 1, -1, -1):
                    prev_line = lines[j].strip()
                    if prev_line and not prev_line.startswith('---'):
                        recipient_lines.insert(0, prev_line)
                    elif recipient_lines:  # Hit empty line after collecting lines
                        break
                
                if recipient_lines and len(recipient_lines) >= 2:
                    recipient_text = '\n'.join(recipient_lines)
                    # Sender is everything before recipient
                    sender_end = dear_line_idx - len(recipient_lines) - 1
                    sender_lines = []
                    for k in range(sender_end):
                        sender_line = lines[k].strip()
                        if sender_line and not sender_line.startswith('---'):
                            sender_lines.append(sender_line)
                    if sender_lines:
                        sender_text = '\n'.join(sender_lines)
                    body_start = dear_line_idx
                else:
                    # No clear recipient block before "Dear", just take first lines as sender
                    sender_lines = []
                    for i, line in enumerate(lines[:dear_line_idx]):
                        line = line.strip()
                        if line and not line.startswith('---'):
                            sender_lines.append(line)
                            if len(sender_lines) >= 5:
                                break
                    if sender_lines:
                        sender_text = '\n'.join(sender_lines)
                    body_start = dear_line_idx
            else:
                # No "Dear" found - use simple first 5 lines heuristic
                first_block = []
                for i, line in enumerate(lines[:15]):
                    line = line.strip()
                    if line and not line.startswith('---'):
                        first_block.append(line)
                        if len(first_block) >= 5:
                            sender_text = '\n'.join(first_block)
                            body_start = i + 1
                            break
        
        # Look for recipient using multiple strategies (if not already found)
        if not recipient_text:
            remaining_lines = lines[body_start:]
            recipient_block = []
            recipient_start_idx = None
            
            # Strategy 0: Look for "Payer Information" or similar receipt patterns
            for i, line in enumerate(remaining_lines[:30]):
                line_stripped = line.strip()
                if 'payer information' in line_stripped.lower() or 'recipient information' in line_stripped.lower():
                    # Found receipt-style header, collect next few lines (name, address, phone, email)
                    for j in range(i+1, min(i+8, len(remaining_lines))):
                        next_line = remaining_lines[j].strip()
                        if next_line:
                            # Stop if we hit another section header
                            if any(keyword in next_line.lower() for keyword in ['account information', 'transaction', 'payment', 'summary']):
                                break
                            recipient_block.append(next_line)
                    if recipient_block:
                        recipient_text = '\n'.join(recipient_block)
                        recipient_start_idx = i + len(recipient_block) + 1
                        # For receipts, there's often no traditional "sender", so skip sender detection
                        sender_text = None
                    break
            
            # Strategy 1: Look for explicit indicators ("To:", "Re:")
            if not recipient_text:
                recipient_block = []  # Reset block
                for i, line in enumerate(remaining_lines[:20]):
                    line_stripped = line.strip()
                    if 'to:' in line_stripped.lower() or 're:' in line_stripped.lower():
                        # Found indicator, collect next few lines
                        for j in range(i+1, min(i+6, len(remaining_lines))):
                            next_line = remaining_lines[j].strip()
                            if next_line:
                                recipient_block.append(next_line)
                        if recipient_block:
                            recipient_text = '\n'.join(recipient_block)
                            recipient_start_idx = i + len(recipient_block) + 1
                        break
            
            # Strategy 2: If no explicit indicator, look for "Dear..." and take preceding address block
            # (This is now less relevant since we handle "Dear" earlier, but keep as fallback)
            if not recipient_text:
                for i, line in enumerate(remaining_lines[:30]):
                    line_stripped = line.strip()
                    if line_stripped.lower().startswith('dear '):
                        # Found "Dear", collect preceding non-empty lines (likely recipient)
                        temp_block = []
                        for j in range(i-1, -1, -1):
                            prev_line = remaining_lines[j].strip()
                            if prev_line:
                                temp_block.insert(0, prev_line)
                            elif temp_block:  # Hit empty line after collecting some lines
                                break
                        
                        if temp_block and len(temp_block) >= 2:  # At least name + address
                            recipient_text = '\n'.join(temp_block)
                            recipient_start_idx = i + 1
                        else:
                            # No clear recipient block, body starts at "Dear"
                            recipient_start_idx = i
                        break
        
        # Calculate body start position
        if recipient_start_idx is not None:
            body_start += recipient_start_idx
        
        # Rest is body text
        body_text = '\n'.join(lines[body_start:]).strip()
        
        # Log heuristic method used
        if sender_text or recipient_text:
            logger.info(f"[HEURISTIC] Block detection completed")
        
        # Return blocks with preserved doc_type (from LLM if available, otherwise None)
        return sender_text, recipient_text, body_text, detected_doc_type
    
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
        
        # Extract hints from filename to help LLM
        filename_hints = extract_filename_hints(file_path)
        if filename_hints['keywords'] or filename_hints['person_name']:
            logger.info(f"[HINTS] File: {filename_hints['filename']}, Type: {filename_hints['suggested_type']}, Person: {filename_hints['person_name']}")
        
        # Extract text based on file type
        if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            raw_text = self.extract_text_from_image(file_path)
        elif path.suffix.lower() == '.pdf':
            raw_text = self.extract_text_from_pdf(file_path)
        elif path.suffix.lower() == '.txt':
            # Support plain text for testing
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            logger.info(f"[TXT] Loaded {len(raw_text)} chars from text file")
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        # Debug output (only if enabled)
        if DEBUG_PARSING:
            logger.debug(f"📄 Extracted text preview:\n{raw_text[:1000]}\n...")
        
        # Parse into blocks with filename hints
        sender_text, recipient_text, body_text, doc_type = self.parse_document_blocks(raw_text, filename_hints)
        
        # Debug output (only if enabled)
        if DEBUG_PARSING:
            logger.debug(f"📦 Sender block: {sender_text[:300] if sender_text else 'None'}")
            logger.debug(f"📦 Recipient block: {recipient_text[:300] if recipient_text else 'None'}")
        
        # Extract structured data
        parsed_sender = self.extract_structured_data(sender_text, "sender") if sender_text else {}
        parsed_recipient = self.extract_structured_data(recipient_text, "recipient") if recipient_text else {}
        
        # Debug output (only if enabled)
        if DEBUG_PARSING:
            logger.debug(f"📊 Parsed sender: {parsed_sender}")
            logger.debug(f"📊 Parsed recipient: {parsed_recipient}")
        
        return {
            'raw_text': raw_text,
            'sender_text': sender_text,
            'recipient_text': recipient_text,
            'body_text': body_text,
            'parsed_sender': parsed_sender,
            'parsed_recipient': parsed_recipient,
            'doc_type': doc_type  # Document category: financial, health, education
        }

