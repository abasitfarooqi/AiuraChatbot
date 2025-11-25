# How to Switch Model Using Frontend

## Step-by-Step Guide

### 1. Access Admin Panel
- Open your browser and go to: `http://127.0.0.1:8000/admin.html`
- Login with your admin credentials:
  - **Super Admin**: `admin@aiurachatbot.com` / `admin123`
  - **Vendor Admin**: `admin@neguinhomotors.co.uk` / `neguinho123`

### 2. Navigate to Models Tab
- After logging in, click on the **"Models"** tab in the admin panel
- This tab is located in the top navigation menu

### 3. View Current Model
- At the top of the Models section, you'll see:
  - **Current Model**: Shows the currently active model (e.g., "✓ **mistral** (ollama) (Vendor: neguinho_motors) [DATABASE]")

### 4. Select New Model
- **Provider Dropdown**: Select the provider (usually "Ollama")
- **Model Dropdown**: Select the model you want to switch to (e.g., "qwen3:0.6b", "mistral", "gemma3:270m")
  - The dropdown is populated from the database
  - Models are loaded from the `models` table

### 5. Switch Model
- Click the **"Switch Model"** button
- A confirmation alert will appear showing:
  ```
  ✅ Model switched successfully!
  
  Model: qwen3:0.6b
  Provider: ollama
  Vendor: neguinho_motors
  
  New model will be used for all future chat requests.
  ```

### 6. Verify Switch
- The "Current Model" display will automatically update
- You can also click **"Refresh Models"** button to reload the current model info
- The new model will be used for all future chat requests

## UI Elements

### Models Tab Layout
```
┌─────────────────────────────────────────┐
│ Model Management                        │
├─────────────────────────────────────────┤
│ Current Model                           │
│ ✓ mistral (ollama) (Vendor: ...)       │
│                                         │
│ Switch Model                            │
│ [Provider: Ollama ▼]                    │
│ [Model: qwen3:0.6b ▼]                  │
│                                         │
│ [Switch Model] [Refresh Models]        │
└─────────────────────────────────────────┘
```

## How It Works Behind the Scenes

1. **Frontend Request**:
   ```javascript
   POST /api/v1/models/switch
   {
     "provider": "ollama",
     "model": "qwen3:0.6b",
     "vendor_id": "neguinho_motors"
   }
   ```

2. **Backend Processing**:
   - Finds model in database by `code` (e.g., "qwen3:0.6b")
   - Gets model's `id` (e.g., 6)
   - Updates `vendors.default_model_id = 6`
   - Commits to database

3. **Next Chat Request**:
   - `LLMService` loads vendor from database
   - Gets `default_model_id = 6`
   - Queries `Model.id == 6` → gets `code = "qwen3:0.6b"`
   - Uses `qwen3:0.6b` for Ollama API calls

## Troubleshooting

### Model Not Appearing in Dropdown
- Click **"Refresh Models"** button
- Check if model exists in database: Run `scripts/sync_ollama_models_to_db.py`
- Verify model is active: Check `models.is_active = 1` in database

### Switch Not Working
- Check browser console for errors (F12 → Console)
- Verify you're logged in (check for JWT token)
- Check server logs: `tail -f logs/server.log`
- Verify database connection: Check `USE_MYSQL` environment variable

### Model Not Changing After Switch
- Wait a few seconds and refresh the page
- Check logs: `tail -f logs/chatbot.log | grep "default_model_id"`
- Verify database update: Check `vendors.default_model_id` in database
- Try switching again - the update should persist

## Quick Test

1. Switch model to `qwen3:0.6b`
2. Send a chat message
3. Check logs: `tail -f logs/chatbot.log | grep "qwen"`
4. Should see: `✅ Loaded vendor model from FRESH DB query: qwen3:0.6b`

## Notes

- **Vendor-Specific**: If you're logged in as a vendor admin, the model switch only affects that vendor
- **Super Admin**: Can switch models for any vendor by selecting the vendor first
- **Database Persistence**: Model switches are saved to the database immediately
- **Real-Time**: New model is used for the next chat request (no server restart needed)

