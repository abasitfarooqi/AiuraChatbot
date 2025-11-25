#!/bin/bash

# Stop script for AiuraChatbot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TUNNEL_PID_FILE="$PROJECT_DIR/.tunnel.pid"

echo "Stopping AiuraChatbot..."

# Find and kill uvicorn processes
pkill -f "uvicorn backend.app.main:app"

echo "AiuraChatbot stopped."

# Check if tunnel is running and prompt user
if [ -f "$TUNNEL_PID_FILE" ]; then
    PID=$(cat "$TUNNEL_PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo ""
        echo "⚠️  Tunnel is running (PID: $PID)"
        echo "Do you want to stop the tunnel as well? (y/n)"
        read -r response
        case "$response" in
            [yY]|[yY][eE][sS])
                echo "Stopping tunnel..."
                kill "$PID" 2>/dev/null
                sleep 1
                # Force kill if still running
                if ps -p "$PID" > /dev/null 2>&1; then
                    kill -9 "$PID" 2>/dev/null
                fi
                rm -f "$TUNNEL_PID_FILE"
                rm -f "$PROJECT_DIR/.tunnel_url"
                echo "✅ Tunnel stopped"
                ;;
            *)
                echo "ℹ️  Tunnel left running"
                ;;
        esac
    else
        rm -f "$TUNNEL_PID_FILE"
    fi
fi

