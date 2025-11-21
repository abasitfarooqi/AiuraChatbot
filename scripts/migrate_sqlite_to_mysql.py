#!/usr/bin/env python3
"""
Migrate data from SQLite to MySQL database.
Transfers all tables and data from data/chatbot.db to MySQL aiura_chatbots database.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger
from backend.config.database import get_mysql_database_url
from backend.models.saas_models import Base

# MySQL connection settings (using existing MySQL with root/abc123)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")  # Use root for existing MySQL
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "abc123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "aiura_chatbots")

# SQLite database path
SQLITE_DB = project_root / "data" / "chatbot.db"


def get_sqlite_connection():
    """Get SQLite connection."""
    if not SQLITE_DB.exists():
        raise FileNotFoundError(f"SQLite database not found: {SQLITE_DB}")
    return sqlite3.connect(str(SQLITE_DB))


def get_mysql_connection():
    """Get MySQL connection using existing MySQL instance."""
    # Connect with root/abc123 to existing MySQL
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )


def create_mysql_tables():
    """Create all tables in MySQL using SQLAlchemy."""
    logger.info("Creating MySQL tables...")
    
    # Get MySQL database URL
    database_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    engine = create_engine(database_url)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("✓ MySQL tables created")
    
    return engine


def get_table_names(sqlite_conn):
    """Get all table names from SQLite."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(sqlite_conn, table_name):
    """Get table schema from SQLite."""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def migrate_table_data(sqlite_conn, mysql_conn, table_name):
    """Migrate data from SQLite table to MySQL table."""
    logger.info(f"Migrating table: {table_name}")
    
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    # Get all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        logger.info(f"  No data in {table_name}, skipping")
        return 0
    
    # Get column names
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    
    # Build INSERT statement
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join([f"`{col}`" for col in columns])
    insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
    
    # Handle special cases for tables with auto-increment
    # For tables with foreign keys, we may need to handle them in order
    try:
        # Clear existing data (optional - comment out if you want to keep existing)
        mysql_cursor.execute(f"DELETE FROM `{table_name}`")
        
        # Insert data
        inserted = 0
        for row in rows:
            try:
                # Convert None to NULL, handle boolean values
                processed_row = []
                for val in row:
                    if val is None:
                        processed_row.append(None)
                    elif isinstance(val, bool):
                        processed_row.append(1 if val else 0)
                    else:
                        processed_row.append(val)
                
                mysql_cursor.execute(insert_sql, processed_row)
                inserted += 1
            except Exception as e:
                logger.warning(f"  Error inserting row into {table_name}: {e}")
                logger.debug(f"  Row data: {row[:3]}...")  # Log first 3 columns
        
        mysql_conn.commit()
        logger.info(f"  ✓ Migrated {inserted}/{len(rows)} rows")
        return inserted
        
    except Exception as e:
        logger.error(f"  ✗ Error migrating {table_name}: {e}")
        mysql_conn.rollback()
        return 0


def migrate_all_data():
    """Migrate all data from SQLite to MySQL."""
    logger.info("=" * 60)
    logger.info("SQLite to MySQL Migration")
    logger.info("=" * 60)
    logger.info(f"Source: {SQLITE_DB}")
    logger.info(f"Target: MySQL {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
    logger.info("")
    
    # Check SQLite database exists
    if not SQLITE_DB.exists():
        logger.error(f"SQLite database not found: {SQLITE_DB}")
        return False
    
    # Connect to databases
    logger.info("Connecting to databases...")
    sqlite_conn = get_sqlite_connection()
    mysql_conn = get_mysql_connection()
    
    try:
        # Create MySQL tables
        create_mysql_tables()
        
        # Get all tables
        tables = get_table_names(sqlite_conn)
        logger.info(f"Found {len(tables)} tables to migrate")
        logger.info("")
        
        # Define migration order (tables with foreign keys should come after their dependencies)
        # Core tables first
        ordered_tables = [
            'admins',
            'models',
            'roles',
            'billing_plans',
            'vendors',
            'users',
            'user_roles',
            'vendor_model_assignments',
            'model_cache',
            'quota_allocations',
            'usage_records',
            'invoices',
            'payments',
            'chat_sessions',
            'chat_messages',
            'knowledge_bases',
            'kb_documents',
            'kb_embeddings_refs',
            'vendor_configs',
            'vendor_endpoints',
            'api_keys',
            'rate_limits',
            'webhook_deliveries',
            'audit_logs',
            'feature_flags',
            'support_tickets',
            'ip_allowlist',
            'notifications',
            'data_export_requests'
        ]
        
        # Add any tables not in ordered list
        for table in tables:
            if table not in ordered_tables:
                ordered_tables.append(table)
        
        # Filter to only tables that exist
        tables_to_migrate = [t for t in ordered_tables if t in tables]
        
        # Migrate each table
        total_rows = 0
        for table_name in tables_to_migrate:
            rows = migrate_table_data(sqlite_conn, mysql_conn, table_name)
            total_rows += rows
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✓ Migration complete! Migrated {total_rows} total rows")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        sqlite_conn.close()
        mysql_conn.close()


def verify_migration():
    """Verify migration by comparing record counts."""
    logger.info("")
    logger.info("Verifying migration...")
    
    sqlite_conn = get_sqlite_connection()
    mysql_conn = get_mysql_connection()
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        mysql_cursor = mysql_conn.cursor()
        
        tables = get_table_names(sqlite_conn)
        
        logger.info("Table | SQLite Count | MySQL Count | Status")
        logger.info("-" * 60)
        
        all_match = True
        for table in tables:
            # SQLite count
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_count = sqlite_cursor.fetchone()[0]
            
            # MySQL count
            mysql_cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            mysql_count = mysql_cursor.fetchone()[0]
            
            status = "✓" if sqlite_count == mysql_count else "✗"
            if sqlite_count != mysql_count:
                all_match = False
            
            logger.info(f"{table:30} | {sqlite_count:12} | {mysql_count:11} | {status}")
        
        logger.info("-" * 60)
        
        if all_match:
            logger.info("✓ All tables migrated successfully!")
        else:
            logger.warning("⚠ Some tables have mismatched counts")
        
    finally:
        sqlite_conn.close()
        mysql_conn.close()


def main():
    """Main migration function."""
    logger.info("Starting SQLite to MySQL migration...")
    
    # Run migration
    success = migrate_all_data()
    
    if success:
        # Verify migration
        verify_migration()
        
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Set environment variable: export USE_MYSQL=true")
        logger.info("2. Update .env file with MySQL settings")
        logger.info("3. Test the application with MySQL")
        logger.info("4. Once verified, you can backup/remove SQLite database")
    else:
        logger.error("Migration failed. Please check errors above.")


if __name__ == "__main__":
    main()

