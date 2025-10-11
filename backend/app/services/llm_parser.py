"""LLM-based document parsing for intelligent field extraction"""
import os
import json
from typing import Dict, Any, Optional, Tuple, List
from .logging_config import setup_logger

logger = setup_logger(__name__)

# Debug mode controlled by environment variable
DEBUG_PARSING = os.getenv('DEBUG_DOCUMENT_PARSING', 'false').lower() == 'true'
VALIDATE_EXTRACTIONS = os.getenv('VALIDATE_LLM_EXTRACTIONS', 'true').lower() == 'true'

# Import models to get schema fields
from backend.app.models import Person, Location

def _get_person_fields() -> List[str]:
    """Extract field names from Person model for prompting"""
    # Exclude internal fields
    exclude = {'id', 'created_at', 'legal_flags'}
    return [field for field in Person.model_fields.keys() if field not in exclude]

def _get_location_fields() -> List[str]:
    """Extract field names from Location model for prompting"""
    # Exclude internal fields
    exclude = {'id', 'created_at', 'updated_at', 'global_position_id'}
    return [field for field in Location.model_fields.keys() if field not in exclude]

# Lazy import for OpenAI
_OPENAI_AVAILABLE = None

def _check_openai():
    global _OPENAI_AVAILABLE
    if _OPENAI_AVAILABLE is None:
        try:
            import openai
            _OPENAI_AVAILABLE = True
        except (ImportError, Exception):
            _OPENAI_AVAILABLE = False
    return _OPENAI_AVAILABLE


