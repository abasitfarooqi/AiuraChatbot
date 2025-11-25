# Model Table Usage in Codebase

## Where Models Table is Used

### 1. Model Loading (`backend/services/llm_service.py`)
- **Line 50**: Raw SQL query to get model by `default_model_id`
- **Line 81**: `db.query(Model).filter(Model.id == vendor.default_model_id).first()`
- **Line 105**: `db.query(Model).filter(Model.id == default_assignment.model_id).first()`
- **Uses**: `model.code` to identify the model for Ollama API calls

### 2. Model Management API (`backend/api/models.py`)
- **Line 45-49**: Query active models from database
- **Line 110-112**: Find model by `code` or `display_name` when switching
- **Line 156**: Update vendor's `default_model_id` to point to model's `id`

### 3. Model Manager (`backend/services/model_manager.py`)
- **Line 123-125**: Get active model from database
- **Uses**: SaaS `Model` table (not old `ModelConfig`)

### 4. Chat API (`backend/api/chat.py`)
- **Line 148-151**: Find model by `code` or `display_name` for usage tracking

### 5. Admin API (`backend/api/admin.py`)
- **Line 473**: Get model by `id` for vendor assignments

## How Model Switching Works

1. **Admin Panel** → Select model → Click "Switch Model"
2. **API Call**: `POST /api/v1/models/switch` with `{"provider": "ollama", "model": "qwen3:0.6b", "vendor_id": "neguinho_motors"}`
3. **Backend**:
   - Finds model in `models` table by `code` (e.g., "qwen3:0.6b")
   - Gets model's `id` (e.g., 5)
   - Updates `vendors.default_model_id = 5`
4. **Next Chat Request**:
   - `LLMService` loads vendor
   - Gets `vendor.default_model_id = 5`
   - Queries `Model.id == 5` → gets `model.code = "qwen3:0.6b"`
   - Uses `model.code` to call Ollama API

## Model Table Structure

```sql
models:
- id (INTEGER PRIMARY KEY) - Used by vendors.default_model_id
- code (VARCHAR) - Model identifier (e.g., "mistral", "qwen3:0.6b")
- display_name (VARCHAR) - Human-readable name
- provider (VARCHAR) - "ollama", "openai", etc.
- is_active (BOOLEAN) - Whether model is available
- is_cache_model (BOOLEAN) - Whether it's a lightweight cache model
```

## Important Notes

- **`vendors.default_model_id`** points to **`models.id`** (not code)
- **Ollama API calls** use **`models.code`** (e.g., "mistral", "qwen3:0.6b")
- **Model switching** updates `vendors.default_model_id` to the new model's `id`
- **Sync script** maps Ollama model names to database codes (e.g., "Mistral:latest" → "mistral")

