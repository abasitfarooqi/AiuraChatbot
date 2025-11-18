"""
Configuration Manager for JSON-based configuration.
Loads and manages configuration from JSON files.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigManager:
    """Manages JSON-based configuration files."""
    
    def __init__(self, config_dir: str = "./config"):
        """Initialize config manager."""
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._app_config: Optional[Dict[str, Any]] = None
        self._system_prompts: Optional[Dict[str, Any]] = None
    
    def load_app_config(self) -> Dict[str, Any]:
        """Load application configuration from JSON."""
        if self._app_config is None:
            config_file = self.config_dir / "app_config.json"
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        self._app_config = json.load(f)
                    logger.info(f"Loaded app config from {config_file}")
                except Exception as e:
                    logger.error(f"Error loading app config: {e}")
                    self._app_config = self._get_default_app_config()
            else:
                logger.warning(f"Config file not found: {config_file}, using defaults")
                self._app_config = self._get_default_app_config()
                self.save_app_config(self._app_config)
        
        return self._app_config
    
    def save_app_config(self, config: Dict[str, Any]) -> bool:
        """Save application configuration to JSON."""
        try:
            config_file = self.config_dir / "app_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._app_config = config
            logger.info(f"Saved app config to {config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving app config: {e}")
            return False
    
    def load_system_prompts(self) -> Dict[str, Any]:
        """Load system prompts from JSON."""
        if self._system_prompts is None:
            prompts_file = self.config_dir / "system_prompts.json"
            if prompts_file.exists():
                try:
                    with open(prompts_file, "r", encoding="utf-8") as f:
                        self._system_prompts = json.load(f)
                    logger.info(f"Loaded system prompts from {prompts_file}")
                except Exception as e:
                    logger.error(f"Error loading system prompts: {e}")
                    self._system_prompts = self._get_default_system_prompts()
            else:
                logger.warning(f"Prompts file not found: {prompts_file}, using defaults")
                self._system_prompts = self._get_default_system_prompts()
                self.save_system_prompts(self._system_prompts)
        
        return self._system_prompts
    
    def save_system_prompts(self, prompts: Dict[str, Any]) -> bool:
        """Save system prompts to JSON."""
        try:
            prompts_file = self.config_dir / "system_prompts.json"
            with open(prompts_file, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=2, ensure_ascii=False)
            self._system_prompts = prompts
            logger.info(f"Saved system prompts to {prompts_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving system prompts: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path (e.g., 'application.api_port')."""
        config = self.load_app_config()
        keys = key_path.split(".")
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> bool:
        """Set configuration value by dot-separated path."""
        config = self.load_app_config()
        keys = key_path.split(".")
        target = config
        
        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the value
        target[keys[-1]] = value
        
        return self.save_app_config(config)
    
    def reload(self):
        """Reload configuration from files."""
        self._app_config = None
        self._system_prompts = None
        self.load_app_config()
        self.load_system_prompts()
    
    def _get_default_app_config(self) -> Dict[str, Any]:
        """Get default application configuration."""
        return {
            "application": {
                "environment": "development",
                "debug": True,
                "app_name": "AiuraChatbot",
                "app_version": "1.0.0",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_prefix": "/api/v1"
            },
            "database": {
                "database_url": "sqlite:///./data/chatbot.db",
                "database_echo": False
            },
            "vector_database": {
                "chroma_db_path": "./data/chroma_db",
                "chroma_collection_name": "neguinho_motors_kb"
            },
            "embedding": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "device": "cpu",
                "batch_size": 32,
                "cache_dir": "./models/embeddings",
                "offline_mode": True
            },
            "llm": {
                "provider": "ollama",
                "model": "mistral",
                "base_url": "http://localhost:11434",
                "temperature": 0.7,
                "max_tokens": 4000,
                "top_p": 0.9,
                "top_k": 40,
                "offline_mode": True
            },
            "openai": {
                "api_key": None,
                "model": "gpt-4-turbo-preview",
                "enabled": False
            },
            "rag": {
                "top_k": 5,
                "similarity_threshold": 0.2,
                "enable_filtering": True,
                "enable_reranking": False,
                "knowledge_base_path": "./rag_knowledge_base.json"
            },
            "memory": {
                "enabled": True,
                "max_turns": 20,
                "summary_enabled": False,
                "summary_threshold": 15
            },
            "domain_restriction": {
                "enabled": True,
                "keywords": [
                    "rental", "sale", "finance", "deposit", "warranty", "policy",
                    "servicing", "mot", "delivery", "accessories", "neguinho", "ngn",
                    "honda", "yamaha", "bike", "motorcycle", "scooter", "opening",
                    "hours", "branch", "branches", "location", "locations", "where",
                    "situated", "situate", "address", "contact", "phone", "email",
                    "how many", "catford", "tooting", "sutton"
                ]
            },
            "credits": {
                "token_tracking_enabled": True,
                "credit_system_enabled": True,
                "default_user_credits": 1000,
                "credit_cost_per_message": 10
            },
            "multi_vendor": {
                "enabled": False,
                "default_vendor_id": "default"
            },
            "logging": {
                "log_level": "INFO",
                "log_file": "./logs/chatbot.log",
                "log_rotation": "10 MB",
                "log_retention": "30 days"
            },
            "cors": {
                "origins": ["*"],
                "credentials": True
            },
            "security": {
                "secret_key": "your-secret-key-change-in-production",
                "access_token_expire_minutes": 1440
            },
            "frontend": {
                "frontend_url": "http://localhost:5173"
            }
        }
    
    def _get_default_system_prompts(self) -> Dict[str, Any]:
        """Get default system prompts."""
        return {
            "main_system_prompt": "You are the Neguinho Motors chatbot assistant.",
            "greeting_prompt": "Respond with a friendly greeting.",
            "query_prompt": "Answer the question using ONLY the information provided.",
            "fallback_message": "I don't have that information in my knowledge base.",
            "out_of_domain_message": "I can only assist with Neguinho Motors services.",
            "error_message": "I'm sorry, I'm experiencing technical difficulties."
        }


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: str = "./config") -> ConfigManager:
    """Get global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager

