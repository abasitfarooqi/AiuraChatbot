# AiuraChatbot - Complete Documentation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Configuration Guide](#configuration-guide)
4. [API Reference](#api-reference)
5. [Knowledge Base Structure](#knowledge-base-structure)
6. [Model Management](#model-management)
7. [RAG System](#rag-system)
8. [Memory System](#memory-system)
9. [Frontend Guide](#frontend-guide)
10. [Deployment Guide](#deployment-guide)
11. [Troubleshooting](#troubleshooting)

## Architecture Overview

The AiuraChatbot system is built with a modular, scalable architecture:

```
┌─────────────┐
│   Frontend  │ (HTML/JS - Chat Interface & Admin Panel)
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────────────────┐
│   FastAPI Backend      │
│  ┌──────────────────┐  │
│  │  Chatbot Service │  │ (Orchestrator)
│  └────────┬─────────┘  │
│           │            │
│  ┌────────▼────────┐   │
│  │  RAG Service   │───┤→ ChromaDB (Vector DB)
│  └────────┬────────┘   │
│           │            │
│  ┌────────▼────────┐   │
│  │  LLM Service    │───┤→ Ollama/OpenAI/M4
│  └────────┬────────┘   │
│           │            │
│  ┌────────▼────────┐   │
│  │ Memory Service  │───┤→ SQLite Database
│  └─────────────────┘   │
└────────────────────────┘
```

### Key Design Principles

1. **No Hardcoding**: All configuration via `.env` file
2. **Multi-Vendor Ready**: Architecture supports multiple vendors
3. **Provider Abstraction**: Easy switching between LLM providers
4. **Scalable**: Modular design allows horizontal scaling
5. **Domain-Bound**: Strict domain restriction for accuracy

## System Components

### 1. Backend Services

#### ChatbotService
Main orchestrator that coordinates:
- RAG retrieval
- LLM generation
- Memory management
- Token tracking
- Credit management

#### RAGService
- Vector database operations
- Embedding generation
- Semantic search
- Filtering by tags/metadata
- Domain relevance checking

#### LLMService
- Provider abstraction (Ollama/OpenAI/M4)
- Model switching
- Response generation
- Token counting

#### MemoryService
- Conversation context tracking
- Entity extraction
- Intent history
- Context summarisation

#### ModelManager
- Model downloading
- Model configuration
- Active model management
- Provider-specific operations

### 2. Database Models

- **User**: User accounts with credits
- **Chat**: Chat sessions
- **Message**: Individual messages
- **ConversationMemory**: Context and entities
- **TokenUsage**: Usage tracking
- **ModelConfig**: Model configurations

### 3. API Endpoints

Organised into modules:
- `/api/v1/chat/*` - Chat operations
- `/api/v1/models/*` - Model management
- `/api/v1/rag/*` - RAG operations

## Configuration Guide

### Environment Variables

All configuration is in `.env` file. Key sections:

#### Application
```env
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
```

#### Database
```env
DATABASE_URL=sqlite:///./data/chatbot.db
DATABASE_ECHO=false
```

#### Vector Database
```env
CHROMA_DB_PATH=./data/chroma_db
CHROMA_COLLECTION_NAME=neguinho_motors_kb
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

#### LLM Provider
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

#### RAG Settings
```env
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.3
RAG_ENABLE_FILTERING=true
```

#### Memory
```env
MEMORY_ENABLED=true
MEMORY_MAX_TURNS=20
MEMORY_SUMMARY_ENABLED=false
MEMORY_SUMMARY_THRESHOLD=15
```

#### Domain Restriction
```env
DOMAIN_RESTRICTION_ENABLED=true
DOMAIN_KEYWORDS=rental,sale,finance,deposit,warranty,policy,servicing,mot,delivery,accessories,neguinho,ngn,honda,yamaha,bike,motorcycle,scooter
```

## API Reference

### Chat Endpoints

#### POST /api/v1/chat/message
Send a message to the chatbot.

**Request:**
```json
{
  "user_id": "user_001",
  "chat_id": "chat_001",
  "message": "What is the rental price?",
  "vendor_id": "default"
}
```

**Response:**
```json
{
  "response": "Honda PCX 125 rental starts from £75 per week...",
  "chat_id": "chat_001",
  "message_id": "msg_123",
  "tokens_used": 150,
  "credits_used": 2,
  "model_used": "llama3.2",
  "retrieved_chunks": 3,
  "is_domain_relevant": true
}
```

#### GET /api/v1/chat/history/{chat_id}
Get chat history.

**Response:**
```json
{
  "chat_id": "chat_001",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "created_at": "2025-01-27T10:00:00",
      "tokens_used": 5
    }
  ]
}
```

#### GET /api/v1/chat/chats/{user_id}
Get all chats for a user.

### Model Endpoints

#### GET /api/v1/models/available
List available models.

#### POST /api/v1/models/switch
Switch to a different model.

**Request:**
```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "temperature": 0.7
}
```

#### POST /api/v1/models/download
Download a model (Ollama only).

#### GET /api/v1/models/current
Get current model configuration.

### RAG Endpoints

#### POST /api/v1/rag/query
Query the RAG system.

**Request:**
```json
{
  "query": "rental prices",
  "top_k": 5,
  "vendor_id": "default"
}
```

#### POST /api/v1/rag/load
Load knowledge base into vector database.

#### GET /api/v1/rag/stats
Get RAG statistics.

## Knowledge Base Structure

The `rag_knowledge_base.json` file contains chunks optimised for RAG:

```json
{
  "chunks": [
    {
      "symbol": "RENTAL_001",
      "keyword": "rental_overview",
      "tags": ["rental", "hire", "overview", "contract"],
      "mapping": {
        "category": "services",
        "subcategory": "rentals",
        "priority": "high",
        "domain": "neguinhomotors"
      },
      "metadata": {
        "source": "services.rentals",
        "confidence": "high",
        "vendor_id": "default"
      },
      "content": "Motorcycle and scooter rental/hire service..."
    }
  ]
}
```

### Chunk Fields

- **symbol**: Unique identifier (e.g., "RENTAL_001")
- **keyword**: Primary query term for filtering
- **tags**: Array of semantic tags for filtering
- **mapping**: Category structure for organisation
- **metadata**: Source, confidence, vendor_id
- **content**: The actual text content

## Model Management

### Supported Providers

1. **Ollama** (Local)
   - Models: llama3.2, mistral, etc.
   - Base URL: http://localhost:11434
   - No API key required

2. **OpenAI** (Cloud)
   - Models: gpt-4-turbo-preview, gpt-3.5-turbo
   - Requires API key
   - Set `OPENAI_API_KEY` in `.env`

3. **M4** (Placeholder)
   - Architecture ready for M4 integration

### Switching Models

Via API:
```bash
curl -X POST "http://localhost:8000/api/v1/models/switch" \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "llama3.2"}'
```

Via Admin Panel:
1. Open `frontend/admin.html`
2. Go to "Models" tab
3. Select provider and model
4. Click "Switch Model"

### Downloading Models (Ollama)

```bash
# Via command line
ollama pull llama3.2

# Via API
curl -X POST "http://localhost:8000/api/v1/models/download?model_name=llama3.2&provider=ollama"
```

## RAG System

### How It Works

1. **Knowledge Base Loading**
   - Chunks are loaded from `rag_knowledge_base.json`
   - Each chunk is embedded using sentence-transformers
   - Embeddings stored in ChromaDB

2. **Query Processing**
   - User query is embedded
   - Similarity search in vector database
   - Filtering by tags/metadata
   - Top-K results returned

3. **Context Building**
   - Retrieved chunks formatted as context
   - Passed to LLM with system prompt
   - LLM generates response using context

### Filtering

RAG supports filtering by:
- **Tags**: Semantic labels
- **Category/Subcategory**: Hierarchical structure
- **Vendor ID**: Multi-vendor support
- **Confidence**: Quality threshold

### Similarity Threshold

Set `RAG_SIMILARITY_THRESHOLD` in `.env` (0.0-1.0). Lower = more results, higher = more relevant.

## Memory System

### Conversation Context

- Tracks last N messages (configurable)
- Maintains per-chat context
- Extracts entities (bike models, services, locations)
- Tracks intent history

### Entity Extraction

Automatically extracts:
- Bike models (Honda, Yamaha, PCX, etc.)
- Service types (rental, sale, finance, etc.)
- Locations (Catford, Tooting, Sutton)

### Context Summarisation

When conversation exceeds threshold:
- Can summarise old messages
- Keeps recent context fresh
- Reduces token usage

## Frontend Guide

### Chat Interface (`frontend/index.html`)

Features:
- Multi-chat support
- Real-time messaging
- Chat history
- User management

Usage:
1. Open in browser
2. User ID auto-generated
3. Start chatting
4. Switch between chats via sidebar

### Admin Panel (`frontend/admin.html`)

Features:
- Dashboard with statistics
- Model management
- RAG management
- Configuration overview

Tabs:
- **Dashboard**: System statistics
- **Models**: Model switching and management
- **RAG**: Knowledge base management
- **Config**: Configuration information

## Deployment Guide

### Development

```bash
./scripts/start.sh
```

### Production

1. **Environment Setup**
```bash
ENVIRONMENT=production
DEBUG=false
```

2. **Database**
- Use PostgreSQL for production
- Update `DATABASE_URL` in `.env`

3. **WSGI Server**
```bash
pip install gunicorn
gunicorn backend.app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

4. **Reverse Proxy (nginx)**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

5. **Process Manager**
Use systemd or supervisor for process management.

## Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   - Check Ollama is running: `ollama serve`
   - Verify `LLM_BASE_URL` in `.env`

2. **RAG Not Loading**
   - Check `rag_knowledge_base.json` exists
   - Verify ChromaDB path is writable
   - Check logs for errors

3. **Model Not Found**
   - For Ollama: Download model first
   - For OpenAI: Set API key

4. **Database Errors**
   - Check database path is writable
   - Verify SQLite version
   - Check logs for specific errors

### Logs

Logs are written to:
- Console (stdout)
- File: `./logs/chatbot.log`

Check logs for detailed error messages.

### Debug Mode

Set `DEBUG=true` in `.env` for verbose logging.

## Additional Resources

- FastAPI Docs: http://localhost:8000/docs
- ChromaDB Docs: https://docs.trychroma.com/
- Ollama Docs: https://ollama.ai/docs
- Sentence Transformers: https://www.sbert.net/

