#!/bin/bash
# Run AiuraChatbot with MySQL

echo "=== Starting AiuraChatbot with MySQL ==="

# Set MySQL environment variables
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots

echo "MySQL Configuration:"
echo "  Database: $MYSQL_DATABASE"
echo "  User: $MYSQL_USER"
echo "  Host: $MYSQL_HOST:$MYSQL_PORT"
echo ""

# Activate virtual environment
source venv/bin/activate

# Test connection first
echo "Testing MySQL connection..."
python3 scripts/test_mysql_connection.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Connection successful!"
    echo ""
    echo "Starting FastAPI server..."
    echo "Access API docs at: http://localhost:8000/docs"
    echo ""
    
    # Start server
    python3 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo ""
    echo "❌ Connection failed. Please check MySQL settings."
    exit 1
fi

