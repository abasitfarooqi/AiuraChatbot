# AiuraChatbot Database Access Guide

## Current Database Setup

The AiuraChatbot uses **SQLite by default** (for development), but can also use **MySQL** (for production).

**Current Database:** SQLite  
**Location:** `./data/chatbot.db`

---

## Option 1: SQLite Database (Current Default)

### Access in DBeaver

#### Step 1: Create SQLite Connection
1. Open DBeaver
2. Click **New Database Connection** (plug icon)
3. Select **SQLite** from the list
4. Click **Next**

#### Step 2: Configure Connection
**Path Tab:**
- **Database**: Click **Browse** and navigate to:
  ```
  /Users/abdulbasit/Projects/HybridApps/AiuraChatbot/data/chatbot.db
  ```
- Or enter absolute path:
  ```
  /Users/abdulbasit/Projects/HybridApps/AiuraChatbot/data/chatbot.db
  ```

#### Step 3: Test and Connect
1. Click **Test Connection**
2. If driver missing, DBeaver will prompt to download SQLite driver
3. Click **Download** if prompted
4. Click **Finish**
5. Double-click connection to connect

### Access in Terminal

```bash
# Navigate to project directory
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot

# Open SQLite database
sqlite3 data/chatbot.db

# Once in SQLite prompt, you can run commands:
.tables                    # List all tables
.schema                    # Show database schema
.schema vendors            # Show schema for specific table
SELECT * FROM vendors;     # Query data
SELECT COUNT(*) FROM vendors;  # Count records

# Exit SQLite
.quit
```

#### Quick SQLite Commands

```bash
# List all tables
sqlite3 data/chatbot.db ".tables"

# Show schema for all tables
sqlite3 data/chatbot.db ".schema"

# Query vendors table
sqlite3 data/chatbot.db "SELECT * FROM vendors;"

# Count records in each table
sqlite3 data/chatbot.db "SELECT 'vendors' as table_name, COUNT(*) as count FROM vendors UNION ALL SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'models', COUNT(*) FROM models;"

# Export to CSV
sqlite3 data/chatbot.db -header -csv "SELECT * FROM vendors;" > vendors.csv

# Backup database
cp data/chatbot.db data/chatbot_backup_$(date +%Y%m%d).db
```

---

## Option 2: MySQL Database (Production)

### Setup MySQL First

```bash
# Run the MySQL setup script
./scripts/setup_mysql.sh

# Or set environment variables
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=aiura_chatbot
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=aiura_chatbots
```

### Access in DBeaver (MySQL)

#### Step 1: Create MySQL Connection
1. Open DBeaver
2. Click **New Database Connection**
3. Select **MySQL**
4. Click **Next**

#### Step 2: Configure Connection
**Main Tab:**
```
Server Host: localhost
Port:         3306
Database:     aiura_chatbots
Username:     aiura_chatbot
Password:     (your MySQL password)
```

**Driver Properties (Optional):**
```
allowPublicKeyRetrieval = true
useSSL = false
```

#### Step 3: Test and Connect
1. Click **Test Connection**
2. Download MySQL driver if prompted
3. Click **Finish**
4. Connect to database

### Access in Terminal (MySQL)

```bash
# Connect to MySQL database
mysql -h localhost -P 3306 -u aiura_chatbot -p aiura_chatbots

# Or with password in command (less secure)
mysql -h localhost -P 3306 -u aiura_chatbot -p'your_password' aiura_chatbots

# Once connected, you can run SQL:
SHOW TABLES;
DESCRIBE vendors;
SELECT * FROM vendors;
SELECT COUNT(*) FROM vendors;

# Exit MySQL
EXIT;
```

#### Quick MySQL Commands

```bash
# List all tables
mysql -u aiura_chatbot -p aiura_chatbots -e "SHOW TABLES;"

# Show table structure
mysql -u aiura_chatbot -p aiura_chatbots -e "DESCRIBE vendors;"

# Query data
mysql -u aiura_chatbot -p aiura_chatbots -e "SELECT * FROM vendors;"

# Count records
mysql -u aiura_chatbot -p aiura_chatbots -e "SELECT COUNT(*) FROM vendors;"

# Export to CSV
mysql -u aiura_chatbot -p aiura_chatbots -e "SELECT * FROM vendors;" | sed 's/\t/,/g' > vendors.csv
```

---

## Database Tables Overview

The AiuraChatbot database contains **29 tables**:

### Core Tables
- `admins` - Platform super admin accounts
- `vendors` - Multi-tenant vendor accounts
- `users` - Vendor and platform users
- `roles` - RBAC roles
- `user_roles` - User-role assignments

### Model & Configuration
- `models` - LLM model registry
- `vendor_model_assignments` - Model assignments per vendor
- `vendor_configs` - Per-vendor configuration
- `model_cache` - Model response cache

### Quotas & Usage
- `quota_allocations` - Resource quotas
- `usage_records` - Usage metering

