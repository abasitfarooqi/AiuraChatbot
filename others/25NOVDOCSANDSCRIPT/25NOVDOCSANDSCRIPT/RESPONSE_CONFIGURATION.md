# Response Configuration Guide

## Where to Configure Response Length (max_tokens)

The LLM response length is controlled by the `max_tokens` parameter. You can configure it in multiple places:

### 1. **Vendor-Specific Configuration (Recommended)**
Location: `config/vendors/{vendor_id}/unified_config.json`

```json
{
  "llm": {
    "provider": "ollama",
    "model": "mistral",
    "max_tokens": 4000,  // ← Change this value
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40
  }
}
```

**Current value for neguinho_motors**: `4000` tokens

### 2. **Default Configuration**
Location: `config/unified_config.json`

```json
{
  "llm": {
    "max_tokens": 4000  // ← Default value
  }
}
```

### 3. **Database Configuration (Admin Panel)**
You can also update it via the admin panel:
- Go to **LLM Config** tab
- Update **Max Tokens** field
- Click **Update Configuration**

### 4. **Environment Variables**
Location: `.env` file

```env
LLM_MAX_TOKENS=4000
```

## Response Length Limits

- **Minimum**: 100 tokens (recommended minimum)
- **Default**: 4000 tokens
- **Maximum**: 
  - Ollama: Usually 32,000+ (model dependent)
  - OpenAI: Model dependent (e.g., GPT-4: 8,192, GPT-4 Turbo: 128,000)
  - M4: Model dependent

## How to Set Unlimited Response

**Note**: There's no true "unlimited" - you must set a very high value based on your model's context window.

### For Ollama:
```json
{
  "llm": {
    "max_tokens": 32000  // Very high limit (most Ollama models support this)
  }
}
```

### For OpenAI:
```json
{
  "llm": {
    "max_tokens": 8000  // GPT-4 standard limit
    // or
    "max_tokens": 128000  // GPT-4 Turbo limit
  }
}
```

## Response Formatting Improvements

The system now includes enhanced response formatting:

1. **Better List Formatting**: Bullet points are properly spaced and formatted
2. **Line Break Handling**: Proper paragraph breaks and line spacing
3. **Section Headers**: Bold headers are properly formatted
4. **Price Formatting**: Currency symbols and prices are correctly spaced

### Formatting Configuration
Location: `config/vendors/{vendor_id}/unified_config.json`

```json
{
  "chatbot_service": {
    "response_formatting": {
      "add_contact_info": true,
      "contact_keywords": ["service", "rental", "sale", "finance"],
      "min_response_length_for_contact": 50,
      "contact_info": "{contact_format}",
      "default_empty_response": "I'm here to help! How can I assist you today?"
    }
  }
}
```

## Testing Changes

After updating `max_tokens`:
1. Restart the server
2. Send a test message
3. Check the response length
4. Monitor token usage in the Model Usage Log

## Notes

- Higher `max_tokens` = longer responses but more tokens used
- Lower `max_tokens` = shorter, more focused responses
- The actual response may be shorter than `max_tokens` if the model finishes earlier
- Token usage affects credits/costs (if credit system is enabled)

