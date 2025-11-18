"""
LLM Service for model switching and inference.
Supports Ollama, OpenAI, and M4 providers.
"""
import httpx
import json
from typing import Dict, List, Optional, Any
from backend.config import get_settings
from loguru import logger

settings = get_settings()


class LLMService:
    """LLM service for model inference with provider switching."""
    
    # Class-level storage for current model (shared across instances)
    _current_provider = None
    _current_model = None
    
    def __init__(self, db=None):
        """Initialize LLM service."""
        self.settings = settings
        
        # Load from database if available, otherwise use settings
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
        
        self.current_provider = LLMService._current_provider
        self.current_model = LLMService._current_model
        self._initialize_provider()
    
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
        # Update class-level storage (shared across instances)
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
        
        logger.info(f"Switched to provider: {provider}, model: {model}")
    
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
                
                payload = {
                    "model": self.current_model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.settings.llm_temperature),
                        "top_p": kwargs.get("top_p", self.settings.llm_top_p),
                        "top_k": kwargs.get("top_k", self.settings.llm_top_k),
                        "num_predict": kwargs.get("max_tokens", self.settings.llm_max_tokens)
                    }
                }
                
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.settings.llm_base_url}/api/chat",
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                
                content = result.get("message", {}).get("content", "")
                tokens_used = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                
                return {
                    "content": content,
                    "tokens_used": tokens_used,
                    "model_used": self.current_model,
                    "provider": "ollama"
                }
            except Exception as chat_error:
                # Fallback to /api/generate (older Ollama versions)
                logger.debug(f"/api/chat failed, trying /api/generate: {chat_error}")
                
                payload = {
                    "model": self.current_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.settings.llm_temperature),
                        "top_p": kwargs.get("top_p", self.settings.llm_top_p),
                        "top_k": kwargs.get("top_k", self.settings.llm_top_k),
                        "num_predict": kwargs.get("max_tokens", self.settings.llm_max_tokens)
                    }
                }
                
                async with httpx.AsyncClient(timeout=120.0) as client:
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
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models for current provider."""
        try:
            if self.current_provider == "ollama":
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{self.settings.llm_base_url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        return [
                            {
                                "name": model["name"],
                                "provider": "ollama",
                                "size": model.get("size", 0),
                                "modified": model.get("modified_at", "")
                            }
                            for model in data.get("models", [])
                        ]
            elif self.current_provider == "openai":
                # OpenAI models would be listed here
                return [
                    {"name": "gpt-4-turbo-preview", "provider": "openai"},
                    {"name": "gpt-3.5-turbo", "provider": "openai"}
                ]
            
            return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []

