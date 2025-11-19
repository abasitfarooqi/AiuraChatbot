"""
Migration script to convert existing Neguinho Motors data to vendor system.
This script:
1. Creates 'neguinho_motors' vendor
2. Moves existing config to vendor-specific location
3. Moves existing RAG KB to vendor-specific location
4. Updates all existing database records to use neguinho_motors vendor_id
5. Updates ChromaDB collection name
"""
import json
import shutil
from pathlib import Path
from loguru import logger
from backend.models.database import (
    Vendor, User, Chat, Message, ConversationMemory, TokenUsage,
    get_database_engine, init_database
)
from backend.utils.vendor_manager import get_vendor_manager
from backend.utils.unified_config_manager import UnifiedConfigManager
from sqlalchemy.orm import Session


def migrate_existing_data():
    """Migrate existing data to neguinho_motors vendor."""
    logger.info("Starting migration to multi-vendor system...")
    
    # Initialize database (creates Vendor table if needed)
    init_database()
    
    # Create vendor manager
    vendor_manager = get_vendor_manager()
    
    # Check if neguinho_motors vendor already exists
    from backend.models.database import get_session_local
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    
    try:
        existing_vendor = db.query(Vendor).filter(Vendor.vendor_id == "neguinho_motors").first()
        
        if existing_vendor:
            logger.info("Vendor 'neguinho_motors' already exists. Skipping vendor creation.")
        else:
            # Step 1: Read existing unified_config.json
            existing_config_path = Path("./config/unified_config.json")
            existing_rag_path = Path("./rag_knowledge_base.json")
            
            if not existing_config_path.exists():
                logger.error("Existing config not found. Cannot migrate.")
                return False
            
            # Load existing config
            with open(existing_config_path, "r", encoding="utf-8") as f:
                existing_config = json.load(f)
            
            company_name = existing_config.get("business", {}).get("company_name", "Neguinho Motors Ltd")
            business_type = existing_config.get("metadata", {}).get("business_type", "motorcycle_dealership")
            
            # Step 2: Create neguinho_motors vendor
            logger.info("Creating neguinho_motors vendor...")
            vendor_info = vendor_manager.create_vendor(
                vendor_id="neguinho_motors",
                vendor_name="Neguinho Motors",
                company_name=company_name,
                business_type=business_type,
                copy_from_vendor=None  # We'll copy manually
            )
            
            # Step 3: Copy existing config to vendor directory
            vendor_config_path = Path(vendor_info["config_path"])
            shutil.copy(existing_config_path, vendor_config_path)
            
            # Update vendor_id in config
            with open(vendor_config_path, "r", encoding="utf-8") as f:
                vendor_config = json.load(f)
            vendor_config["metadata"]["vendor_id"] = "neguinho_motors"
            with open(vendor_config_path, "w", encoding="utf-8") as f:
                json.dump(vendor_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Copied config to {vendor_config_path}")
            
            # Step 4: Copy existing RAG KB to vendor directory
            if existing_rag_path.exists():
                vendor_rag_path = Path(vendor_info["rag_path"])
                shutil.copy(existing_rag_path, vendor_rag_path)
                
                # Update vendor_id in RAG KB
                with open(vendor_rag_path, "r", encoding="utf-8") as f:
                    rag_data = json.load(f)
                
                rag_data["metadata"]["vendor_id"] = "neguinho_motors"
                for chunk in rag_data.get("chunks", []):
                    if "metadata" in chunk:
                        chunk["metadata"]["vendor_id"] = "neguinho_motors"
                
                with open(vendor_rag_path, "w", encoding="utf-8") as f:
                    json.dump(rag_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Copied RAG KB to {vendor_rag_path}")
            
            # Step 5: Update vendor record with correct paths
            vendor = db.query(Vendor).filter(Vendor.vendor_id == "neguinho_motors").first()
            if vendor:
                vendor.config_path = str(vendor_config_path)
                vendor.rag_path = str(vendor_rag_path) if existing_rag_path.exists() else None
                vendor.chroma_collection = "neguinho_motors_kb"
                db.commit()
        
        # Step 6: Update all existing database records
        logger.info("Updating existing database records...")
        
        # Update users with vendor_id = "default" or NULL to "neguinho_motors"
        users_updated = db.query(User).filter(
            (User.vendor_id == "default") | (User.vendor_id.is_(None))
        ).update({"vendor_id": "neguinho_motors"}, synchronize_session=False)
        logger.info(f"Updated {users_updated} users")
        
        # Update chats with vendor_id = "default" or NULL to "neguinho_motors"
        chats_updated = db.query(Chat).filter(
            (Chat.vendor_id == "default") | (Chat.vendor_id.is_(None))
        ).update({"vendor_id": "neguinho_motors"}, synchronize_session=False)
        logger.info(f"Updated {chats_updated} chats")
        
        db.commit()
        
        logger.info("✅ Migration completed successfully!")
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  - Vendor created: neguinho_motors")
        logger.info(f"  - Config: {vendor_info.get('config_path', 'N/A')}")
        logger.info(f"  - RAG KB: {vendor_info.get('rag_path', 'N/A')}")
        logger.info(f"  - ChromaDB Collection: neguinho_motors_kb")
        logger.info(f"  - Users updated: {users_updated}")
        logger.info(f"  - Chats updated: {chats_updated}")
        logger.info("")
        logger.info("⚠️  Note: You may need to reload the RAG knowledge base for the new ChromaDB collection.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    migrate_existing_data()

