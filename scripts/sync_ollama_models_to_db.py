#!/usr/bin/env python3
"""
Sync Ollama models to database.
Adds all models currently installed in Ollama to the database.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import httpx
except ImportError:
    # Try using requests as fallback
    import requests
    httpx = None
from sqlalchemy.orm import Session
from backend.config.database import get_session_local
from backend.models.saas_models import Model
from loguru import logger

def get_ollama_models() -> list:
    """Get list of models from Ollama."""
    try:
        if httpx:
            with httpx.Client(timeout=60.0) as client:
                response = client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    data = response.json()
                else:
                    logger.error(f"Failed to get Ollama models: {response.status_code}")
                    return []
        else:
            # Fallback to requests
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
            else:
                logger.error(f"Failed to get Ollama models: {response.status_code}")
                return []
        
        models = []
        for model_info in data.get("models", []):
            model_name = model_info.get("name", "")
            # Extract model name (remove :latest, :tag, etc.)
            base_name = model_name.split(":")[0] if ":" in model_name else model_name
            models.append({
                "name": model_name,
                "base_name": base_name,
                "size": model_info.get("size", 0),
                "modified": model_info.get("modified_at", "")
            })
        return models
    except Exception as e:
        logger.error(f"Error connecting to Ollama: {e}")
        return []

def sync_models_to_db(db: Session):
    """Sync Ollama models to database."""
    ollama_models = get_ollama_models()
    
    if not ollama_models:
        logger.warning("No models found in Ollama. Is Ollama running?")
        return
    
    logger.info(f"Found {len(ollama_models)} models in Ollama")
    
    added_count = 0
    updated_count = 0
    matched_count = 0
    
    # Mapping of Ollama model names to database codes (for models that might have different names)
    # Key: Ollama model name (lowercase), Value: Database code
    model_mappings = {
        "mistral:latest": "mistral",
        "mistral": "mistral",
        "llama2": "llama2x",
        "llama2:latest": "llama2x",
        "phi": "phix",
        "phi:latest": "phix",
        "phi-2": "phix",
        "qwen3:0.6b": "qwen3:0.6b",
        "gemma3:270m": "gemma3:270m"
    }
    
    for model_info in ollama_models:
        model_name = model_info["name"]  # Full name from Ollama (e.g., "Mistral:latest")
        base_name = model_info["base_name"]  # Base name (e.g., "mistral")
        
        # Determine the database code to use - check both full name and base name
        db_code = model_mappings.get(model_name.lower())
        if not db_code:
            db_code = model_mappings.get(base_name.lower())
        if not db_code:
            # If no mapping found, use the model name as-is (remove :latest if present)
            db_code = base_name if ":latest" in model_name.lower() else model_name
        
        # Check if model exists in database by code
        existing_model = db.query(Model).filter(
            Model.code == db_code
        ).first()
        
        if existing_model:
            # Model exists - update metadata if needed
            meta_data = existing_model.meta or {}
            new_meta = {"size": model_info["size"], "modified": model_info["modified"], "ollama_name": model_name}
            if meta_data != new_meta:
                existing_model.meta = new_meta
                updated_count += 1
                logger.info(f"Updated metadata for model: {db_code} (Ollama: {model_name})")
            else:
                matched_count += 1
                logger.debug(f"Model already in DB: {db_code} (Ollama: {model_name})")
        else:
            # Create new model
            # Determine display name
            display_name = model_name.replace(":latest", "").title()
            if ":" in model_name and ":latest" not in model_name:
                # Handle versioned models like "qwen3:0.6b"
                parts = model_name.split(":")
                display_name = f"{parts[0].title()} {parts[1]}"
            
            # Determine if it's a cache model (lightweight models)
            is_cache_model = any(keyword in model_name.lower() for keyword in ["phi", "gemma", "tiny", "small", "270m", "0.6b"])
            
            new_model = Model(
                code=db_code,
                display_name=display_name,
                provider="ollama",
                capabilities={"chat": True, "embeddings": False, "streaming": True},
                default_max_tokens=4000 if not is_cache_model else 2000,
                price_per_1k_tokens=0.0,  # Free for self-hosted
                is_cache_model=is_cache_model,
                is_active=True,
                meta={"size": model_info["size"], "modified": model_info["modified"], "ollama_name": model_name}
            )
            db.add(new_model)
            added_count += 1
            logger.info(f"✅ Added new model: {db_code} (display: {display_name}, Ollama: {model_name})")
    
    db.commit()
    logger.info(f"✅ Sync complete: {added_count} added, {updated_count} updated, {matched_count} already matched")
    
    # List all active models
    all_models = db.query(Model).filter(Model.is_active == True, Model.provider == "ollama").all()
    logger.info(f"📊 Active Ollama models in database: {', '.join([m.code for m in all_models])}")
    
    # Clean up duplicates - if we have both "mistral" and "Mistral:latest", keep only "mistral"
    mistral_models = db.query(Model).filter(
        Model.provider == "ollama",
        Model.code.in_(["mistral", "Mistral:latest", "mistral:latest"])
    ).all()
    if len(mistral_models) > 1:
        # Keep the one with code="mistral", delete others
        for model in mistral_models:
            if model.code.lower() != "mistral":
                logger.info(f"🗑️  Removing duplicate model: {model.code} (keeping 'mistral')")
                db.delete(model)
        db.commit()
        logger.info("✅ Cleaned up duplicate Mistral models")

def main():
    """Main function."""
    logger.info("Syncing Ollama models to database...")
    
    # Ensure MySQL is used if USE_MYSQL is set
    use_mysql = os.getenv("USE_MYSQL", "false").lower() in ("true", "1", "yes")
    if use_mysql:
        os.environ["USE_MYSQL"] = "true"
        logger.info("Using MySQL database")
    else:
        logger.info("Using SQLite database")
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        sync_models_to_db(db)
        logger.info("✅ Database sync complete!")
    except Exception as e:
        logger.error(f"Error syncing models: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()

