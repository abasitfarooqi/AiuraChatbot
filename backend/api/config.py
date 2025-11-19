"""
Configuration management API endpoints.
Allows reading and updating JSON-based configuration.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime
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
async def get_config(vendor_id: Optional[str] = None):
    """Get full application configuration (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        from backend.utils.vendor_manager import get_vendor_manager
        
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        # Try vendor-specific file first
        vendor_manager = get_vendor_manager()
        app_config_path = vendor_manager.get_vendor_app_config_path(effective_vendor_id)
        
        if app_config_path.exists():
            with open(app_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        
        # Fallback to unified config
        config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
        unified_config = config_manager.load_config()
        
        # Convert unified config to app_config format
        config = {
            "application": unified_config.get("application", {}),
            "database": unified_config.get("database", {}),
            "vector_database": unified_config.get("vector_database", {}),
            "embedding": unified_config.get("embedding", {}),
            "llm": unified_config.get("llm", {}),
            "openai": unified_config.get("openai", {}),
            "rag": unified_config.get("rag", {}),
            "memory": unified_config.get("memory", {}),
            "domain_restriction": unified_config.get("domain_restriction", {}),
            "credits": unified_config.get("credits", {}),
            "multi_vendor": unified_config.get("multi_vendor", {}),
            "logging": unified_config.get("logging", {}),
            "cors": unified_config.get("cors", {}),
            "security": unified_config.get("security", {}),
            "frontend": unified_config.get("frontend", {}),
            "contact": unified_config.get("contact", {}),
            "company": {
                "name": unified_config.get("business", {}).get("company_name", ""),
                "company_number": unified_config.get("business", {}).get("company_number", ""),
                "registered_address": unified_config.get("business", {}).get("registered_address", ""),
                "trading_names": unified_config.get("business", {}).get("trading_names", [])
            },
            "branches": unified_config.get("branches", [])
        }
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
async def update_config_section(request: ConfigSectionRequest, vendor_id: Optional[str] = None):
    """Update an entire configuration section or full config (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        from backend.utils.vendor_manager import get_vendor_manager
        
        effective_vendor_id = vendor_id or settings.default_vendor_id
        vendor_manager = get_vendor_manager()
        app_config_path = vendor_manager.get_vendor_app_config_path(effective_vendor_id)
        
        # Load existing config or create from unified config
        if app_config_path.exists():
            with open(app_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            # Create from unified config
            config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
            unified_config = config_manager.load_config()
            business = unified_config.get("business", {})
            config = {
                "application": unified_config.get("application", {}),
                "database": unified_config.get("database", {}),
                "vector_database": unified_config.get("vector_database", {}),
                "embedding": unified_config.get("embedding", {}),
                "llm": unified_config.get("llm", {}),
                "openai": unified_config.get("openai", {}),
                "rag": unified_config.get("rag", {}),
                "memory": unified_config.get("memory", {}),
                "domain_restriction": unified_config.get("domain_restriction", {}),
                "credits": unified_config.get("credits", {}),
                "multi_vendor": unified_config.get("multi_vendor", {}),
                "logging": unified_config.get("logging", {}),
                "cors": unified_config.get("cors", {}),
                "security": unified_config.get("security", {}),
                "frontend": unified_config.get("frontend", {}),
                "contact": unified_config.get("contact", {}),
                "company": {
                    "name": business.get("company_name", ""),
                    "company_number": business.get("company_number", ""),
                    "registered_address": business.get("registered_address", ""),
                    "trading_names": business.get("trading_names", [])
                },
                "branches": unified_config.get("branches", [])
            }
        
        # If section is "all", replace entire config
        if request.section == "all":
            config = request.data
        else:
            config[request.section] = request.data
        
        # Save to vendor-specific file
        app_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(app_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {"status": "success", "section": request.section, "vendor_id": effective_vendor_id}
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
async def get_system_prompts(vendor_id: Optional[str] = None):
    """Get system prompts configuration (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        from backend.utils.vendor_manager import get_vendor_manager
        
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        # Try vendor-specific file first
        vendor_manager = get_vendor_manager()
        prompts_path = vendor_manager.get_vendor_system_prompts_path(effective_vendor_id)
        
        if prompts_path.exists():
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts = json.load(f)
            return prompts
        
        # Fallback to unified config
        config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
        unified_config = config_manager.load_config()
        prompts = unified_config.get("prompts", {})
        return prompts
    except Exception as e:
        logger.error(f"Error getting system prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts")
async def update_system_prompts(prompts: Dict[str, Any], vendor_id: Optional[str] = None):
    """Update system prompts (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        from backend.utils.vendor_manager import get_vendor_manager
        
        effective_vendor_id = vendor_id or settings.default_vendor_id
        vendor_manager = get_vendor_manager()
        
        # Save to vendor-specific file
        prompts_path = vendor_manager.get_vendor_system_prompts_path(effective_vendor_id)
        prompts_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(prompts_path, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        
        # Also update unified config
        config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
        unified_config = config_manager.load_config()
        unified_config["prompts"] = prompts
        config_manager.save_config(unified_config)
        
        return {"status": "success", "message": f"System prompts updated for vendor {effective_vendor_id}"}
    except Exception as e:
        logger.error(f"Error updating system prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base")
async def get_knowledge_base(vendor_id: Optional[str] = None):
    """Get knowledge base content (vendor-aware)."""
    try:
        # If vendor_id provided, use vendor-specific endpoint logic
        if vendor_id:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            
            # Check if vendor exists
            existing = vendor_manager.get_vendor(vendor_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
            
            rag_path = vendor_manager.get_vendor_rag_path(vendor_id)
            
            if not rag_path.exists():
                # Return empty structure if file doesn't exist
                return {
                    "metadata": {
                        "version": "2.0.0",
                        "vendor_id": vendor_id,
                        "description": f"Knowledge base for vendor {vendor_id}",
                        "chunking_strategy": "semantic_chunks_with_metadata"
                    },
                    "chunks": []
                }
            
            with open(rag_path, "r", encoding="utf-8") as f:
                kb_data = json.load(f)
            
            return kb_data
        
        # Default: use settings path
        from backend.config import get_settings
        settings = get_settings()
        kb_path = Path(settings.rag_knowledge_base_path)
        
        if not kb_path.exists():
            # Return empty structure if file doesn't exist
            return {
                "metadata": {
                    "version": "2.0.0",
                    "description": "Default knowledge base",
                    "chunking_strategy": "semantic_chunks_with_metadata"
                },
                "chunks": []
            }
        
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
async def get_chatbot_service_config(vendor_id: Optional[str] = None):
    """Get chatbot service configuration (vendor-aware)."""
    try:
        from backend.config import get_settings
        settings = get_settings()
        from backend.utils.vendor_manager import get_vendor_manager
        
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        # Try vendor-specific file first
        vendor_manager = get_vendor_manager()
        config_path = vendor_manager.get_vendor_chatbot_service_config_path(effective_vendor_id)
        
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                chatbot_service = json.load(f)
            return chatbot_service
        
        # Fallback to unified config
        config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
        unified_config = config_manager.load_config()
        chatbot_service = unified_config.get("chatbot_service", {})
        return chatbot_service
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

