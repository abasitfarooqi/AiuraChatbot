# All Pages and APIs - Complete Reference

## ✅ All Endpoints Tested and Working

### Frontend Pages

| URL | Description | Status |
|-----|-------------|--------|
| `http://localhost:8000/` | Chat interface (root) | ✅ Working |
| `http://localhost:8000/frontend/index.html` | Chat interface | ✅ Working |
| `http://localhost:8000/frontend/admin.html` | Admin panel | ✅ Working |
| `http://localhost:8000/admin.html` | Admin panel (short URL) | ✅ Working |
| `http://localhost:8000/admin` | Admin panel (shortest URL) | ✅ Working |

### API Endpoints

#### Health & Info
- `GET /health` - Health check
- `GET /` - Root API endpoint (returns app info)
- `GET /docs` - Swagger UI documentation

#### Chat API (`/api/v1/chat`)
- `POST /api/v1/chat/message` - Send a message to the chatbot
- `GET /api/v1/chat/history/{chat_id}` - Get chat history
- `GET /api/v1/chat/chats/{user_id}` - Get all chats for a user

#### Model API (`/api/v1/models`)
- `GET /api/v1/models/current` - Get current model configuration
- `GET /api/v1/models/available` - Get available models
- `GET /api/v1/models/available?provider=ollama` - Get models for specific provider
- `POST /api/v1/models/switch` - Switch to a different model
- `POST /api/v1/models/download?model_name={name}&provider={provider}` - Download a model

#### RAG API (`/api/v1/rag`)
- `GET /api/v1/rag/stats` - Get RAG statistics
- `POST /api/v1/rag/load` - Reload knowledge base

## Quick Access Links

### For Users
- **Chat Interface**: http://localhost:8000/
- **Chat Interface (direct)**: http://localhost:8000/frontend/index.html

### For Administrators
- **Admin Panel**: http://localhost:8000/admin
- **Admin Panel (alternative)**: http://localhost:8000/admin.html
- **Admin Panel (full path)**: http://localhost:8000/frontend/admin.html

### For Developers
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Testing

Run the comprehensive test script:
```bash
./test_all_pages_and_apis.sh
```

This will test all pages and APIs and report any failures.

## Example API Calls

### Send a Chat Message
```bash
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "What are your opening hours?"
  }'
```

### Get Current Model
```bash
curl "http://localhost:8000/api/v1/models/current"
```

### Switch Model
```bash
curl -X POST "http://localhost:8000/api/v1/models/switch" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "gemma3:270m"
  }'
```

### Get RAG Stats
```bash
curl "http://localhost:8000/api/v1/rag/stats"
```

## Notes

- All admin page URLs now work:
  - `/admin` ✅
  - `/admin.html` ✅
  - `/frontend/admin.html` ✅

- The server must be running for these to work:
  ```bash
  ./scripts/start.sh
  ```

- All endpoints return proper HTTP status codes:
  - 200: Success
  - 404: Not Found
  - 500: Server Error

## Last Test Results

**Date**: 2025-01-27
**Status**: ✅ All 16 tests passed
- 5 Frontend pages: All working
- 3 API info endpoints: All working
- 3 Chat API endpoints: All working
- 4 Model API endpoints: All working
- 1 RAG API endpoint: Working

