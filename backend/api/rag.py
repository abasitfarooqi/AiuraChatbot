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
    """Query the RAG system."""
    try:
        rag_service = RAGService()
        results = rag_service.retrieve(
            query=request.query,
            top_k=request.top_k,
            vendor_id=request.vendor_id
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_knowledge_base(kb_path: str = "rag_knowledge_base.json"):
    """Load knowledge base into vector database."""
    try:
        rag_service = RAGService()
        success = rag_service.load_knowledge_base(kb_path)
        
        return {
            "status": "success" if success else "failed",
            "kb_path": kb_path
        }
        
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_rag_stats():
    """Get RAG statistics."""
    try:
        rag_service = RAGService()
        stats = rag_service.get_collection_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_chromadb():
    """Clear all data from ChromaDB collection."""
    try:
        rag_service = RAGService()
        from backend.config import get_settings
        settings = get_settings()
        
        # Delete collection
        rag_service.client.delete_collection(name=settings.chroma_collection_name)
        
        # Recreate collection
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        unified_config = config_manager.load_config()
        company_name = unified_config.get("business", {}).get("company_name", "Company")
        collection_desc = f"{company_name} Knowledge Base"
        
        rag_service.collection = rag_service.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": collection_desc}
        )
        
        return {"status": "success", "message": "ChromaDB collection cleared"}
        
    except Exception as e:
        logger.error(f"Error clearing ChromaDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chromadb/info")
async def get_chromadb_info():
    """Get detailed ChromaDB information."""
    try:
        rag_service = RAGService()
        from backend.config import get_settings
        settings = get_settings()
        
        # Get collection info
        count = rag_service.collection.count()
        collection_name = settings.chroma_collection_name
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

