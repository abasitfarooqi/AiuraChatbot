# Quick MySQL Setup & Migration

## 🚀 Quick Start (3 Steps)

### Step 1: Setup MySQL Database

```bash
# Run automated setup (will prompt for MySQL root password if needed)
./scripts/setup_and_migrate_to_mysql.sh
```

**OR manually:**

```bash
# Connect to MySQL
mysql -u root -p

# Run these commands:
CREATE DATABASE IF NOT EXISTS aiura_chatbots CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aiura_chatbot'@'localhost' IDENTIFIED BY 'abc123';
GRANT ALL PRIVILEGES ON aiura_chatbots.* TO 'aiura_chatbot'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 2: Set Environment Variables

```bash
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=aiura_chatbot
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots
```

### Step 3: Run Migration

```bash
source venv/bin/activate
python3 scripts/migrate_sqlite_to_mysql.py
```

## ✅ Verify Setup

```bash
# Test MySQL connection
python3 scripts/test_mysql_connection.py

# Or test manually
mysql -u aiura_chatbot -pabc123 aiura_chatbots -e "SHOW TABLES;"
```

## 📝 DBeaver Connection

```
Type:     MySQL
Host:     localhost
Port:     3306
Database: aiura_chatbots
User:     aiura_chatbot
Password: abc123
```

## 🔄 Switch Between SQLite and MySQL

**Use MySQL:**
```bash
export USE_MYSQL=true
export MYSQL_PASSWORD=abc123
```

**Use SQLite:**
```bash
unset USE_MYSQL
# or
export USE_MYSQL=false
```

## 🎯 That's It!

Once migration is complete:
- ✅ All SQLite data is in MySQL
- ✅ Application uses MySQL when `USE_MYSQL=true`
- ✅ All 29 tables migrated
- ✅ Neguinho Motors vendor data preserved

## 📚 Full Documentation

See `MYSQL_MIGRATION_GUIDE.md` for detailed instructions.

