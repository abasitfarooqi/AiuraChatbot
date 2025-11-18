"""
Offline Model Manager for downloading and managing Hugging Face models locally.
Ensures all models work offline without internet connection.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch


class OfflineModelManager:
    """Manages offline model downloads and caching."""
    
    def __init__(self, cache_dir: str = "./models"):
        """Initialize offline model manager."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir = self.cache_dir / "embeddings"
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.llm_dir = self.cache_dir / "llm"
        self.llm_dir.mkdir(parents=True, exist_ok=True)
    
    def download_embedding_model(self, model_name: str, force: bool = False) -> bool:
        """
        Download embedding model for offline use.
        
        Args:
            model_name: Hugging Face model name (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
            force: Force re-download even if exists
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Downloading embedding model: {model_name}")
            
            # Set cache directory
            os.environ['TRANSFORMERS_CACHE'] = str(self.embeddings_dir)
            os.environ['HF_HOME'] = str(self.embeddings_dir)
            
            # Download model
            model = SentenceTransformer(
                model_name,
                cache_folder=str(self.embeddings_dir),
                device='cpu'
            )
            
            # Save to local directory
            local_path = self.embeddings_dir / model_name.replace("/", "_")
            if not local_path.exists() or force:
                model.save(str(local_path))
                logger.info(f"Model saved to {local_path}")
            
            logger.info(f"Embedding model {model_name} ready for offline use")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading embedding model: {e}")
            return False
    
    def load_embedding_model_offline(self, model_name: str) -> Optional[SentenceTransformer]:
        """
        Load embedding model from local cache (offline).
        
        Args:
            model_name: Hugging Face model name
        
        Returns:
            SentenceTransformer model or None
        """
        try:
            local_path = self.embeddings_dir / model_name.replace("/", "_")
            
            if local_path.exists():
                logger.info(f"Loading embedding model from local cache: {local_path}")
                model = SentenceTransformer(str(local_path), device='cpu')
                return model
            else:
                logger.warning(f"Model not found in cache: {local_path}")
                # Try to load from Hugging Face cache
                os.environ['TRANSFORMERS_CACHE'] = str(self.embeddings_dir)
                os.environ['HF_HOME'] = str(self.embeddings_dir)
                model = SentenceTransformer(model_name, device='cpu')
                return model
                
        except Exception as e:
            logger.error(f"Error loading embedding model offline: {e}")
            return None
    
    def check_model_exists(self, model_name: str, model_type: str = "embedding") -> bool:
        """Check if model exists in local cache."""
        if model_type == "embedding":
            local_path = self.embeddings_dir / model_name.replace("/", "_")
        else:
            local_path = self.llm_dir / model_name.replace("/", "_")
        
        return local_path.exists()
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a cached model."""
        local_path = self.embeddings_dir / model_name.replace("/", "_")
        
        info = {
            "name": model_name,
            "cached": local_path.exists(),
            "path": str(local_path),
            "size": self._get_dir_size(local_path) if local_path.exists() else 0
        }
        
        return info
    
    def _get_dir_size(self, path: Path) -> int:
        """Get directory size in bytes."""
        total = 0
        if path.exists():
            for entry in path.rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
        return total
    
    def list_cached_models(self) -> list:
        """List all cached models."""
        models = []
        for model_dir in self.embeddings_dir.iterdir():
            if model_dir.is_dir():
                models.append({
                    "name": model_dir.name.replace("_", "/"),
                    "path": str(model_dir),
                    "size": self._get_dir_size(model_dir)
                })
        return models

