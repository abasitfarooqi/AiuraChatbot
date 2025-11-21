# Database Connection Guide - DBeaver

## MySQL Connection for Laravel Project

### Connection Details
- **Host**: localhost
- **Port**: 3306
- **Database**: ngnlocal
- **Username**: root
- **Password**: (empty/blank)

## Steps to Connect in DBeaver

### 1. Open DBeaver
Launch DBeaver application.

### 2. Create New Connection
- Click **"New Database Connection"** button (plug icon) in the toolbar
- Or go to: **Database** → **New Database Connection**

### 3. Select MySQL
- In the connection wizard, select **MySQL** from the list
- Click **Next**

### 4. Enter Connection Details

**Main Tab:**
- **Server Host**: `localhost`
- **Port**: `3306`
- **Database**: `ngnlocal`
- **Username**: `root`
- **Password**: (leave blank/empty)

**Driver Properties Tab (Optional):**
- You can leave defaults or add:
  - `allowPublicKeyRetrieval=true` (if needed)
  - `useSSL=false` (for local development)

### 5. Test Connection
- Click **"Test Connection"** button
- If driver is missing, DBeaver will prompt to download MySQL driver
- Click **Download** if prompted

### 6. Save Connection
- Click **Finish** to save the connection
- The connection will appear in the Database Navigator panel

### 7. Connect
- Double-click the connection name to connect
- Or right-click → **Connect**

## Alternative: Using Connection String

If you prefer to use a connection string:

```
jdbc:mysql://localhost:3306/ngnlocal?user=root&password=
```

## Troubleshooting

### Issue: "Access denied for user 'root'@'localhost'"
**Solution**: 
- Check if MySQL is running: `brew services list | grep mysql`
- Start MySQL: `brew services start mysql`
- Try connecting with password if you have one set

### Issue: "Driver not found"
**Solution**:
- DBeaver will prompt to download MySQL driver
- Click **Download** when prompted
- Or manually: **Window** → **Preferences** → **Drivers** → **MySQL** → **Download**

### Issue: "Connection refused"
**Solution**:
- Verify MySQL is running: `mysql -u root -e "SELECT 1;"`
- Check port 3306 is not blocked
- Verify MySQL is listening: `lsof -i :3306`

### Issue: "Unknown database 'ngnlocal'"
**Solution**:
- Create the database first:
  ```sql
  CREATE DATABASE ngnlocal;
  ```
- Or connect without specifying database, then create it

## Quick Connection Test (Terminal)

Test your connection from terminal first:

```bash
mysql -h localhost -P 3306 -u root -e "SHOW DATABASES;"
```

If this works, DBeaver should work too.

## For Our SaaS Platform Database

If you want to connect to the AiuraChatbot SaaS database:

### SQLite (Current Default)
- **Type**: SQLite
- **Path**: `./data/chatbot.db` (relative to project root)
- **No username/password needed**

### MySQL (If Configured)
- **Host**: localhost
- **Port**: 3306
- **Database**: `aiura_chatbots` (or as configured)
- **Username**: `aiura_chatbot` (or as configured)
- **Password**: (as configured)

## DBeaver Connection Settings Summary

```
Connection Type: MySQL
Host: localhost
Port: 3306
Database: ngnlocal
Username: root
Password: (empty)
```

## Additional Tips

1. **Save Password**: Check "Save password" if you want DBeaver to remember it
2. **Show All Databases**: Uncheck "Show only default database" to see all databases
3. **Connection Timeout**: Increase if you have slow connections
4. **SSL**: Disable for local development (useSSL=false)

## Quick Setup Script

If you need to create the database first:

```bash
mysql -u root -e "CREATE DATABASE IF NOT EXISTS ngnlocal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Then connect in DBeaver using the settings above.

