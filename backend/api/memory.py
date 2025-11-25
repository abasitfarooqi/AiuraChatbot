"""
Memory Management API endpoints.
Handles conversation memory operations: get, update, clear, stats.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from backend.api.database import get_db
from backend.services.memory_service import MemoryService
from backend.models.saas_models import ConversationMemory, Vendor
from loguru import logger

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryUpdateRequest(BaseModel):
    """Request model for updating memory."""
    entities: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    topics: Optional[List[str]] = None
    summary: Optional[str] = None
    increment_turn: bool = True


@router.get("/chat/{chat_id}")
async def get_memory(
    chat_id: str,
    vendor_id: Optional[str] = Query(None, description="Vendor ID (slug)"),
    db: Session = Depends(get_db)
):
    """Get memory for a chat session."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        memory_service = MemoryService(db=db, vendor_id=effective_vendor_id)
        memory = memory_service.get_or_create_memory(chat_id)
        
        return {
            "status": "success",
            "chat_id": chat_id,
            "memory": memory
        }
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chat/{chat_id}")
async def update_memory(
    chat_id: str,
    request: MemoryUpdateRequest,
    vendor_id: Optional[str] = Query(None, description="Vendor ID (slug)"),
    db: Session = Depends(get_db)
):
    """Update memory for a chat session."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        memory_service = MemoryService(db=db, vendor_id=effective_vendor_id)
        memory_service.update_memory(
            chat_id=chat_id,
            entities=request.entities,
            intent=request.intent,
            topics=request.topics,
            summary=request.summary,
            increment_turn=request.increment_turn
        )
        
        return {
            "status": "success",
            "message": f"Memory updated for chat {chat_id}"
        }
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{chat_id}")
async def clear_memory(
    chat_id: str,
    vendor_id: Optional[str] = Query(None, description="Vendor ID (slug)"),
    db: Session = Depends(get_db)
):
    """Clear memory for a chat session."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        memory_service = MemoryService(db=db, vendor_id=effective_vendor_id)
        success = memory_service.clear_memory(chat_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Memory cleared for chat {chat_id}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Memory not found for chat {chat_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vendor/{vendor_id}")
async def clear_all_memories(
    vendor_id: str,
    db: Session = Depends(get_db)
):
    """Clear all memories for a vendor."""
    try:
        memory_service = MemoryService(db=db, vendor_id=vendor_id)
        deleted_count = memory_service.clear_all_memories(vendor_id)
        
        return {
            "status": "success",
            "message": f"Cleared {deleted_count} memories for vendor {vendor_id}",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error clearing all memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_stats(
    vendor_id: Optional[str] = Query(None, description="Vendor ID (slug)"),
    db: Session = Depends(get_db)
):
    """Get memory statistics for a vendor."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        memory_service = MemoryService(db=db, vendor_id=effective_vendor_id)
        stats = memory_service.get_memory_stats(effective_vendor_id)
        
        return {
            "status": "success",
            "vendor_id": effective_vendor_id,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_memories(
    vendor_id: Optional[str] = Query(None, description="Vendor ID (slug)"),
    chat_user_id: Optional[int] = Query(None, description="Chat User ID (optional filter)"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all memories for a vendor (optionally filtered by chat_user)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        vendor = db.query(Vendor).filter(Vendor.slug == effective_vendor_id).first()
        
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {effective_vendor_id} not found")
        
        query = db.query(ConversationMemory).filter(
            ConversationMemory.vendor_id == vendor.id
        )
        
        # Filter by chat_user if provided
        if chat_user_id:
            query = query.filter(ConversationMemory.chat_user_id == chat_user_id)
        
        memories = query.order_by(
            ConversationMemory.last_accessed_at.desc()
        ).offset(offset).limit(limit).all()
        
        total = query.count()
        
        return {
            "status": "success",
            "vendor_id": effective_vendor_id,
            "chat_user_id": chat_user_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "memories": [
                {
                    "id": m.id,
                    "chat_id": m.chat_id,
                    "chat_user_id": m.chat_user_id,
                    "turn_count": m.turn_count,
                    "topics": m.topics or [],
                    "entities": m.entities or {},
                    "is_active": m.is_active,
                    "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                    "created_at": m.created_at.isoformat()
                }
                for m in memories
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

