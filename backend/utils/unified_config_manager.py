"""
Unified Configuration Manager.
Loads and manages a single unified configuration file with variable substitution.
Supports multi-vendor and multi-business scenarios.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
import re


class UnifiedConfigManager:
    """Manages unified configuration with variable substitution."""
    
    def __init__(self, config_file: str = "./config/unified_config.json"):
        """Initialize unified config manager."""
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config: Optional[Dict[str, Any]] = None
        self._resolved_config: Optional[Dict[str, Any]] = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load unified configuration from JSON."""
        if self._config is None:
            if self.config_file.exists():
                try:
                    with open(self.config_file, "r", encoding="utf-8") as f:
                        self._config = json.load(f)
                    logger.info(f"Loaded unified config from {self.config_file}")
                    # Resolve variables
                    self._resolved_config = self._resolve_variables(self._config.copy())
                except Exception as e:
                    logger.error(f"Error loading unified config: {e}")
                    self._config = self._get_default_config()
                    self._resolved_config = self._resolve_variables(self._config.copy())
                    self.save_config(self._config)
            else:
                logger.warning(f"Config file not found: {self.config_file}, using defaults")
                self._config = self._get_default_config()
                self._resolved_config = self._resolve_variables(self._config.copy())
                self.save_config(self._config)
        
        return self._resolved_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save unified configuration to JSON."""
        try:
            # Remove resolved config before saving (keep original with variables)
            config_to_save = self._unresolve_variables(config)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            self._config = config_to_save
            self._resolved_config = self._resolve_variables(config_to_save.copy())
            logger.info(f"Saved unified config to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving unified config: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path."""
        config = self.load_config()
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
        config = self.load_config()
        # Work with unresolved config
        unresolved_config = self._config.copy() if self._config else self._get_default_config()
        keys = key_path.split(".")
        target = unresolved_config
        
        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set the value
        target[keys[-1]] = value
        
        return self.save_config(unresolved_config)
    
    def reload(self):
        """Reload configuration from file."""
        self._config = None
        self._resolved_config = None
        self.load_config()
    
    def _resolve_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve variables in configuration using business info."""
        # Get business info for variable substitution
        business = config.get("business", {})
        contact = config.get("contact", {})
        
        # Build variable map
        variables = {
            "company_name": business.get("company_name", "Company"),
            "company_name_lower": business.get("company_name", "company").lower().replace(" ", "_").replace(".", ""),
            "contact_phone": contact.get("primary_phone", ""),
            "contact_email": contact.get("primary_email", ""),
            "services_list": ", ".join(business.get("services_list", [])),
            "primary_service": business.get("services_list", [""])[0] if business.get("services_list") else "our services",
            "contact_format": contact.get("contact_format", "Contact: {phone} or {email}").format(
                phone=contact.get("primary_phone", ""),
                email=contact.get("primary_email", "")
            ),
            "fallback_message": config.get("prompts", {}).get("fallback_message", ""),
            "out_of_domain_message": config.get("prompts", {}).get("out_of_domain_message", "")
        }
        
        # Resolve variables recursively
        return self._resolve_dict(config, variables)
    
    def _resolve_dict(self, obj: Any, variables: Dict[str, str]) -> Any:
        """Recursively resolve variables in dict/list/string."""
        if isinstance(obj, dict):
            return {k: self._resolve_dict(v, variables) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_dict(item, variables) for item in obj]
        elif isinstance(obj, str):
            # Replace variables in string
            result = obj
            for var, value in variables.items():
                result = result.replace(f"{{{var}}}", str(value))
            return result
        else:
            return obj
    
    def _unresolve_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert resolved config back to template form (for saving)."""
        # This is a simplified version - in practice, we keep the original
        # For now, just return as-is (variables should be preserved in original)
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default unified configuration."""
        return {
            "metadata": {
                "version": "3.0.0",
                "vendor_id": "default",
                "business_type": "generic"
            },
            "business": {
                "company_name": "Company Name",
                "services_list": ["service 1", "service 2"]
            },
            "contact": {
                "primary_phone": "",
                "primary_email": "",
                "contact_format": "Contact: {phone} or {email}"
            },
            "application": {
                "api_port": 8000
            },
            "prompts": {
                "main_system_prompt": "You are a helpful assistant.",
                "fallback_message": "I don't have that information."
            },
            "chatbot_service": {
                "greetings": {
                    "simple_greetings": ["hi", "hello"]
                }
            }
        }
    
    def get_business_info(self) -> Dict[str, Any]:
        """Get business information."""
        config = self.load_config()
        return config.get("business", {})
    
    def get_contact_info(self) -> Dict[str, Any]:
        """Get contact information."""
        config = self.load_config()
        return config.get("contact", {})
    
    def get_prompts(self) -> Dict[str, Any]:
        """Get system prompts (with variables resolved)."""
        config = self.load_config()
        return config.get("prompts", {})
    
    def get_chatbot_service_config(self) -> Dict[str, Any]:
        """Get chatbot service configuration."""
        config = self.load_config()
        return config.get("chatbot_service", {})


# Global unified config manager instance
_unified_config_manager: Optional[UnifiedConfigManager] = None


def get_unified_config_manager(config_file: str = "./config/unified_config.json") -> UnifiedConfigManager:
    """Get global unified config manager instance."""
    global _unified_config_manager
    if _unified_config_manager is None:
        _unified_config_manager = UnifiedConfigManager(config_file)
    return _unified_config_manager

