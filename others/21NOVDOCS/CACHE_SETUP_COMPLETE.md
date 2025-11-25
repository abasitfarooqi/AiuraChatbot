# Cache Setup Complete

## Summary

Cache functionality is now fully connected to the database and working with the chat frontend.

## Database Tables Created

### `main_cache`
- **Purpose**: Persistent cache shared across all users for a vendor
- **Key Fields**:
  - `vendor_id` (Integer, FK to `vendors.id`)
  - `cache_id` (String, unique)
  - `question`, `answer` (Text)
  - `question_embedding` (JSON)
  - `usage_count`, `tokens_saved`, `credits_saved`
  - `is_active` (Boolean)

### `temporary_cache`
- **Purpose**: Session-based cache per chat
- **Key Fields**:
  - `vendor_id` (Integer, FK to `vendors.id`)
  - `chat_id` (String, chat session UUID)
  - `cache_id` (String, unique)
  - `question`, `answer` (Text)
  - `question_embedding` (JSON)
  - `usage_count`, `tokens_saved`

## How Cache Works

### 1. During Chat (Frontend → Backend)

**Flow:**
```
User sends message → Chat API → ChatbotService.process_message()
  ↓
CacheService.check_cache() → Checks temporary cache first, then main cache
  ↓
If cache hit: Return cached answer (no LLM call)
If cache miss: Generate LLM response → Save to cache
```

**Cache Saving:**
- **Temporary Cache**: Saved for every chat response (if enabled)
- **Main Cache**: Saved for complete questions (min 10 words, configurable)

### 2. Cache Service (`backend/services/cache_service.py`)

**Key Methods:**
- `check_cache()`: Checks both temporary and main cache
- `save_to_temporary_cache()`: Saves to temporary cache
- `save_to_main_cache()`: Saves to main cache
- `_get_vendor_db_id()`: Converts vendor slug to vendor.id (Integer)

**Vendor ID Conversion:**
- Input: `vendor_id` (slug, e.g., "neguinho_motors")
- Conversion: Query `vendors` table by `slug` → get `id` (Integer)
- Database: Uses `vendor.id` (Integer) for all cache operations

### 3. Cache API (`backend/api/cache.py`)

**Endpoints:**
- `GET /api/v1/cache/main` - Get main cache entries
- `GET /api/v1/cache/temporary` - Get temporary cache entries
- `GET /api/v1/cache/stats` - Get cache statistics
- `POST /api/v1/cache/main` - Create main cache entry
- `POST /api/v1/cache/temporary` - Create temporary cache entry
- `POST /api/v1/cache/promote` - Promote temp to main
- `DELETE /api/v1/cache/main/{cache_id}` - Delete main cache entry
- `DELETE /api/v1/cache/temporary/{cache_id}` - Delete temporary cache entry

**Vendor Conversion:**
- All endpoints convert `vendor_id` (slug) to `vendor.id` (Integer) before querying

### 4. Admin Panel (`frontend/admin.html`)

**Cache Tab Features:**
- **Cache Settings**: Toggle cache usage, fallback, LLM disable
- **Cache Statistics**: View total entries, usage, tokens saved
- **Main Cache**: View, load, clear persistent cache entries
- **Temporary Cache**: View, load, clear session-based cache entries
- **Cache Actions**: Promote, toggle, delete cache entries

**JavaScript Functions:**
- `loadCacheStats()`: Loads cache statistics
- `loadMainCache()`: Loads main cache entries
- `loadTemporaryCache()`: Loads temporary cache entries
- `clearMainCache()`: Clears all main cache for vendor
- `clearTemporaryCache()`: Clears all temporary cache for vendor

## Testing

### 1. Test Cache Saving

1. Send a chat message via frontend
2. Check logs: Should see `[CACHE] ✅ Saved to temporary cache: ...`
3. Go to Admin Panel → Caching tab
4. Click "Load Entries" for Temporary Cache
5. Should see the cached Q&A pair

### 2. Test Cache Loading

1. Send the same question again
2. Check logs: Should see `[CACHE-SERVICE] ✅ Found in TEMPORARY cache`
3. Response should be instant (no LLM call)

### 3. Test Main Cache

1. Send a complete question (10+ words)
2. Check logs: Should see `[CACHE] ✅ Saved to main cache: ...`
3. Go to Admin Panel → Caching tab
4. Click "Load Entries" for Main Cache
5. Should see the cached Q&A pair

### 4. Test Cache Stats

1. Go to Admin Panel → Caching tab
2. Click "Refresh Stats"
3. Should see:
   - Main Cache: Total entries, active entries, usage count, tokens saved
   - Temporary Cache: Total entries, active chats, usage count, tokens saved

## Configuration

Cache settings are stored in unified config:
```json
{
  "chatbot_service": {
    "caching": {
      "use_cache_for_responses": true,
      "fallback_to_llm_on_cache_miss": true,
      "disable_llm_completely": false,
      "save_to_temporary_cache": true,
      "save_to_main_cache": true,
      "min_question_length_for_main_cache": 10,
      "cache_similarity_threshold": 0.85
    }
  }
}
```

## Notes

- **Vendor-Aware**: All cache operations are vendor-specific
- **Database-Backed**: All cache entries are stored in MySQL database
- **Real-Time**: Cache is checked and saved during every chat interaction
- **Automatic**: Cache saving happens automatically when LLM generates responses
- **Similarity Matching**: Uses embeddings + text similarity for intelligent matching

## Troubleshooting

### Cache Not Saving
- Check logs: `tail -f logs/chatbot.log | grep CACHE`
- Verify cache settings: Check unified config
- Verify vendor exists: Check `vendors` table

### Cache Not Loading
- Check cache tables exist: `SHOW TABLES LIKE '%cache%'`
- Verify vendor_id conversion: Check logs for `_get_vendor_db_id`
- Check cache entries: Query `main_cache` and `temporary_cache` tables

### Frontend Not Showing Cache
- Check browser console for errors
- Verify API endpoints: Test `/api/v1/cache/main` directly
- Check vendor_id is set: Verify `currentVendorId` in admin panel

