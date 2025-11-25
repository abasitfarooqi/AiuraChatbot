# MySQL Migration Guide - AiuraChatbot

## Overview

This guide will help you migrate from SQLite to MySQL and update the code to use MySQL.

## Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
# Run the automated setup script
./scripts/setup_and_migrate_to_mysql.sh
```

This script will:
1. Create MySQL database `aiura_chatbots`
2. Create user `aiura_chatbot` with password `abc123`
3. Migrate all data from SQLite to MySQL
4. Create `.env.mysql` file with configuration

### Option 2: Manual Setup

#### Step 1: Create MySQL Database and User

```bash
# Connect to MySQL (you'll be prompted for root password if needed)
mysql -u root -p

# Run these SQL commands:
CREATE DATABASE IF NOT EXISTS aiura_chatbots CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aiura_chatbot'@'localhost' IDENTIFIED BY 'abc123';
GRANT ALL PRIVILEGES ON aiura_chatbots.* TO 'aiura_chatbot'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Step 2: Set Environment Variables

```bash
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=aiura_chatbot
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots
```

#### Step 3: Run Migration

```bash
source venv/bin/activate
python3 scripts/migrate_sqlite_to_mysql.py
```

## Update Code to Use MySQL

### Method 1: Environment Variables (Recommended)

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=aiura_chatbot
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### Method 2: .env File

Create `.env` file in project root:

```env
USE_MYSQL=true
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=aiura_chatbot
MYSQL_PASSWORD=abc123
MYSQL_DATABASE=aiura_chatbots
```

Load it:
```bash
export $(cat .env | grep -v '^#' | xargs)
```

### Method 3: Update settings.py

You can also hardcode in `backend/config/settings.py` (not recommended for production).

## Verify Migration

### Check MySQL Connection

```bash
# Test connection
mysql -u aiura_chatbot -pabc123 aiura_chatbots -e "SHOW TABLES;"
```

### Verify Data

```bash
# Compare record counts
python3 scripts/migrate_sqlite_to_mysql.py
# (The script includes verification at the end)
```

### Test Application

```bash
# Set MySQL environment
export USE_MYSQL=true
export MYSQL_PASSWORD=abc123

# Test database connection
source venv/bin/activate
python3 -c "from backend.config.database import get_db_session; from backend.models.saas_models import Vendor; db = next(get_db_session()); print(f'✅ Connected! Vendors: {db.query(Vendor).count()}')"
```

## DBeaver Connection

### MySQL Connection Settings

```
Connection Type: MySQL
Host:            localhost
Port:            3306
Database:        aiura_chatbots
Username:        aiura_chatbot
Password:        abc123
```

## Code Changes Made

### 1. Database Configuration (`backend/config/database.py`)

- ✅ Updated `get_mysql_database_url()` to handle empty passwords
- ✅ Already supports `USE_MYSQL` environment variable
- ✅ Automatic fallback to SQLite if MySQL not configured

### 2. Migration Script (`scripts/migrate_sqlite_to_mysql.py`)

- ✅ Creates MySQL tables using SQLAlchemy
- ✅ Migrates all data from SQLite to MySQL
- ✅ Handles foreign key relationships
- ✅ Verifies migration by comparing record counts

## Switching Back to SQLite

If you need to switch back to SQLite:

```bash
unset USE_MYSQL
# or
export USE_MYSQL=false
```

The application will automatically use SQLite.

## Troubleshooting

### Issue: "Access denied for user"

**Solution:**
1. Check MySQL user exists: `mysql -u root -p -e "SELECT User FROM mysql.user WHERE User='aiura_chatbot';"`
2. Recreate user: `./scripts/setup_and_migrate_to_mysql.sh`
3. Check password: Ensure `MYSQL_PASSWORD=abc123` is set

### Issue: "Unknown database"

**Solution:**
```bash
mysql -u root -p -e "CREATE DATABASE aiura_chatbots CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Issue: Migration fails on foreign keys

**Solution:**
The migration script handles tables in the correct order. If issues persist:
1. Drop all tables in MySQL
2. Re-run migration script

### Issue: Application still uses SQLite

**Solution:**
1. Check environment variable: `echo $USE_MYSQL` (should be "true")
2. Restart application/server
3. Check logs for database connection messages

## Production Considerations

For production:
1. ✅ Use strong MySQL password
2. ✅ Restrict MySQL user permissions if needed
3. ✅ Enable SSL connections
4. ✅ Use connection pooling (already configured)
5. ✅ Set up database backups
6. ✅ Monitor connection pool usage

## Next Steps

1. ✅ Run migration script
2. ✅ Set environment variables
3. ✅ Test application with MySQL
4. ✅ Update deployment scripts
5. ✅ Set up database backups
6. ✅ Monitor performance

## Summary

- **Database**: `aiura_chatbots`
- **User**: `aiura_chatbot`
- **Password**: `abc123`
- **Host**: `localhost:3306`
- **Environment Variable**: `USE_MYSQL=true`

Once migration is complete, all your SQLite data will be in MySQL and the application will use MySQL automatically when `USE_MYSQL=true` is set.

