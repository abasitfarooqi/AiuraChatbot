# Model Configuration Structure

## Overview

The model configuration system uses a **three-tier fallback hierarchy**:

1. **`model_configs` table** (Runtime Configuration) - Highest priority
2. **`models.default_max_tokens`** (Model Default) - Medium priority  
3. **Settings/Config files** (Global Defaults) - Lowest priority

## Database Tables

### `models` Table
Stores model registry with **default/recommended** values for each model.

**Key Column: `default_max_tokens`**
- This is the **recommended maximum tokens** for that specific model
- Different models have different capabilities:
  - `qwen3:0.6b`: 10000 tokens (larger context window)
  - `mistral`: 4000 tokens (standard)
  - `phix`: 2000 tokens (lightweight model)
  - `gpt-4-turbox`: 4000 tokens

**Purpose:**
- Provides model-specific defaults
- Used when no runtime config exists
- Helps set reasonable limits per model

**Example:**
```sql
SELECT id, code, display_name, default_max_tokens FROM models;
```
```
id | code        | display_name | default_max_tokens
1  | mistral     | Mistral 7B   | 4000
5  | qwen3:0.6b  | Qwen 3 0.6B  | 10000
```

### `model_configs` Table
Stores **runtime configuration** that can override model defaults.

**Structure:**
- `model_id` (FK to `models.id`)
- `vendor_id` (FK to `vendors.id`, NULL = global config)
- `max_tokens` (actual runtime value)
- `temperature`, `top_p`, `top_k` (LLM parameters)

**Purpose:**
- Allows per-vendor customization
- Overrides model defaults
- Stores user-configured values from admin panel

**Example:**
```sql
SELECT * FROM model_configs WHERE model_id = 1 AND vendor_id = 1;
```
```
id | model_id | vendor_id | max_tokens | temperature | top_p | top_k
1  | 1        | 1         | 3000       | 0.8         | 0.95  | 50
```

## Configuration Loading Flow

### 1. LLMService Initialization

When `LLMService` is created:

```python
llm_service = LLMService(db=db, vendor_id="neguinho_motors")
```

**Current Behavior:**
- Loads model from `vendors.default_model_id` → `models.code`
- Uses `settings.llm_max_tokens` from config files
- **Does NOT yet load from `model_configs` table**

### 2. API Endpoint: `/api/v1/models/config`

**GET Request:**
```python
# Priority order:
1. Check model_configs table (vendor-specific or global)
2. Fall back to models.default_max_tokens
3. Fall back to settings.llm_max_tokens
```

**POST Request:**
```python
# Saves to model_configs table:
- Creates or updates config for active model
- Vendor-specific if vendor_id provided
- Global if vendor_id is None
```

### 3. LLM Generation

When generating a response:

```python
llm_service.generate(
    prompt="...",
    max_tokens=kwargs.get("max_tokens", self.settings.llm_max_tokens),
    temperature=kwargs.get("temperature", self.settings.llm_temperature)
)
```

**Current Behavior:**
- Uses `self.settings.llm_max_tokens` (from config files)
- **Does NOT yet load from `model_configs` table**

## Recommended Changes

### Update LLMService to Load from Database

**In `backend/services/llm_service.py`:**

```python
def __init__(self, db=None, vendor_id: Optional[str] = None):
    # ... existing model loading code ...
    
    # Load config from database
    if db is not None:
        self._load_model_config_from_db(db, vendor_id)

def _load_model_config_from_db(self, db, vendor_id: Optional[str] = None):
    """Load model configuration from database."""
    from backend.models.saas_models import ModelConfig, Vendor, Model
    
    model_id = None
    vendor_db_id = None
    
    # Get model_id
    if vendor_id:
        vendor = db.query(Vendor).filter(Vendor.slug == vendor_id).first()
        if vendor and vendor.default_model_id:
            model_id = vendor.default_model_id
            vendor_db_id = vendor.id
    else:
        # Global active model
        model = db.query(Model).filter(Model.is_active == True).first()
        if model:
            model_id = model.id
    
    if not model_id:
        return  # Use settings defaults
    
    # Try to load from model_configs
    config = None
    if vendor_db_id:
        config = db.query(ModelConfig).filter(
            ModelConfig.model_id == model_id,
            ModelConfig.vendor_id == vendor_db_id,
            ModelConfig.is_active == True
        ).first()
    
    if not config:
        config = db.query(ModelConfig).filter(
            ModelConfig.model_id == model_id,
            ModelConfig.vendor_id.is_(None),
            ModelConfig.is_active == True
        ).first()
    
    if config:
        # Override settings with database values
        self.settings.llm_max_tokens = int(config.max_tokens)
        self.settings.llm_temperature = float(config.temperature)
        self.settings.llm_top_p = float(config.top_p)
        self.settings.llm_top_k = int(config.top_k)
        logger.info(f"✅ Loaded model config from DB: max_tokens={config.max_tokens}, temp={config.temperature}")
    else:
        # Fall back to model default
        model = db.query(Model).filter(Model.id == model_id).first()
        if model and model.default_max_tokens:
            self.settings.llm_max_tokens = model.default_max_tokens
            logger.info(f"✅ Using model default max_tokens: {model.default_max_tokens}")
```

## Summary

### `models.default_max_tokens` Usage:
- **Purpose**: Model-specific recommended maximum tokens
- **When Used**: When no `model_configs` entry exists
- **Example**: `qwen3:0.6b` has 10000, `mistral` has 4000

### `model_configs` Table Usage:
- **Purpose**: Runtime configuration (user-customizable)
- **When Used**: Always checked first (highest priority)
- **Scope**: Can be vendor-specific or global

### Current State:
- ✅ `model_configs` table created
- ✅ API endpoints save/load from `model_configs`
- ⚠️ `LLMService` still uses `settings` (needs update to load from DB)

### Next Steps:
1. Update `LLMService.__init__` to load config from `model_configs` table
2. Fall back to `models.default_max_tokens` if no config exists
3. Fall back to `settings.llm_max_tokens` as last resort

