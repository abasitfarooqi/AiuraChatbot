#!/bin/bash

# ngrok Script for Exposing Chatbot Backend
# This script starts an ngrok tunnel to expose localhost:8000

echo "🌐 Starting ngrok..."
echo ""
echo "Make sure your chatbot server is running on http://localhost:8000"
echo "Press Ctrl+C to stop the tunnel"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed!"
    echo ""
    echo "Install it with:"
    echo "  brew install ngrok/ngrok/ngrok"
    echo ""
    echo "Or download from: https://ngrok.com/download"
    echo ""
    echo "After installation, sign up at https://dashboard.ngrok.com/signup"
    echo "Then run: ngrok config add-authtoken YOUR_AUTH_TOKEN"
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

# Start ngrok
echo "🚀 Starting tunnel to http://localhost:8000..."
echo "📊 ngrok web interface: http://localhost:4040"
echo ""
ngrok http 8000

