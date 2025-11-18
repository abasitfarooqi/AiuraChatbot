#!/bin/bash

# Quick script to get the current tunnel URL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check saved URL first
if [ -f "$PROJECT_DIR/.tunnel_url" ]; then
    TUNNEL_URL=$(cat "$PROJECT_DIR/.tunnel_url")
    echo "🌍 Tunnel URL: $TUNNEL_URL"
    echo ""
    echo "API Base: $TUNNEL_URL/api/v1"
    echo "API Docs: $TUNNEL_URL/docs"
    echo "Health:   $TUNNEL_URL/health"
    exit 0
fi

# Try to extract from logs
if [ -f "$PROJECT_DIR/logs/tunnel.log" ]; then
    TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$PROJECT_DIR/logs/tunnel.log" 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo "🌍 Tunnel URL: $TUNNEL_URL"
        echo ""
        echo "API Base: $TUNNEL_URL/api/v1"
        echo "API Docs: $TUNNEL_URL/docs"
        echo "Health:   $TUNNEL_URL/health"
        exit 0
    fi
fi

echo "❌ No tunnel URL found. Is the tunnel running?"
echo "Run: ./scripts/manage.sh expose"

