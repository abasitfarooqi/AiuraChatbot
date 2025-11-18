# Quick Start Guide

Get the AiuraChatbot running in 5 minutes!

## Step 1: Prerequisites

Ensure you have:
- Python 3.8+ installed
- Ollama installed and running (for local LLM)

### Install Ollama (if needed)

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve
```

### Download a Model

```bash
ollama pull llama3.2
```

## Step 2: Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create directories
mkdir -p data logs

# 4. Copy environment file
cp .env.example .env

# 5. Edit .env if needed (defaults should work)
# No changes needed for basic setup
```

## Step 3: Start

```bash
# Option 1: Using script
./scripts/start.sh

# Option 2: Using Make
make start

# Option 3: Manual
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 4: Test

1. **Open Chat Interface**
   - Open `frontend/index.html` in your browser
   - Start chatting!

2. **Open Admin Panel**
   - Open `frontend/admin.html` in your browser
   - Check system status

3. **API Docs**
   - Visit http://localhost:8000/docs
   - Interactive API documentation

## Step 5: First Chat

Try these queries:
- "What is the rental price for Honda PCX 125?"
- "Do you offer finance options?"
- "What are your opening hours?"
- "Tell me about your services"

## Troubleshooting

### Ollama Connection Error
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### Port Already in Use
```bash
# Change port in .env
API_PORT=8001
```

### Knowledge Base Not Loading
```bash
# Manually load via API
curl -X POST "http://localhost:8000/api/v1/rag/load"
```

## Next Steps

- Read [README.md](README.md) for detailed information
- Read [DOCUMENTATION.md](DOCUMENTATION.md) for complete guide
- Customise `.env` for your needs
- Add more knowledge base chunks in `rag_knowledge_base.json`

## Support

For issues, check:
1. Logs in `./logs/chatbot.log`
2. API docs at http://localhost:8000/docs
3. Documentation in [DOCUMENTATION.md](DOCUMENTATION.md)

