#!/usr/bin/env python3
"""
Sync knowledge base chunks to kb_documents table.
"""
import sys
import json
import hashlib
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config.database import get_db_session
from backend.models.saas_models import Vendor, KnowledgeBase, KBDocument
from backend.utils.vendor_manager import get_vendor_manager
from loguru import logger

def sync_kb_documents(vendor_slug: str):
    """Sync knowledge base chunks to kb_documents table."""
    db = next(get_db_session())
    try:
        # Get vendor
        vendor = db.query(Vendor).filter(
            Vendor.slug == vendor_slug,
            Vendor.deleted_at.is_(None)
        ).first()
        
        if not vendor:
            logger.error(f"Vendor {vendor_slug} not found")
            return False
        
        # Get vendor manager
        vendor_manager = get_vendor_manager()
        kb_path = vendor_manager.get_vendor_rag_path(vendor_slug)
        
        if not kb_path.exists():
            logger.error(f"Knowledge base file not found: {kb_path}")
            return False
        
        # Load knowledge base
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)
        
        chunks = kb_data.get("chunks", [])
        if not chunks:
            logger.warning(f"No chunks found in knowledge base for {vendor_slug}")
            return False
        
        # Get or create knowledge base
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.vendor_id == vendor.id,
            KnowledgeBase.name == "default"
        ).first()
        
        if not kb:
            kb = KnowledgeBase(
                vendor_id=vendor.id,
                name="default",
                description=f"Default knowledge base for {vendor_slug}",
                vector_db_collection=f"{vendor_slug}_kb"
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)
            logger.info(f"Created knowledge base for vendor {vendor_slug}")
        
        # Delete existing documents for this KB
        deleted_count = db.query(KBDocument).filter(KBDocument.knowledge_base_id == kb.id).delete()
        logger.info(f"Deleted {deleted_count} existing documents")
        
        # Create documents from chunks
        created_count = 0
        for chunk in chunks:
            content = chunk.get("content", "")
            if not content:
                continue
            
            # Create checksum for deduplication
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            doc = KBDocument(
                knowledge_base_id=kb.id,
                vendor_id=vendor.id,
                title=chunk.get("keyword", chunk.get("symbol", "Untitled")),
                content=content,
                checksum=checksum,
                meta={
                    "symbol": chunk.get("symbol", ""),
                    "keyword": chunk.get("keyword", ""),
                    "tags": chunk.get("tags", []),
                    "mapping": chunk.get("mapping", {}),
                    "metadata": chunk.get("metadata", {})
                }
            )
            db.add(doc)
            created_count += 1
        
        db.commit()
        logger.info(f"Synced {created_count} chunks to kb_documents for vendor {vendor_slug}")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing KB documents: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return False
    finally:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_kb_documents.py <vendor_slug>")
        print("Example: python sync_kb_documents.py neguinho_motors")
        sys.exit(1)
    
    vendor_slug = sys.argv[1]
    success = sync_kb_documents(vendor_slug)
    sys.exit(0 if success else 1)

