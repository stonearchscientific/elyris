# 🚀 Quick Start: Free LLM Parsing with Ollama

## You're All Set Up! Just Follow These 3 Steps:

### Step 1: Install Ollama (2 minutes)

**Windows:** Download from https://ollama.com/download and run the installer

It will install as a background service automatically.

### Step 2: Pull a Model (3 minutes)

Open PowerShell and run:

```powershell
ollama pull llama3.2
```

This downloads the model (~2GB). Wait for it to complete.

### Step 3: Update Your .env File

Edit `backend/.env` and change:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

(Remove or comment out `OPENAI_API_KEY` if you want)

### Step 4: Restart Backend

```powershell
# Make sure you're using the venv Python!
.\backend\elyris-venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Test!

Upload your PDF at http://localhost:5173

You should see:
```
✅ Ollama enabled: http://localhost:11434 with model llama3.2
✅ LLM-based parsing enabled
✓ LLM parsing complete: sender=found, recipient=found
```

## That's It!

No more API quotas, no more costs. Parse unlimited documents for free! 🎉

## Verify Ollama is Running

```powershell
curl http://localhost:11434/api/tags
```

Should return your installed models.

## Alternative: Add OpenAI Credits

If you prefer OpenAI, add credits at: https://platform.openai.com/account/billing

Then keep your .env as:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here
```