### Billing
- `billing_plans` - Billing plan definitions
- `invoices` - Invoices
- `payments` - Payment records

### Chat System
- `chat_sessions` - Chat sessions
- `chat_messages` - Chat messages

### Knowledge Base
- `knowledge_bases` - Knowledge bases per vendor
- `kb_documents` - Documents in knowledge bases
- `kb_embeddings_refs` - Embedding references

### API & Security
- `api_keys` - API keys
- `rate_limits` - Rate limits
- `vendor_endpoints` - Webhook endpoints
- `webhook_deliveries` - Webhook delivery logs

### Audit & Support
- `audit_logs` - Audit trail
- `feature_flags` - Feature flags
- `support_tickets` - Support tickets
- `ip_allowlist` - IP allowlist/blocklist
- `notifications` - Notifications
- `data_export_requests` - Data export requests

---

## Useful Queries

### Check Neguinho Motors Vendor

**SQLite:**
```sql
SELECT * FROM vendors WHERE slug = 'neguinho_motors';
```

**MySQL:**
```sql
SELECT * FROM vendors WHERE slug = 'neguinho_motors';
```

### View All Vendors

```sql
SELECT id, slug, name, status, plan_code, credit_balance, created_at 
FROM vendors 
ORDER BY created_at DESC;
```

### Check Vendor Quotas

```sql
SELECT 
    v.name as vendor_name,
    q.resource_type,
    q.allocated_amount,
    q.used_amount,
    (q.allocated_amount - q.used_amount) as remaining
FROM quota_allocations q
JOIN vendors v ON q.vendor_id = v.id
WHERE v.slug = 'neguinho_motors';
```

### View Model Assignments

```sql
SELECT 
    v.name as vendor_name,
    m.display_name as model_name,
    m.provider,
    vma.is_default,
    vma.enabled,
    vma.priority_order
FROM vendor_model_assignments vma
JOIN vendors v ON vma.vendor_id = v.id
JOIN models m ON vma.model_id = m.id
WHERE v.slug = 'neguinho_motors'
ORDER BY vma.priority_order;
```

### Check Knowledge Bases

```sql
SELECT 
    v.name as vendor_name,
    kb.name as kb_name,
    kb.vector_db_collection,
    kb.created_at
FROM knowledge_bases kb
JOIN vendors v ON kb.vendor_id = v.id
WHERE v.slug = 'neguinho_motors';
```

### View Usage Statistics

```sql
SELECT 
    v.name as vendor_name,
    ur.resource_type,
    SUM(ur.amount) as total_used,
    COUNT(*) as usage_count
FROM usage_records ur
JOIN vendors v ON ur.vendor_id = v.id
WHERE v.slug = 'neguinho_motors'
GROUP BY ur.resource_type;
```

---

## Switching Between SQLite and MySQL

### Use SQLite (Default)
```bash
# No environment variable needed, or explicitly set:
export USE_MYSQL=false
# or
unset USE_MYSQL
```

### Use MySQL
```bash
export USE_MYSQL=true
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=aiura_chatbot
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=aiura_chatbots
```

### Check Current Database
```bash
# In Python
python3 -c "from backend.config.database import get_database_engine; print(get_database_engine().url)"
```

---

## Database Backup

### SQLite Backup
```bash
# Simple copy
cp data/chatbot.db data/chatbot_backup_$(date +%Y%m%d_%H%M%S).db

# SQL dump
sqlite3 data/chatbot.db .dump > backup_$(date +%Y%m%d).sql
```

### MySQL Backup
```bash
# Full database backup
mysqldump -u aiura_chatbot -p aiura_chatbots > backup_$(date +%Y%m%d).sql

# Restore
mysql -u aiura_chatbot -p aiura_chatbots < backup_20251121.sql
```

---

## Quick Reference

### SQLite (Current)
- **File**: `data/chatbot.db`
- **DBeaver**: SQLite connection → Browse to file
- **Terminal**: `sqlite3 data/chatbot.db`

### MySQL (If Enabled)
- **Host**: localhost
- **Port**: 3306
- **Database**: aiura_chatbots
- **User**: aiura_chatbot
- **DBeaver**: MySQL connection with above settings
- **Terminal**: `mysql -u aiura_chatbot -p aiura_chatbots`

---

## Troubleshooting

### SQLite: "Database is locked"
- Close other connections
- Check if application is using database
- Wait a moment and retry

### MySQL: "Access denied"
- Check username/password
- Verify user has permissions: `GRANT ALL ON aiura_chatbots.* TO 'aiura_chatbot'@'localhost';`
- Check MySQL is running: `brew services list | grep mysql`

### DBeaver: "Driver not found"
- DBeaver will prompt to download driver
- Or manually: Window → Preferences → Drivers → Download

---

## Next Steps

1. ✅ Connect to database in DBeaver
2. ✅ Explore tables and data
3. ✅ Run queries to check vendor setup
4. ✅ Monitor usage and quotas
5. ✅ Backup database regularly

