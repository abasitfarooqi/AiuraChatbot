"""
Configuration management API endpoints.
Allows reading and updating JSON-based configuration.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from backend.utils.config_manager import get_config_manager
from loguru import logger
import json
from pathlib import Path

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    """Request model for updating config."""
    key_path: str
    value: Any


class ConfigSectionRequest(BaseModel):
    """Request model for updating config section."""
    section: str
    data: Dict[str, Any]


@router.get("/")
async def get_config():
    """Get full application configuration."""
    try:
        config_manager = get_config_manager()
        config = config_manager.load_app_config()
        return config
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_config(request: ConfigUpdateRequest):
    """Update a single configuration value."""
    try:
        config_manager = get_config_manager()
        success = config_manager.set(request.key_path, request.value)
        if success:
            return {"status": "success", "key_path": request.key_path, "value": request.value}
        else:
            raise HTTPException(status_code=500, detail="Failed to update config")
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/section")
async def update_config_section(request: ConfigSectionRequest):
    """Update an entire configuration section or full config."""
    try:
        config_manager = get_config_manager()
        config = config_manager.load_app_config()
        
        # If section is "all", replace entire config
        if request.section == "all":
            config = request.data
        else:
            config[request.section] = request.data
        
        success = config_manager.save_app_config(config)
        if success:
            return {"status": "success", "section": request.section}
        else:
            raise HTTPException(status_code=500, detail="Failed to update config section")
    except Exception as e:
        logger.error(f"Error updating config section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config():
    """Reload configuration from files."""
    try:
        config_manager = get_config_manager()
        config_manager.reload()
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
async def get_system_prompts():
    """Get system prompts configuration from unified config."""
    try:
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        unified_config = config_manager.load_config()
        prompts = unified_config.get("prompts", {})
        return prompts
    except Exception as e:
        logger.error(f"Error getting system prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts")
async def update_system_prompts(prompts: Dict[str, Any]):
    """Update system prompts configuration in unified config."""
    try:
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        unified_config = config_manager.load_config()
        unified_config["prompts"] = prompts
        success = config_manager.save_config(unified_config)
        if success:
            return {"status": "success", "message": "System prompts updated. Restart server for full effect."}
        else:
            raise HTTPException(status_code=500, detail="Failed to update system prompts")
    except Exception as e:
        logger.error(f"Error updating system prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base")
async def get_knowledge_base():
    """Get knowledge base content."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        kb_path = Path(settings.rag_knowledge_base_path)
        
        if not kb_path.exists():
            raise HTTPException(status_code=404, detail="Knowledge base file not found")
        
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)
        
        return kb_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-base")
async def update_knowledge_base(kb_data: Dict[str, Any]):
    """Update knowledge base content."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        kb_path = Path(settings.rag_knowledge_base_path)
        
        # Backup existing file
        if kb_path.exists():
            backup_path = kb_path.with_suffix(f".backup.{kb_path.suffix}")
            with open(kb_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Save new data
        with open(kb_path, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=2, ensure_ascii=False)
        
        # Reload into vector database
        from backend.services.rag_service import RAGService
        rag_service = RAGService()
        success = rag_service.load_knowledge_base(str(kb_path))
        
        if success:
            return {"status": "success", "message": "Knowledge base updated and reloaded"}
        else:
            return {"status": "warning", "message": "Knowledge base updated but reload failed"}
            
    except Exception as e:
        logger.error(f"Error updating knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/offline")
async def get_offline_models():
    """Get list of offline cached models with detailed info."""
    try:
        from backend.services.offline_model_manager import OfflineModelManager
        from backend.config import get_settings
        settings = get_settings()
        
        model_manager = OfflineModelManager(cache_dir=settings.embedding_cache_dir)
        models = model_manager.list_cached_models()
        
        # Get detailed info for each model
        detailed_models = []
        for model in models:
            info = model_manager.get_model_info(model["name"])
            detailed_models.append({
                "name": info["name"],
                "cached": info["cached"],
                "path": info["path"],
                "size": info["size"],
                "size_mb": info.get("size_mb", round(info["size"] / 1024 / 1024, 2) if info["size"] > 0 else 0)
            })
        
        return {"models": detailed_models, "count": len(detailed_models), "cache_dir": str(settings.embedding_cache_dir)}
    except Exception as e:
        logger.error(f"Error getting offline models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ModelDownloadRequest(BaseModel):
    """Request model for downloading a model."""
    model_name: str


@router.get("/unified")
async def get_unified_config():
    """Get unified configuration."""
    try:
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        config = config_manager.load_config()
        # Return unresolved config (with variables) for editing
        return config_manager._config if config_manager._config else config
    except Exception as e:
        logger.error(f"Error getting unified config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unified")
async def update_unified_config(config: Dict[str, Any]):
    """Update unified configuration."""
    try:
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        success = config_manager.save_config(config)
        if success:
            return {"status": "success", "message": "Unified configuration updated. Restart server for full effect."}
        else:
            raise HTTPException(status_code=500, detail="Failed to update unified config")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating unified config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chatbot-service")
async def get_chatbot_service_config():
    """Get chatbot service configuration from unified config."""
    try:
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        unified_config = config_manager.load_config()
        return unified_config.get("chatbot_service", {})
    except Exception as e:
        logger.error(f"Error getting chatbot service config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chatbot-service")
async def update_chatbot_service_config(config: Dict[str, Any]):
    """Update chatbot service configuration in unified config."""
    try:
        from backend.utils.unified_config_manager import get_unified_config_manager
        config_manager = get_unified_config_manager()
        unified_config = config_manager.load_config()
        unified_config["chatbot_service"] = config
        success = config_manager.save_config(unified_config)
        if success:
            return {"status": "success", "message": "Chatbot service configuration updated. Restart server for full effect."}
        else:
            raise HTTPException(status_code=500, detail="Failed to update chatbot service config")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chatbot service config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/download")
async def download_model(request: ModelDownloadRequest):
    """Download a model for offline use."""
    try:
        from backend.services.offline_model_manager import OfflineModelManager
        from backend.config import get_settings
        settings = get_settings()
        
        model_manager = OfflineModelManager(cache_dir=settings.embedding_cache_dir)
        success = model_manager.download_embedding_model(request.model_name)
        
        if success:
            return {"status": "success", "message": f"Model {request.model_name} downloaded successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to download model {request.model_name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key_path:path}")
async def get_config_value(key_path: str):
    """Get configuration value by dot-separated path."""
    try:
        config_manager = get_config_manager()
        value = config_manager.get(key_path)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Config key not found: {key_path}")
        return {"key_path": key_path, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config value: {e}")
        raise HTTPException(status_code=500, detail=str(e))

