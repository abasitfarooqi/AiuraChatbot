#!/bin/bash
# Fix MySQL root password to allow empty password connection
# This script helps set up MySQL for Laravel development

echo "=== MySQL Root Password Setup ==="
echo ""
echo "This script will help you configure MySQL root user for Laravel."
echo ""

# Check if MySQL is running
if ! brew services list | grep -q "mysql.*started"; then
    echo "⚠️  MySQL is not running. Starting MySQL..."
    brew services start mysql
    sleep 3
fi

echo "Choose an option:"
echo "1. Set root password to empty (for Laravel development)"
echo "2. Set root password to a specific value"
echo "3. Create new user 'laravel_user' with empty password"
echo "4. Just test current connection"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Setting root password to empty..."
        echo "You may need to enter current root password:"
        mysql -u root -p <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '';
FLUSH PRIVILEGES;
SELECT 'Root password set to empty successfully!' AS Status;
EOF
        ;;
    2)
        read -sp "Enter new root password: " new_password
        echo ""
        echo "Setting root password..."
        mysql -u root -p <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '$new_password';
FLUSH PRIVILEGES;
SELECT 'Root password updated successfully!' AS Status;
EOF
        echo ""
        echo "⚠️  Update your Laravel .env file:"
        echo "   DB_PASSWORD=$new_password"
        ;;
    3)
        echo ""
        echo "Creating laravel_user with empty password..."
        echo "You may need to enter root password:"
        mysql -u root -p <<EOF
CREATE USER IF NOT EXISTS 'laravel_user'@'localhost' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON *.* TO 'laravel_user'@'localhost';
FLUSH PRIVILEGES;
SELECT 'User laravel_user created successfully!' AS Status;
EOF
        echo ""
        echo "✅ Use these credentials in DBeaver:"
        echo "   Username: laravel_user"
        echo "   Password: (empty)"
        ;;
    4)
        echo ""
        echo "Testing MySQL connection..."
        if mysql -u root -e "SELECT 1;" 2>/dev/null; then
            echo "✅ Connection successful with empty password!"
        else
            echo "❌ Connection failed. Root requires password."
            echo "   Run this script again and choose option 1 or 2."
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=== Testing Connection ==="
if mysql -u root -e "SHOW DATABASES;" 2>/dev/null; then
    echo "✅ MySQL connection working!"
    echo ""
    echo "DBeaver Connection Settings:"
    echo "  Host: localhost"
    echo "  Port: 3306"
    echo "  Database: ngnlocal"
    echo "  Username: root"
    echo "  Password: (empty)"
else
    echo "❌ Connection still failing. You may need to:"
    echo "   1. Enter root password when prompted"
    echo "   2. Reset MySQL root password"
    echo "   3. Check MySQL is running: brew services list | grep mysql"
fi

