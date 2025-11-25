# Model Switching Database Connection Verification

## Database Connection Flow

### 1. Database Session Creation
**File**: `backend/api/models.py`
- Line 17-23: Uses `get_db()` dependency which calls `get_session_local()`
- `get_session_local()` comes from `backend.models.database` or `backend.config.database`
- This uses the database engine configured in `backend/config/database.py`

### 2. Database Selection Logic
**File**: `backend/config/database.py`
- Line 37: Checks `USE_MYSQL` environment variable
- If `USE_MYSQL=true`: Uses MySQL with connection from env vars:
  - `MYSQL_HOST` (default: localhost)
  - `MYSQL_PORT` (default: 3306)
  - `MYSQL_USER` (default: aiura_chatbot)
  - `MYSQL_PASSWORD` (default: abc123)
  - `MYSQL_DATABASE` (default: aiura_chatbots)
- If `USE_MYSQL=false` or not set: Uses SQLite from `settings.database_url`

### 3. Model Switching Process
**File**: `backend/api/models.py` - `switch_model()` function

1. **Get Database Session** (Line 91):
   ```python
   db: Session = Depends(get_db)
   ```
   - This gets a database session from the configured database (MySQL or SQLite)

2. **Query Vendor** (Line 101-104):
   ```python
   vendor = db.query(Vendor).filter(
       Vendor.slug == request.vendor_id,
       Vendor.deleted_at.is_(None)
   ).first()
   ```
   - Queries `vendors` table in the database

3. **Query Model** (Line 110-112):
   ```python
   model = db.query(Model).filter(
       (Model.code == request.model) | (Model.display_name == request.model)
   ).first()
   ```
   - Queries `models` table in the database

4. **Update Vendor** (Line 156):
   ```python
   vendor.default_model_id = model.id
   db.commit()
   ```
   - Updates `vendors.default_model_id` in the database
   - Commits the transaction

5. **Verify Update** (Line 170-199):
   ```python
   db.expire_all()  # Force fresh query
   vendor_verify = db.query(Vendor).filter(...).first()
   if vendor_verify.default_model_id != model.id:
       # Use raw SQL to force update
       db.execute(text("UPDATE vendors SET default_model_id = :model_id WHERE id = :vendor_id"))
   ```
   - Verifies the update was committed
   - Uses raw SQL if ORM update didn't work

### 4. Model Loading Process
**File**: `backend/services/llm_service.py` - `__init__()` method

1. **Raw SQL Query** (Line 49-52):
   ```python
   result = db.execute(
       text("SELECT v.id, v.default_model_id, m.code, m.provider FROM vendors v LEFT JOIN models m ON v.default_model_id = m.id WHERE v.slug = :slug"),
       {"slug": vendor_id}
   ).first()
   ```
   - Uses raw SQL to bypass ORM caching
   - Gets fresh `default_model_id` from database
   - Joins with `models` table to get model `code`

2. **Use Model Code** (Line 63):
   ```python
   self.current_model = fresh_model_code  # e.g., "qwen3:0.6b"
   ```
   - Uses the model code from database for Ollama API calls

## Verification Steps

### Check Which Database is Being Used

1. **Check Server Logs**:
   ```bash
   tail -100 logs/server.log | grep "Using.*database"
   ```
   Should show: `Using MySQL database: localhost:3306/aiura_chatbots` or `Using SQLite database: ...`

2. **Check Environment Variables**:
   ```bash
   echo $USE_MYSQL
   echo $MYSQL_DATABASE
   ```

3. **Test Model Switch**:
   ```bash
   curl -X POST 'http://127.0.0.1:8000/api/v1/models/switch' \
     -H 'Content-Type: application/json' \
     -d '{"provider": "ollama", "model": "qwen3:0.6b", "vendor_id": "neguinho_motors"}'
   ```

4. **Check Logs for Database Operations**:
   ```bash
   tail -50 logs/server.log | grep -E "Committed|default_model_id|Verified"
   ```
   Should show:
   - `✅ Committed vendor model update: vendor_id=1, default_model_id=6`
   - `✅ Verified vendor neguinho_motors model update - default_model_id: 6`

5. **Verify Model Loading**:
   ```bash
   tail -30 logs/chatbot.log | grep "Fresh DB query"
   ```
   Should show:
   - `📊 Fresh DB query (by slug): vendor_slug=neguinho_motors, default_model_id=6, model_code=qwen3:0.6b`

## Database Tables Used

1. **`vendors`** table:
   - `id` (INTEGER) - Vendor ID
   - `slug` (VARCHAR) - Vendor slug (e.g., "neguinho_motors")
   - `default_model_id` (INTEGER) - Foreign key to `models.id`

2. **`models`** table:
   - `id` (INTEGER) - Model ID
   - `code` (VARCHAR) - Model code (e.g., "mistral", "qwen3:0.6b")
   - `display_name` (VARCHAR) - Human-readable name
   - `provider` (VARCHAR) - Provider (e.g., "ollama")

3. **`vendor_model_assignments`** table:
   - `vendor_id` (INTEGER) - Foreign key to `vendors.id`
   - `model_id` (INTEGER) - Foreign key to `models.id`
   - `is_default` (BOOLEAN) - Whether this is the default model

## Conclusion

✅ **Model switching IS connected to your database** (MySQL or SQLite based on `USE_MYSQL` env var)

- All queries use SQLAlchemy ORM which connects to the configured database
- Updates are committed with `db.commit()`
- Verification uses fresh queries to ensure data persistence
- Raw SQL is used as fallback if ORM update fails

The database connection is determined by the `USE_MYSQL` environment variable when the server starts.

