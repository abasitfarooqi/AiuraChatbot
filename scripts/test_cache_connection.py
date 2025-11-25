#!/usr/bin/env python3
"""
Test cache API endpoints and database connection.
Verifies that cache data can be loaded from the database correctly.
"""
import sys
import os
import requests
import json
from loguru import logger

# CRITICAL: Set USE_MYSQL before importing database modules
os.environ["USE_MYSQL"] = "true"
os.environ["MYSQL_USER"] = "root"
os.environ["MYSQL_PASSWORD"] = "abc123"
os.environ["MYSQL_DATABASE"] = "aiura_chatbots"
os.environ["MYSQL_HOST"] = "localhost"
os.environ["MYSQL_PORT"] = "3306"

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.config import get_settings
from backend.config.database import get_database_engine
from sqlalchemy.orm import Session
from backend.models.database import get_session_local
from backend.models.saas_models import MainCache, TemporaryCache, Vendor

settings = get_settings()
API_BASE = "http://localhost:8000/api/v1"
# Don't create session at module level - create it in the function after env vars are set


def test_database_connection():
    """Test direct database connection to cache tables."""
    logger.info("=" * 80)
    logger.info("TESTING DATABASE CONNECTION")
    logger.info("=" * 80)
    
    try:
        # Create fresh session factory after env vars are set
        SessionLocal = get_session_local()
        
        # Verify we're using MySQL
        engine = get_database_engine()
        db_url = str(engine.url)
        logger.info(f"Database URL: {db_url.split('@')[1] if '@' in db_url else db_url}")
        
        if "sqlite" in db_url.lower():
            logger.error("❌ ERROR: Using SQLite instead of MySQL!")
            logger.error("   Set USE_MYSQL=true environment variable")
            return False
        
        db = SessionLocal()
        
        # Debug: Try raw SQL first to verify connection
        from sqlalchemy import text
        raw_result = db.execute(text('SELECT COUNT(*) FROM main_cache'))
        raw_count = raw_result.scalar()
        logger.info(f"🔍 Raw SQL count: {raw_count}")
        
        # Test main cache with ORM
        main_count = db.query(MainCache).count()
        logger.info(f"✅ Main cache entries (ORM): {main_count}")
        
        # If ORM returns 0 but raw SQL returns data, there's a model issue
        if raw_count > 0 and main_count == 0:
            logger.error(f"❌ ORM query returned 0 but raw SQL returned {raw_count} - checking table mapping...")
            # Try to get a sample with raw SQL
            sample_result = db.execute(text('SELECT id, cache_id, vendor_id FROM main_cache LIMIT 1'))
            sample_row = sample_result.fetchone()
            if sample_row:
                logger.info(f"   Raw SQL sample: id={sample_row[0]}, cache_id={sample_row[1]}, vendor_id={sample_row[2]}")
            # Try ORM with explicit table
            orm_sample = db.query(MainCache).first()
            if orm_sample:
                logger.info(f"   ORM sample: id={orm_sample.id}, cache_id={orm_sample.cache_id}, vendor_id={orm_sample.vendor_id}")
            else:
                logger.error("   ORM query returned None even though raw SQL has data!")
        
        if main_count > 0:
            sample = db.query(MainCache).first()
            logger.info(f"   Sample: cache_id={sample.cache_id}, vendor_id={sample.vendor_id}, question={sample.question[:50]}...")
        else:
            logger.warning("⚠️  No main cache entries found (expected 24)")
        
        # Test temporary cache
        temp_count = db.query(TemporaryCache).count()
        logger.info(f"✅ Temporary cache entries: {temp_count}")
        
        if temp_count > 0:
            sample = db.query(TemporaryCache).first()
            logger.info(f"   Sample: cache_id={sample.cache_id}, vendor_id={sample.vendor_id}, chat_id={sample.chat_id}")
        else:
            logger.warning("⚠️  No temporary cache entries found (expected 55)")
        
        # Test vendor lookup
        vendor = db.query(Vendor).filter(Vendor.slug == "neguinho_motors").first()
        if vendor:
            logger.info(f"✅ Vendor found: {vendor.slug} (id={vendor.id})")
            
            # Test vendor-specific queries
            main_vendor_count = db.query(MainCache).filter(MainCache.vendor_id == vendor.id).count()
            temp_vendor_count = db.query(TemporaryCache).filter(TemporaryCache.vendor_id == vendor.id).count()
            logger.info(f"✅ Main cache for vendor {vendor.slug}: {main_vendor_count}")
            logger.info(f"✅ Temporary cache for vendor {vendor.slug}: {temp_vendor_count}")
            
            if main_vendor_count == 0 and main_count > 0:
                logger.warning(f"⚠️  Vendor query returned 0 but total is {main_count} - checking all entries...")
                all_main = db.query(MainCache).all()
                vendor_ids = set([m.vendor_id for m in all_main])
                logger.info(f"   Found vendor_ids in main_cache: {vendor_ids}")
        else:
            logger.error("❌ Vendor 'neguinho_motors' not found")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test cache API endpoints."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TESTING API ENDPOINTS")
    logger.info("=" * 80)
    
    vendor_slug = "neguinho_motors"
    
    # Test cache stats
    try:
        logger.info(f"Testing GET /cache/stats?vendor_id={vendor_slug}")
        response = requests.get(f"{API_BASE}/cache/stats", params={"vendor_id": vendor_slug}, timeout=5)
        if response.status_code == 200:
            stats = response.json()
            logger.info(f"✅ Cache stats loaded successfully")
            logger.info(f"   Main cache: {stats.get('main_cache', {}).get('total_entries', 0)} entries")
            logger.info(f"   Temporary cache: {stats.get('temporary_cache', {}).get('total_entries', 0)} entries")
        else:
            logger.error(f"❌ Cache stats failed: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Cache stats error: {e}")
    
    # Test main cache
    try:
        logger.info(f"Testing GET /cache/main?vendor_id={vendor_slug}")
        response = requests.get(f"{API_BASE}/cache/main", params={"vendor_id": vendor_slug, "limit": 10}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Main cache loaded: {data.get('total', 0)} total, {len(data.get('entries', []))} returned")
            if data.get('entries'):
                logger.info(f"   First entry: {data['entries'][0].get('cache_id')}")
        else:
            logger.error(f"❌ Main cache failed: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Main cache error: {e}")
    
    # Test temporary cache
    try:
        logger.info(f"Testing GET /cache/temporary?vendor_id={vendor_slug}")
        response = requests.get(f"{API_BASE}/cache/temporary", params={"vendor_id": vendor_slug, "limit": 10}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Temporary cache loaded: {data.get('total', 0)} total, {len(data.get('entries', []))} returned")
            if data.get('entries'):
                logger.info(f"   First entry: {data['entries'][0].get('cache_id')}")
        else:
            logger.error(f"❌ Temporary cache failed: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Temporary cache error: {e}")
    
    # Test cache settings
    try:
        logger.info(f"Testing GET /cache/settings?vendor_id={vendor_slug}")
        response = requests.get(f"{API_BASE}/cache/settings", params={"vendor_id": vendor_slug}, timeout=5)
        if response.status_code == 200:
            settings = response.json()
            logger.info(f"✅ Cache settings loaded: use_cache={settings.get('use_cache_for_responses')}")
        else:
            logger.error(f"❌ Cache settings failed: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Cache settings error: {e}")


def main():
    """Main test function."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("CACHE CONNECTION TEST")
    logger.info("=" * 80)
    logger.info("")
    
    # Test database connection
    db_ok = test_database_connection()
    
    if not db_ok:
        logger.error("❌ Database connection failed. Cannot proceed with API tests.")
        sys.exit(1)
    
    # Test API endpoints (only if server is running)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            logger.info("")
            logger.info("✅ Server is running, testing API endpoints...")
            test_api_endpoints()
        else:
            logger.warning("⚠️ Server responded but may not be fully ready")
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ Server not running. Skipping API endpoint tests.")
        logger.info("   Start the server with: python3 -m backend.main")
    except Exception as e:
        logger.warning(f"⚠️ Could not test API endpoints: {e}")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()

