"""
LLM Service for model switching and inference.
Supports Ollama, OpenAI, and M4 providers.
"""
import httpx
import json
from typing import Dict, List, Optional, Any
from backend.config import get_settings
from backend.config.database import get_db_session
from loguru import logger

Optional = Optional  # For type hints

settings = get_settings()


class LLMService:
    """LLM service for model inference with provider switching."""
    
    # Class-level storage for current model (shared across instances)
    _current_provider = None
    _current_model = None
    
    def __init__(self, db=None, vendor_id: Optional[str] = None):
        """Initialize LLM service."""
        self.settings = settings
        self.vendor_id = vendor_id
        
        # Load vendor-specific model if vendor_id is provided
        vendor_model_loaded = False
        if db is not None and vendor_id:
            logger.info(f"🔍 [LLMService.__init__] Attempting to load vendor-specific model for vendor_id: {vendor_id} (db: {db is not None})")
            try:
                from backend.models.saas_models import Vendor, VendorModelAssignment, Model
                # Get vendor by slug
                vendor = db.query(Vendor).filter(
                    Vendor.slug == vendor_id,
                    Vendor.deleted_at.is_(None)
                ).first()
                
                if vendor:
                    # Force a completely fresh query to bypass any session caching
                    # This ensures we get the latest default_model_id even if it was just updated
                    vendor_id_db = vendor.id
                    db.expire_all()  # Expire all objects in session
                    # CRITICAL: Use a raw SQL query to bypass ORM caching and get absolutely fresh data
                    from sqlalchemy import text
                    # Query by slug to ensure we get the latest data
                    result = db.execute(
                        text("SELECT v.id, v.default_model_id, m.code, m.provider FROM vendors v LEFT JOIN models m ON v.default_model_id = m.id WHERE v.slug = :slug AND v.deleted_at IS NULL"),
                        {"slug": vendor_id}
                    ).first()
                    if result:
                        fresh_vendor_id = result[0]
                        fresh_default_model_id = result[1]
                        fresh_model_code = result[2]
                        fresh_model_provider = result[3]
                        logger.info(f"📊 Fresh DB query (by slug): vendor_slug={vendor_id}, vendor_id={fresh_vendor_id}, default_model_id={fresh_default_model_id}, model_code={fresh_model_code}")
                        # Use the fresh data directly instead of ORM
                        if fresh_default_model_id and fresh_model_code:
                            # Set instance variables directly from fresh DB query
                            self.current_provider = fresh_model_provider or "ollama"
                            self.current_model = fresh_model_code
                            self._vendor_model = fresh_model_code
                            self._vendor_provider = fresh_model_provider or "ollama"
                            logger.info(f"✅ Loaded vendor model from FRESH DB query: {self.current_model} ({self.current_provider}) for vendor {vendor_id} (model_id: {fresh_default_model_id})")
                            vendor_model_loaded = True
                        else:
                            logger.warning(f"⚠️ Vendor {vendor_id} has default_model_id={fresh_default_model_id} but model not found!")
                    else:
                        logger.warning(f"⚠️ Vendor {vendor_id} not found in fresh query")
                        # Fall back to ORM query
                        vendor = db.query(Vendor).filter(
                            Vendor.slug == vendor_id,
                            Vendor.deleted_at.is_(None)
                        ).first()
                        logger.debug(f"Found vendor via ORM: {vendor.name if vendor else 'None'} (slug: {vendor_id}), default_model_id: {vendor.default_model_id if vendor else 'N/A'}")
                    
                    # First, try vendor's default_model_id (most direct)
                    if vendor.default_model_id:
                        model = db.query(Model).filter(Model.id == vendor.default_model_id).first()
                        if model:
                            # Set instance variables (vendor-specific, don't update class-level)
                            self.current_provider = model.provider
                            self.current_model = model.code
                            # Store original model to prevent overwriting
                            self._vendor_model = model.code
                            self._vendor_provider = model.provider
                            logger.info(f"✅ Loaded vendor default model from DB: {self.current_model} ({self.current_provider}) for vendor {vendor_id} (model_id: {model.id}, vendor.default_model_id: {vendor.default_model_id})")
                            # CRITICAL: Ensure instance variables are set and won't be overwritten
                            logger.debug(f"🔒 Locked instance model: {self.current_model} (vendor_id: {self.vendor_id})")
                            vendor_model_loaded = True
                        else:
                            logger.warning(f"⚠️ Vendor {vendor_id} has default_model_id={vendor.default_model_id} but model not found in database!")
                    
                    # Fallback to default model assignment if default_model_id not set
                    if not vendor_model_loaded:
                        default_assignment = db.query(VendorModelAssignment).filter(
                            VendorModelAssignment.vendor_id == vendor.id,
                            VendorModelAssignment.is_default == True,
                            VendorModelAssignment.enabled == True
                        ).first()
                        
                        if default_assignment:
                            model = db.query(Model).filter(Model.id == default_assignment.model_id).first()
                            if model:
                                # Set instance variables (vendor-specific, don't update class-level)
                                self.current_provider = model.provider
                                self.current_model = model.code  # Use 'code' field for model identifier
                                # Store vendor model to prevent overwriting
                                self._vendor_model = model.code
                                self._vendor_provider = model.provider
                                logger.info(f"✅ Loaded vendor model from assignment: {self.current_model} ({self.current_provider}) for vendor {vendor_id} (model_id: {model.id}, assignment_id: {default_assignment.id})")
                                vendor_model_loaded = True
            except Exception as e:
                logger.warning(f"Could not load vendor model from DB for vendor {vendor_id}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        else:
            if db is None:
                logger.debug(f"DB is None, skipping vendor model load for vendor_id: {vendor_id}")
            if not vendor_id:
                logger.debug(f"vendor_id is None or empty, skipping vendor model load")
        
        # Only load from global config if vendor model wasn't loaded
        if not vendor_model_loaded:
            # For vendor-specific instances, don't use class-level variables (they might be stale)
            # Only use class-level for global instances (no vendor_id)
            if self.vendor_id:
                # Vendor instance but no vendor model found - use settings directly
                self.current_provider = settings.llm_provider
                self.current_model = settings.llm_model
                logger.warning(f"⚠️ Vendor {self.vendor_id} has no model assigned, using default: {self.current_model}")
            else:
                # Global instance - can use class-level variables
                # Load from global model config if available, otherwise use settings
                if db is not None:
                    try:
                        from backend.services.model_manager import ModelManager
                        model_manager = ModelManager(db)
                        active_model = model_manager.get_active_model()
                        if active_model:
                            LLMService._current_provider = active_model.provider
                            LLMService._current_model = active_model.model_name
                            logger.info(f"Loaded active model from DB: {active_model.model_name} ({active_model.provider})")
                    except Exception as e:
                        logger.warning(f"Could not load model from DB: {e}")
                
                # Use class-level if set, otherwise use settings
                if LLMService._current_provider is None:
                    LLMService._current_provider = settings.llm_provider
                if LLMService._current_model is None:
                    LLMService._current_model = settings.llm_model
                
                # Set instance variables from class-level (for global/default model)
                self.current_provider = LLMService._current_provider
                self.current_model = LLMService._current_model
        # else: vendor model already set in instance variables above, don't overwrite
        
        # Load model configuration from database (max_tokens, temperature, etc.)
        if db is not None:
            self._load_model_config_from_db(db)
        
        # CRITICAL: If vendor model was loaded, it's already stored in _vendor_model (set at lines 77-78 or 100)
        # NEVER overwrite _vendor_model - it's the source of truth
        if vendor_model_loaded:
            # Ensure _vendor_model is set (it should be from lines 77-78 or 100)
            if not hasattr(self, '_vendor_model') or not self._vendor_model:
                logger.error(f"❌ CRITICAL: vendor_model_loaded=True but _vendor_model not set! Setting it now from current_model: {self.current_model}")
                self._vendor_model = self.current_model
                self._vendor_provider = self.current_provider
            # Ensure current_model matches _vendor_model (it should already, but double-check)
            if self.current_model != self._vendor_model:
                logger.warning(f"⚠️ current_model ({self.current_model}) != _vendor_model ({self._vendor_model}), fixing current_model...")
                self.current_model = self._vendor_model
                self.current_provider = self._vendor_provider
            logger.info(f"🔒 Vendor model locked: {self._vendor_model} (vendor_id: {self.vendor_id}) [SOURCE: DATABASE]")
        
        # Initialize provider with the model we loaded
        self._initialize_provider()
        
        # CRITICAL: After initialization, FORCE vendor model to stay - never allow overwriting
        if vendor_model_loaded and hasattr(self, '_vendor_model'):
            # ALWAYS use the vendor model, ignore any class-level variables or initialization changes
            self.current_model = self._vendor_model
            self.current_provider = self._vendor_provider
            logger.info(f"🔒 FORCED vendor model after init: {self.current_model} (vendor_id: {self.vendor_id}) [SOURCE: DATABASE]")
        
        # Final verification: Log the actual model that will be used and its source
        source = "DATABASE" if (vendor_model_loaded and hasattr(self, '_vendor_model')) else ("CONFIG" if not self.vendor_id else "ERROR")
        logger.info(f"🔍 FINAL CHECK - LLMService instance model: {self.current_model} (provider: {self.current_provider}, vendor_id: {self.vendor_id or 'global'}) [SOURCE: {source}]")
        
        # Load model configuration from database (max_tokens, temperature, etc.)
        if db is not None:
            self._load_model_config_from_db(db)
    
    def _load_model_config_from_db(self, db):
        """Load model configuration from database (model_configs table)."""
        try:
            from backend.models.saas_models import ModelConfig, Vendor, Model
            
            model_id = None
            vendor_db_id = None
            
            # Get model_id from current model
            if self.current_model:
                model = db.query(Model).filter(Model.code == self.current_model).first()
                if model:
                    model_id = model.id
            
            # Get vendor_db_id if vendor_id is set
            if self.vendor_id:
                vendor = db.query(Vendor).filter(
                    Vendor.slug == self.vendor_id,
                    Vendor.deleted_at.is_(None)
                ).first()
                if vendor:
                    vendor_db_id = vendor.id
                    # Also try to get model_id from vendor's default_model_id
                    if vendor.default_model_id:
                        model_id = vendor.default_model_id
            
            if not model_id:
                logger.debug("No model_id found, skipping database config load")
                return
            
            # Try to load from model_configs (vendor-specific first, then global)
            config = None
            if vendor_db_id:
                config = db.query(ModelConfig).filter(
                    ModelConfig.model_id == model_id,
                    ModelConfig.vendor_id == vendor_db_id,
                    ModelConfig.is_active == True
                ).first()
                if config:
                    logger.debug(f"✅ Loaded vendor-specific config from DB for model_id={model_id}, vendor_id={vendor_db_id}")
            
            if not config:
                # Try global config
                config = db.query(ModelConfig).filter(
                    ModelConfig.model_id == model_id,
                    ModelConfig.vendor_id.is_(None),
                    ModelConfig.is_active == True
                ).first()
                if config:
                    logger.debug(f"✅ Loaded global config from DB for model_id={model_id}")
            
            if config:
                # Override settings with database values
                self.settings.llm_max_tokens = int(config.max_tokens)
                self.settings.llm_temperature = float(config.temperature)
                self.settings.llm_top_p = float(config.top_p)
                self.settings.llm_top_k = int(config.top_k)
                logger.info(f"✅ Loaded model config from DB: max_tokens={config.max_tokens}, temp={config.temperature}, top_p={config.top_p}, top_k={config.top_k}")
            else:
                # Fall back to model default_max_tokens
                model = db.query(Model).filter(Model.id == model_id).first()
                if model and model.default_max_tokens:
                    self.settings.llm_max_tokens = model.default_max_tokens
                    logger.info(f"✅ Using model default max_tokens: {model.default_max_tokens} (from models.default_max_tokens)")
        except Exception as e:
            logger.warning(f"Could not load model config from DB: {e}")
            # Continue with settings defaults
    
    def _initialize_provider(self):
        """Initialize the current LLM provider."""
        try:
            if self.current_provider == "ollama":
                self._check_ollama_connection()
            elif self.current_provider == "openai":
                if not self.settings.openai_api_key:
                    logger.warning("OpenAI API key not set")
            elif self.current_provider == "m4":
                logger.info("M4 provider configured")
            
            logger.info(f"LLM service initialized with provider: {self.current_provider}, model: {self.current_model}")
        except Exception as e:
            logger.error(f"Error initializing LLM provider: {e}")
    
    def _check_ollama_connection(self):
        """Check if Ollama is accessible."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.settings.llm_base_url}/api/tags")
                if response.status_code == 200:
                    logger.info("Ollama connection successful")
                else:
                    logger.warning(f"Ollama connection check failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ollama not accessible: {e}")
    
    def switch_model(self, provider: str, model: str, **kwargs):
        """Switch to a different model/provider."""
        # CRITICAL: If this is a vendor-specific instance with a locked vendor model, only allow temporary switches
        if hasattr(self, '_vendor_model') and self._vendor_model:
            if kwargs.get('_allow_vendor_switch', False):
                # Temporary switch allowed (e.g., for cache models)
                logger.info(f"🔄 Temporarily switching vendor model: {self._vendor_model} → {model} (will restore after)")
                self.current_provider = provider
                self.current_model = model
                return
            else:
                # Block permanent switches - vendor models must be changed via database
                logger.warning(f"⚠️ BLOCKED: Attempted to permanently switch vendor {self.vendor_id} model from {self._vendor_model} to {model}. Use database switch endpoint instead.")
                return
        
        # For non-vendor instances, update class-level storage
        if not self.vendor_id:
            LLMService._current_provider = provider
            LLMService._current_model = model
        
        # Update instance variables
        self.current_provider = provider
        self.current_model = model
        
        # Update settings if provided
        if "temperature" in kwargs:
            self.settings.llm_temperature = kwargs["temperature"]
        if "max_tokens" in kwargs:
            self.settings.llm_max_tokens = kwargs["max_tokens"]
        
        logger.info(f"Switched to provider: {provider}, model: {model} (vendor_id: {self.vendor_id or 'global'})")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt to prepend
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Dict with 'content', 'tokens_used', 'model_used', etc.
        """
        try:
            if self.current_provider == "ollama":
                return await self._generate_ollama(messages, system_prompt, **kwargs)
            elif self.current_provider == "openai":
                return await self._generate_openai(messages, system_prompt, **kwargs)
            elif self.current_provider == "m4":
                return await self._generate_m4(messages, system_prompt, **kwargs)
            else:
                raise ValueError(f"Unknown provider: {self.current_provider}")
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "content": "I'm sorry, I'm experiencing technical difficulties. Please try again later.",
                "tokens_used": 0,
                "model_used": self.current_model,
                "error": str(e)
            }
    
    async def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using Ollama."""
        try:
            # Build prompt from messages for /api/generate fallback
            prompt_parts = []
            if system_prompt:
                prompt_parts.append(f"System: {system_prompt}\n")
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            
            prompt_parts.append("\nAssistant:")
            full_prompt = "\n".join(prompt_parts)
            
            # Try /api/chat first (newer Ollama versions)
            try:
                formatted_messages = []
                if system_prompt:
                    formatted_messages.append({
                        "role": "system",
                        "content": system_prompt
                    })
                formatted_messages.extend(messages)
                
                # CRITICAL: If vendor model was locked, ALWAYS use it - never allow overwriting
                logger.debug(f"🔍 DEBUG: hasattr(_vendor_model): {hasattr(self, '_vendor_model')}, _vendor_model: {getattr(self, '_vendor_model', 'NOT SET')}, current_model: {self.current_model}, vendor_id: {self.vendor_id}")
                if hasattr(self, '_vendor_model') and self._vendor_model:
                    if self.current_model != self._vendor_model:
                        logger.error(f"❌ CRITICAL: Vendor model was overwritten! Expected {self._vendor_model}, got {self.current_model}. FORCING vendor model...")
                        self.current_model = self._vendor_model
                        self.current_provider = self._vendor_provider
                        logger.info(f"✅ FORCED vendor model: {self.current_model}")
                    # ALWAYS use vendor model, even if current_model matches (to prevent any race conditions)
                    model_to_use = self._vendor_model
                    provider_to_use = self._vendor_provider
                    logger.info(f"✅ Using locked vendor model from DATABASE: {model_to_use} (vendor_id: {self.vendor_id})")
                else:
                    model_to_use = self.current_model
                    provider_to_use = self.current_provider
                    logger.warning(f"⚠️ NO VENDOR MODEL LOCKED! Using current_model from CONFIG/SETTINGS: {model_to_use} (vendor_id: {self.vendor_id or 'global'})")
                    if self.vendor_id:
                        logger.error(f"❌ CRITICAL ERROR: Vendor {self.vendor_id} has no _vendor_model set! This should not happen!")
                
                # Log the model being used for debugging
                logger.info(f"[OLLAMA] 🚀 GENERATING with model: {model_to_use} (provider: {provider_to_use}, vendor_id: {self.vendor_id or 'global'})")
                
                # CRITICAL: Verify model hasn't been overwritten
                if self.vendor_id and not self.current_model:
                    logger.error(f"❌ CRITICAL: Vendor {self.vendor_id} has no model set! This should not happen.")
                    raise ValueError(f"Model not set for vendor {self.vendor_id}")
                
                # Use the model we determined above (vendor model if locked)
                payload = {
                    "model": model_to_use,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.settings.llm_temperature),
                        "top_p": kwargs.get("top_p", self.settings.llm_top_p),
                        "top_k": kwargs.get("top_k", self.settings.llm_top_k),
                        "num_predict": kwargs.get("max_tokens", self.settings.llm_max_tokens)
                    }
                }
                
                # Timeout: 120 seconds (2 minutes) - adjust if needed for faster/slower responses
                # Lower timeout = faster failure, Higher timeout = allows longer responses
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.settings.llm_base_url}/api/chat",
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                
                content = result.get("message", {}).get("content", "")
                tokens_used = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                
                # CRITICAL: Use the model we actually used (vendor model if locked)
                model_for_response = model_to_use if 'model_to_use' in locals() else (self._vendor_model if (hasattr(self, '_vendor_model') and self._vendor_model) else self.current_model)
                logger.info(f"📤 Returning response with model: {model_for_response} [SOURCE: {'DATABASE' if hasattr(self, '_vendor_model') and self._vendor_model else 'CONFIG'}]")
                
                return {
                    "content": content,
                    "tokens_used": tokens_used,
                    "model_used": model_for_response,
                    "provider": "ollama"
                }
            except Exception as chat_error:
                # Fallback to /api/generate (older Ollama versions)
                logger.debug(f"/api/chat failed, trying /api/generate: {chat_error}")
                
                # CRITICAL: Use vendor model if locked, otherwise current_model
                logger.info(f"🔍 DEBUG in /api/generate fallback: hasattr(_vendor_model): {hasattr(self, '_vendor_model')}, _vendor_model: {getattr(self, '_vendor_model', 'NOT SET')}, current_model: {self.current_model}, vendor_id: {self.vendor_id}")
                if hasattr(self, '_vendor_model') and self._vendor_model:
                    model_for_generate = self._vendor_model
                    provider_for_generate = self._vendor_provider
                    logger.info(f"✅ Using locked vendor model in /api/generate: {model_for_generate} (vendor_id: {self.vendor_id})")
                else:
                    model_for_generate = self.current_model
                    provider_for_generate = self.current_provider
                    logger.warning(f"⚠️ NO VENDOR MODEL in /api/generate fallback! Using: {model_for_generate} (vendor_id: {self.vendor_id or 'global'})")
                
                payload = {
                    "model": model_for_generate,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.settings.llm_temperature),
                        "top_p": kwargs.get("top_p", self.settings.llm_top_p),
                        "top_k": kwargs.get("top_k", self.settings.llm_top_k),
                        "num_predict": kwargs.get("max_tokens", self.settings.llm_max_tokens)
                    }
                }
                
                # Timeout: 120 seconds (2 minutes) - adjust if needed for faster/slower responses
                # Lower timeout = faster failure, Higher timeout = allows longer responses
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.settings.llm_base_url}/api/generate",
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                
                content = result.get("response", "")
                tokens_used = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                
                return {
                    "content": content,
                    "tokens_used": tokens_used,
                    "model_used": self.current_model,
                    "provider": "ollama"
                }
            
        except Exception as e:
            logger.error(f"Error generating with Ollama: {e}")
            raise
    
    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using OpenAI."""
        try:
            import openai
            
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            client = openai.AsyncOpenAI(api_key=self.settings.openai_api_key)
            
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            formatted_messages.extend(messages)
            
            response = await client.chat.completions.create(
                model=kwargs.get("model", self.settings.openai_model),
                messages=formatted_messages,
                temperature=kwargs.get("temperature", self.settings.llm_temperature),
                max_tokens=kwargs.get("max_tokens", self.settings.llm_max_tokens),
                top_p=kwargs.get("top_p", self.settings.llm_top_p)
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "model_used": response.model,
                "provider": "openai"
            }
            
        except Exception as e:
            logger.error(f"Error generating with OpenAI: {e}")
            raise
    
    async def _generate_m4(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using M4 (placeholder for M4 integration)."""
        # M4 integration would go here
        # For now, fallback to Ollama
        logger.warning("M4 provider not fully implemented, using Ollama fallback")
        return await self._generate_ollama(messages, system_prompt, **kwargs)
    
    def get_available_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available models for specified provider or all providers."""
        all_models = []
        
        # Get Ollama models
        if not provider or provider == "ollama":
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.get(f"{self.settings.llm_base_url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        ollama_models = [
                            {
                                "name": model["name"],
                                "provider": "ollama",
                                "size": model.get("size", 0),
                                "modified": model.get("modified_at", "")
                            }
                            for model in data.get("models", [])
                        ]
                        all_models.extend(ollama_models)
            except Exception as e:
                logger.warning(f"Error getting Ollama models: {e}")
        
        # Get OpenAI models
        if not provider or provider == "openai":
            # OpenAI models (static list for now)
            openai_models = [
                {"name": "gpt-4-turbo-preview", "provider": "openai", "size": 0},
                {"name": "gpt-4", "provider": "openai", "size": 0},
                {"name": "gpt-3.5-turbo", "provider": "openai", "size": 0}
            ]
            all_models.extend(openai_models)
        
        return all_models

