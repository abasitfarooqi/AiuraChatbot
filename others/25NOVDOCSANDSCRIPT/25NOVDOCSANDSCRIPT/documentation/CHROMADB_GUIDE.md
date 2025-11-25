# ChromaDB Guide

## What is ChromaDB?

ChromaDB is the **vector database** used by the chatbot to store and retrieve knowledge base information. It's a critical component of the RAG (Retrieval-Augmented Generation) system.

## Role of ChromaDB

1. **Stores Embeddings**: Converts knowledge base text into numerical vectors (embeddings) for semantic search
2. **Enables Fast Retrieval**: Quickly finds relevant information based on user queries
3. **Persistent Storage**: Stores data in `data/chroma_db/` directory
4. **Semantic Search**: Uses similarity matching to find the most relevant chunks

## How It Works

1. **Knowledge Base Loading**: When you load `rag_knowledge_base.json`, each chunk is:
   - Converted to an embedding using the sentence transformer model
   - Stored in ChromaDB with metadata (tags, categories, etc.)
   - Indexed for fast retrieval

2. **Query Processing**: When a user asks a question:
   - The query is converted to an embedding
   - ChromaDB searches for similar embeddings
   - Returns the most relevant chunks
   - These chunks are sent to the LLM for generating the answer

## ChromaDB Structure

```
data/chroma_db/
├── chroma.sqlite3          # Main database file
└── [collection-uuid]/      # Collection data directories
    ├── data_level0.bin
    ├── header.bin
    ├── length.bin
    └── link_lists.bin
```

## Managing ChromaDB

### Via Admin Panel

1. **View ChromaDB Info**: Go to "Knowledge Base" tab → "ChromaDB Management" section
   - See current collection name
   - View total chunks
   - Check all collections

2. **Clear ChromaDB**: Click "Clear ChromaDB" button
   - ⚠️ **WARNING**: This deletes ALL vector data
   - You'll need to reload the knowledge base after clearing

3. **Reload Knowledge Base**: After editing `rag_knowledge_base.json`:
   - Click "Save & Reload" in Knowledge Base tab
   - This automatically updates ChromaDB

### Via API

```bash
# Get ChromaDB info
GET /api/v1/rag/chromadb/info

# Clear ChromaDB
POST /api/v1/rag/clear

# Get RAG stats
GET /api/v1/rag/stats

# Reload knowledge base
POST /api/v1/rag/load
```

## When to Clear ChromaDB

- After major changes to knowledge base structure
- When switching to a different knowledge base
- If you suspect data corruption
- When changing embedding models

## Best Practices

1. **Backup Before Clearing**: Always backup `rag_knowledge_base.json` before clearing
2. **Reload After Changes**: Always reload knowledge base after editing
3. **Monitor Collection Size**: Check stats regularly to ensure data is loaded
4. **Use Same Embedding Model**: Don't change embedding models without clearing and reloading

## Troubleshooting

### ChromaDB Not Loading
- Check if `data/chroma_db/` directory exists and is writable
- Verify embedding model is downloaded
- Check logs for errors

### Wrong Results
- Clear ChromaDB and reload knowledge base
- Verify knowledge base JSON is valid
- Check if embedding model matches

### Performance Issues
- ChromaDB is optimized for fast retrieval
- Large knowledge bases may take time to load initially
- Consider splitting into multiple collections for very large datasets

## Collection Names

The collection name is automatically generated from your company name:
- Format: `{company_name_lower}_kb`
- Example: `neguinho_motors_ltd_kb`
- Configurable in `config/unified_config.json` → `vector_database.chroma_collection_name`

## Metadata Stored

Each chunk in ChromaDB includes:
- `symbol`: Unique identifier
- `keyword`: Primary search term
- `tags`: Semantic labels
- `category`: Main category
- `subcategory`: Subcategory
- `priority`: Priority level
- `domain`: Domain classification
- `vendor_id`: For multi-vendor support
- `source`: Source of information
- `confidence`: Confidence level

This metadata enables advanced filtering and retrieval strategies.

