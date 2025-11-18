# Chat Persistence & Admin Controls - Complete Guide

## ✅ Issues Fixed

### 1. Chat Persistence on Page Refresh
**Problem:** Chats disappeared when refreshing the page because:
- `userId` was regenerated on each page load
- `currentChatId` was not saved

**Solution:**
- `userId` is now stored in `localStorage` and persists across page refreshes
- `currentChatId` is saved to `localStorage` when a chat is created/loaded
- On page load, the last active chat is automatically loaded
- Chat history is restored from the database

### 2. Memory Clear Functionality
**Added:**
- API endpoint: `POST /api/v1/chat/memory/clear/{chat_id}`
- Admin panel "Memory" tab with clear memory button
- Clears conversation context while preserving chat history

### 3. Token/Response Length Control
**Added:**
- API endpoints for getting/updating LLM configuration
- Admin panel "Configuration" tab with controls for:
  - Max Tokens (response length): 100-4000
  - Temperature: 0.0-2.0
  - Top P: 0.0-1.0
  - Top K: 1-100

## How It Works

### Chat Persistence

**Frontend (`frontend/index.html`):**
```javascript
// userId persists in localStorage
let userId = localStorage.getItem('chatbot_userId') || generateNewUserId();

// currentChatId persists in localStorage
let currentChatId = localStorage.getItem('chatbot_currentChatId');

// On page load, restore last chat
if (currentChatId) {
    loadChat(currentChatId);
}
```

**Benefits:**
- Same user ID across sessions
- Last chat automatically restored
- All previous chats accessible in sidebar

### Memory Clear

**API Endpoint:**
```bash
POST /api/v1/chat/memory/clear/{chat_id}
```

**Admin Panel:**
1. Go to "Memory" tab
2. Enter chat_id
3. Click "Clear Memory"
4. Confirmation dialog appears

**What it does:**
- Deletes `ConversationMemory` record for the chat
- Chat history (messages) remains intact
- Bot will not remember previous context in that chat
- Next message starts fresh context

### Token/Response Length Control

**API Endpoints:**
```bash
# Get current config
GET /api/v1/models/config

# Update config
POST /api/v1/models/config
{
    "max_tokens": 2500,
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40
}
```

**Admin Panel:**
1. Go to "Configuration" tab
2. Adjust settings:
   - **Max Tokens**: Controls response length (100-4000)
   - **Temperature**: Controls creativity (0.0-2.0, lower = more focused)
   - **Top P**: Nucleus sampling (0.0-1.0)
   - **Top K**: Top K sampling (1-100)
3. Click "Update Configuration"
4. Settings are saved to database and applied immediately

## Usage Examples

### Clear Memory via API
```bash
curl -X POST "http://localhost:8000/api/v1/chat/memory/clear/chat_123456" \
  -H "Content-Type: application/json"
```

### Update Token Limit via API
```bash
curl -X POST "http://localhost:8000/api/v1/models/config" \
  -H "Content-Type: application/json" \
  -d '{
    "max_tokens": 3000,
    "temperature": 0.6
  }'
```

### Get Current Config
```bash
curl "http://localhost:8000/api/v1/models/config"
```

## Admin Panel Tabs

1. **Dashboard** - Statistics and overview
2. **Models** - Model switching and management
3. **RAG** - Knowledge base management
4. **Memory** - Clear chat memory
5. **Configuration** - LLM token/response controls

## Technical Details

### localStorage Keys
- `chatbot_userId` - Persistent user identifier
- `chatbot_currentChatId` - Last active chat ID

### Database Changes
- `ModelConfig` table stores token/response settings
- `ConversationMemory` table stores chat context (can be cleared)

### Settings Persistence
- Runtime changes are saved to database
- Settings persist across server restarts
- Can be overridden via `.env` file

## Testing

All features have been tested and are working:
- ✅ Chat persistence on page refresh
- ✅ Memory clear functionality
- ✅ Token/response length control
- ✅ Admin panel controls

## Access

- **Chat Interface**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/docs

