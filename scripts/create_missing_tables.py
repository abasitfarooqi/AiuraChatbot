#!/usr/bin/env python3
"""
Create missing tables in MySQL database.
Creates: chat_users, conversation_memories, suggestion_cache, model_presets
"""
import os
import sys
from sqlalchemy import create_engine, inspect
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.saas_models import (
    Base, ChatUser, ConversationMemory, SuggestionCache, ModelPreset
)

# MySQL credentials (matching database.py defaults)
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'abc123')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'aiura_chatbots')

# Tables to create
TABLES_TO_CREATE = {
    'chat_users': ChatUser,
    'conversation_memories': ConversationMemory,
    'suggestion_cache': SuggestionCache,
    'model_presets': ModelPreset,
}


def get_mysql_engine():
    """Get MySQL database engine."""
    database_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    return engine


def check_table_exists(engine, table_name):
    """Check if table exists in database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_missing_tables():
    """Create missing tables in MySQL."""
    logger.info("=" * 80)
    logger.info("CREATING MISSING TABLES IN MYSQL")
    logger.info("=" * 80)
    logger.info(f"Database: {MYSQL_DATABASE}")
    logger.info(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")
    logger.info(f"User: {MYSQL_USER}")
    logger.info("")
    
    try:
        # Connect to MySQL
        engine = get_mysql_engine()
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        logger.info(f"Existing tables: {len(existing_tables)}")
        logger.info("")
        
        # Check which tables are missing
        missing_tables = {}
        for table_name, model_class in TABLES_TO_CREATE.items():
            if table_name not in existing_tables:
                missing_tables[table_name] = model_class
                logger.info(f"❌ Missing: {table_name}")
            else:
                logger.info(f"✅ Exists: {table_name}")
        
        logger.info("")
        
        if not missing_tables:
            logger.info("✅ All tables already exist! Nothing to create.")
            return True
        
        # Create missing tables
        logger.info(f"Creating {len(missing_tables)} missing table(s)...")
        logger.info("")
        
        # Create tables one by one
        for table_name, model_class in missing_tables.items():
            try:
                logger.info(f"Creating table: {table_name}...")
                # Create only this specific table
                model_class.__table__.create(bind=engine, checkfirst=True)
                logger.info(f"✅ Created: {table_name}")
            except Exception as e:
                logger.error(f"❌ Error creating {table_name}: {e}")
                return False
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)
        
        # Verify tables were created
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        all_created = True
        for table_name in TABLES_TO_CREATE.keys():
            if table_name in existing_tables:
                logger.info(f"✅ Verified: {table_name} exists")
            else:
                logger.error(f"❌ Failed: {table_name} still missing")
                all_created = False
        
        logger.info("")
        if all_created:
            logger.info("✅ All tables created successfully!")
            return True
        else:
            logger.error("❌ Some tables failed to create")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    success = create_missing_tables()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

