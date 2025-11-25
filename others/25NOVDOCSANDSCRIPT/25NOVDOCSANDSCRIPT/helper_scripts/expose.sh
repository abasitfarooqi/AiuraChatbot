#!/bin/bash

# Cloudflare Tunnel Expose Script
# Quick command to expose chatbot backend to Laravel or any frontend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR" || exit 1

echo "🌐 Cloudflare Tunnel - Expose Chatbot Backend"
echo "=============================================="
echo ""

# Run the main management script with expose command
exec "$PROJECT_DIR/scripts/manage.sh" expose
