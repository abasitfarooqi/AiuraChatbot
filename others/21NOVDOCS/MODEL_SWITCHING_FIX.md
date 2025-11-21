# Model Switching Fix - 21 Nov 2025

## Summary
Fixed model switching to use **ONLY the database** as the single source of truth. Removed all config file fallbacks.

## Changes Made

### 1. Cleaned Up Project
- Moved unused documentation to `others/21NOVDOCS/`
- Moved deprecated config files to `others/deprecated_configs/`
- Removed unused vendor configs (kept only `neguinho_motors`)

### 2. Model Loading - Database Only
**File**: `backend/services/llm_service.py`
- Removed all config file fallbacks
- Models MUST be loaded from database
- If vendor has no model in database, raises error (no silent fallback)
- Global instances also MUST load from database

### 3. Model Management API
**File**: `backend/api/models.py`
- `/models/available` now returns models from **database first**
- Optionally shows Ollama models not in database (for discovery)
- `/models/current` returns model from database (vendor-aware)

### 4. Admin Panel - Single Source of Truth
**File**: `frontend/admin.html`
- Model Management tab (lines 356-383) is the **ONLY** place to switch models
- Loads models from database
- Shows current model with `[DATABASE]` indicator
- Model switching updates database immediately

### 5. Ollama Model Sync
**File**: `scripts/sync_ollama_models_to_db.py`
- New script to sync Ollama models to database
- Run: `python3 scripts/sync_ollama_models_to_db.py`
- Adds all installed Ollama models to database

## How It Works Now

1. **Model Selection**: Admin panel → Models tab → Select model → Switch
2. **Database Update**: Updates `vendors.default_model_id` in database
3. **Model Loading**: `LLMService` loads model from database (fresh query every time)
4. **No Config Fallback**: If model not in database, raises error

## Testing

```bash
# Sync Ollama models to database
python3 scripts/sync_ollama_models_to_db.py

# Switch model via admin panel
# http://127.0.0.1:8000/admin.html → Models tab

# Verify model is loaded from database
curl 'http://127.0.0.1:8000/api/v1/models/current?vendor_id=neguinho_motors'
```

## Important Notes

- **Models MUST be in database** - no config file fallback
- **Admin panel is the ONLY way to switch models** - no manual config editing
- **Database is the single source of truth** - all model selection comes from DB

