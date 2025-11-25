# Response Speed Configuration Guide

## Why Responses Are Slow

Response time depends on several factors:
1. **LLM Generation Time** - The model needs time to generate tokens
2. **Ollama Timeout** - Currently set to 120 seconds (2 minutes)
3. **RAG Processing** - Vector search and embedding generation
4. **Cache Lookup** - Checking cache for similar questions
5. **Model Size** - Larger models are slower but more accurate

## Where to Control Response Time

### 1. **Ollama Timeout (Main Control)**

**Location**: `backend/services/llm_service.py`

**Current Setting**: 120 seconds (2 minutes)

**Lines to Change**:
- Line 433: `async with httpx.AsyncClient(timeout=120.0) as client:`
- Line 481: `async with httpx.AsyncClient(timeout=120.0) as client:`

**To Speed Up**:
```python
# Change from 120.0 to 30.0 for faster timeout (30 seconds)
async with httpx.AsyncClient(timeout=30.0) as client:
```

**To Allow Longer Responses**:
```python
# Change to 300.0 for 5 minutes (for very long responses)
async with httpx.AsyncClient(timeout=300.0) as client:
```

### 2. **Model Configuration (Speed vs Quality)**

**Location**: `config/vendors/neguinho_motors/unified_config.json`

```json
{
  "llm": {
    "provider": "ollama",
    "model": "mistral",  // ← Change to faster model
    "max_tokens": 4000,   // ← Reduce for faster responses
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40
  }
}
```

**Faster Models** (smaller, faster):
- `qwen2:0.5b` - Very fast, smaller responses
- `qwen2:1.5b` - Fast, good quality
- `phi3:mini` - Fast, efficient

**Slower Models** (larger, better quality):
- `mistral` - Good balance
- `llama3` - Better quality, slower
- `qwen2.5:7b` - High quality, slower

**To Speed Up**:
1. Use a smaller model (e.g., `qwen2:0.5b`)
2. Reduce `max_tokens` (e.g., `2000` instead of `4000`)
3. Lower `temperature` (e.g., `0.5` instead of `0.7`)

### 3. **RAG Configuration (Reduce Retrieval Time)**

**Location**: `config/vendors/neguinho_motors/unified_config.json`

```json
{
  "rag": {
    "top_k": 5,  // ← Reduce for faster retrieval (e.g., 3)
    "similarity_threshold": 0.2,
    "enable_filtering": true,
    "enable_reranking": false,  // ← Keep false for speed
    "mvs": {
      "enabled": true,  // ← Set to false for faster (simpler search)
      "dense_weight": 0.6,
      "sparse_weight": 0.4,
      "fusion_method": "rrf",
      "rrf_k": 60
    }
  }
}
```

**To Speed Up RAG**:
1. Reduce `top_k` from `5` to `3` (fewer chunks to retrieve)
2. Disable MVS: Set `"enabled": false` (simpler search is faster)
3. Keep `enable_reranking: false` (reranking adds delay)

### 4. **Cache Configuration (Enable for Instant Responses)**

**Location**: `config/vendors/neguinho_motors/unified_config.json`

```json
{
  "chatbot_service": {
    "caching": {
      "enabled": true,  // ← Keep enabled for speed
      "use_cache_for_responses": true,  // ← Instant responses for cached questions
      "fallback_to_llm_on_cache_miss": true,
      "similarity_threshold": 0.75  // ← Lower = more cache hits (faster)
    }
  }
}
```

**To Speed Up with Cache**:
1. Lower `similarity_threshold` to `0.70` (more cache hits)
2. Keep `use_cache_for_responses: true` (instant responses)

### 5. **Frontend Timeout (User Experience)**

**Location**: `frontend/index.html`

The frontend doesn't have a timeout, but you can add one:

```javascript
// Add timeout to fetch request
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds

const response = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
    signal: controller.signal
});

clearTimeout(timeoutId);
```

## Recommended Settings for Fast Responses

### Option 1: Fastest (Lower Quality)
```json
{
  "llm": {
    "model": "qwen2:0.5b",
    "max_tokens": 2000,
    "temperature": 0.5
  },
  "rag": {
    "top_k": 3,
    "mvs": {
      "enabled": false
    }
  }
}
```
**Expected Time**: 2-5 seconds

### Option 2: Balanced (Recommended)
```json
{
  "llm": {
    "model": "qwen2:1.5b",
    "max_tokens": 3000,
    "temperature": 0.6
  },
  "rag": {
    "top_k": 4,
    "mvs": {
      "enabled": true
    }
  }
}
```
**Expected Time**: 5-10 seconds

### Option 3: Quality (Slower)
```json
{
  "llm": {
    "model": "mistral",
    "max_tokens": 4000,
    "temperature": 0.7
  },
  "rag": {
    "top_k": 5,
    "mvs": {
      "enabled": true
    }
  }
}
```
**Expected Time**: 10-30 seconds

## Quick Fixes

### Immediate Speed Improvements:

1. **Reduce Ollama Timeout** (in `llm_service.py`):
   ```python
   timeout=30.0  # Instead of 120.0
   ```

2. **Use Smaller Model** (in `unified_config.json`):
   ```json
   "model": "qwen2:0.5b"
   ```

3. **Reduce max_tokens**:
   ```json
   "max_tokens": 2000
   ```

4. **Disable MVS** (if not needed):
   ```json
   "mvs": { "enabled": false }
   ```

5. **Lower RAG top_k**:
   ```json
   "top_k": 3
   ```

## Monitoring Response Time

Check logs for timing information:
- `logs/chatbot.log` - Shows processing times
- Model Usage Log in frontend - Shows token usage and time

Look for lines like:
```
[LLM] ✅ LLM response received
[LLM]   - LLM call time: 5.234s
[LLM]   - Total processing time: 6.123s
```

## Troubleshooting Slow Responses

1. **Check Ollama is Running**: `curl http://localhost:11434/api/tags`
2. **Check Model is Loaded**: Ollama needs to load model first time
3. **Check RAG Database**: Large knowledge bases slow down retrieval
4. **Check Network**: Slow connection to Ollama server
5. **Check CPU/GPU**: Model generation is CPU/GPU intensive

## Environment Variables

You can also set timeouts via environment variables (if supported):
```env
OLLAMA_TIMEOUT=30
LLM_MAX_TOKENS=2000
```

