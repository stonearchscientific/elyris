# Environment Setup for LLM-Based Parsing

## Choose Your LLM Provider

The system supports **two LLM providers** for document parsing:

### Option 1: Ollama (Recommended for Development) 🆓

**Advantages:**
- ✅ Completely free
- ✅ No API quotas or rate limits
- ✅ Runs locally (no internet required)
- ✅ Fast responses
- ✅ Privacy-focused (data stays on your machine)

**Setup:**
1. Download Ollama from https://ollama.com/download
2. Install and start Ollama
3. Pull a model: `ollama pull llama3.2`
4. Set environment variables in `backend/.env`:
   ```
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```

**Recommended Models:**
- `llama3.2` (3B): Fast, good for development
- `llama3.2:1b`: Very fast, lighter accuracy
- `mistral`: Good balance of speed and accuracy
- `phi3`: Microsoft's efficient model

### Option 2: OpenAI (GPT-4) 💳

**Advantages:**
- ✅ High accuracy
- ✅ No local setup required
- ✅ Good for production

**Disadvantages:**
- ❌ Costs money per API call
- ❌ Rate limits and quotas
- ❌ Requires internet connection

**Setup:**
1. Get your API key from https://platform.openai.com/api-keys
2. Set environment variables in `backend/.env`:
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-key-here
   ```

---

# Environment Setup for LLM-Based Parsing (Legacy OpenAI-only instructions)

## OpenAI API Key Setup

The system uses OpenAI's GPT-4 for intelligent document parsing (sender/recipient extraction).

### Steps:

1. **Get your API key**:
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy the key (you won't see it again!)

2. **Create `.env` file** in the `backend` directory:
   ```bash
   cd backend
   echo "OPENAI_API_KEY=sk-your-actual-key-here" > .env
   ```

3. **Restart the backend** - it will automatically detect and use the key

## How It Works:

**With API Key:**
- ✅ Uses GPT-4o-mini for intelligent block detection
- ✅ Accurately finds sender/recipient regardless of layout
- ✅ Extracts structured fields (name, address, etc.)
- 💰 ~$0.15 per 1M tokens (very cheap for typical documents)

**Without API Key:**
- ⚠️ Falls back to regex-based heuristics
- ⚠️ Less accurate, depends on document layout
- ✅ Still works, just requires more manual review

## Cost Estimate:

- Typical document: ~1,000 tokens = $0.0002 (fractions of a cent)
- 100 documents/day: ~$0.02/day = $0.60/month
- Very affordable for production use!

## Backend Console Output:

You'll see this when the API key is working:
```
✅ LLM-based parsing enabled
✓ LLM parsing complete: sender=found, recipient=found
✓ LLM extracted 5 fields from sender
```

Without the key:
```
⚠️ OPENAI_API_KEY not set. LLM parsing unavailable.
```