class LLMDocumentParser:
    """
    Uses LLM to intelligently parse document structure
    Supports: OpenAI (GPT-4) and Ollama (local models)
    
    Environment variables:
    - LLM_PROVIDER: "openai" or "ollama" (default: "openai")
    - OPENAI_API_KEY: Your OpenAI API key (required for OpenAI)
    - OLLAMA_BASE_URL: Ollama server URL (default: "http://localhost:11434")
    - OLLAMA_MODEL: Model to use (default: "llama3.2")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        self.available = False
        
        if self.provider == 'ollama':
            self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
            self.available = self._check_ollama_available()
            if self.available:
                logger.info(f"[OK] Ollama enabled: {self.ollama_model}")
        else:  # openai
            self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            self.available = _check_openai() and self.api_key is not None
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama server is running"""
        try:
            import httpx
            response = httpx.get(f"{self.ollama_base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def _call_llm(self, prompt: str, system_message: str = "You are a helpful assistant.") -> str:
        """Call the configured LLM provider (OpenAI or Ollama)"""
        if self.provider == 'ollama':
            import httpx
            response = httpx.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": f"{system_message}\n\n{prompt}",
                    "stream": False,
                    "format": "json",
                    "options": {
                        "num_predict": 1000,  # Max tokens
                        "temperature": 0.1
                    }
                },
                timeout=60.0  # Longer timeout for complete responses
            )
            response.raise_for_status()
            return response.json()['response']
        else:  # openai
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            return response.choices[0].message.content.strip()
    
    def parse_document_with_llm(self, text: str) -> Tuple[Optional[str], Optional[str], str]:
        """
        Use LLM to intelligently identify text blocks for Person and Location entities
        
        Returns:
            Tuple of (sender_text, recipient_text, body_text) for backward compatibility
            sender_text = FROM entity block (typically Location for organizations)
            recipient_text = TO entity block (typically Person)
        """
        if not self.available:
            return None, None, text
        
        try:
            person_fields = _get_person_fields()
            location_fields = _get_location_fields()
            
            prompt = f"""You are a document processing assistant. Analyze this document and identify text blocks containing entity information.

ENTITY TYPES TO EXTRACT:

1. **LOCATION entities** (organizations, businesses, government agencies):
   - Fields: {', '.join(location_fields)}
   - Usually: Letterhead, return address, company info, organization names
   
2. **PERSON entities** (individual people):
   - Fields: {', '.join(person_fields)}
   - Usually: Recipient name/address, "To:", "Attention:", individual contacts

3. **BODY**: Main document content (letters, body text, transaction details)

INSTRUCTIONS:
- Return the raw text blocks where these entities appear
- For "FROM" (sender), look for letterhead/return address → typically a LOCATION
- For "TO" (recipient), look for addressee → typically a PERSON
- If document has contact signatures, that's also a PERSON entity

Return JSON:
{{
  "from_block": "raw text of FROM entity (sender)",
  "to_block": "raw text of TO entity (recipient)",
  "body_text": "main content"
}}

Document text:
{text[:4000]}

Return ONLY valid JSON, no explanation."""

            result_text = self._call_llm(prompt, "You are a precise document parser. Return only valid JSON.")
            
            # Remove markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
            
            from_block = result.get('from_block')
            to_block = result.get('to_block')
            body = result.get('body_text', text)
            
            # Validate that blocks are strings (or None), not dicts
            if from_block and not isinstance(from_block, str):
                logger.warning(f"LLM returned non-string from_block (type: {type(from_block).__name__}), ignoring")
                from_block = None
            if to_block and not isinstance(to_block, str):
                logger.warning(f"LLM returned non-string to_block (type: {type(to_block).__name__}), ignoring")
                to_block = None
            
            logger.info(f"[LLM] Block detection: from={'found' if from_block else 'not found'}, to={'found' if to_block else 'not found'}")
            
            # Return as (sender, recipient, body) for backward compatibility
            return from_block, to_block, body
            
        except Exception as e:
            logger.warning(f"LLM block detection failed: {str(e)}")
            return None, None, text
    
    def _post_process_extraction(self, result: Dict[str, Any], text: str, block_type: str) -> Dict[str, Any]:
        """
        Post-process LLM extraction results to fill in missing fields using regex
        Only fills in fields that LLM returned as null
        """
        import re
        
        # Get clean lines (skip page markers, empty lines)
        lines = [l.strip() for l in text.split('\n') 
                 if l.strip() and not l.strip().startswith('---')]
        
        if block_type == "sender":
            # Extract organization name from first line if missing
            if not result.get('organization_name') and lines:
                result['organization_name'] = lines[0]
            
            # Extract department if missing (often second line, but not PO Box or zip code)
            if not result.get('department') and len(lines) > 1:
                candidate = lines[1]
                if 'PO Box' not in candidate and not re.search(r'\d{5}', candidate):
                    result['department'] = candidate
            
            # Extract city if missing - look for pattern: City, ST ZIP
            if not result.get('city'):
                # Match city including abbreviations like "St. Paul"
                city_match = re.search(r'([A-Za-z][A-Za-z\s.]+?),\s*([A-Z]{2})\s+\d{5}', text)
                if city_match:
                    result['city'] = city_match.group(1).strip()
        
        elif block_type == "recipient":
            # Extract name from first line if missing
            if not result.get('first_name') or not result.get('last_name'):
                if lines and isinstance(lines[0], str):
                    name_parts = lines[0].split()
                    if len(name_parts) >= 2:
                        if not result.get('first_name'):
                            result['first_name'] = name_parts[0].title()
                        if not result.get('last_name'):
                            result['last_name'] = ' '.join(name_parts[1:]).title()
            
            # Extract city and state if missing - find the city line (NOT street address)
            # Pattern: CITY, ST ZIP (where CITY is all caps and NOT a street address)
            if not result.get('city') or not result.get('state'):
                # Look for line that has city, state, zip pattern
                for line in lines:
                    if not isinstance(line, str):
                        continue
                    # Skip street addresses (lines with numbers at start or "DR", "ST", "AVE")
                    if re.match(r'^\d+\s', line) or any(suffix in line.upper() for suffix in [' DR', ' ST', ' AVE', ' RD', ' LN', ' CT', 'VIEW', 'STREET', 'DRIVE']):
                        continue
                    # Look for CITY, ST ZIP pattern (handle "St." in city names)
                    city_state_match = re.search(r'^([A-Z][A-Za-z\s.]+?),\s*([A-Z]{2})\s+\d{5}', line)
                    if city_state_match:
                        city_name = city_state_match.group(1).strip()
                        # Don't use if it looks like a street name
                        if not any(word in city_name.upper() for word in ['VIEW', 'DRIVE', 'STREET', 'AVENUE']):
                            if not result.get('city'):
                                result['city'] = city_name.title()
                            if not result.get('state'):
                                result['state'] = city_state_match.group(2)
                            break
        
        return result
    
    def _validate_extraction(self, result: Dict[str, Any], source_text: str) -> Dict[str, Any]:
        """
        Validate extracted data against source text to prevent hallucinations
        Remove fields that don't appear in the source
        """
        validated = {}
        source_lower = source_text.lower()
        
        for key, value in result.items():
            if value is None:
                continue
                
            # Check if the value actually appears in the source text
            value_lower = str(value).lower()
            
            # For addresses, zip codes, phone numbers - must be verbatim in source
            if key in ['address', 'zip', 'phone', 'email']:
                # For zip codes, be flexible with formatting (55164-0989 vs 55164 -0989)
                if key == 'zip':
                    zip_normalized = value_lower.replace(' ', '').replace('-', '')
                    source_normalized = source_lower.replace(' ', '').replace('-', '')
                    if zip_normalized in source_normalized:
                        validated[key] = value
                        continue
                
                # For others, check verbatim presence (with some flexibility for whitespace)
                if value_lower in source_lower or value_lower.replace(' ', '') in source_lower.replace(' ', ''):
                    validated[key] = value
                else:
                    logger.debug(f"Rejecting hallucinated {key}: '{value}' not found in source")
            
            # For names, cities, states, organizations - be more lenient (might have OCR artifacts)
            elif key in ['first_name', 'last_name', 'city', 'state', 'organization_name', 'department', 'name']:
                # Check if at least part of it appears (handle OCR spacing like "St. Paul" vs "St . Paul")
                value_parts = value_lower.split()
                if any(part in source_lower for part in value_parts if len(part) > 2):
                    validated[key] = value
                else:
                    logger.debug(f"Rejecting hallucinated {key}: '{value}' not found in source")
            else:
                # Other fields - keep as is
                validated[key] = value
        
        return validated
    
    def extract_structured_with_llm(self, text_block: str, block_type: str) -> Dict[str, Any]:
        """
        Use LLM to extract structured fields from a text block using SQL schema
        
        Args:
            text_block: Raw text containing entity information
            block_type: "sender" (Location entity) or "recipient" (Person entity)
        
        Returns:
            Dict with structured fields matching SQL schema
        """
        if not self.available or not text_block:
            return {}
        
        try:
            # Determine entity type and get schema fields
            if block_type == "sender":
                # Sender is typically a Location (organization)
                entity_type = "LOCATION"
                fields = _get_location_fields()
                field_descriptions = {
                    "name": "Organization/company name (e.g. 'Minnesota Department of Human Services')",
                    "department": "Department/division if present (e.g. 'Legislative Mailing')",
                    "address": "Physical/mailing address - PO Box or street (e.g. 'PO Box 64989')",
                    "city": "City name",
                    "state": "2-letter state code",
                    "zip": "ZIP code (keep hyphen if present)",
                    "country": "Country if specified",
                    "phone": "Phone number",
                    "email": "Email address",
                    "website": "Website URL"
                }
                
                prompt = f"""Extract {entity_type} entity information from this text block.

DATABASE SCHEMA: {entity_type} table has these fields:
{chr(10).join(f'- "{field}": {field_descriptions.get(field, "string value")}' for field in fields)}

CRITICAL RULES:
1. "name" = Organization name ONLY, NOT address
2. "address" = MAILING address ONLY (PO Box or street numbers)
3. NEVER put organization name in address field
4. Return FLAT JSON matching the schema fields above
5. Use null for fields not found in the text

Text block:
{text_block}

Return ONLY valid JSON with NO nested objects."""

            else:  # recipient
                # Recipient is typically a Person
                entity_type = "PERSON"
                fields = _get_person_fields()
                field_descriptions = {
                    "first_name": "First name only",
                    "last_name": "Last name only",
                    "dob": "Date of birth (YYYY-MM-DD format)"
                }
                
                # Note: Person entities might have address info stored elsewhere, but we'll extract it for matching
                # Add common address fields that appear in person blocks for smart query matching
                fields.extend(["address", "city", "state", "zip", "phone", "email"])
                
                prompt = f"""Extract {entity_type} entity information from this text block.

DATABASE SCHEMA: {entity_type} table has these core fields:
{chr(10).join(f'- "{field}": {field_descriptions.get(field, "string value")}' for field in _get_person_fields())}

ALSO extract these fields for entity matching (if present):
- "address": Full street address
- "city": City name
- "state": 2-letter state code
- "zip": ZIP code (keep hyphen if present)
- "phone": Phone number
- "email": Email address

CRITICAL RULES:
1. Look for FULL NAME - often appears as "FIRSTNAME LASTNAME"
2. "address" = COMPLETE street address with number AND street name
3. "zip" = COMPLETE ZIP code with hyphen if present
4. Return FLAT JSON matching the schema fields
5. Use null for fields not found in the text

Text block:
{text_block}

Return ONLY valid JSON with NO nested objects."""
            
            result_text = self._call_llm(prompt, "You are a precise data extractor. Return only valid JSON.")
            
            # Clean markdown
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
            
            # Track which fields came from LLM vs post-processing
            parsing_methods = {}
            for key in result:
                if result[key] is not None:
                    parsing_methods[key] = "llm"
            
            # Post-processing: Fill in missing fields using regex if LLM returned null
            pre_regex_keys = set(k for k, v in result.items() if v is not None)
            result = self._post_process_extraction(result, text_block, block_type)
            post_regex_keys = set(k for k, v in result.items() if v is not None)
            
            # Track fields added by regex
            regex_added = post_regex_keys - pre_regex_keys
            for key in regex_added:
                parsing_methods[key] = "regex"
            
            # Validation: Remove hallucinated data (fields not found in source text)
            if VALIDATE_EXTRACTIONS:
                pre_validation_keys = set(k for k, v in result.items() if v is not None)
                result = self._validate_extraction(result, text_block)
                post_validation_keys = set(k for k, v in result.items() if v is not None)
                
                # Track rejected fields
                rejected_keys = pre_validation_keys - post_validation_keys
                if rejected_keys:
                    logger.info(f"Validation rejected fields: {', '.join(rejected_keys)}")
            
            # Remove None values
            result = {k: v for k, v in result.items() if v is not None}
            
            # Log extraction summary
            llm_fields = [k for k, v in parsing_methods.items() if v == "llm" and k in result]
            regex_fields = [k for k, v in parsing_methods.items() if v == "regex" and k in result]
            
            logger.info(f"[LLM] Extracted {len(result)} {entity_type} fields from {block_type}")
            if DEBUG_PARSING:
                if llm_fields:
                    logger.debug(f"  LLM: {', '.join(llm_fields)}")
                if regex_fields:
                    logger.debug(f"  Regex: {', '.join(regex_fields)}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM field extraction failed for {block_type}: {str(e)}")
            return {}

