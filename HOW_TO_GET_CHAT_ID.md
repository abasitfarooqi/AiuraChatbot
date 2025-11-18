# How to Get Chat ID - Complete Guide

## ✅ Multiple Ways to Get Chat ID

### Method 1: Chat Interface Header (Easiest)
1. Open the chat interface: http://localhost:8000/
2. Look at the top-right corner of the chat header
3. You'll see: **Chat ID: [your_chat_id]**
4. Click the **"Copy"** button next to it
5. Chat ID is now in your clipboard!

### Method 2: Chat List Sidebar
1. In the chat interface, look at the left sidebar
2. Each chat shows:
   - Chat title (click to open)
   - Chat ID below it (click to copy)
3. Click on the chat ID to copy it to clipboard

### Method 3: Browser Console
1. Open browser developer tools (F12)
2. Go to Console tab
3. Type: `localStorage.getItem('chatbot_currentChatId')`
4. Press Enter
5. The current chat ID will be displayed

### Method 4: API Call
```bash
# Get all chats for a user
curl "http://localhost:8000/api/v1/chat/chats/{user_id}"

# Response includes chat_id for each chat
```

### Method 5: From Chat Response
When you send a message, the API response includes `chat_id`:
```json
{
  "response": "...",
  "chat_id": "chat_1234567890_abc123",
  ...
}
```

## Clear All Functionality

### In Chat Interface
1. **"Clear All" button** in the chat header
   - Shows next to Chat ID
   - Click to clear ALL data for current chat
   - Double confirmation required

### In Admin Panel
1. Go to: http://localhost:8000/admin
2. Click **"Memory"** tab
3. Two options:
   - **Clear Memory Only**: Clears conversation context (messages remain)
   - **Clear All Data**: Deletes everything (messages, memory, token usage)

### What Gets Cleared

**Clear Memory Only:**
- Conversation context/memory
- Chat history remains intact

**Clear All Data:**
- ✅ All messages
- ✅ Conversation memory
- ✅ Token usage records
- ⚠️ Chat record remains (so you can still see it in list, but it's empty)

## API Endpoints

### Clear Memory Only
```bash
POST /api/v1/chat/memory/clear/{chat_id}
```

### Clear All Data
```bash
POST /api/v1/chat/clear/{chat_id}
```

Response:
```json
{
  "status": "success",
  "message": "All data cleared for chat {chat_id}",
  "deleted": {
    "messages": 5,
    "memory": 1,
    "token_usage": 3
  }
}
```

## Quick Reference

| Method | Location | Action |
|--------|----------|--------|
| Header Copy Button | Chat interface header | Click to copy |
| Sidebar Chat ID | Left sidebar, under chat title | Click to copy |
| Browser Console | F12 → Console | Type command |
| API | `/api/v1/chat/chats/{user_id}` | Get all chats |
| Clear All Button | Chat interface header | Clear current chat |

## Example Workflow

1. **Start a chat** → Chat ID appears in header
2. **Click "Copy"** → Chat ID copied to clipboard
3. **Go to Admin Panel** → Memory tab
4. **Paste chat_id** → Enter in "Clear All Chat Data" field
5. **Click "Clear All Data"** → Double confirm
6. **Done!** → All data deleted

## Notes

- Chat ID is always visible in the chat header
- You can copy it with one click
- Clear All requires double confirmation for safety
- Clearing doesn't delete the chat record itself (so it stays in your list, but empty)

