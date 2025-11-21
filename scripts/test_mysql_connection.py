#!/usr/bin/env python3
"""Test MySQL connection and verify setup."""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config.database import get_database_engine, get_db_session
from backend.models.saas_models import Vendor, User, Model, Role, BillingPlan
from loguru import logger

def test_mysql_connection():
    """Test MySQL connection."""
    logger.info("Testing MySQL connection...")
    
    # Check if MySQL is enabled
    use_mysql = os.getenv("USE_MYSQL", "false").lower() == "true"
    
    if not use_mysql:
        logger.warning("USE_MYSQL is not set to 'true'")
        logger.info("Set environment variable: export USE_MYSQL=true")
        return False
    
    try:
        # Get database engine
        engine = get_database_engine()
        logger.info(f"✓ Database engine created: {engine.url}")
        
        # Test connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
        
        # Test ORM queries
        db = next(get_db_session())
        try:
            vendor_count = db.query(Vendor).count()
            user_count = db.query(User).count()
            model_count = db.query(Model).count()
            role_count = db.query(Role).count()
            plan_count = db.query(BillingPlan).count()
            
            logger.info("")
            logger.info("=== Database Status ===")
            logger.info(f"Vendors: {vendor_count}")
            logger.info(f"Users: {user_count}")
            logger.info(f"Models: {model_count}")
            logger.info(f"Roles: {role_count}")
            logger.info(f"Billing Plans: {plan_count}")
            logger.info("")
            logger.info("✅ MySQL connection working perfectly!")
            
            return True
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        logger.info("")
        logger.info("Troubleshooting:")
        logger.info("1. Check MySQL is running: brew services list | grep mysql")
        logger.info("2. Verify credentials in environment variables")
        logger.info("3. Check database exists: mysql -u aiura_chatbot -p aiura_chatbots")
        return False

if __name__ == "__main__":
    test_mysql_connection()

