"""
Model management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.config.database import get_session_local
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
    vendor_id: Optional[str] = None  # Make vendor-aware


@router.get("/available")
async def get_available_models(
    provider: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get available models from DATABASE first, then optionally from Ollama."""
    try:
        from backend.models.saas_models import Model
        
        # CRITICAL: Get models from DATABASE first (single source of truth)
        query = db.query(Model).filter(Model.is_active == True)
        if provider:
            query = query.filter(Model.provider == provider)
        
        db_models = query.all()
        
        models = []
        for model in db_models:
            models.append({
                "name": model.code,  # Use 'code' as the identifier
                "display_name": model.display_name,
                "provider": model.provider,
                "is_active": model.is_active,
                "is_cache_model": model.is_cache_model,
                "source": "database"
            })
        
        # Optionally add Ollama models that aren't in database (for discovery)
        if provider == "ollama" or provider is None:
            try:
                model_manager = ModelManager(db)
                ollama_models = model_manager.list_ollama_models()
                db_model_codes = {m.code for m in db_models}
                
                for ollama_model in ollama_models:
                    if ollama_model["name"] not in db_model_codes:
                        models.append({
                            "name": ollama_model["name"],
                            "display_name": ollama_model["name"],
                            "provider": "ollama",
                            "size": ollama_model.get("size", 0),
                            "source": "ollama_not_in_db"
                        })
            except Exception as e:
                logger.warning(f"Could not fetch Ollama models: {e}")
        
        return {"provider": provider or "all", "models": models, "source": "database"}
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch")
async def switch_model(
    request: ModelSwitchRequest,
    db: Session = Depends(get_db)
):
    """Switch to a different model. If vendor_id is provided, updates vendor's model assignment."""
    try:
        # If vendor_id is provided, update vendor's model assignment
        if request.vendor_id:
            from backend.models.saas_models import Vendor, Model, VendorModelAssignment
            from datetime import datetime
            
            # Get vendor by slug
            vendor = db.query(Vendor).filter(
                Vendor.slug == request.vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            
            if not vendor:
                raise HTTPException(status_code=404, detail=f"Vendor {request.vendor_id} not found")
            
            # Find or create model in registry
            model = db.query(Model).filter(
                (Model.code == request.model) | (Model.display_name == request.model)
            ).first()
            
            if not model:
                # Create model if it doesn't exist
                model = Model(
                    code=request.model,
                    display_name=request.model,
                    provider=request.provider,
                    is_active=True
                )
                db.add(model)
                db.commit()
                db.refresh(model)
                logger.info(f"Created new model in registry: {request.model} ({request.provider})")
            
            # Unset ALL other defaults for this vendor FIRST
            db.query(VendorModelAssignment).filter(
                VendorModelAssignment.vendor_id == vendor.id
            ).update({"is_default": False})
            
            # Update or create vendor model assignment
            assignment = db.query(VendorModelAssignment).filter(
                VendorModelAssignment.vendor_id == vendor.id,
                VendorModelAssignment.model_id == model.id
            ).first()
            
            if assignment:
                # Update existing assignment
                assignment.is_default = True
                assignment.enabled = True
                assignment.updated_at = datetime.utcnow()
                logger.info(f"Updated existing assignment for vendor {request.vendor_id} to model {model.code} (id: {model.id})")
            else:
                # Create new assignment
                assignment = VendorModelAssignment(
                    vendor_id=vendor.id,
                    model_id=model.id,
                    is_default=True,
                    enabled=True
                )
                db.add(assignment)
                logger.info(f"Created new assignment for vendor {request.vendor_id} to model {model.code} (id: {model.id})")
            
            # Update vendor's default_model_id
            vendor.default_model_id = model.id
            db.flush()  # Flush to ensure changes are visible
            
            # Commit all changes with explicit commit
            try:
                db.commit()
                logger.info(f"✅ Committed vendor model update: vendor_id={vendor.id}, default_model_id={model.id}")
            except Exception as commit_error:
                logger.error(f"❌ Error committing vendor model update: {commit_error}")
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to commit vendor model update: {commit_error}")
            
            # Force a completely fresh query to verify the update
            db.expire_all()  # Expire all objects to force fresh queries
            vendor_verify = db.query(Vendor).filter(
                Vendor.id == vendor.id,
                Vendor.deleted_at.is_(None)
            ).first()
            
            if not vendor_verify:
                logger.error(f"❌ Vendor {vendor.id} not found after update!")
                raise HTTPException(status_code=500, detail="Vendor not found after update")
            
            if vendor_verify.default_model_id != model.id:
                logger.error(f"❌ CRITICAL: Database still shows wrong default_model_id! Expected {model.id}, got {vendor_verify.default_model_id}")
                # Force update with raw SQL if needed
                try:
                    from sqlalchemy import text
                    db.execute(
                        text("UPDATE vendors SET default_model_id = :model_id WHERE id = :vendor_id"),
                        {"model_id": model.id, "vendor_id": vendor.id}
                    )
                    db.commit()
                    # Verify again
                    db.expire_all()
                    vendor_verify = db.query(Vendor).filter(Vendor.id == vendor.id).first()
                    if vendor_verify.default_model_id != model.id:
                        raise HTTPException(status_code=500, detail=f"Failed to update vendor default model even with raw SQL. Expected {model.id}, got {vendor_verify.default_model_id}")
                    logger.info(f"✅ Fixed vendor default_model_id using raw SQL: {vendor_verify.default_model_id}")
                except Exception as sql_error:
                    logger.error(f"❌ Raw SQL update also failed: {sql_error}")
                    raise HTTPException(status_code=500, detail=f"Failed to update vendor default model: {sql_error}")
            
            logger.info(f"✅ Verified vendor {request.vendor_id} model update - default_model_id: {vendor_verify.default_model_id} (model: {model.code}, model_id: {model.id})")
            
            return {
                "status": "success",
                "provider": request.provider,
                "model": request.model,
                "vendor_id": request.vendor_id
            }
        
        # Global model switch (for backward compatibility)
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
async def get_current_model(
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get current model configuration. If vendor_id is provided, returns vendor's model."""
    try:
        llm_service = LLMService(db=db, vendor_id=vendor_id)
        return {
            "provider": llm_service.current_provider,
            "model": llm_service.current_model,
            "vendor_id": vendor_id
        }
    except Exception as e:
        logger.error(f"Error getting current model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_llm_config(
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get LLM configuration from database (vendor-aware, connected to active model)."""
    try:
        from backend.models.saas_models import Vendor, Model, ModelConfig
        
        # Get active model for vendor (or global)
        model_code = None
        model_id = None
        
        if vendor_id:
            # Get vendor's active model
            vendor = db.query(Vendor).filter(
                Vendor.slug == vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            
            if vendor and vendor.default_model_id:
                model = db.query(Model).filter(Model.id == vendor.default_model_id).first()
                if model:
                    model_code = model.code
                    model_id = model.id
        else:
            # Get global active model
            active_model = db.query(Model).filter(Model.is_active == True).first()
            if active_model:
                model_code = active_model.code
                model_id = active_model.id
        
        # Get model config from database
        config = None
        if model_id:
            if vendor_id and vendor:
                # Get vendor-specific config
                config = db.query(ModelConfig).filter(
                    ModelConfig.model_id == model_id,
                    ModelConfig.vendor_id == vendor.id,
                    ModelConfig.is_active == True
                ).first()
            
            # Fallback to global config for this model
            if not config:
                config = db.query(ModelConfig).filter(
                    ModelConfig.model_id == model_id,
                    ModelConfig.vendor_id.is_(None),
                    ModelConfig.is_active == True
                ).first()
        
        # Return config from database or defaults
        if config:
            return {
                "model_code": model_code,
                "model_id": model_id,
                "max_tokens": int(config.max_tokens),
                "temperature": float(config.temperature),
                "top_p": float(config.top_p),
                "top_k": int(config.top_k),
                "source": "database"
            }
        else:
            # Return defaults if no config found
            from backend.config import get_settings
            settings = get_settings()
            return {
                "model_code": model_code,
                "model_id": model_id,
                "max_tokens": settings.llm_max_tokens,
                "temperature": settings.llm_temperature,
                "top_p": settings.llm_top_p,
                "top_k": settings.llm_top_k,
                "source": "defaults"
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
    vendor_id: Optional[str] = None


@router.post("/config")
async def update_llm_config(
    request: LLMConfigRequest,
    db: Session = Depends(get_db)
):
    """Update LLM configuration in database (connected to active model)."""
    try:
        from backend.models.saas_models import Vendor, Model, ModelConfig
        from datetime import datetime
        
        # Get active model for vendor (or global)
        model_id = None
        vendor_db_id = None
        
        effective_vendor_id = request.vendor_id
        if effective_vendor_id:
            vendor = db.query(Vendor).filter(
                Vendor.slug == effective_vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            
            if vendor:
                vendor_db_id = vendor.id
                if vendor.default_model_id:
                    model_id = vendor.default_model_id
        else:
            # Get global active model
            active_model = db.query(Model).filter(Model.is_active == True).first()
            if active_model:
                model_id = active_model.id
        
        if not model_id:
            raise HTTPException(status_code=404, detail="No active model found. Please select a model first.")
        
        # Get or create model config
        config = None
        if vendor_db_id:
            # Get vendor-specific config
            config = db.query(ModelConfig).filter(
                ModelConfig.model_id == model_id,
                ModelConfig.vendor_id == vendor_db_id
            ).first()
        
        if not config:
            # Get or create global config for this model
            config = db.query(ModelConfig).filter(
                ModelConfig.model_id == model_id,
                ModelConfig.vendor_id.is_(None)
            ).first()
        
        if not config:
            # Create new config
            config = ModelConfig(
                model_id=model_id,
                vendor_id=vendor_db_id,
                max_tokens=request.max_tokens or 4000,
                temperature=request.temperature or 0.7,
                top_p=request.top_p or 0.9,
                top_k=request.top_k or 40
            )
            db.add(config)
        else:
            # Update existing config
            if request.max_tokens is not None:
                config.max_tokens = request.max_tokens
            if request.temperature is not None:
                config.temperature = request.temperature
            if request.top_p is not None:
                config.top_p = request.top_p
            if request.top_k is not None:
                config.top_k = request.top_k
            config.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(config)
        
        return {
            "status": "success",
            "config": {
                "model_id": model_id,
                "vendor_id": effective_vendor_id,
                "max_tokens": int(config.max_tokens),
                "temperature": float(config.temperature),
                "top_p": float(config.top_p),
                "top_k": int(config.top_k)
            },
            "message": "LLM configuration updated in database"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM config: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ========== MODEL PRESETS ==========

from datetime import datetime
from backend.models.saas_models import ModelPreset, ModelConfig

class PresetCreateRequest(BaseModel):
    """Request model for creating a preset."""
    name: str
    description: Optional[str] = None
    max_tokens: int
    temperature: float
    top_p: float
    top_k: int
    model_id: Optional[int] = None
    vendor_id: Optional[str] = None


class PresetUpdateRequest(BaseModel):
    """Request model for updating a preset."""
    name: Optional[str] = None
    description: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None


@router.get("/presets")
async def get_presets(
    vendor_id: Optional[str] = Query(None),
    model_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all presets (optionally filtered by vendor or model)."""
    try:
        from backend.models.saas_models import Vendor
        
        query = db.query(ModelPreset).filter(
            ModelPreset.is_active == True,
            ModelPreset.deleted_at.is_(None)
        )
        
        if vendor_id:
            vendor = db.query(Vendor).filter(
                Vendor.slug == vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            if vendor:
                query = query.filter(
                    (ModelPreset.vendor_id == vendor.id) | (ModelPreset.vendor_id.is_(None))
                )
        
        if model_id:
            query = query.filter(
                (ModelPreset.model_id == model_id) | (ModelPreset.model_id.is_(None))
            )
        
        presets = query.order_by(ModelPreset.is_default.desc(), ModelPreset.created_at.desc()).all()
        
        return {
            "presets": [
                {
                    "id": preset.id,
                    "name": preset.name,
                    "description": preset.description,
                    "model_id": preset.model_id,
                    "vendor_id": preset.vendor_id,
                    "max_tokens": int(preset.max_tokens),
                    "temperature": float(preset.temperature),
                    "top_p": float(preset.top_p),
                    "top_k": int(preset.top_k),
                    "is_default": preset.is_default,
                    "created_at": preset.created_at.isoformat() if preset.created_at else None
                }
                for preset in presets
            ]
        }
    except Exception as e:
        logger.error(f"Error getting presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/presets")
async def create_preset(
    request: PresetCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new preset."""
    try:
        from backend.models.saas_models import Vendor
        
        vendor_db_id = None
        if request.vendor_id:
            vendor = db.query(Vendor).filter(
                Vendor.slug == request.vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            if vendor:
                vendor_db_id = vendor.id
            else:
                raise HTTPException(status_code=404, detail=f"Vendor {request.vendor_id} not found")
        
        # Validate ranges
        if not (100 <= request.max_tokens <= 4000):
            raise HTTPException(status_code=400, detail="max_tokens must be between 100 and 4000")
        if not (0.0 <= request.temperature <= 2.0):
            raise HTTPException(status_code=400, detail="temperature must be between 0.0 and 2.0")
        if not (0.0 <= request.top_p <= 1.0):
            raise HTTPException(status_code=400, detail="top_p must be between 0.0 and 1.0")
        if not (1 <= request.top_k <= 100):
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")
        
        preset = ModelPreset(
            name=request.name,
            description=request.description,
            model_id=request.model_id,
            vendor_id=vendor_db_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            is_default=False,
            is_active=True
        )
        
        db.add(preset)
        db.commit()
        db.refresh(preset)
        
        return {
            "status": "success",
            "preset": {
                "id": preset.id,
                "name": preset.name,
                "description": preset.description,
                "max_tokens": int(preset.max_tokens),
                "temperature": float(preset.temperature),
                "top_p": float(preset.top_p),
                "top_k": int(preset.top_k)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating preset: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/presets/{preset_id}")
async def update_preset(
    preset_id: int,
    request: PresetUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update a preset."""
    try:
        preset = db.query(ModelPreset).filter(
            ModelPreset.id == preset_id,
            ModelPreset.deleted_at.is_(None)
        ).first()
        
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        if request.name is not None:
            preset.name = request.name
        if request.description is not None:
            preset.description = request.description
        if request.max_tokens is not None:
            if not (100 <= request.max_tokens <= 4000):
                raise HTTPException(status_code=400, detail="max_tokens must be between 100 and 4000")
            preset.max_tokens = request.max_tokens
        if request.temperature is not None:
            if not (0.0 <= request.temperature <= 2.0):
                raise HTTPException(status_code=400, detail="temperature must be between 0.0 and 2.0")
            preset.temperature = request.temperature
        if request.top_p is not None:
            if not (0.0 <= request.top_p <= 1.0):
                raise HTTPException(status_code=400, detail="top_p must be between 0.0 and 1.0")
            preset.top_p = request.top_p
        if request.top_k is not None:
            if not (1 <= request.top_k <= 100):
                raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")
            preset.top_k = request.top_k
        
        preset.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(preset)
        
        return {
            "status": "success",
            "preset": {
                "id": preset.id,
                "name": preset.name,
                "max_tokens": int(preset.max_tokens),
                "temperature": float(preset.temperature),
                "top_p": float(preset.top_p),
                "top_k": int(preset.top_k)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preset: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db)
):
    """Delete a preset (soft delete)."""
    try:
        preset = db.query(ModelPreset).filter(
            ModelPreset.id == preset_id,
            ModelPreset.deleted_at.is_(None)
        ).first()
        
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        preset.deleted_at = datetime.utcnow()
        preset.is_active = False
        db.commit()
        
        return {
            "status": "success",
            "message": f"Preset '{preset.name}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preset: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/presets/{preset_id}/apply")
async def apply_preset(
    preset_id: int,
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Apply a preset to the active model configuration."""
    try:
        from backend.models.saas_models import Vendor, Model
        
        preset = db.query(ModelPreset).filter(
            ModelPreset.id == preset_id,
            ModelPreset.is_active == True,
            ModelPreset.deleted_at.is_(None)
        ).first()
        
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        # Get active model for vendor (or global)
        model_id = None
        vendor_db_id = None
        
        if vendor_id:
            vendor = db.query(Vendor).filter(
                Vendor.slug == vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            
            if vendor:
                vendor_db_id = vendor.id
                if vendor.default_model_id:
                    model_id = vendor.default_model_id
        else:
            # Get global active model
            active_model = db.query(Model).filter(Model.is_active == True).first()
            if active_model:
                model_id = active_model.id
        
        if not model_id:
            raise HTTPException(status_code=404, detail="No active model found. Please select a model first.")
        
        # Get or create model config
        config = None
        if vendor_db_id:
            config = db.query(ModelConfig).filter(
                ModelConfig.model_id == model_id,
                ModelConfig.vendor_id == vendor_db_id
            ).first()
        
        if not config:
            config = db.query(ModelConfig).filter(
                ModelConfig.model_id == model_id,
                ModelConfig.vendor_id.is_(None)
            ).first()
        
        if not config:
            # Create new config
            config = ModelConfig(
                model_id=model_id,
                vendor_id=vendor_db_id,
                max_tokens=preset.max_tokens,
                temperature=preset.temperature,
                top_p=preset.top_p,
                top_k=preset.top_k
            )
            db.add(config)
        else:
            # Update existing config with preset values
            config.max_tokens = preset.max_tokens
            config.temperature = preset.temperature
            config.top_p = preset.top_p
            config.top_k = preset.top_k
            config.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(config)
        
        return {
            "status": "success",
            "preset_name": preset.name,
            "config": {
                "model_id": model_id,
                "vendor_id": vendor_id,
                "max_tokens": int(config.max_tokens),
                "temperature": float(config.temperature),
                "top_p": float(config.top_p),
                "top_k": int(config.top_k)
            },
            "message": f"Preset '{preset.name}' applied successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying preset: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
