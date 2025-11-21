"""
Cache Management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.models.database import get_session_local
from backend.services.cache_service import CacheService
from backend.models.database import MainCache, TemporaryCache
from loguru import logger

SessionLocal = get_session_local()

router = APIRouter(prefix="/cache", tags=["cache"])


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CacheEntryRequest(BaseModel):
    """Request model for creating cache entry."""
    question: str
    answer: str
    similarity_threshold: Optional[float] = 0.85
    metadata: Optional[Dict[str, Any]] = None


class CachePromoteRequest(BaseModel):
    """Request model for promoting temporary cache to main."""
    temp_cache_id: str


class CacheSettingsRequest(BaseModel):
    """Request model for cache settings."""
    use_cache_for_responses: Optional[bool] = None
    fallback_to_llm_on_cache_miss: Optional[bool] = None
    disable_llm_completely: Optional[bool] = None
    cache_model_provider: Optional[str] = None
    cache_model_name: Optional[str] = None
    use_lightweight_model_for_cache: Optional[bool] = None


@router.get("/settings")
async def get_cache_settings(
    vendor_id: Optional[str] = Query(None)
):
    """Get cache settings for a vendor."""
    try:
        from backend.config import get_settings
        from backend.utils.vendor_manager import get_vendor_manager
        
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        # Load from unified config
        vendor_manager = get_vendor_manager()
        
        # Check if config file exists
        config_path = vendor_manager.vendors_dir / effective_vendor_id / "unified_config.json"
        if not config_path.exists():
            raise HTTPException(status_code=404, detail=f"Config file not found for vendor {effective_vendor_id}. Please ensure the vendor is properly configured.")
        
        config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
        unified_config = config_manager.load_config()
        
        caching_config = unified_config.get("chatbot_service", {}).get("caching", {})
        use_cache = caching_config.get("use_cache_for_responses", caching_config.get("enabled", True))
        fallback_to_llm = caching_config.get("fallback_to_llm_on_cache_miss", True)
        disable_llm = caching_config.get("disable_llm_completely", False)
        cache_model_provider = caching_config.get("cache_model_provider", None)
        cache_model_name = caching_config.get("cache_model_name", None)
        use_lightweight_model = caching_config.get("use_lightweight_model_for_cache", False)
        
        return {
            "vendor_id": effective_vendor_id,
            "use_cache_for_responses": use_cache,
            "fallback_to_llm_on_cache_miss": fallback_to_llm,
            "disable_llm_completely": disable_llm,
            "cache_model_provider": cache_model_provider,
            "cache_model_name": cache_model_name,
            "use_lightweight_model_for_cache": use_lightweight_model,
            "caching_enabled": caching_config.get("enabled", True)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache settings: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings")
async def update_cache_settings(
    request: CacheSettingsRequest,
    vendor_id: Optional[str] = Query(None)
):
    """Update cache settings for a vendor."""
    try:
        from backend.config import get_settings
        from backend.utils.vendor_manager import get_vendor_manager
        
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        # Load unified config
        vendor_manager = get_vendor_manager()
        
        # Check if config file exists
        config_path = vendor_manager.vendors_dir / effective_vendor_id / "unified_config.json"
        if not config_path.exists():
            raise HTTPException(status_code=404, detail=f"Config file not found for vendor {effective_vendor_id}. Please ensure the vendor is properly configured.")
        
        config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
        unified_config = config_manager.load_config()
        
        # Update cache settings
        if "chatbot_service" not in unified_config:
            unified_config["chatbot_service"] = {}
        if "caching" not in unified_config["chatbot_service"]:
            unified_config["chatbot_service"]["caching"] = {}
        
        updated_settings = []
        if request.use_cache_for_responses is not None:
            unified_config["chatbot_service"]["caching"]["use_cache_for_responses"] = request.use_cache_for_responses
            updated_settings.append(f"use_cache_for_responses={request.use_cache_for_responses}")
        
        if request.fallback_to_llm_on_cache_miss is not None:
            unified_config["chatbot_service"]["caching"]["fallback_to_llm_on_cache_miss"] = request.fallback_to_llm_on_cache_miss
            updated_settings.append(f"fallback_to_llm_on_cache_miss={request.fallback_to_llm_on_cache_miss}")
        
        if request.disable_llm_completely is not None:
            unified_config["chatbot_service"]["caching"]["disable_llm_completely"] = request.disable_llm_completely
            updated_settings.append(f"disable_llm_completely={request.disable_llm_completely}")
            # If disabling LLM, ensure cache is enabled
            if request.disable_llm_completely:
                unified_config["chatbot_service"]["caching"]["use_cache_for_responses"] = True
                unified_config["chatbot_service"]["caching"]["fallback_to_llm_on_cache_miss"] = False
        
        if request.cache_model_provider is not None:
            unified_config["chatbot_service"]["caching"]["cache_model_provider"] = request.cache_model_provider
            updated_settings.append(f"cache_model_provider={request.cache_model_provider}")
        
        if request.cache_model_name is not None:
            unified_config["chatbot_service"]["caching"]["cache_model_name"] = request.cache_model_name
            updated_settings.append(f"cache_model_name={request.cache_model_name}")
        
        if request.use_lightweight_model_for_cache is not None:
            unified_config["chatbot_service"]["caching"]["use_lightweight_model_for_cache"] = request.use_lightweight_model_for_cache
            updated_settings.append(f"use_lightweight_model_for_cache={request.use_lightweight_model_for_cache}")
        
        # Save config
        config_manager.save_config(unified_config)
        
        # Reload config in chatbot service (if service instance exists, it will reload on next request)
        # The setting will be read from config on each request, so no need to reload service instances
        
        logger.info(f"Cache settings updated for vendor {effective_vendor_id}: {', '.join(updated_settings)}")
        
        return {
            "status": "success",
            "vendor_id": effective_vendor_id,
            "use_cache_for_responses": unified_config["chatbot_service"]["caching"].get("use_cache_for_responses"),
            "fallback_to_llm_on_cache_miss": unified_config["chatbot_service"]["caching"].get("fallback_to_llm_on_cache_miss"),
            "disable_llm_completely": unified_config["chatbot_service"]["caching"].get("disable_llm_completely", False),
            "cache_model_provider": unified_config["chatbot_service"]["caching"].get("cache_model_provider"),
            "cache_model_name": unified_config["chatbot_service"]["caching"].get("cache_model_name"),
            "use_lightweight_model_for_cache": unified_config["chatbot_service"]["caching"].get("use_lightweight_model_for_cache", False),
            "message": "Cache settings updated successfully. Changes take effect immediately for new requests."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cache settings: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_cache_stats(
    vendor_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get cache statistics for a vendor."""
    try:
        cache_service = CacheService(db=db, vendor_id=vendor_id)
        stats = cache_service.get_cache_stats(vendor_id=vendor_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/main")
async def get_main_cache(
    vendor_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get main cache entries for a vendor."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        query = db.query(MainCache).filter(MainCache.vendor_id == effective_vendor_id)
        
        if active_only:
            query = query.filter(MainCache.is_active == True)
        
        total = query.count()
        entries = query.order_by(MainCache.last_used_at.desc().nullslast(), MainCache.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "vendor_id": effective_vendor_id,
            "total": total,
            "offset": offset,
            "limit": limit,
            "entries": [
                {
                    "cache_id": entry.cache_id,
                    "question": entry.question,
                    "answer": entry.answer,
                    "usage_count": entry.usage_count,
                    "tokens_saved": entry.tokens_saved,
                    "credits_saved": entry.credits_saved,
                    "is_active": entry.is_active,
                    "similarity_threshold": entry.similarity_threshold,
                    "metadata": entry.cache_metadata,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                    "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
                    "last_used_at": entry.last_used_at.isoformat() if entry.last_used_at else None
                }
                for entry in entries
            ]
        }
    except Exception as e:
        logger.error(f"Error getting main cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporary")
async def get_temporary_cache(
    chat_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get temporary cache entries (optionally filtered by chat_id)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        query = db.query(TemporaryCache).filter(TemporaryCache.vendor_id == effective_vendor_id)
        
        if chat_id:
            query = query.filter(TemporaryCache.chat_id == chat_id)
        
        total = query.count()
        entries = query.order_by(TemporaryCache.last_used_at.desc().nullslast(), TemporaryCache.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "vendor_id": effective_vendor_id,
            "chat_id": chat_id,
            "total": total,
            "offset": offset,
            "limit": limit,
            "entries": [
                {
                    "cache_id": entry.cache_id,
                    "chat_id": entry.chat_id,
                    "question": entry.question,
                    "answer": entry.answer,
                    "usage_count": entry.usage_count,
                    "tokens_saved": entry.tokens_saved,
                    "similarity_threshold": entry.similarity_threshold,
                    "metadata": entry.cache_metadata,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                    "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
                    "last_used_at": entry.last_used_at.isoformat() if entry.last_used_at else None
                }
                for entry in entries
            ]
        }
    except Exception as e:
        logger.error(f"Error getting temporary cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/main")
async def create_main_cache_entry(
    request: CacheEntryRequest,
    vendor_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a main cache entry."""
    try:
        cache_service = CacheService(db=db, vendor_id=vendor_id)
        cache_id = cache_service.save_to_main_cache(
            question=request.question,
            answer=request.answer,
            vendor_id=vendor_id,
            tokens_used=0,  # Will be updated when used
            similarity_threshold=request.similarity_threshold,
            metadata=request.metadata
        )
        
        if not cache_id:
            raise HTTPException(status_code=500, detail="Failed to create cache entry")
        
        return {
            "status": "success",
            "cache_id": cache_id,
            "message": "Main cache entry created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating main cache entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/temporary")
async def create_temporary_cache_entry(
    request: CacheEntryRequest,
    chat_id: str,
    vendor_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a temporary cache entry."""
    try:
        cache_service = CacheService(db=db, vendor_id=vendor_id)
        cache_id = cache_service.save_to_temporary_cache(
            chat_id=chat_id,
            question=request.question,
            answer=request.answer,
            vendor_id=vendor_id,
            tokens_used=0,
            metadata=request.metadata
        )
        
        if not cache_id:
            raise HTTPException(status_code=500, detail="Failed to create cache entry")
        
        return {
            "status": "success",
            "cache_id": cache_id,
            "message": "Temporary cache entry created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating temporary cache entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/promote")
async def promote_to_main_cache(
    request: CachePromoteRequest,
    vendor_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Promote a temporary cache entry to main cache."""
    try:
        cache_service = CacheService(db=db, vendor_id=vendor_id)
        main_cache_id = cache_service.promote_to_main_cache(
            temp_cache_id=request.temp_cache_id,
            vendor_id=vendor_id
        )
        
        if not main_cache_id:
            raise HTTPException(status_code=404, detail="Temporary cache entry not found or promotion failed")
        
        return {
            "status": "success",
            "main_cache_id": main_cache_id,
            "temp_cache_id": request.temp_cache_id,
            "message": "Temporary cache entry promoted to main cache successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/main/{cache_id}")
async def delete_main_cache_entry(
    cache_id: str,
    db: Session = Depends(get_db)
):
    """Delete a main cache entry."""
    try:
        cache_entry = db.query(MainCache).filter(MainCache.cache_id == cache_id).first()
        
        if not cache_entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        db.delete(cache_entry)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Main cache entry {cache_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting main cache entry: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/temporary/{cache_id}")
async def delete_temporary_cache_entry(
    cache_id: str,
    db: Session = Depends(get_db)
):
    """Delete a temporary cache entry."""
    try:
        cache_entry = db.query(TemporaryCache).filter(TemporaryCache.cache_id == cache_id).first()
        
        if not cache_entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        db.delete(cache_entry)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Temporary cache entry {cache_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting temporary cache entry: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/temporary/chat/{chat_id}")
async def delete_temporary_cache_for_chat(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Delete all temporary cache entries for a chat."""
    try:
        cache_service = CacheService(db=db)
        deleted_count = cache_service.delete_temporary_cache_for_chat(chat_id)
        
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} temporary cache entries for chat {chat_id}",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting temporary cache for chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/main/{cache_id}/toggle")
async def toggle_main_cache_entry(
    cache_id: str,
    db: Session = Depends(get_db)
):
    """Toggle active status of a main cache entry."""
    try:
        cache_entry = db.query(MainCache).filter(MainCache.cache_id == cache_id).first()
        
        if not cache_entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        cache_entry.is_active = not cache_entry.is_active
        db.commit()
        
        return {
            "status": "success",
            "cache_id": cache_id,
            "is_active": cache_entry.is_active,
            "message": f"Cache entry {'activated' if cache_entry.is_active else 'deactivated'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling cache entry: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/main/vendor/{vendor_id}")
async def clear_main_cache_for_vendor(
    vendor_id: str,
    db: Session = Depends(get_db)
):
    """Clear all main cache entries for a vendor."""
    try:
        deleted_count = db.query(MainCache).filter(MainCache.vendor_id == vendor_id).delete()
        db.commit()
        
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} main cache entries for vendor {vendor_id}",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error clearing main cache: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/temporary/vendor/{vendor_id}")
async def clear_temporary_cache_for_vendor(
    vendor_id: str,
    db: Session = Depends(get_db)
):
    """Clear all temporary cache entries for a vendor."""
    try:
        deleted_count = db.query(TemporaryCache).filter(TemporaryCache.vendor_id == vendor_id).delete()
        db.commit()
        
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} temporary cache entries for vendor {vendor_id}",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error clearing temporary cache: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

