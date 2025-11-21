#!/bin/bash
# Start AiuraChatbot server with authentication

cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Set MySQL environment variables
export USE_MYSQL=true
export MYSQL_USER=root
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots
export JWT_SECRET_KEY=${JWT_SECRET_KEY:-"test-secret-key-change-in-production"}

# Start server
echo "🚀 Starting AiuraChatbot server..."
echo "📝 MySQL: $MYSQL_DATABASE"
echo "🔐 JWT Secret: ${JWT_SECRET_KEY:0:20}..."
echo ""
echo "🌐 Access URLs:"
echo "   Login: http://127.0.0.1:8000/login.html"
echo "   Admin: http://127.0.0.1:8000/admin.html"
echo "   Chatbot: http://127.0.0.1:8000/"
echo "   API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "🔑 Test Credentials:"
echo "   Super Admin: admin@aiurachatbot.com / admin123"
echo "   Vendor Admin: admin@neguinhomotors.co.uk / neguinho123"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

