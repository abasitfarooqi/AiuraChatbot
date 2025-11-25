# MVS (Multi-Vector Search) Integration Complete

## Summary

Successfully integrated Multi-Vector Search (MVS) architecture into the existing RAG system. The system now supports hybrid search combining dense (semantic) and sparse (keyword) embeddings for improved retrieval accuracy.

## What Was Implemented

### 1. MVS Service (`backend/services/mvs_service.py`)

**Features:**
- **Dense Embeddings**: Uses existing SentenceTransformer model
- **Sparse Embeddings**: BM25/TF-IDF for keyword matching
- **Hybrid Search**: Combines dense + sparse results
- **Ranking Methods**:
  - Reciprocal Rank Fusion (RRF) - default
  - Weighted Fusion (configurable weights)

**Key Classes:**
- `SparseEmbeddingGenerator`: Generates BM25/TF-IDF sparse vectors
- `MVSService`: Main service for multi-vector operations

### 2. Updated RAG Service (`backend/services/rag_service.py`)

**Changes:**
- Integrated MVS service
- Updated `load_knowledge_base()` to generate and store sparse embeddings
- Updated `retrieve()` to use hybrid search when MVS is enabled
- Backward compatible: Falls back to single embedding if MVS disabled

**New Methods:**
- `_retrieve_mvs()`: Hybrid search using dense + sparse
- `_retrieve_single()`: Legacy single embedding search

### 3. Configuration

**Added to `config/unified_config.json`:**
```json
{
  "rag": {
    "mvs": {
      "enabled": true,
      "dense_weight": 0.6,
      "sparse_weight": 0.4,
      "sparse_model": "bm25",
      "fusion_method": "rrf",
      "rrf_k": 60
    }
  }
}
```

### 4. Storage Strategy

**ChromaDB + Metadata:**
- Dense embeddings: Stored in ChromaDB vectors (existing)
- Sparse embeddings: Stored in ChromaDB metadata as JSON
- No database schema changes required
- Easy migration path

## How It Works

### Architecture Flow

```
User Query
    │
    ├─→ Generate Dense Embedding (SentenceTransformer)
    │
    ├─→ Generate Sparse Embedding (BM25)
    │
    └─→ Hybrid Search
        │
        ├─→ Dense Vector Search (ChromaDB)
        │   └─→ Top K chunks by semantic similarity
        │
        ├─→ Sparse Vector Search (In-Memory)
        │   └─→ Top K chunks by keyword matching
        │
        └─→ Result Fusion & Ranking
            │
            ├─→ Combine results (RRF or Weighted Fusion)
            ├─→ Re-rank by combined score
            └─→ Top N chunks → RAG Context Builder → LLM
```

### Knowledge Base Loading

1. **Load chunks** from JSON
2. **Initialize sparse index** with corpus
3. **For each chunk:**
   - Generate dense embedding (SentenceTransformer)
   - Generate sparse embedding (BM25)
   - Store dense in ChromaDB vector
   - Store sparse in ChromaDB metadata as JSON

### Query Retrieval

1. **Generate query vectors:**
   - Dense embedding for semantic search
   - Sparse embedding for keyword search

2. **Search both indices:**
   - Dense: ChromaDB query (cosine similarity)
   - Sparse: In-memory similarity calculation

3. **Fuse results:**
   - RRF: `score = Σ(1 / (k + rank))`
   - Weighted: `score = dense_score * dense_weight + sparse_score * sparse_weight`

4. **Rank and return** top K chunks

## Benefits

1. **Better Keyword Matching**: Sparse embeddings catch exact keyword matches
2. **Improved Short Query Handling**: BM25 excels at short queries
3. **Hybrid Intelligence**: Combines semantic (dense) + lexical (sparse) understanding
4. **Flexible Ranking**: Can tune dense/sparse weights per use case
5. **Backward Compatible**: Works with existing knowledge bases

## Configuration Options

### Enable/Disable MVS

```json
{
  "rag": {
    "mvs": {
      "enabled": true  // Set to false to use single embedding
    }
  }
}
```

### Tune Fusion Method

**RRF (Reciprocal Rank Fusion):**
```json
{
  "rag": {
    "mvs": {
      "fusion_method": "rrf",
      "rrf_k": 60  // Higher = more weight on top results
    }
  }
}
```

**Weighted Fusion:**
```json
{
  "rag": {
    "mvs": {
      "fusion_method": "weighted",
      "dense_weight": 0.6,   // Weight for semantic similarity
      "sparse_weight": 0.4   // Weight for keyword matching
    }
  }
}
```

### Sparse Model Selection

```json
{
  "rag": {
    "mvs": {
      "sparse_model": "bm25"  // or "tfidf"
    }
  }
}
```

## Migration

### For Existing Knowledge Bases

1. **Reload knowledge base:**
   - MVS will automatically generate sparse embeddings
   - Sparse embeddings stored in ChromaDB metadata
   - No data loss, backward compatible

2. **Enable MVS:**
   - Set `rag.mvs.enabled = true` in config
   - Restart service or reload RAG service

3. **Test:**
   - Send queries and verify improved retrieval
   - Check logs for MVS retrieval messages

## Testing

### Verify MVS is Working

1. **Check logs:**
   ```
   Retrieved X chunks (MVS hybrid) for query: ...
   ```

2. **Compare results:**
   - Enable MVS: `rag.mvs.enabled = true`
   - Disable MVS: `rag.mvs.enabled = false`
   - Compare retrieval quality

3. **Test with different queries:**
   - Short queries (should benefit from sparse)
   - Long queries (should benefit from dense)
   - Keyword-heavy queries (should benefit from sparse)

## Dependencies

Added to `requirements.txt`:
```
numpy>=1.24.0  # For vector operations
```

## Next Steps

1. **Performance Testing**: Measure improvement in retrieval accuracy
2. **Tuning**: Adjust weights and fusion parameters per vendor
3. **Monitoring**: Track MVS vs single embedding performance
4. **Documentation**: Update API docs with MVS configuration

## Notes

- **Backward Compatible**: Existing knowledge bases work without changes
- **Optional**: MVS can be disabled per vendor via config
- **Storage Efficient**: Sparse embeddings stored as JSON in metadata
- **No Database Changes**: Uses existing ChromaDB infrastructure

