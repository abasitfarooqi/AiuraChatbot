#!/usr/bin/env python3
"""
Add ModelPreset and ModelConfig tables to the database.
Run this after updating saas_models.py to create the new tables.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.config.database import get_database_engine, init_database
from backend.models.saas_models import Base, ModelPreset, ModelConfig
from loguru import logger

def main():
    """Create ModelPreset and ModelConfig tables."""
    try:
        logger.info("Creating ModelPreset and ModelConfig tables...")
        
        # Get database engine
        engine = get_database_engine()
        
        # Create tables
        ModelPreset.__table__.create(engine, checkfirst=True)
        ModelConfig.__table__.create(engine, checkfirst=True)
        
        logger.info("✅ ModelPreset and ModelConfig tables created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

