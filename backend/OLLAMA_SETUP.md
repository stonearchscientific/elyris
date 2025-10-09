# Ollama Setup for Elyris 🦙

## Quick Start (5 minutes)

### 1. Install Ollama

**Windows:**
Download and run the installer from https://ollama.com/download

**Mac/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Start Ollama

Ollama runs as a background service after installation. You can verify it's running:

```bash
ollama --version
```

### 3. Pull a Model

Pull Llama 3.2 (recommended for development):

```bash
ollama pull llama3.2
```

**Other recommended models:**
```bash
# Smaller/faster
ollama pull llama3.2:1b

# Larger/more accurate  
ollama pull mistral
ollama pull llama3.1
```

### 4. Configure Elyris

Update your `backend/.env` file:

```env
# Use Ollama instead of OpenAI
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 5. Test It!

Restart your backend and upload a document. You should see:

```
✅ Ollama enabled: http://localhost:11434 with model llama3.2
✅ LLM-based parsing enabled
```

## Testing Ollama Connection

Quick test to make sure Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

Should return a list of installed models.

## Switching Back to OpenAI

Just change `backend/.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here
```

## Troubleshooting

**"Ollama not available"**
- Check if Ollama is running: `ollama serve` (should say "already running" if it's active)
- Verify the model is pulled: `ollama list`
- Check the URL in `.env` matches your Ollama installation

**Slow responses**
- Try a smaller model: `llama3.2:1b`
- Check your system resources (Ollama needs RAM)

**Model not found**
- Pull the model first: `ollama pull llama3.2`
- Check available models: `ollama list`

## Model Comparison

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| llama3.2:1b | 1.3GB | ⚡⚡⚡ | ⭐⭐ | Quick testing |
| llama3.2 | 2GB | ⚡⚡ | ⭐⭐⭐ | Development |
| mistral | 4.1GB | ⚡ | ⭐⭐⭐⭐ | Production-like |
| llama3.1 | 4.7GB | ⚡ | ⭐⭐⭐⭐ | Best accuracy |

## Benefits for Your Project

1. **No API costs** during development
2. **No quota limits** - parse as many documents as you want
3. **Privacy** - sensitive documents never leave your machine
4. **Offline work** - no internet dependency
5. **Fast iteration** - no network latency

## Next Steps

Once your OpenAI quota is replenished, you can:
- Use Ollama for dev, OpenAI for production
- Compare accuracy between models
- Fine-tune prompts on Ollama (free!) then deploy to OpenAI

