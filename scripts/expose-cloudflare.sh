#!/bin/bash

# Cloudflare Tunnel Script for Exposing Chatbot Backend
# This script starts a Cloudflare tunnel to expose localhost:8000

echo "🌐 Starting Cloudflare Tunnel..."
echo ""
echo "Make sure your chatbot server is running on http://localhost:8000"
echo "Press Ctrl+C to stop the tunnel"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed!"
    echo ""
    echo "Install it with:"
    echo "  brew install cloudflare/cloudflare/cloudflared"
    echo ""
    echo "Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
    exit 1
fi

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Cannot reach http://localhost:8000/health"
    echo "   Make sure your chatbot server is running!"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start Cloudflare Tunnel
echo "🚀 Starting tunnel to http://localhost:8000..."
echo ""
cloudflared tunnel --url http://localhost:8000

