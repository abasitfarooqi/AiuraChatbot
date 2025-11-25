# MVS Knowledge Base Migration Guide

## Answer: NO Changes Needed to Knowledge Base JSON Files

### ✅ Your Knowledge Base is Already Compatible

The existing knowledge base structure for Neguinho Motors (and all vendors) is **already compatible** with MVS. No changes are required to the `knowledge_base.json` files.

### Current Knowledge Base Structure

Your knowledge base files already have the correct structure:

```json
{
  "metadata": {
    "version": "2.0.0",
    "vendor_id": "neguinho_motors",
    ...
  },
  "chunks": [
    {
      "symbol": "COMPANY_001",
      "keyword": "company_info",
      "tags": ["company", "business", ...],
      "mapping": {
        "category": "company",
        "subcategory": "general",
        "priority": "high",
        "domain": "neguinhomotors"
      },
      "metadata": {
        "source": "company",
        "vendor_id": "neguinho_motors",
        ...
      },
      "content": "NEGUINHO MOTORS LTD (Company Number: 11600635)..."
    }
  ]
}
```

### What Happens Automatically

When you **reload the knowledge base** with MVS enabled:

1. **Sparse embeddings are generated automatically** from the `content` field
2. **Sparse embeddings are stored in ChromaDB metadata** (not in the JSON file)
3. **No changes to the JSON file** are needed or made

### What You DO Need to Do

#### 1. Enable MVS in Config (Already Done ✅)

The Neguinho Motors config has been updated with MVS settings:

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

#### 2. Reload Knowledge Base

To activate MVS for Neguinho Motors:

**Option A: Via Admin Panel**
1. Go to Admin Panel → Knowledge Base tab
2. Click "Save & Reload" or "Reload Knowledge Base"
3. MVS will automatically generate sparse embeddings

**Option B: Via API**
```bash
POST /api/v1/rag/load?vendor_id=neguinho_motors
```

**Option C: Automatic on Next Server Start**
- If ChromaDB collection is empty or chunk count doesn't match, it auto-reloads
- MVS sparse embeddings will be generated automatically

### What Gets Stored Where

**In Knowledge Base JSON (unchanged):**
- Chunk structure (symbol, keyword, tags, mapping, metadata, content)
- All existing fields remain the same

**In ChromaDB (automatically generated):**
- **Dense embeddings**: Stored in ChromaDB vectors (as before)
- **Sparse embeddings**: Stored in ChromaDB metadata as JSON string
  ```json
  {
    "sparse_embedding": "{\"motorcycle\": 2.5, \"rental\": 1.8, ...}",
    "sparse_model": "bm25"
  }
  ```

### Verification

After reloading, you can verify MVS is working:

1. **Check logs:**
   ```
   Initialized sparse index with X documents
   Loaded X chunks into vector database
   ```

2. **Check ChromaDB metadata:**
   - Each chunk should have `sparse_embedding` in metadata
   - Each chunk should have `sparse_model: "bm25"` in metadata

3. **Test queries:**
   - Send a query and check logs for "MVS hybrid" message
   - Compare retrieval quality with MVS enabled vs disabled

### Summary

✅ **Knowledge Base JSON**: No changes needed  
✅ **Config File**: MVS settings added (already done)  
✅ **Next Step**: Reload knowledge base to generate sparse embeddings  
✅ **Storage**: Sparse embeddings stored in ChromaDB, not JSON  

The system is designed to be **backward compatible** - your existing knowledge bases work without any modifications!

