# MVS (Multi-Vector Search) Architecture Plan

## Overview

Refactoring the RAG system to use **Multi-Vector Search (MVS)** instead of single dense embeddings. This will improve retrieval accuracy by combining:
- **Dense Embeddings**: Semantic similarity (existing SentenceTransformer)
- **Sparse Embeddings**: Keyword/lexical matching (BM25/TF-IDF)

## Current Architecture

```
User Query → Single Dense Embedding → ChromaDB Search → Top K Chunks → LLM
```

**Limitations:**
- Single embedding type (dense only)
- Misses keyword-exact matches
- Poor performance on short queries
- No hybrid ranking

## New MVS Architecture

```
User Query
    │
    ├─→ Generate Dense Embedding (SentenceTransformer)
    │
    ├─→ Generate Sparse Embedding (BM25/TF-IDF)
    │
    └─→ Hybrid Search
        │
        ├─→ Dense Vector Search (ChromaDB)
        │   └─→ Top K chunks by semantic similarity
        │
        ├─→ Sparse Vector Search (In-Memory/DB)
        │   └─→ Top K chunks by keyword matching
        │
        └─→ Result Fusion & Ranking
            │
            ├─→ Combine results (Reciprocal Rank Fusion)
            ├─→ Re-rank by combined score
            └─→ Top N chunks → RAG Context Builder → LLM
```

## Implementation Steps

### 1. MVS Service (`backend/services/mvs_service.py`)

**Responsibilities:**
- Generate dense embeddings (existing SentenceTransformer)
- Generate sparse embeddings (BM25/TF-IDF)
- Store both embeddings per chunk
- Perform hybrid search
- Rank and fuse results

**Key Methods:**
```python
class MVSService:
    def generate_dense_embedding(text: str) -> List[float]
    def generate_sparse_embedding(text: str) -> Dict[str, float]  # BM25 weights
    def store_chunk(chunk_id: str, content: str, dense_emb: List[float], sparse_emb: Dict)
    def hybrid_search(query: str, top_k: int) -> List[Dict]
    def rank_results(dense_results: List, sparse_results: List) -> List[Dict]
```

### 2. Database Schema Updates

**New Tables:**

#### `kb_chunk_embeddings`
```sql
CREATE TABLE kb_chunk_embeddings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    chunk_id VARCHAR(100) NOT NULL,
    knowledge_base_id INT,
    vendor_id INT,
    
    -- Dense embedding (stored as JSON array)
    dense_embedding JSON,
    dense_model VARCHAR(200),  -- e.g., "sentence-transformers/all-MiniLM-L6-v2"
    
    -- Sparse embedding (stored as JSON dict: {term: weight})
    sparse_embedding JSON,
    sparse_model VARCHAR(50),  -- e.g., "bm25", "tfidf"
    
    -- Metadata
    created_at DATETIME,
    updated_at DATETIME,
    
    INDEX idx_chunk_id (chunk_id),
    INDEX idx_kb_id (knowledge_base_id),
    INDEX idx_vendor_id (vendor_id)
);
```

**Alternative: Store in ChromaDB with metadata**
- Use ChromaDB's metadata to store sparse embeddings
- Keep dense embeddings in ChromaDB vectors
- Store sparse as JSON in metadata field

### 3. Sparse Embedding Generation

**Options:**
1. **BM25 (Best Match 25)**: Industry standard for keyword search
   - Library: `rank-bm25` or custom implementation
   - Better for exact keyword matches
   
2. **TF-IDF (Term Frequency-Inverse Document Frequency)**
   - Library: `scikit-learn`
   - Good for keyword importance weighting

**Implementation:**
```python
from rank_bm25 import BM25Okapi
import numpy as np

class SparseEmbeddingGenerator:
    def __init__(self, corpus: List[str]):
        # Tokenize corpus
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.vocab = self._build_vocab(tokenized_corpus)
    
    def generate(self, text: str) -> Dict[str, float]:
        """Generate BM25 sparse vector for text."""
        tokens = self._tokenize(text)
        scores = self.bm25.get_scores(tokens)
        
        # Convert to sparse dict: {term: weight}
        sparse_vector = {}
        for i, token in enumerate(tokens):
            if token in self.vocab:
                sparse_vector[token] = float(scores[i])
        
        return sparse_vector
```

