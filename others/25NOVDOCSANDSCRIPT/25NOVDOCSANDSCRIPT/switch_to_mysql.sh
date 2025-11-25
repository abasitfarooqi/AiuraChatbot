#!/bin/bash
# Quick script to switch to MySQL and test connection

echo "=== Switching to MySQL ==="

# Set environment variables
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots

echo "Environment variables set:"
echo "  USE_MYSQL=$USE_MYSQL"
echo "  MYSQL_USER=$MYSQL_USER"
echo "  MYSQL_DATABASE=$MYSQL_DATABASE"
echo ""

# Activate venv and test
source venv/bin/activate

echo "Testing MySQL connection..."
python3 scripts/test_mysql_connection.py

echo ""
echo "✅ To use MySQL, run:"
echo "  source scripts/switch_to_mysql.sh"
echo ""
echo "Or add to your shell profile:"
echo "  export USE_MYSQL=true"
echo "  export MYSQL_PASSWORD=abc123"

