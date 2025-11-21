#!/bin/bash
# Complete setup: Create MySQL database, user, and migrate from SQLite

set -e

echo "=== AiuraChatbot MySQL Setup & Migration ==="
echo ""

# Check MySQL is running
if ! brew services list | grep -q "mysql.*started"; then
    echo "Starting MySQL..."
    brew services start mysql
    sleep 3
fi

# Get MySQL root password (or empty)
echo "MySQL Root Access:"
echo "If your MySQL root user has a password, you'll be prompted."
echo "If no password, just press Enter."
echo ""

# Create database and user
echo "Creating database and user..."

# Try with empty password first, then prompt if needed
mysql -u root <<'MYSQL_SCRIPT' 2>/dev/null || mysql -u root -p <<'MYSQL_SCRIPT'
CREATE DATABASE IF NOT EXISTS aiura_chatbots CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

DROP USER IF EXISTS 'aiura_chatbot'@'localhost';
CREATE USER 'aiura_chatbot'@'localhost' IDENTIFIED BY 'abc123';

GRANT ALL PRIVILEGES ON aiura_chatbots.* TO 'aiura_chatbot'@'localhost';

FLUSH PRIVILEGES;

SELECT 'Database and user created successfully!' AS Status;
MYSQL_SCRIPT

if [ $? -eq 0 ]; then
    echo "✅ MySQL database and user created!"
    echo ""
    echo "Database: aiura_chatbots"
    echo "User: aiura_chatbot"
    echo "Password: abc123"
    echo ""
    
    # Create .env file for MySQL
    echo "Creating .env file for MySQL..."
    cat > .env.mysql <<EOF
# MySQL Configuration
USE_MYSQL=true
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=aiura_chatbot
MYSQL_PASSWORD=abc123
MYSQL_DATABASE=aiura_chatbots
EOF
    
    echo "✅ Created .env.mysql file"
    echo ""
    echo "Now running migration..."
    echo ""
    
    # Export environment variables
    export USE_MYSQL=true
    export MYSQL_HOST=localhost
    export MYSQL_PORT=3306
    export MYSQL_USER=aiura_chatbot
    export MYSQL_PASSWORD=abc123
    export MYSQL_DATABASE=aiura_chatbots
    
    # Run migration
    source venv/bin/activate
    python3 scripts/migrate_sqlite_to_mysql.py
    
    echo ""
    echo "✅ Migration complete!"
    echo ""
    echo "To use MySQL, set environment variables:"
    echo "  export USE_MYSQL=true"
    echo "  export MYSQL_PASSWORD=abc123"
    echo ""
    echo "Or copy .env.mysql to .env and source it"
    
else
    echo "❌ Failed to setup MySQL"
    exit 1
fi

