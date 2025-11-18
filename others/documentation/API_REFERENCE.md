# 📡 Chatbot API Reference

## Base URLs

- **Local Development**: `http://localhost:8000`
- **Public (Cloudflare Tunnel)**: `https://your-tunnel-url.trycloudflare.com`
- **API Base**: `{base_url}/api/v1`

---

## Authentication

Currently, the API does not require authentication. In production, add API keys or JWT tokens.

---

## Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### Send Chat Message

```http
POST /api/v1/chat/message
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": "string (required)",
  "message": "string (required)",
  "chat_id": "string (optional)",
  "vendor_id": "string (optional, default: 'default')"
}
```

**Response:**
```json
{
  "response": "string",
  "chat_id": "string",
  "message_id": "string",
  "tokens_used": 150,
  "credits_used": 2,
  "model_used": "mistral",
  "retrieved_chunks": 3,
  "is_domain_relevant": true,
  "suggestions": [
    "Tell me about finance options",
    "What are your opening hours?"
  ]
}
```

**Example:**
```bash
curl -X POST https://your-tunnel-url.trycloudflare.com/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "What is the rental price for Honda PCX 125?"
  }'
```

---

### Get Chat History

```http
GET /api/v1/chat/history/{chat_id}?limit=50
```

**Parameters:**
- `chat_id` (path, required): Chat session ID
- `limit` (query, optional): Number of messages to return (default: 50)

**Response:**
```json
{
  "chat_id": "chat_001",
  "messages": [
    {
      "role": "user",
      "content": "What is the rental price?",
      "created_at": "2025-01-27T10:00:00",
      "tokens_used": 10
    },
    {
      "role": "assistant",
      "content": "Honda PCX 125 rental starts from £75 per week...",
      "created_at": "2025-01-27T10:00:01",
      "tokens_used": 150
    }
  ]
}
```

---

### Get User Chats

```http
GET /api/v1/chat/chats/{user_id}
```

**Response:**
```json
{
  "user_id": "user_001",
  "chats": [
    {
      "chat_id": "chat_001",
      "title": "Rental Inquiry",
      "created_at": "2025-01-27T10:00:00",
      "updated_at": "2025-01-27T10:05:00"
    }
  ]
}
```

---

### Delete Chat

```http
DELETE /api/v1/chat/delete/{chat_id}
```

**Response:**
```json
{
  "status": "success",
  "message": "Chat chat_001 deleted successfully",
  "deleted": {
    "messages": 10,
    "memory": 1,
    "token_usage": 5,
    "chat": true
  }
}
```

---

### RAG Query

```http
POST /api/v1/rag/query
Content-Type: application/json
```

**Request:**
```json
{
  "query": "rental prices",
  "top_k": 5,
  "vendor_id": "default"
}
```

**Response:**
```json
{
  "query": "rental prices",
  "results": [
    {
      "content": "Honda PCX 125 rental: £75/week...",
      "score": 0.85,
      "metadata": {}
    }
  ],
  "count": 5
}
```

---

### RAG Stats

```http
GET /api/v1/rag/stats
```

**Response:**
```json
{
  "total_chunks": 38,
  "collection_name": "neguinho_motors_ltd_kb",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

---

### Database Stats

```http
GET /api/v1/database/stats
```

**Response:**
```json
{
  "users": 34,
  "chats": 63,
  "messages": 356,
  "conversation_memory": 45,
  "token_usage": 120,
  "model_configs": 1,
  "total_tokens": 154065,
  "total_credits": 1461,
  "avg_messages_per_chat": 5.65,
  "recent_messages_24h": 12,
  "recent_chats_24h": 3,
  "recent_users_24h": 1
}
```

---

### Current Model

```http
GET /api/v1/models/current
```

**Response:**
```json
{
  "provider": "ollama",
  "model": "mistral",
  "base_url": "http://localhost:11434"
}
```

---

### Available Models

```http
GET /api/v1/models/available
```

**Response:**
```json
{
  "models": [
    {
      "name": "mistral",
      "provider": "ollama",
      "available": true
    },
    {
      "name": "llama3.2",
      "provider": "ollama",
      "available": true
    }
  ]
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message"
}
```

---

## Request Examples

### JavaScript (Fetch)
```javascript
const response = await fetch('https://your-tunnel-url.trycloudflare.com/api/v1/chat/message', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        user_id: 'user_001',
        message: 'What is the rental price?'
    })
});

const data = await response.json();
console.log(data.response);
```

### PHP (Laravel)
```php
use Illuminate\Support\Facades\Http;

$response = Http::post('https://your-tunnel-url.trycloudflare.com/api/v1/chat/message', [
    'user_id' => 'user_001',
    'message' => 'What is the rental price?'
]);

$data = $response->json();
echo $data['response'];
```

### Python (Requests)
```python
import requests

url = "https://your-tunnel-url.trycloudflare.com/api/v1/chat/message"
response = requests.post(url, json={
    "user_id": "user_001",
    "message": "What is the rental price?"
})

data = response.json()
print(data['response'])
```

### cURL
```bash
curl -X POST https://your-tunnel-url.trycloudflare.com/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "What is the rental price for Honda PCX 125?"
  }'
```

---

## Interactive API Documentation

Visit `https://your-tunnel-url/docs` for interactive Swagger UI where you can:
- See all endpoints
- Test API calls
- View request/response schemas
- Try different parameters

---

## Rate Limiting

Currently, there is no rate limiting. In production, implement rate limiting based on:
- User ID
- IP address
- API key

---

## CORS

The API allows all origins by default. In production, restrict to specific domains:

```python
# backend/config/settings.py
cors_origins = ["https://yourdomain.com", "https://app.yourdomain.com"]
```

---

## WebSocket Support

Currently, the API uses HTTP REST. For real-time chat, WebSocket support can be added.

---

## Best Practices

1. **Always include user_id**: Helps track usage and provide context
2. **Reuse chat_id**: For conversation continuity
3. **Handle errors**: Check response status before using data
4. **Set timeouts**: API calls may take 5-30 seconds
5. **Cache responses**: For frequently asked questions

---

## Support

- **API Docs**: `https://your-tunnel-url/docs`
- **Health Check**: `https://your-tunnel-url/health`
- **Logs**: Check server logs for debugging

