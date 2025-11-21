# DBeaver MySQL Connection Setup Guide

## Your Laravel Database Connection Details

```
DB_CONNECTION=mysql
DB_HOST=localhost
DB_PORT=3306
DB_DATABASE=ngnlocal
DB_USERNAME=root
DB_PASSWORD= (empty)
```

## Step-by-Step DBeaver Setup

### Step 1: Open DBeaver
Launch DBeaver application.

### Step 2: Create New Connection
1. Click the **"New Database Connection"** icon (plug/socket icon) in toolbar
   - OR go to: **Database** → **New Database Connection** (Ctrl+Shift+N / Cmd+Shift+N)

### Step 3: Select MySQL
1. In the connection wizard, find and select **MySQL**
2. Click **Next**

### Step 4: Enter Connection Settings

**Main Tab:**
```
Server Host: localhost
Port:         3306
Database:     ngnlocal
Username:     root
Password:     (leave blank - empty)
```

**Important Settings:**
- ✅ Uncheck "Show all databases" (or check if you want to see all)
- ✅ Check "Save password" if you want DBeaver to remember
- ⚠️ If connection fails, you may need to set a password (see troubleshooting below)

### Step 5: Driver Settings (if needed)
Click **"Driver properties"** tab and add if needed:
```
allowPublicKeyRetrieval = true
useSSL = false
```

### Step 6: Test Connection
1. Click **"Test Connection"** button
2. If MySQL driver is missing, DBeaver will prompt to download it
3. Click **Download** when prompted
4. Wait for download to complete
5. Test again

### Step 7: Save and Connect
1. Click **Finish** to save connection
2. Connection appears in Database Navigator (left panel)
3. Double-click connection name to connect
4. Enter password if prompted (or leave blank)

## Troubleshooting

### Issue 1: "Access denied for user 'root'@'localhost'"

**This means MySQL root user has a password set.**

**Solution A: Find/Set MySQL Root Password**

1. Check if MySQL has a password:
   ```bash
   # Try with common passwords
   mysql -u root -p
   # (Enter password when prompted)
   ```

2. If you don't know the password, reset it:
   ```bash
   # Stop MySQL
   brew services stop mysql
   
   # Start MySQL in safe mode (skip grant tables)
   sudo mysqld_safe --skip-grant-tables &
   
   # Connect without password
   mysql -u root
   
   # Reset password
   ALTER USER 'root'@'localhost' IDENTIFIED BY '';
   # OR set a password:
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password';
   
   # Flush privileges
   FLUSH PRIVILEGES;
   
   # Exit and restart MySQL normally
   exit
   brew services restart mysql
   ```

**Solution B: Create New MySQL User for Laravel**

```sql
-- Connect as root (with password if needed)
mysql -u root -p

-- Create new user
CREATE USER 'laravel_user'@'localhost' IDENTIFIED BY '';

-- Grant all privileges on ngnlocal database
GRANT ALL PRIVILEGES ON ngnlocal.* TO 'laravel_user'@'localhost';
FLUSH PRIVILEGES;
```

Then use in DBeaver:
- Username: `laravel_user`
- Password: (empty)

**Solution C: Update Laravel Config with Password**

If MySQL root has a password, update your `.env`:
```
DB_PASSWORD=your_mysql_password
```

Then use that password in DBeaver.

### Issue 2: "Unknown database 'ngnlocal'"

**Create the database:**

```bash
# Connect to MySQL
mysql -u root -p

# Create database
CREATE DATABASE ngnlocal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Exit
exit
```

### Issue 3: "Driver not found"

1. DBeaver will prompt to download MySQL driver
2. Click **Download** when prompted
3. Or manually: **Window** → **Preferences** → **Drivers** → **MySQL** → **Download**

### Issue 4: "Connection refused"

**Check MySQL is running:**

```bash
# Check MySQL status
brew services list | grep mysql

# Start MySQL if not running
brew services start mysql

# Verify it's listening on port 3306
lsof -i :3306
```

## Quick Connection Test

Test your connection from terminal:

```bash
# If no password
mysql -h localhost -P 3306 -u root ngnlocal -e "SELECT 1;"

# If password required
mysql -h localhost -P 3306 -u root -p ngnlocal -e "SELECT 1;"
```

If this works, DBeaver will work with the same credentials.

## DBeaver Connection Summary

**Connection Type:** MySQL  
**Host:** localhost  
**Port:** 3306  
**Database:** ngnlocal  
**Username:** root  
**Password:** (empty - or your MySQL root password)

## Alternative: Connection String

If you prefer connection string format:

```
jdbc:mysql://localhost:3306/ngnlocal?user=root&password=
```

## After Connecting

Once connected in DBeaver, you can:
- ✅ Browse database structure
- ✅ View tables, views, procedures
- ✅ Run SQL queries
- ✅ Edit data
- ✅ Export/Import data
- ✅ View Laravel migrations table

## For Laravel Projects

Common tables you'll see:
- `migrations` - Laravel migration history
- `users` - User accounts
- `password_resets` / `password_reset_tokens` - Password reset
- `failed_jobs` - Failed queue jobs
- `personal_access_tokens` - API tokens
- Plus your application tables

## Security Note

⚠️ **For Production:**
- Never use root user with empty password
- Create dedicated database user
- Use strong passwords
- Enable SSL connections

For local development, empty password is acceptable.

