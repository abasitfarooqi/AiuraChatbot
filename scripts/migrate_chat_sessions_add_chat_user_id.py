#!/usr/bin/env python3
"""
Migrate chat_sessions table to add chat_user_id column.
This script adds the missing chat_user_id column to existing chat_sessions table.
"""
import os
import sys
import pymysql
from loguru import logger

# MySQL credentials
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'abc123')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'aiura_chatbots')


def check_column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = %s 
        AND COLUMN_NAME = %s
    """, (MYSQL_DATABASE, table_name, column_name))
    result = cursor.fetchone()
    return result[0] > 0


def migrate_chat_sessions():
    """Add chat_user_id column to chat_sessions table."""
    logger.info("=" * 80)
    logger.info("MIGRATING chat_sessions TABLE")
    logger.info("=" * 80)
    logger.info(f"Database: {MYSQL_DATABASE}")
    logger.info("")
    
    try:
        # Connect to MySQL
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Check if chat_user_id column exists
        if check_column_exists(connection, 'chat_sessions', 'chat_user_id'):
            logger.info("✅ Column 'chat_user_id' already exists in chat_sessions")
        else:
            logger.info("❌ Column 'chat_user_id' missing in chat_sessions")
            logger.info("Adding column...")
            
            # Check if chat_users table exists
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'chat_users'
            """, (MYSQL_DATABASE,))
            
            if cursor.fetchone()[0] == 0:
                logger.error("❌ chat_users table does not exist! Please create it first.")
                connection.close()
                return False
            
            # Get count of existing sessions
            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            session_count = cursor.fetchone()[0]
            logger.info(f"Found {session_count} existing chat sessions")
            
            # Add chat_user_id column
            # First, make it nullable temporarily to allow existing rows
            logger.info("Step 1: Adding chat_user_id column (nullable)...")
            cursor.execute("""
                ALTER TABLE chat_sessions 
                ADD COLUMN chat_user_id INTEGER NULL 
                AFTER vendor_id
            """)
            logger.info("✅ Column added (nullable)")
            
            # Add index
            logger.info("Step 2: Adding index on chat_user_id...")
            try:
                cursor.execute("""
                    CREATE INDEX idx_chat_sessions_chat_user_id 
                    ON chat_sessions(chat_user_id)
                """)
                logger.info("✅ Index created")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    logger.info("✅ Index already exists")
                else:
                    raise
            
            # Add foreign key constraint
            logger.info("Step 3: Adding foreign key constraint...")
            try:
                cursor.execute("""
                    ALTER TABLE chat_sessions 
                    ADD CONSTRAINT fk_chat_sessions_chat_user 
                    FOREIGN KEY (chat_user_id) 
                    REFERENCES chat_users(id) 
                    ON DELETE CASCADE
                """)
                logger.info("✅ Foreign key constraint added")
            except Exception as e:
                if "Duplicate foreign key" in str(e) or "already exists" in str(e):
                    logger.info("✅ Foreign key constraint already exists")
                else:
                    logger.warning(f"⚠️ Could not add foreign key: {e}")
                    logger.info("Continuing without foreign key constraint...")
            
            # Commit changes
            connection.commit()
            logger.info("✅ Migration completed")
            
            if session_count > 0:
                logger.warning(f"⚠️ {session_count} existing sessions have NULL chat_user_id")
                logger.info("You may need to create ChatUser records and update these sessions")
        
        # Verify column exists
        if check_column_exists(connection, 'chat_sessions', 'chat_user_id'):
            logger.info("")
            logger.info("=" * 80)
            logger.info("VERIFICATION")
            logger.info("=" * 80)
            cursor.execute("DESCRIBE chat_sessions")
            columns = cursor.fetchall()
            logger.info("chat_sessions table structure:")
            for col in columns:
                if 'chat_user_id' in col[0]:
                    logger.info(f"  ✅ {col[0]}: {col[1]} {col[2]} {col[3]}")
            
            connection.close()
            logger.info("")
            logger.info("✅ Migration successful!")
            return True
        else:
            logger.error("❌ Column still missing after migration")
            connection.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    success = migrate_chat_sessions()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

