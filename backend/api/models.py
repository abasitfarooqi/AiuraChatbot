"""
Model management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.database import get_session_local
SessionLocal = get_session_local()
from backend.services.model_manager import ModelManager
from backend.services.llm_service import LLMService
from loguru import logger

router = APIRouter(prefix="/models", tags=["models"])


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ModelSwitchRequest(BaseModel):
    """Request model for switching models."""
    provider: str
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@router.get("/available")
async def get_available_models(
    provider: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get available models."""
    try:
        llm_service = LLMService(db=db)
        provider = provider or llm_service.current_provider
        
        if provider == "ollama":
            model_manager = ModelManager(db)
            models = model_manager.list_ollama_models()
        else:
            models = llm_service.get_available_models()
        
        return {"provider": provider, "models": models}
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch")
async def switch_model(
    request: ModelSwitchRequest,
    db: Session = Depends(get_db)
):
    """Switch to a different model."""
    try:
        llm_service = LLMService(db=db)
        llm_service.switch_model(
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        model_manager = ModelManager(db)
        # Save model config
        model_manager.save_model_config(
            model_name=request.model,
            provider=request.provider,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000
        )
        # Set as active model
        model_manager.set_active_model(request.model)
        
        return {
            "status": "success",
            "provider": request.provider,
            "model": request.model
        }
        
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_model(
    model_name: str,
    provider: str = "ollama",
    db: Session = Depends(get_db)
):
    """Download a model."""
    try:
        if provider == "ollama":
            model_manager = ModelManager(db)
            result = await model_manager.download_ollama_model(model_name)
            return result
        else:
            raise HTTPException(status_code=400, detail=f"Download not supported for provider: {provider}")
        
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_model(db: Session = Depends(get_db)):
    """Get current model configuration."""
    try:
        llm_service = LLMService(db=db)
        return {
            "provider": llm_service.current_provider,
            "model": llm_service.current_model
        }
    except Exception as e:
        logger.error(f"Error getting current model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_llm_config():
    """Get LLM configuration (token limits, etc.)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        return {
            "max_tokens": settings.llm_max_tokens,
            "temperature": settings.llm_temperature,
            "top_p": settings.llm_top_p,
            "top_k": settings.llm_top_k
        }
    except Exception as e:
        logger.error(f"Error getting LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LLMConfigRequest(BaseModel):
    """Request model for LLM configuration."""
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None


@router.post("/config")
async def update_llm_config(
    request: LLMConfigRequest,
    db: Session = Depends(get_db)
):
    """Update LLM configuration."""
    try:
        from backend.config import get_settings
        from backend.services.model_manager import ModelManager
        
        settings = get_settings()
        
        # Update settings (these are runtime changes, not persisted to .env)
        if request.max_tokens is not None:
            settings.llm_max_tokens = request.max_tokens
        if request.temperature is not None:
            settings.llm_temperature = request.temperature
        if request.top_p is not None:
            settings.llm_top_p = request.top_p
        if request.top_k is not None:
            settings.llm_top_k = request.top_k
        
        # Save to database for persistence
        model_manager = ModelManager(db)
        active_model = model_manager.get_active_model()
        if active_model:
            model_manager.save_model_config(
                model_name=active_model.model_name,
                provider=active_model.provider,
                temperature=request.temperature or settings.llm_temperature,
                max_tokens=request.max_tokens or settings.llm_max_tokens
            )
        
        return {
            "status": "success",
            "config": {
                "max_tokens": settings.llm_max_tokens,
                "temperature": settings.llm_temperature,
                "top_p": settings.llm_top_p,
                "top_k": settings.llm_top_k
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

