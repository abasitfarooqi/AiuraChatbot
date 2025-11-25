# 🚀 How to Start and Test the Chatbot

## Quick Start (3 Steps)

### Step 1: Start the Server

Open a terminal and run:

```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Keep this terminal open!** The server needs to keep running.

---

### Step 2: Open the Chat Interface

**Option A: Chat Interface (Recommended)**
1. Open your web browser
2. Go to: `file:///Users/abdulbasit/Projects/HybridApps/AiuraChatbot/frontend/index.html`
   - Or simply double-click `frontend/index.html` in Finder
3. Start chatting!

**Option B: Admin Panel**
1. Open: `file:///Users/abdulbasit/Projects/HybridApps/AiuraChatbot/frontend/admin.html`
2. View system status and manage models

**Option C: API Documentation**
1. Open: http://localhost:8000/docs
2. Interactive API testing interface

---

### Step 3: Test It!

#### Test in Browser (Chat Interface)
1. Type a message like: "What is the rental price for Honda PCX 125?"
2. Click "Send"
3. See the response!

#### Test via API (Terminal)
Open a **new terminal** (keep server running) and run:

```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","message":"What is the rental price?"}'
```

#### Test via API Documentation
1. Go to http://localhost:8000/docs
2. Click on `POST /api/v1/chat/message`
3. Click "Try it out"
4. Enter:
   ```json
   {
     "user_id": "test_user",
     "message": "What is the rental price for Honda PCX 125?"
   }
   ```
5. Click "Execute"

---

## Example Questions to Test

Try these questions:

✅ **Domain Questions (Should work):**
- "What is the rental price for Honda PCX 125?"
- "Do you offer finance options?"
- "What are your opening hours?"
- "Tell me about your services"
- "What branches do you have?"

❌ **Out-of-Domain Questions (Should be rejected):**
- "What is the capital of France?"
- "Tell me a joke"
- "What's the weather?"

---

## Troubleshooting

### Server Won't Start?
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill existing process if needed
pkill -f "uvicorn backend.app.main:app"

# Try starting again
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Ollama Not Working?
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama
ollama serve
```

### Frontend Not Loading?
- Make sure the server is running first
- Check browser console for errors (F12)
- Try accessing API docs: http://localhost:8000/docs

---

## Quick Commands

### Start Server
```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Stop Server
Press `Ctrl+C` in the terminal where server is running

### Check Server Status
```bash
curl http://localhost:8000/health
```

### View Logs
Server logs appear in the terminal where you started it.

---

## Access Points Summary

| Interface | URL/Path |
|-----------|----------|
| **Chat Interface** | `frontend/index.html` (open in browser) |
| **Admin Panel** | `frontend/admin.html` (open in browser) |
| **API Docs** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |
| **API Base** | http://localhost:8000/api/v1 |

---

## Need Help?

1. Check server is running: `curl http://localhost:8000/health`
2. Check logs in the terminal
3. See `README.md` for detailed documentation
4. See `DOCUMENTATION.md` for complete guide

---

**🎉 You're ready to go! Start the server and open the chat interface!**

