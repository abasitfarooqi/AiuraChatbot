#!/bin/bash

# Start script for AiuraChatbot Server

cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot

# Activate virtual environment
source venv/bin/activate

# Kill any existing server
pkill -f "uvicorn backend.app.main:app" 2>/dev/null
sleep 1

# Clear port if needed
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 1

echo "Starting AiuraChatbot server..."
echo "Server will run on: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

