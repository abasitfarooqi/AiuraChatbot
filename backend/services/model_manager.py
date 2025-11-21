"""
Model Manager Service.
Handles model downloading, loading, switching, and management.
"""
import httpx
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.models.database import ModelConfig
from backend.config import get_settings
from loguru import logger

settings = get_settings()


class ModelManager:
    """Service for managing LLM models."""
    
    def __init__(self, db: Session):
        """Initialize model manager."""
        self.db = db
        self.settings = settings
    
    async def download_ollama_model(self, model_name: str) -> Dict[str, Any]:
        """Download an Ollama model."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.settings.llm_base_url}/api/pull",
                    json={"name": model_name},
                    timeout=300.0
                )
                response.raise_for_status()
                
                # Stream response if needed
                result = {"status": "downloading", "model": model_name}
                return result
                
        except Exception as e:
            logger.error(f"Error downloading Ollama model: {e}")
            return {"status": "error", "error": str(e)}
    
    def list_ollama_models(self) -> List[Dict[str, Any]]:
        """List available Ollama models."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.settings.llm_base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "name": model["name"],
                            "size": model.get("size", 0),
                            "modified": model.get("modified_at", ""),
                            "provider": "ollama"
                        }
                        for model in data.get("models", [])
                    ]
            return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get model configuration from database."""
        return self.db.query(ModelConfig).filter(
            ModelConfig.model_name == model_name
        ).first()
    
    def save_model_config(
        self,
        model_name: str,
        provider: str,
        **kwargs
    ) -> ModelConfig:
        """Save or update model configuration."""
        try:
            config = self.get_model_config(model_name)
            
            if not config:
                config = ModelConfig(
                    model_name=model_name,
                    provider=provider,
                    **kwargs
                )
                self.db.add(config)
            else:
                for key, value in kwargs.items():
                    setattr(config, key, value)
            
            self.db.commit()
            self.db.refresh(config)
            return config
            
        except Exception as e:
            logger.error(f"Error saving model config: {e}")
            self.db.rollback()
            raise
    
    def set_active_model(self, model_name: str) -> bool:
        """Set a model as active."""
        try:
            # Deactivate all models
            self.db.query(ModelConfig).update({"is_active": False})
            
            # Activate specified model
            config = self.get_model_config(model_name)
            if config:
                config.is_active = True
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting active model: {e}")
            self.db.rollback()
            return False
    
    def get_active_model(self):
        """Get the currently active model from SaaS Model table."""
        from backend.models.saas_models import Model
        # Get first active model from SaaS models table
        return self.db.query(Model).filter(
            Model.is_active == True
        ).first()
    
    def list_all_models(self) -> List[Dict[str, Any]]:
        """List all configured models."""
        configs = self.db.query(ModelConfig).all()
        return [
            {
                "name": config.model_name,
                "provider": config.provider,
                "is_active": config.is_active,
                "is_available": config.is_available,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens
            }
            for config in configs
        ]

