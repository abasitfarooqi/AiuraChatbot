# 🚀 Server Start Guide

## Quick Start Command

**Copy and paste this in your terminal:**

```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Keep this terminal open!** The server needs to keep running.

---

## Verify Server is Running

Open a **new terminal** and run:

```bash
curl http://localhost:8000/health
```

You should see:
```json
{"status":"healthy","version":"1.0.0"}
```

---

## Then Open Chat Interface

1. Open your browser
2. Go to: `file:///Users/abdulbasit/Projects/HybridApps/AiuraChatbot/frontend/index.html`
3. Start chatting!

---

## Stop Server

Press `Ctrl+C` in the terminal where server is running.

Or:
```bash
pkill -f "uvicorn backend.app.main:app"
```

---

## Troubleshooting

### Port Already in Use?
```bash
lsof -ti:8000 | xargs kill -9
```

### Server Won't Start?
```bash
# Check if virtual environment is activated
which python
# Should show: /Users/abdulbasit/Projects/HybridApps/AiuraChatbot/venv/bin/python

# If not, activate it:
source venv/bin/activate
```

---

**The server must be running for the chat interface to work!**

