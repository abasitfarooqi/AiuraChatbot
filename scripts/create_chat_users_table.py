#!/usr/bin/env python3
"""
Create chat_users table in the database.
Run this after updating saas_models.py to create the new table.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.config.database import get_database_engine, init_database
from backend.models.saas_models import Base, ChatUser
from loguru import logger

def main():
    """Create ChatUser table."""
    try:
        logger.info("Creating ChatUser table...")
        
        # Get database engine
        engine = get_database_engine()
        
        # Create table
        ChatUser.__table__.create(engine, checkfirst=True)
        
        logger.info("✅ ChatUser table created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


