# Admin Panel Guide

## Overview

The admin panel provides comprehensive control over all aspects of the chatbot system. All tabs now auto-load data when opened.

## Tabs Overview

### 1. Unified Config Tab

**Purpose**: Central configuration for the entire system

**Features**:
- Loads automatically when tab is opened
- Shows complete unified configuration JSON
- Supports variable substitution (e.g., `{company_name}`, `{contact_email}`)
- Validates JSON before saving
- All changes require server restart for full effect

**Key Sections**:
- `business` - Company information, services, branches
- `contact` - Phone, email, contact format
- `prompts` - System prompts with variables
- `chatbot_service` - Chatbot behavior settings
- `application` - API, database, embedding, LLM config

**How to Use**:
1. Click "Unified Config" tab
2. Click "Load Config" (or it loads automatically)
3. Edit JSON in the textarea
4. Click "Validate JSON" to check syntax
5. Click "Save Config"
6. Restart server for changes to take effect

### 2. Knowledge Base Tab

**Purpose**: Edit and manage the knowledge base that powers RAG

**Features**:
- Auto-loads knowledge base JSON when tab is opened
- Shows current status (chunks, collection, model)
- Automatically reloads into ChromaDB when saved
- ChromaDB management section

**Knowledge Base Status**:
- Total Chunks: Number of chunks in vector database
- Collection: Current ChromaDB collection name
- Embedding Model: Model used for embeddings

**ChromaDB Management**:
- View current collection info
- See all collections
- Clear ChromaDB (⚠️ deletes all vector data)
- Reload knowledge base after clearing

**How to Use**:
1. Click "Knowledge Base" tab
2. Data loads automatically
3. Edit JSON chunks
4. Click "Save & Reload" to update ChromaDB
5. Use "Clear ChromaDB" if needed (then reload)

### 3. Updates Tab

**Purpose**: Manage offline models and system prompts

**Features**:
- Offline model management
- Model download with progress
- System prompts editor

**Offline Model Management**:
- Shows all cached models
- Displays model size and path
- Status indicator (✓ Cached / ✗ Not Cached)
- Cache directory location

**Download Model**:
1. Enter model name (e.g., `sentence-transformers/all-MiniLM-L6-v2`)
2. Click "Download Model"
3. Wait for download (may take several minutes)
4. Model appears in list when complete

**System Prompts**:
- Loads from unified config
- Supports variables: `{company_name}`, `{contact_email}`, etc.
- Auto-replaces variables when used

## ChromaDB Explained

### What is ChromaDB?

ChromaDB is the **vector database** that stores your knowledge base as embeddings (numerical vectors). It enables fast semantic search.

### How It Works

1. **Loading**: Knowledge base chunks → Embeddings → Stored in ChromaDB
2. **Querying**: User question → Embedding → Search ChromaDB → Find similar chunks
3. **Retrieval**: Return most relevant chunks to LLM for answer generation

### ChromaDB Location

- **Path**: `data/chroma_db/`
- **Database**: `chroma.sqlite3`
- **Collections**: UUID-based directories

### Managing ChromaDB

**Via Admin Panel**:
- Knowledge Base tab → ChromaDB Management section
- View info, clear collection, reload data

**When to Clear**:
- After major knowledge base changes
- When switching knowledge bases
- If experiencing wrong results
- When changing embedding models

**After Clearing**:
- Always reload knowledge base
- Use "Save & Reload" button
- Verify chunks are loaded (check status)

### Collection Names

- Auto-generated from company name
- Format: `{company_name_lower}_kb`
- Configurable in unified config

## Troubleshooting

### Unified Config Not Loading
- Check browser console for errors
- Verify API endpoint: `/api/v1/config/unified`
- Ensure server is running

### Knowledge Base Not Loading
- Check if `rag_knowledge_base.json` exists
- Verify file is valid JSON
- Check server logs for errors

### Offline Models Not Showing
- Models are cached in `models/embeddings/`
- Check if directory exists
- Verify model was downloaded successfully

### ChromaDB Issues
- Clear ChromaDB and reload knowledge base
- Check `data/chroma_db/` directory permissions
- Verify embedding model is loaded

## Best Practices

1. **Always Validate**: Use "Validate JSON" before saving
2. **Backup First**: Backup configs before major changes
3. **Restart Server**: After config changes, restart for full effect
4. **Monitor Status**: Check status indicators regularly
5. **Clear When Needed**: Clear ChromaDB after major KB changes

## API Endpoints

All admin panel features use these endpoints:

- `GET /api/v1/config/unified` - Get unified config
- `POST /api/v1/config/unified` - Update unified config
- `GET /api/v1/config/knowledge-base` - Get knowledge base
- `POST /api/v1/config/knowledge-base` - Update knowledge base
- `GET /api/v1/config/models/offline` - List offline models
- `POST /api/v1/config/models/download` - Download model
- `GET /api/v1/config/prompts` - Get system prompts
- `POST /api/v1/config/prompts` - Update system prompts
- `GET /api/v1/rag/stats` - Get RAG statistics
- `GET /api/v1/rag/chromadb/info` - Get ChromaDB info
- `POST /api/v1/rag/clear` - Clear ChromaDB