### 4. Hybrid Search Implementation

**Strategy: Reciprocal Rank Fusion (RRF)**

```python
def reciprocal_rank_fusion(dense_results: List[Dict], sparse_results: List[Dict], k: int = 60):
    """
    Combine dense and sparse search results using RRF.
    
    RRF Score = Σ(1 / (k + rank))
    """
    scores = {}
    
    # Add dense results
    for rank, result in enumerate(dense_results, 1):
        chunk_id = result['id']
        scores[chunk_id] = scores.get(chunk_id, 0) + (1 / (k + rank))
    
    # Add sparse results
    for rank, result in enumerate(sparse_results, 1):
        chunk_id = result['id']
        scores[chunk_id] = scores.get(chunk_id, 0) + (1 / (k + rank))
    
    # Sort by combined score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
```

### 5. Updated RAG Service Flow

```python
class RAGService:
    def __init__(self, vendor_id: str):
        self.mvs_service = MVSService(vendor_id)
        self.chroma_client = ...  # For dense search
        self.sparse_index = ...   # For sparse search
    
    def retrieve(self, query: str, top_k: int = 5):
        # Step 1: Generate multi-vectors for query
        query_dense = self.mvs_service.generate_dense_embedding(query)
        query_sparse = self.mvs_service.generate_sparse_embedding(query)
        
        # Step 2: Search both indices
        dense_results = self._dense_search(query_dense, top_k * 2)
        sparse_results = self._sparse_search(query_sparse, top_k * 2)
        
        # Step 3: Rank and fuse
        ranked_chunks = self.mvs_service.rank_results(dense_results, sparse_results)
        
        # Step 4: Return top K
        return ranked_chunks[:top_k]
```

### 6. Storage Strategy

**Option A: ChromaDB + Metadata (Recommended)**
- Store dense embeddings in ChromaDB vectors (existing)
- Store sparse embeddings in ChromaDB metadata as JSON
- Single database, easier migration

**Option B: ChromaDB + Separate Index**
- Dense: ChromaDB (existing)
- Sparse: In-memory BM25 index or separate DB table
- More complex but potentially faster

**Option C: Migrate to Multi-Vector DB**
- Consider Weaviate, Qdrant, or Pinecone
- Native multi-vector support
- Requires migration effort

**Recommendation: Option A** (ChromaDB + Metadata)
- Minimal changes
- Leverages existing infrastructure
- Easy to implement

### 7. Configuration

Add to `unified_config.json`:
```json
{
  "rag": {
    "top_k": 5,
    "similarity_threshold": 0.2,
    "enable_filtering": true,
    "enable_reranking": false,
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

## Migration Plan

### Phase 1: Add MVS Service (Non-Breaking)
1. Create `MVSService` class
2. Add sparse embedding generation
3. Store sparse embeddings in ChromaDB metadata
4. Keep existing dense search working

### Phase 2: Hybrid Search (Backward Compatible)
1. Implement hybrid search
2. Add configuration flag `mvs.enabled`
3. Default to `false` (use existing single embedding)
4. Test with `mvs.enabled = true`

### Phase 3: Full Migration
1. Set `mvs.enabled = true` by default
2. Update all knowledge bases to include sparse embeddings
3. Remove old single-embedding code (optional)

## Benefits

1. **Better Keyword Matching**: Sparse embeddings catch exact keyword matches
2. **Improved Short Query Handling**: BM25 excels at short queries
3. **Hybrid Intelligence**: Combines semantic (dense) + lexical (sparse) understanding
4. **Flexible Ranking**: Can tune dense/sparse weights per use case
5. **Industry Standard**: RRF is proven in production systems

## Dependencies

Add to `requirements.txt`:
```
rank-bm25==0.2.2  # For BM25 sparse embeddings
scikit-learn==1.4.0  # Alternative: TF-IDF (optional)
```

## Testing

1. **Unit Tests**: Test sparse embedding generation
2. **Integration Tests**: Test hybrid search with sample queries
3. **Performance Tests**: Compare MVS vs single embedding retrieval
4. **Accuracy Tests**: Measure improvement in retrieval quality

## Timeline

- **Week 1**: MVS Service + Sparse Embeddings
- **Week 2**: Hybrid Search + Ranking
- **Week 3**: Integration + Testing
- **Week 4**: Migration + Production

