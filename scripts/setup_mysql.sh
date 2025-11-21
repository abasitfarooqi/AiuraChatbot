#!/bin/bash
# Setup script for MySQL database initialization

set -e

echo "=== AiuraChatbot MySQL Database Setup ==="

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo "Error: MySQL client not found. Please install MySQL first."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
MYSQL_HOST=${MYSQL_HOST:-localhost}
MYSQL_PORT=${MYSQL_PORT:-3306}
MYSQL_USER=${MYSQL_USER:-aiura_chatbot}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
MYSQL_DATABASE=${MYSQL_DATABASE:-aiura_chatbots}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-}

echo "Database Configuration:"
echo "  Host: $MYSQL_HOST"
echo "  Port: $MYSQL_PORT"
echo "  User: $MYSQL_USER"
echo "  Database: $MYSQL_DATABASE"

# Prompt for root password if not set
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    read -sp "Enter MySQL root password: " MYSQL_ROOT_PASSWORD
    echo
fi

# Create database and user
echo "Creating database and user..."

mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';
GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "✓ Database and user created successfully"
else
    echo "✗ Error creating database or user"
    exit 1
fi

# Update .env file
if [ ! -f .env ]; then
    cat > .env <<EOF
# MySQL Configuration
USE_MYSQL=true
MYSQL_HOST=$MYSQL_HOST
MYSQL_PORT=$MYSQL_PORT
MYSQL_USER=$MYSQL_USER
MYSQL_PASSWORD=$MYSQL_PASSWORD
MYSQL_DATABASE=$MYSQL_DATABASE
EOF
    echo "✓ Created .env file with MySQL configuration"
else
    echo "⚠ .env file already exists. Please update it manually with:"
    echo "  USE_MYSQL=true"
    echo "  MYSQL_HOST=$MYSQL_HOST"
    echo "  MYSQL_PORT=$MYSQL_PORT"
    echo "  MYSQL_USER=$MYSQL_USER"
    echo "  MYSQL_PASSWORD=$MYSQL_PASSWORD"
    echo "  MYSQL_DATABASE=$MYSQL_DATABASE"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Run: python -m backend.config.database create_database_if_not_exists"
echo "2. Run: python -m alembic upgrade head (if using Alembic)"
echo "3. Or run: python -c 'from backend.config.database import init_database; init_database()'"
echo "4. Start the server: python -m uvicorn backend.app.main:app --reload"

