"""LLM-based document parsing for intelligent field extraction"""
import os
import json
from typing import Dict, Any, Optional, Tuple

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
                print(f"✅ Ollama enabled: {self.ollama_model}", flush=True)
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
        Use LLM to intelligently extract sender, recipient, and body from document text
        
        Returns:
            Tuple of (sender_text, recipient_text, body_text)
        """
        if not self.available:
            return None, None, text
        
        try:
            prompt = f"""You are a document processing assistant. Analyze the following document text and extract:

1. SENDER information (usually organization in top left corner or letterhead)
2. RECIPIENT information (usually person's name and address, may have "To:" or "Re:" prefix)
3. BODY text (main content of the document)

Return a JSON object with these keys:
- "sender_text": The raw text block containing sender info (or null if not found)
- "recipient_text": The raw text block containing recipient info (or null if not found)  
- "body_text": The main document content

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
            
            sender = result.get('sender_text')
            recipient = result.get('recipient_text')
            body = result.get('body_text', text)
            
            print(f"✓ LLM parsing complete: sender={'found' if sender else 'not found'}, recipient={'found' if recipient else 'not found'}", flush=True)
            
            return sender, recipient, body
            
        except Exception as e:
            print(f"⚠️ LLM parsing failed: {str(e)}", flush=True)
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
                if lines:
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
    
    def extract_structured_with_llm(self, text_block: str, block_type: str) -> Dict[str, Any]:
        """
        Use LLM to extract structured fields from a text block
        
        Args:
            text_block: Raw text (sender or recipient block)
            block_type: "sender" or "recipient"
        
        Returns:
            Dict with structured fields (name, address, city, state, zip, etc.)
        """
        if not self.available or not text_block:
            return {}
        
        try:
            if block_type == "sender":
                prompt = f"""Extract structured information from this sender/organization text block.

CRITICAL RULES:
1. "organization_name" = Company/agency name ONLY (e.g. "Minnesota Department of Human Services")
2. "department" = Department/division if present (e.g. "Legislative Mailing")
3. "address" = MAILING address ONLY - look for PO Box or street numbers (e.g. "PO Box 64989" or "123 Main St")
4. NEVER put organization name in address field
5. Return FLAT JSON - no nested objects

Extract these fields (use null if not found):
- "organization_name": string
- "department": string
- "address": string (PO Box or street address ONLY)
- "city": string
- "state": string (2 letters)
- "zip": string (keep hyphen if present)
- "phone": string
- "email": string

Text:
{text_block}

Return ONLY valid JSON with NO nested objects."""
            else:  # recipient
                prompt = f"""Extract structured information from this recipient/person text block.

CRITICAL RULES:
1. Look for FULL NAME (first and last) - often appears first as "FIRSTNAME LASTNAME"
2. "address" = COMPLETE street address including number AND street name (e.g. "1085 Willow View Dr")
3. "zip" = COMPLETE ZIP code, may have hyphen (e.g. "55356-4304")
4. Return FLAT JSON - no nested objects

Extract these fields (use null if not found):
- "first_name": string (first name only)
- "last_name": string (last name only)
- "address": string (FULL street address)
- "city": string
- "state": string (2 letters)
- "zip": string (COMPLETE zip code with hyphen if present)

Text:
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
            
            # Post-processing: Fill in missing fields using regex if LLM returned null
            result = self._post_process_extraction(result, text_block, block_type)
            
            # Remove None values
            result = {k: v for k, v in result.items() if v is not None}
            
            print(f"✓ LLM extracted {len(result)} fields from {block_type}", flush=True)
            
            return result
            
        except Exception as e:
            print(f"⚠️ LLM field extraction failed for {block_type}: {str(e)}", flush=True)
            return {}

