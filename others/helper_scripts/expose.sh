#!/bin/bash

# Universal Tunnel Script - Choose your tunnel method
# This script helps you expose your local chatbot backend to Laravel

echo "🌐 Expose Chatbot Backend to Laravel"
echo "======================================"
echo ""
echo "Choose your tunnel method:"
echo ""
echo "1) Cloudflare Tunnel (Recommended - Free, Unlimited, Stable URLs)"
echo "2) localtunnel (Free, Unlimited, Quick Setup)"
echo "3) ngrok (Free tier, requires signup)"
echo "4) Show comparison and exit"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting Cloudflare Tunnel..."
        exec "$(dirname "$0")/expose-cloudflare.sh"
        ;;
    2)
        echo ""
        echo "🚀 Starting localtunnel..."
        exec "$(dirname "$0")/expose-localtunnel.sh"
        ;;
    3)
        echo ""
        echo "🚀 Starting ngrok..."
        exec "$(dirname "$0")/expose-ngrok.sh"
        ;;
    4)
        echo ""
        echo "📊 Tunnel Comparison:"
        echo ""
        echo "┌─────────────────────┬──────────────────┬──────────────┬─────────────┐"
        echo "│ Feature              │ Cloudflare       │ localtunnel  │ ngrok       │"
        echo "├─────────────────────┼──────────────────┼──────────────┼─────────────┤"
        echo "│ Cost                 │ Free Forever     │ Free         │ Free (lim.) │"
        echo "│ Bandwidth            │ Unlimited        │ Unlimited    │ Limited     │"
        echo "│ Stable URL           │ ✅ (with setup)  │ ❌           │ ✅ (acct)   │"
        echo "│ Custom Domain        │ ✅               │ ❌           │ ✅ (paid)   │"
        echo "│ HTTPS                │ ✅               │ ✅           │ ✅          │"
        echo "│ Setup Complexity     │ Medium           │ Easy         │ Easy        │"
        echo "│ Best For             │ Production-ready │ Quick test   │ Development │"
        echo "└─────────────────────┴──────────────────┴──────────────┴─────────────┘"
        echo ""
        echo "📚 For detailed guide, see: EXPOSE_TO_LARAVEL.md"
        echo ""
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

