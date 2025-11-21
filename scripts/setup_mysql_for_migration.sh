#!/bin/bash
# Setup MySQL database and user for AiuraChatbot migration

echo "=== Setting up MySQL for AiuraChatbot ==="

# Check if MySQL is running
if ! brew services list | grep -q "mysql.*started"; then
    echo "Starting MySQL..."
    brew services start mysql
    sleep 3
fi

# Try to connect as root (with or without password)
echo "Creating database and user..."

# Try without password first
mysql -u root <<EOF 2>/dev/null || mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS aiura_chatbots CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user if not exists
CREATE USER IF NOT EXISTS 'aiura_chatbot'@'localhost' IDENTIFIED BY 'abc123';

-- Grant privileges
GRANT ALL PRIVILEGES ON aiura_chatbots.* TO 'aiura_chatbot'@'localhost';

FLUSH PRIVILEGES;

SELECT 'Database and user created successfully!' AS Status;
EOF

if [ $? -eq 0 ]; then
    echo "✅ MySQL setup complete!"
    echo ""
    echo "Database: aiura_chatbots"
    echo "User: aiura_chatbot"
    echo "Password: abc123"
else
    echo "❌ Failed to setup MySQL. You may need to:"
    echo "   1. Enter MySQL root password when prompted"
    echo "   2. Or run: mysql -u root -p and execute the SQL manually"
fi

