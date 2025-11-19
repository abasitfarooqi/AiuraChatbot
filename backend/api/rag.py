"""
RAG API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.database import get_session_local
SessionLocal = get_session_local()
from backend.services.rag_service import RAGService
from loguru import logger

router = APIRouter(prefix="/rag", tags=["rag"])


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RAGQueryRequest(BaseModel):
    """Request model for RAG query."""
    query: str
    top_k: Optional[int] = None
    vendor_id: Optional[str] = None


@router.post("/query")
async def query_rag(request: RAGQueryRequest):
    """Query the RAG system (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        # Use vendor-specific RAG service
        effective_vendor_id = request.vendor_id or settings.default_vendor_id
        rag_service = RAGService(vendor_id=effective_vendor_id)
        
        results = rag_service.retrieve(
            query=request.query,
            top_k=request.top_k,
            vendor_id=effective_vendor_id
        )
        
        return {
            "query": request.query,
            "vendor_id": effective_vendor_id,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_knowledge_base(vendor_id: Optional[str] = None, kb_path: Optional[str] = None):
    """Load knowledge base into vector database (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        # Use vendor-specific RAG service if vendor_id provided
        effective_vendor_id = vendor_id or settings.default_vendor_id
        rag_service = RAGService(vendor_id=effective_vendor_id)
        
        # If no path provided, use vendor-specific path
        if kb_path is None:
            success = rag_service.load_knowledge_base()
        else:
            success = rag_service.load_knowledge_base(kb_path)
        
        return {
            "status": "success" if success else "failed",
            "vendor_id": effective_vendor_id,
            "kb_path": kb_path or f"vendor {effective_vendor_id} default"
        }
        
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_rag_stats(vendor_id: Optional[str] = None):
    """Get RAG statistics (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        # Use vendor-specific RAG service if vendor_id provided
        effective_vendor_id = vendor_id or settings.default_vendor_id
        rag_service = RAGService(vendor_id=effective_vendor_id)
        stats = rag_service.get_collection_stats()
        
        # Add vendor info to stats
        stats["vendor_id"] = effective_vendor_id
        return stats
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_chromadb(vendor_id: Optional[str] = None):
    """Clear all data from ChromaDB collection (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        # Use vendor-specific RAG service
        effective_vendor_id = vendor_id or settings.default_vendor_id
        rag_service = RAGService(vendor_id=effective_vendor_id)
        
        # Get vendor-specific collection name
        from backend.utils.vendor_manager import get_vendor_manager
        vendor_manager = get_vendor_manager()
        collection_name = vendor_manager.get_vendor_chroma_collection(effective_vendor_id)
        
        # Delete collection
        rag_service.client.delete_collection(name=collection_name)
        
        # Recreate collection with vendor-specific info
        try:
            config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
            unified_config = config_manager.load_config()
            company_name = unified_config.get("business", {}).get("company_name", "Company")
            collection_desc = f"{company_name} Knowledge Base"
        except:
            collection_desc = "Knowledge Base"
        
        rag_service.collection = rag_service.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": collection_desc, "vendor_id": effective_vendor_id}
        )
        
        return {
            "status": "success",
            "message": f"ChromaDB collection cleared for vendor {effective_vendor_id}",
            "vendor_id": effective_vendor_id,
            "collection_name": collection_name
        }
        
    except Exception as e:
        logger.error(f"Error clearing ChromaDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chromadb/info")
async def get_chromadb_info(vendor_id: Optional[str] = None):
    """Get detailed ChromaDB information (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        # Use vendor-specific RAG service
        effective_vendor_id = vendor_id or settings.default_vendor_id
        rag_service = RAGService(vendor_id=effective_vendor_id)
        
        # Get vendor-specific collection name
        from backend.utils.vendor_manager import get_vendor_manager
        vendor_manager = get_vendor_manager()
        collection_name = vendor_manager.get_vendor_chroma_collection(effective_vendor_id)
        
        # Get collection info
        count = rag_service.collection.count()
        db_path = settings.chroma_db_path
        
        # Get all collections
        all_collections = rag_service.client.list_collections()
        collections_info = []
        for col in all_collections:
            collections_info.append({
                "name": col.name,
                "count": col.count(),
                "metadata": col.metadata
            })
        
        return {
            "vendor_id": effective_vendor_id,
            "current_collection": {
                "name": collection_name,
                "count": count,
                "path": db_path
            },
            "all_collections": collections_info,
            "total_collections": len(all_collections)
        }
        
    except Exception as e:
        logger.error(f"Error getting ChromaDB info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

