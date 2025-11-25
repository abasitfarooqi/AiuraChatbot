# LLM Configuration and Cache Setup

## Overview
This document describes the LLM Configuration and Cache functionality that has been implemented with database connectivity.

## Database Tables

### ModelConfig
Stores LLM configuration settings (max_tokens, temperature, top_p, top_k) for each model, optionally per vendor.

**Schema:**
- `id` (BigInteger, PK)
- `model_id` (BigInteger, FK to models.id)
- `vendor_id` (BigInteger, FK to vendors.id, nullable - NULL = global config)
- `max_tokens` (Integer, default: 4000)
- `temperature` (Numeric(3,2), default: 0.7)
- `top_p` (Numeric(3,2), default: 0.9)
- `top_k` (Integer, default: 40)
- `is_active` (Boolean, default: True)
- `created_at`, `updated_at` (DateTime)

**Unique Constraint:** `(model_id, vendor_id)` - ensures one config per model per vendor

### ModelPreset
Stores preset configurations for quick switching.

**Schema:**
- `id` (BigInteger, PK)
- `name` (String(200))
- `description` (Text, nullable)
- `model_id` (BigInteger, FK to models.id, nullable - NULL = applies to any model)
- `vendor_id` (BigInteger, FK to vendors.id, nullable - NULL = global preset)
- `max_tokens`, `temperature`, `top_p`, `top_k` (same as ModelConfig)
- `is_default` (Boolean, default: False)
- `is_active` (Boolean, default: True)
- `created_by` (BigInteger, FK to admins.id, nullable)
- `created_at`, `updated_at`, `deleted_at` (DateTime)

## API Endpoints

### LLM Configuration

#### GET `/api/v1/models/config`
Get LLM configuration for active model (vendor-aware).

**Query Parameters:**
- `vendor_id` (optional): Vendor slug

**Response:**
```json
{
  "model_code": "mistral",
  "model_id": 1,
  "max_tokens": 4000,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "source": "database"
}
```

#### POST `/api/v1/models/config`
Update LLM configuration for active model (vendor-aware).

**Request Body:**
```json
{
  "max_tokens": 4000,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "vendor_id": "neguinho_motors"  // optional
}
```

**Response:**
```json
{
  "status": "success",
  "config": {
    "model_id": 1,
    "vendor_id": "neguinho_motors",
    "max_tokens": 4000,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40
  },
  "message": "LLM configuration updated in database"
}
```

### Presets

#### GET `/api/v1/models/presets`
Get all presets (optionally filtered by vendor or model).

**Query Parameters:**
- `vendor_id` (optional): Vendor slug
- `model_id` (optional): Model ID

**Response:**
```json
{
  "presets": [
    {
      "id": 1,
      "name": "Creative Mode",
      "description": "High creativity for creative tasks",
      "model_id": null,
      "vendor_id": null,
      "max_tokens": 4000,
      "temperature": 1.2,
      "top_p": 0.95,
      "top_k": 50,
      "is_default": false,
      "created_at": "2025-11-21T23:00:00"
    }
  ]
}
```

#### POST `/api/v1/models/presets`
Create a new preset.

**Request Body:**
```json
{
  "name": "Creative Mode",
  "description": "High creativity for creative tasks",
  "max_tokens": 4000,
  "temperature": 1.2,
  "top_p": 0.95,
  "top_k": 50,
  "model_id": null,  // optional
  "vendor_id": "neguinho_motors"  // optional
}
```

#### PUT `/api/v1/models/presets/{preset_id}`
Update a preset.

#### DELETE `/api/v1/models/presets/{preset_id}`
Delete a preset (soft delete).

#### POST `/api/v1/models/presets/{preset_id}/apply`
Apply a preset to the active model configuration.

**Query Parameters:**
- `vendor_id` (optional): Vendor slug

## Frontend (admin.html)

### LLM Configuration Tab

**Location:** `frontend/admin.html` - Tab: "LLM Config"

**Features:**
1. **Active Model Display**: Shows the current active model for the vendor
2. **Configuration Inputs**:
   - Max Tokens (100-4000)
   - Temperature (0.0-2.0)
   - Top P (0.0-1.0)
   - Top K (1-100)
3. **Actions**:
   - **Update Configuration**: Saves config to database
   - **Load Current**: Loads config from database
   - **Save as Preset**: Quick action to save current config as preset
