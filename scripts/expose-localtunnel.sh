#!/bin/bash

# localtunnel Script for Exposing Chatbot Backend
# This script starts a localtunnel to expose localhost:8000

echo "🌐 Starting localtunnel..."
echo ""
echo "Make sure your chatbot server is running on http://localhost:8000"
echo "Press Ctrl+C to stop the tunnel"
echo ""

# Check if localtunnel is installed
if ! command -v lt &> /dev/null; then
    echo "❌ localtunnel is not installed!"
    echo ""
    echo "Install it with:"
    echo "  npm install -g localtunnel"
    echo ""
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

# Ask for custom subdomain (optional)
read -p "Enter custom subdomain (or press Enter for random): " subdomain

if [ -z "$subdomain" ]; then
    echo "🚀 Starting tunnel to http://localhost:8000 (random subdomain)..."
    echo ""
    lt --port 8000
else
    echo "🚀 Starting tunnel to http://localhost:8000 (subdomain: $subdomain)..."
    echo ""
    lt --port 8000 --subdomain "$subdomain"
fi

