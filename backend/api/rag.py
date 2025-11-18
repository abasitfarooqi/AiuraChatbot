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

