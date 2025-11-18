# Offline Setup Guide

This guide explains how to set up and use the chatbot in **fully offline mode** on macOS without internet connection.

## Overview

The chatbot now supports:
- ✅ **JSON-based configuration** (no hardcoded values)
- ✅ **Offline model management** (Hugging Face models cached locally)
- ✅ **Admin panel** for managing all settings
- ✅ **Knowledge base editor** in admin panel
- ✅ **System prompts** editable via admin panel

## Initial Setup (With Internet)

### 1. Download Models for Offline Use

Before going offline, download the required models:

```bash
# Start the server
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then:
1. Open admin panel: http://localhost:8000/admin
2. Go to **"Updates"** tab
3. Enter model name: `sentence-transformers/all-MiniLM-L6-v2`
4. Click **"Download Model"**
5. Wait for download to complete (may take several minutes)

### 2. Verify Offline Mode

Check `config/app_config.json`:

```json
{
  "embedding": {
    "offline_mode": true,
    "cache_dir": "./models/embeddings"
  },
  "llm": {
    "offline_mode": true
  }
}
```

## Configuration Files

All configuration is now stored in JSON files:

### `config/app_config.json`
Main application configuration:
- Application settings
- Database configuration
- LLM settings
- RAG settings
- Domain restrictions
- Contact information
- Branch details

### `config/system_prompts.json`
System prompts for the chatbot:
- Main system prompt
- Greeting prompt
- Query prompt
- Fallback messages

### `rag_knowledge_base.json`
Knowledge base chunks with metadata.

## Admin Panel Features

### New Tabs

1. **App Config** - Edit full application configuration
2. **Knowledge Base** - Edit knowledge base chunks
3. **Updates** - Manage offline models and system prompts

### Using the Admin Panel

#### Edit Application Configuration

1. Go to **"App Config"** tab
2. Click **"Load Config"** to load current configuration
3. Edit the JSON directly
4. Click **"Save Config"** to save changes
5. Click **"Reload from File"** to reload from disk

#### Edit Knowledge Base

1. Go to **"Knowledge Base"** tab
2. Click **"Load Knowledge Base"** to load current KB
3. Edit chunks, add new ones, or modify existing
4. Click **"Validate JSON"** to check syntax
5. Click **"Save & Reload"** to save and reload into vector database

#### Manage Offline Models

1. Go to **"Updates"** tab
2. View cached models in the list
3. Download new models by entering model name and clicking **"Download Model"**

#### Edit System Prompts

1. Go to **"Updates"** tab
2. Scroll to **"System Prompts"** section
3. Click **"Load Prompts"** to load current prompts
4. Edit prompts as needed
5. Click **"Save Prompts"** to save

## Offline Operation

Once models are downloaded and configuration is set:

1. **No internet required** - All models are cached locally
2. **Ollama must be running** - For LLM inference (runs locally)
3. **All settings editable** - Via admin panel or JSON files

### Starting Offline

```bash
# Make sure Ollama is running
ollama serve

# Start chatbot (in another terminal)
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Model Storage

Models are stored in:
- `./models/embeddings/` - Embedding models
- `./models/llm/` - LLM models (if needed)

## API Endpoints

New configuration endpoints:

- `GET /api/v1/config/` - Get full config
- `POST /api/v1/config/section` - Update config section
- `GET /api/v1/config/knowledge-base` - Get knowledge base
- `POST /api/v1/config/knowledge-base` - Update knowledge base
- `GET /api/v1/config/prompts` - Get system prompts
- `POST /api/v1/config/prompts` - Update system prompts
- `GET /api/v1/config/models/offline` - List cached models
- `POST /api/v1/config/models/download` - Download model

## Troubleshooting

### Models Not Loading Offline

1. Check `config/app_config.json` has `"offline_mode": true`
2. Verify models exist in `./models/embeddings/`
3. Check logs for errors

### Configuration Not Saving

1. Check file permissions on `config/` directory
2. Verify JSON is valid before saving
3. Check server logs for errors

### Knowledge Base Not Reloading

1. Validate JSON syntax first
2. Check that chunks have required fields: `symbol`, `content`, `tags`, `mapping`
3. Check server logs for RAG service errors

## Best Practices

1. **Backup before editing** - JSON files are critical
2. **Validate JSON** - Always validate before saving
3. **Test changes** - Test chatbot after configuration changes
4. **Version control** - Consider versioning config files
5. **Document changes** - Keep notes on what you changed

## File Structure

```
AiuraChatbot/
├── config/
│   ├── app_config.json          # Main configuration
│   └── system_prompts.json      # System prompts
├── models/
│   └── embeddings/              # Cached embedding models
├── rag_knowledge_base.json      # Knowledge base
└── backend/
    └── utils/
        └── config_manager.py   # Config manager
```

## Migration from Environment Variables

If you were using `.env` files:
1. Settings now load from JSON first
2. Environment variables still override JSON values
3. For offline use, configure everything in JSON

## Support

For issues:
1. Check server logs: `logs/chatbot.log`
2. Verify JSON syntax
3. Check model files exist
4. Ensure Ollama is running (for LLM)

