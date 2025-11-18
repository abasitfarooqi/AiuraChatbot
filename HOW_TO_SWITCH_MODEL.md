# How to Switch LLM Models

The chatbot supports multiple ways to switch between different LLM models. Here are all the methods:

## Method 1: Admin Panel (Easiest)

1. **Open the Admin Panel:**
   - Navigate to: `http://localhost:8000/admin` (shortest URL)
   - Or: `http://localhost:8000/admin.html`
   - Or: `http://localhost:8000/frontend/admin.html`

2. **Go to Models Tab:**
   - Click on the "Models" tab in the navigation

3. **Select Model:**
   - Choose the provider (Ollama, OpenAI, or M4)
   - Select the model from the dropdown
   - Click "Switch Model" button

4. **Verify:**
   - The current model is displayed at the top
   - You'll see a confirmation message when switched

## Method 2: API Endpoint

### Switch Model via API

```bash
curl -X POST "http://localhost:8000/api/v1/models/switch" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "gemma3:270m",
    "temperature": 0.7,
    "max_tokens": 2000
  }'
```

### Get Available Models

```bash
# Get all available models for current provider
curl "http://localhost:8000/api/v1/models/available"

# Get models for specific provider
curl "http://localhost:8000/api/v1/models/available?provider=ollama"
```

### Get Current Model

```bash
curl "http://localhost:8000/api/v1/models/current"
```

## Method 3: Environment Variables (.env file)

Edit the `.env` file in the project root:

```env
# LLM Provider (ollama, openai, m4)
LLM_PROVIDER=ollama

# LLM Model name
LLM_MODEL=gemma3:270m

# LLM Base URL (for Ollama)
LLM_BASE_URL=http://localhost:11434

# LLM Parameters
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_TOP_P=0.9
LLM_TOP_K=40

# OpenAI (if using OpenAI)
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
```

**Note:** After changing `.env`, restart the server:
```bash
./scripts/restart.sh
```

## Method 4: Programmatic (Python)

```python
from backend.services.llm_service import LLMService

# Create service instance
llm_service = LLMService()

# Switch model
llm_service.switch_model(
    provider="ollama",
    model="gemma3:270m",
    temperature=0.7,
    max_tokens=2000
)
```

## Available Models

### Ollama Models (Local)

To see available Ollama models:
```bash
ollama list
```

Or via API:
```bash
curl "http://localhost:8000/api/v1/models/available?provider=ollama"
```

Common Ollama models:
- `gemma3:270m` (small, fast)
- `qwen3:0.6b` (small, fast)
- `llama3.2` (medium, better quality)
- `mistral` (medium, good quality)
- `llama3.1` (large, high quality)

### Download New Ollama Model

```bash
# Via command line
ollama pull llama3.2

# Via API
curl -X POST "http://localhost:8000/api/v1/models/download?model_name=llama3.2&provider=ollama"
```

### OpenAI Models (Cloud)

Requires `OPENAI_API_KEY` in `.env`:
- `gpt-4-turbo-preview`
- `gpt-4`
- `gpt-3.5-turbo`

## Important Notes

1. **Model Persistence:**
   - Model switches via API/Admin Panel are saved to the database
   - They persist until changed again
   - `.env` changes require server restart

2. **Current Model:**
   - The chatbot service uses the model set in `LLMService.current_model`
   - Each new `ChatbotService` instance uses the current model

3. **Provider Switching:**
   - You can switch between providers (Ollama, OpenAI, M4)
   - Make sure the provider is properly configured
   - Ollama must be running for Ollama models
   - OpenAI requires valid API key

4. **Testing:**
   - After switching, test with a simple query
   - Check the response quality
   - Monitor token usage if using OpenAI

## Troubleshooting

### Model Not Found
- For Ollama: Make sure the model is downloaded (`ollama pull <model_name>`)
- For OpenAI: Check API key is valid
- Verify model name spelling

### Model Not Switching
- Restart the server after `.env` changes
- Check server logs for errors
- Verify API endpoint is accessible

### Poor Response Quality
- Try a different model
- Adjust temperature (lower = more focused, higher = more creative)
- Increase max_tokens for longer responses

## Quick Reference

| Method | Best For | Persistence |
|--------|----------|-------------|
| Admin Panel | Quick testing, UI users | ✅ Saved to DB |
| API | Automation, scripts | ✅ Saved to DB |
| .env file | Production, defaults | ✅ After restart |
| Programmatic | Development, testing | ❌ Session only |

## Example: Switch to Better Model

If you want better responses, try switching to a larger model:

```bash
# Via API
curl -X POST "http://localhost:8000/api/v1/models/switch" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama3.2",
    "temperature": 0.7
  }'
```

Or use the Admin Panel for a visual interface!