4. **Presets Section**:
   - **Select Preset**: Dropdown of available presets
   - **Apply Preset**: Applies selected preset to active model
   - **Delete Preset**: Deletes selected preset
   - **Create New Preset**: Form to create a new preset

**JavaScript Functions:**
- `loadLLMConfig()`: Loads current config and active model info
- `updateLLMConfig()`: Updates config in database
- `loadPresets()`: Loads available presets
- `createPreset()`: Creates a new preset
- `applyPreset()`: Applies a preset to active model
- `deletePreset()`: Deletes a preset
- `saveAsPreset()`: Quick action to save current config as preset

## Cache Functionality

### Cache Settings
Cache settings are stored in the unified config file (`config/vendors/{vendor_id}/unified_config.json`) under `chatbot_service.caching`.

**API Endpoints:**
- `GET /api/v1/cache/settings?vendor_id={vendor_id}`: Get cache settings
- `POST /api/v1/cache/settings?vendor_id={vendor_id}`: Update cache settings

**Cache Settings:**
- `use_cache_for_responses`: Enable/disable cache
- `fallback_to_llm_on_cache_miss`: Use LLM if cache miss
- `disable_llm_completely`: Cache-only mode (no LLM)
- `cache_model_provider`: Provider for cache model
- `cache_model_name`: Model name for cache
- `use_lightweight_model_for_cache`: Use lightweight model for cache responses

### Cache Tabs in Admin Panel

**Location:** `frontend/admin.html` - Tab: "Caching"

**Features:**
1. **Cache Settings Toggles**:
   - Use Cache for Responses
   - Fallback to LLM on Cache Miss
   - Disable LLM Completely (Cache Only)
   - Use Lightweight Model for Cache
2. **Cache Model Selection**: Select provider and model for cache responses
3. **Cache Statistics**: View cache hit/miss stats
4. **Main Cache**: View and manage persistent cache entries
5. **Temporary Cache**: View and manage session-based cache entries
6. **Cache Actions**: Promote, toggle, delete cache entries

**Database Tables:**
- `main_cache`: Persistent cache entries
- `temporary_cache`: Session-based cache entries

## Setup Instructions

### 1. Create Database Tables

Run the migration script:
```bash
python3 scripts/add_model_presets_tables.py
```

### 2. Verify Tables Created

Check MySQL:
```sql
SHOW TABLES LIKE 'model_%';
DESCRIBE model_configs;
DESCRIBE model_presets;
```

### 3. Test API Endpoints

```bash
# Get current config
curl -X GET "http://127.0.0.1:8000/api/v1/models/config?vendor_id=neguinho_motors"

# Update config
curl -X POST "http://127.0.0.1:8000/api/v1/models/config" \
  -H "Content-Type: application/json" \
  -d '{"max_tokens": 3000, "temperature": 0.8, "vendor_id": "neguinho_motors"}'

# Get presets
curl -X GET "http://127.0.0.1:8000/api/v1/models/presets?vendor_id=neguinho_motors"

# Create preset
curl -X POST "http://127.0.0.1:8000/api/v1/models/presets" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Preset", "max_tokens": 2000, "temperature": 0.5, "top_p": 0.9, "top_k": 40}'
```

## Notes

- **Vendor-Aware**: All config operations are vendor-aware. If `vendor_id` is provided, config is vendor-specific. Otherwise, it's global.
- **Active Model Connection**: Config is always connected to the active model for the vendor (from `vendors.default_model_id`).
- **Database Persistence**: All config changes are saved to the database immediately.
- **Real-Time**: Changes take effect immediately for new chat requests (no server restart needed).
- **Cache Settings**: Cache settings are stored in unified config files, not in the database (for now).

## Troubleshooting

### Config Not Loading
- Check if active model is set: `SELECT default_model_id FROM vendors WHERE slug = 'neguinho_motors'`
- Check if config exists: `SELECT * FROM model_configs WHERE model_id = ? AND vendor_id = ?`

### Presets Not Appearing
- Check if presets exist: `SELECT * FROM model_presets WHERE is_active = 1 AND deleted_at IS NULL`
- Verify vendor_id filter is correct

### Cache Not Working
- Check cache settings in unified config: `config/vendors/{vendor_id}/unified_config.json`
- Verify cache tables exist: `SHOW TABLES LIKE '%cache%'`
- Check cache service logs: `tail -f logs/chatbot.log | grep cache`

