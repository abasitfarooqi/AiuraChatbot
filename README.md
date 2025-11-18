# AiuraChatbot - Neguinho Motors Chatbot System

A production-ready, intelligent chatbot system for Neguinho Motors with RAG (Retrieval-Augmented Generation), LLM integration, multi-turn conversation memory, and comprehensive management capabilities.

## Features

- **RAG System**: Vector database (ChromaDB) with semantic search and filtering
- **LLM Integration**: Support for Ollama, OpenAI, and M4 providers with model switching
- **Multi-Turn Memory**: Per-user, per-chat conversation context tracking
- **Domain-Bound**: Strict domain restriction to company services only
- **Multi-Vendor Ready**: Architecture supports multiple vendors
- **Token & Credit Tracking**: Usage monitoring and credit management
- **Configuration Management**: All settings in .env file, no hardcoding
- **RESTful API**: Complete API for chat, models, and RAG management
- **Frontend**: Testing interface and admin panel
- **Database**: SQLite database for chat history and user management

## Project Structure

```
AiuraChatbot/
├── backend/
│   ├── app/
│   │   └── main.py              # FastAPI application
│   ├── api/
│   │   ├── chat.py              # Chat endpoints
│   │   ├── models.py            # Model management endpoints
│   │   └── rag.py               # RAG endpoints
│   ├── config/
│   │   └── settings.py          # Configuration management
│   ├── models/
│   │   └── database.py          # Database models
│   ├── services/
│   │   ├── chatbot_service.py   # Main chatbot orchestrator
│   │   ├── llm_service.py        # LLM provider abstraction
│   │   ├── rag_service.py       # RAG retrieval service
│   │   ├── memory_service.py    # Conversation memory
│   │   └── model_manager.py      # Model management
│   └── utils/
├── frontend/
│   ├── index.html               # Chat interface
│   └── admin.html               # Admin panel
├── data/                        # Database and vector DB storage
├── logs/                        # Application logs
├── scripts/
│   ├── start.sh                 # Start script
│   ├── stop.sh                  # Stop script
│   └── restart.sh               # Restart script
├── rag_knowledge_base.json      # RAG-optimised knowledge base (active)
├── others/                      # Non-essential files (documentation, tests, reference data)
│   ├── documentation/          # All documentation files
│   ├── test_scripts/           # Test scripts
│   ├── helper_scripts/         # Helper scripts (tunnels, etc.)
│   └── reference_data/         # Reference data files
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## Quick Start

### Prerequisites

- Python 3.8+
- Ollama installed and running (for local LLM)
- Or OpenAI API key (for OpenAI provider)

### Installation

1. **Clone and navigate to project:**
```bash
cd AiuraChatbot
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Create necessary directories:**
```bash
mkdir -p data logs
```

6. **Start the application:**
```bash
# Using script
./scripts/start.sh

# Or manually
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

7. **Access the frontend:**
- Chat Interface: Open `frontend/index.html` in browser
- Admin Panel: Open `frontend/admin.html` in browser
- API Docs: http://localhost:8000/docs

## Configuration

All configuration is done via the `.env` file. Key settings:

### LLM Configuration
```env
LLM_PROVIDER=ollama          # ollama, openai, m4
LLM_MODEL=llama3.2           # Model name
LLM_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

### RAG Configuration
```env
CHROMA_DB_PATH=./data/chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.3
```

### Memory Configuration
```env
MEMORY_ENABLED=true
MEMORY_MAX_TURNS=20
MEMORY_SUMMARY_ENABLED=false
```

### Domain Restriction
```env
DOMAIN_RESTRICTION_ENABLED=true
DOMAIN_KEYWORDS=rental,sale,finance,deposit,warranty,policy,servicing,mot,delivery,accessories,neguinho,ngn,honda,yamaha,bike,motorcycle,scooter
```

## API Endpoints

### Chat
- `POST /api/v1/chat/message` - Send a message
- `GET /api/v1/chat/history/{chat_id}` - Get chat history
- `GET /api/v1/chat/chats/{user_id}` - Get user's chats

### Models
- `GET /api/v1/models/available` - List available models
- `POST /api/v1/models/switch` - Switch model
- `POST /api/v1/models/download` - Download model
- `GET /api/v1/models/current` - Get current model

### RAG
- `POST /api/v1/rag/query` - Query RAG system
- `POST /api/v1/rag/load` - Load knowledge base
- `GET /api/v1/rag/stats` - Get RAG statistics

## Usage Examples

### Send a Chat Message

```bash
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "What is the rental price for Honda PCX 125?",
    "chat_id": "chat_001"
  }'
```

### Switch Model

```bash
curl -X POST "http://localhost:8000/api/v1/models/switch" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama3.2",
    "temperature": 0.7
  }'
```

### Query RAG

```bash
curl -X POST "http://localhost:8000/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "rental prices",
    "top_k": 5
  }'
```

## Knowledge Base

The system uses `rag_knowledge_base.json` which contains:
- Symbolic mapping for each chunk
- Tags for semantic filtering
- Comprehensive metadata
- Vendor support
- Domain-specific content

Each chunk includes:
- `symbol`: Unique identifier
- `keyword`: Primary query term
- `tags`: Semantic labels
- `mapping`: Category/subcategory structure
- `metadata`: Source, confidence, vendor_id

## Development

### Running in Development Mode

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations

The database is automatically initialised on first run. For production, consider using Alembic for migrations.

### Adding New Knowledge Base Chunks

Edit `rag_knowledge_base.json` and reload:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/load"
```

## Production Deployment

1. Set `ENVIRONMENT=production` in `.env`
2. Set `DEBUG=false`
3. Use a production WSGI server (e.g., Gunicorn)
4. Set up proper database (PostgreSQL recommended)
5. Configure proper CORS origins
6. Set secure `SECRET_KEY`
7. Enable logging to file
8. Set up reverse proxy (nginx)

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check `LLM_BASE_URL` in `.env`

### RAG Not Loading
- Check `rag_knowledge_base.json` exists
- Verify ChromaDB path is writable
- Check logs for errors

### Model Not Found
- For Ollama: Download model first: `ollama pull llama3.2`
- For OpenAI: Set `OPENAI_API_KEY` in `.env`

## License

Proprietary - Neguinho Motors

## Support

For issues or questions, contact: enquiries@neguinhomotors.co.uk

