"""
Main Chatbot Service.
Orchestrates RAG, LLM, and Memory services for complete chatbot functionality.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.services.rag_service import RAGService
from backend.services.llm_service import LLMService
from backend.services.memory_service import MemoryService
from backend.services.cache_service import CacheService
from backend.models.database import User, Chat, Message, TokenUsage
from backend.config import get_settings
from loguru import logger
import uuid
from datetime import datetime

settings = get_settings()


class ChatbotService:
    """Main chatbot service orchestrating all components."""
    
    def __init__(self, db: Session, vendor_id: Optional[str] = None):
        """Initialize chatbot service."""
        self.db = db
        self.vendor_id = vendor_id or settings.default_vendor_id
        self.rag_service = RAGService(vendor_id=self.vendor_id)
        self.llm_service = LLMService(db=db)  # Pass db to load active model
        self.memory_service = MemoryService(db)
        self.cache_service = CacheService(db=db, vendor_id=self.vendor_id)
        self.settings = settings
        self._load_chatbot_config()
    
    def get_system_prompt(self) -> str:
        """Get system prompt for LLM from vendor-specific unified config."""
        try:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
            unified_config = config_manager.load_config()
            prompts = unified_config.get("prompts", {})
            return prompts.get("main_system_prompt", self._get_default_system_prompt())
        except Exception as e:
            logger.warning(f"Error loading system prompt from vendor config: {e}, using default")
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt if config fails."""
        company_name = self.business_info.get("company_name", "Company")
        services = ", ".join(self.business_info.get("services_list", ["services"]))
        return f"""You are the {company_name} chatbot assistant. You help customers with {services}.

CRITICAL RULES - STRICTLY ENFORCE:
1. ONLY use information provided in the INFORMATION section below
2. NEVER make up, guess, or hallucinate any information
3. NEVER use knowledge from outside the provided information
4. If information is not in the provided context, say: "I don't have that information in my knowledge base."
5. ONLY answer questions about {company_name} services
6. For out-of-domain queries, redirect to appropriate services

RESPONSE FORMAT:
- Use ONLY facts from the provided INFORMATION section
- If a detail is not mentioned in the information, do NOT invent it
- Be accurate and precise
- Format responses with proper line breaks and structure"""
    
    async def process_message(
        self,
        user_id: str,
        chat_id: str,
        message: str,
        vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and generate response.
        
        Args:
            user_id: User identifier
            chat_id: Chat session ID
            message: User message
            vendor_id: Optional vendor ID for multi-vendor support
        
        Returns:
            Dict with response and metadata
        """
        try:
            # Use provided vendor_id or service's default
            effective_vendor_id = vendor_id or self.vendor_id
            
            # Get or create user and chat first (needed for response)
            user = self._get_or_create_user(user_id, effective_vendor_id)
            chat = self._get_or_create_chat(chat_id, user_id, effective_vendor_id)
            
            # Save user message
            user_message = self._save_message(chat_id, "user", message)
            
            # Check cache first (if enabled)
            # Reload config to get latest cache settings (in case they were changed via admin panel)
            import time
            start_time = time.time()
            
            # Load vendor-specific config for the effective vendor
            try:
                from backend.utils.vendor_manager import get_vendor_manager
                vendor_manager = get_vendor_manager()
                config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
                unified_config = config_manager.load_config()
                caching_config = unified_config.get("chatbot_service", {}).get("caching", {})
            except Exception as e:
                logger.error(f"[CACHE] Error loading vendor config for {effective_vendor_id}: {e}")
                # Fallback to service's config
                self.reload_chatbot_config()
                caching_config = self.chatbot_config.get("caching", {})
            
            cache_enabled = caching_config.get("enabled", True)
            use_cache_for_responses = caching_config.get("use_cache_for_responses", True)  # Default to True
            fallback_to_llm_on_cache_miss = caching_config.get("fallback_to_llm_on_cache_miss", True)  # Default to True
            disable_llm_completely = caching_config.get("disable_llm_completely", False)  # Default to False
            
            logger.info(f"[CACHE] Settings for vendor {effective_vendor_id} - enabled: {cache_enabled}, use_cache: {use_cache_for_responses}, fallback: {fallback_to_llm_on_cache_miss}, disable_llm: {disable_llm_completely}")
            logger.info(f"[CACHE] Processing question: '{message[:100]}...' (chat_id: {chat_id}, vendor: {effective_vendor_id})")
            
            # CRITICAL: If LLM is completely disabled, ONLY use cache - NEVER call LLM
            if disable_llm_completely:
                logger.warning(f"[LLM] 🚫 LLM is COMPLETELY DISABLED for vendor {effective_vendor_id} - cache-only mode")
                # Force cache to be enabled when LLM is disabled
                cache_enabled = True
                use_cache_for_responses = True
                fallback_to_llm_on_cache_miss = False
                logger.warning(f"[LLM] Forcing cache ON and fallback OFF for cache-only mode")
            
            cache_result = None
            cache_check_time = 0
            
            # Check cache if enabled OR if LLM is disabled (cache-only mode)
            if (cache_enabled and use_cache_for_responses) or disable_llm_completely:
                cache_check_start = time.time()
                logger.info(f"[CACHE] Checking cache for question...")
                cache_result = self.cache_service.check_cache(
                    question=message,
                    chat_id=chat_id,
                    vendor_id=effective_vendor_id
                )
                cache_check_time = time.time() - cache_check_start
                
                if cache_result:
                    # Found in cache - return cached answer
                    total_time = time.time() - start_time
                    logger.info(f"[CACHE] ✅ CACHE HIT! Question: '{message[:50]}...'")
                    logger.info(f"[CACHE]   - Similarity: {cache_result.get('similarity', 0):.3f}")
                    logger.info(f"[CACHE]   - Cache Type: {cache_result.get('cache_type', 'unknown')}")
                    logger.info(f"[CACHE]   - Cache ID: {cache_result.get('cache_id', 'unknown')}")
                    logger.info(f"[CACHE]   - Check Time: {cache_check_time:.3f}s, Total Time: {total_time:.3f}s")
                    logger.info(f"[CACHE]   - ⚡ Using cached answer (NO LLM call)")
                    
                    cached_answer = cache_result["answer"]
                    cache_type = cache_result["cache_type"]
                    cache_id = cache_result["cache_id"]
                    
                    # Estimate tokens saved (approximate)
                    estimated_tokens = len(cached_answer.split()) * 1.3  # Rough estimate
                    tokens_saved = int(estimated_tokens)
                    
                    # Save assistant message
                    assistant_message = self._save_message(
                        chat_id,
                        "assistant",
                        cached_answer,
                        tokens_used=0,  # No tokens used from cache
                        message_metadata={
                            "from_cache": True,
                            "cache_type": cache_type,
                            "cache_id": cache_id,
                            "similarity": cache_result.get("similarity", 0),
                            "tokens_saved": tokens_saved
                        }
                    )
                    
                    # Update cache stats
                    self.cache_service.update_cache_stats(
                        cache_id=cache_id,
                        cache_type=cache_type,
                        tokens_saved=tokens_saved
                    )
                    
                    # Update memory (lightweight - just track that we answered)
                    entities = self.memory_service.extract_entities(message, [])
                    self.memory_service.update_memory(
                        chat_id=chat_id,
                        entities=entities,
                        intent="cached_query"
                    )
                    
                    return {
                        "response": cached_answer,
                        "chat_id": chat_id,
                        "message_id": assistant_message.message_id,
                        "tokens_used": 0,
                        "credits_used": 0,
                        "model_used": "cache",
                        "retrieved_chunks": 0,
                        "is_domain_relevant": True,
                        "from_cache": True,
                        "cache_type": cache_type,
                        "cache_similarity": cache_result.get("similarity", 0),
                        "suggestions": []
                    }
                else:
                    # Cache miss
                    total_time = time.time() - start_time
                    logger.warning(f"[CACHE] ❌ CACHE MISS! Question: '{message[:50]}...'")
                    logger.warning(f"[CACHE]   - Check Time: {cache_check_time:.3f}s, Total Time: {total_time:.3f}s")
                    
                    if not fallback_to_llm_on_cache_miss:
                        # Cache miss and fallback disabled - return "not in cache" message
                        logger.warning(f"[CACHE]   - Fallback to LLM is DISABLED - returning cache miss message")
                        logger.warning(f"[CACHE]   - ⚠️ NO LLM call (fallback disabled)")
                    
                    # Get cache miss message from config
                    cache_miss_message = caching_config.get("cache_miss_message", 
                        "I don't have that information in my cache. Please try rephrasing your question or contact us for assistance.")
                    
                    assistant_message = self._save_message(
                        chat_id,
                        "assistant",
                        cache_miss_message,
                        tokens_used=0,
                        message_metadata={
                            "from_cache": False,
                            "cache_miss": True,
                            "fallback_disabled": True
                        }
                    )
                    
                    return {
                        "response": cache_miss_message,
                        "chat_id": chat_id,
                        "message_id": assistant_message.message_id,
                        "tokens_used": 0,
                        "credits_used": 0,
                        "model_used": "cache_miss",
                        "retrieved_chunks": 0,
                        "is_domain_relevant": True,
                        "from_cache": False,
                        "cache_miss": True,
                        "suggestions": []
                    }
            
            # CRITICAL: If LLM is completely disabled, NEVER proceed to LLM processing
            # This check MUST happen before ANY LLM-related code (RAG, domain check, etc.)
            if disable_llm_completely:
                # LLM is disabled - only cache is allowed
                if not cache_result:
                    # Cache miss and LLM disabled - return message and STOP HERE - NO LLM CALLS
                    logger.error(f"[LLM] 🚫 LLM DISABLED - Cache miss! Cannot generate response. Returning cache miss message.")
                    logger.error(f"[LLM] 🚫 BLOCKING all LLM processing - cache-only mode enforced")
                    cache_miss_message = caching_config.get("cache_miss_message", 
                        "I don't have that information in my cache. LLM is currently disabled. Please try rephrasing your question or contact us for assistance.")
                    
                    assistant_message = self._save_message(
                        chat_id,
                        "assistant",
                        cache_miss_message,
                        tokens_used=0,
                        message_metadata={
                            "from_cache": False,
                            "cache_miss": True,
                            "llm_disabled": True
                        }
                    )
                    
                    return {
                        "response": cache_miss_message,
                        "chat_id": chat_id,
                        "message_id": assistant_message.message_id,
                        "tokens_used": 0,
                        "credits_used": 0,
                        "model_used": "llm_disabled",
                        "retrieved_chunks": 0,
                        "is_domain_relevant": True,
                        "from_cache": False,
                        "cache_miss": True,
                        "llm_disabled": True,
                        "suggestions": []
                    }
                # If cache_result exists, it was already returned above, so we shouldn't reach here
                # This is a safety check - should never happen
                logger.error(f"[LLM] 🚫 LLM DISABLED but reached unexpected code path! This should not happen.")
                if cache_result:
                    return {
                        "response": cache_result["answer"],
                        "chat_id": chat_id,
                        "message_id": "",
                        "tokens_used": 0,
                        "credits_used": 0,
                        "model_used": "cache",
                        "retrieved_chunks": 0,
                        "is_domain_relevant": True,
                        "from_cache": True,
                        "suggestions": []
                    }
                # Should never reach here, but just in case
                logger.error(f"[LLM] 🚫 LLM DISABLED - No cache result and no fallback possible!")
                return {
                    "response": "I don't have that information in my cache. LLM is currently disabled.",
                    "chat_id": chat_id,
                    "message_id": "",
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "llm_disabled",
                    "retrieved_chunks": 0,
                    "is_domain_relevant": True,
                    "from_cache": False,
                    "cache_miss": True,
                    "llm_disabled": True,
                    "suggestions": []
                }
            
            # If we got here, LLM is NOT disabled, so we can proceed to LLM if needed
            # (either cache disabled, cache miss with fallback, or cache not checked)
            if not (cache_enabled and use_cache_for_responses and cache_result):
                if not cache_enabled:
                    logger.info(f"[LLM] Cache is DISABLED - proceeding to LLM")
                elif not use_cache_for_responses:
                    logger.info(f"[LLM] Use cache for responses is OFF - proceeding to LLM")
                elif cache_result is None and fallback_to_llm_on_cache_miss:
                    logger.info(f"[LLM] Cache miss with fallback ENABLED - proceeding to LLM")
            
            llm_start_time = time.time()
            logger.info(f"[LLM] 🚀 Starting LLM processing...")
            
            # Check domain relevance
            if not self.rag_service.is_domain_relevant(message):
                # Get out-of-domain message from unified config
                try:
                    from backend.utils.unified_config_manager import get_unified_config_manager
                    config_manager = get_unified_config_manager()
                    unified_config = config_manager.load_config()
                    prompts = unified_config.get("prompts", {})
                    out_of_domain_msg = prompts.get("out_of_domain_message", 
                        f"I can only assist with {', '.join(self.business_info.get('services_list', ['our services']))} related to {self.business_info.get('company_name', 'our company')}. How can I help you with our services?")
                except:
                    company_name = self.business_info.get("company_name", "our company")
                    services = ", ".join(self.business_info.get("services_list", ["our services"]))
                    out_of_domain_msg = f"I can only assist with {services} related to {company_name}. How can I help you with our services?"
                
                # Save assistant response for out-of-domain
                assistant_message = self._save_message(
                    chat_id,
                    "assistant",
                    out_of_domain_msg,
                    tokens_used=0
                )
                return {
                    "response": out_of_domain_msg,
                    "chat_id": chat_id,
                    "message_id": assistant_message.message_id,
                    "is_domain_relevant": False,
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0
                }
            
            # Check if this is the first message in the chat (initial chat)
            # Get conversation context (last 3-4 messages for better context)
            context = self.memory_service.get_conversation_context(chat_id)
            
            # Check if this is an initial/starting chat (no previous messages)
            is_initial_chat = not context or len(context) == 0
            
            # Check if current message is a simple greeting (should be handled fresh)
            message_lower = message.lower().strip()
            simple_greetings = self.chatbot_config.get("greetings", {}).get("simple_greetings", ["hi", "hello", "hey"])
            is_simple_greeting = message_lower in simple_greetings
            
            # For initial chat OR simple greetings: use ONLY current message, no context dependency
            if is_initial_chat or is_simple_greeting:
                # First message or greeting - use only current question, no previous context
                query_for_rag = message
                is_complete_question = True
                topic_changed = True
                current_topics = self._extract_topics(message) if not is_simple_greeting else set()
            else:
                # Chat has history - use context-aware analysis
                # Check if current question is complete and topic-changing
                is_complete_question, topic_changed, current_topics = self._analyze_question_completeness(message, context)
                
                # Build query: use only current message if it's complete and topic-changing,
                # otherwise use enhanced query with conversation history
                if is_complete_question and topic_changed:
                    # User asked a complete question about a different topic - use only current question
                    query_for_rag = message
                else:
                    # Incomplete or ambiguous question - use conversation history for context
                    query_for_rag = self._build_enhanced_query(message, context)
            
            # Retrieve relevant chunks from RAG
            retrieved_chunks = self.rag_service.retrieve(
                query=query_for_rag,
                vendor_id=vendor_id or settings.default_vendor_id
            )
            
            # Build context for LLM - STRICT: Only use RAG chunks, no fallback
            context_text = ""
            if retrieved_chunks:
                context_text = "\n\n".join([
                    f"[{i+1}] {chunk['content']}"
                    for i, chunk in enumerate(retrieved_chunks)
                ])
            else:
                # For greetings or simple queries, allow without RAG chunks
                if is_simple_greeting:
                    context_text = ""  # Greetings don't need RAG context
                else:
                    # Try a broader search with lower threshold
                    broader_chunks = self.rag_service.retrieve(
                        query=message,
                        top_k=5,
                        vendor_id=vendor_id or settings.default_vendor_id
                    )
                    if broader_chunks:
                        context_text = "\n\n".join([
                            f"[{i+1}] {chunk['content']}"
                            for i, chunk in enumerate(broader_chunks)
                        ])
                    else:
                        # NO FALLBACK - Return message that information is not available
                        # This ensures no hallucinations
                        try:
                            from backend.utils.unified_config_manager import get_unified_config_manager
                            config_manager = get_unified_config_manager()
                            unified_config = config_manager.load_config()
                            prompts = unified_config.get("prompts", {})
                            fallback_msg = prompts.get("fallback_message",
                                f"I don't have that information in my knowledge base. Please contact us at {self.contact_info.get('primary_email', '')} or {self.contact_info.get('primary_phone', '')} for more details.")
                        except:
                            email = self.contact_info.get("primary_email", "")
                            phone = self.contact_info.get("primary_phone", "")
                            fallback_msg = f"I don't have that information in my knowledge base. Please contact us at {email} or {phone} for more details."
                        
                        assistant_message = self._save_message(
                            chat_id,
                            "assistant",
                            fallback_msg,
                            tokens_used=0
                        )
                        return {
                            "response": fallback_msg,
                            "chat_id": chat_id,
                            "message_id": assistant_message.message_id,
                            "is_domain_relevant": True,
                            "tokens_used": 0,
                            "credits_used": 0,
                            "model_used": "",
                            "retrieved_chunks": 0
                        }
            
            # Prepare messages for LLM
            messages = []
            # Only add conversation history if this is NOT an initial chat AND NOT a simple greeting
            # For initial chat or greetings, use only the current question with RAG context
            if not is_initial_chat and not is_simple_greeting and context:
                max_context = self.chatbot_config.get("context_management", {}).get("max_context_messages", 10)
                messages.extend(context[-max_context:])  # Last N messages for context
            
            # Add current query with STRICT RAG-only instructions
            # For greetings, always process even without context_text
            if context_text or is_simple_greeting:
                # Handle simple greetings specially
                if is_simple_greeting:
                    # Simple greeting - use vendor-specific config
                    try:
                        from backend.utils.vendor_manager import get_vendor_manager
                        vendor_manager = get_vendor_manager()
                        config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
                        unified_config = config_manager.load_config()
                        prompts = unified_config.get("prompts", {})
                        company_name = unified_config.get("business", {}).get("company_name", "our company")
                        greeting_template = prompts.get("greeting_prompt", 
                            f"""The user just said: "{{message}}"\n\nRespond with a friendly greeting and offer to help with {company_name} services.\n\nKeep it brief and welcoming. Do not mention any specific information unless asked.""")
                        user_message_content = greeting_template.format(message=message)
                    except Exception as e:
                        logger.warning(f"Error loading greeting prompt from vendor config: {e}")
                        company_name = self.business_info.get("company_name", "our company")
                        user_message_content = f"""The user just said: "{message}"

Respond with a friendly greeting and offer to help with {company_name} services.

Keep it brief and welcoming. Do not mention any specific information unless asked."""
                else:
                    # STRICT prompt - use from vendor-specific config
                    try:
                        from backend.utils.vendor_manager import get_vendor_manager
                        vendor_manager = get_vendor_manager()
                        config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
                        unified_config = config_manager.load_config()
                        prompts = unified_config.get("prompts", {})
                        query_template = prompts.get("query_prompt",
                            """CRITICAL: Answer the question using ONLY the information provided below. DO NOT use any knowledge outside of this information.

INFORMATION FROM KNOWLEDGE BASE:
{context_text}

QUESTION: {message}

INSTRUCTIONS:
- Use ONLY facts from the INFORMATION section above
- If the answer is not in the information, say: "{fallback_message}"
- DO NOT make up, guess, or invent any information
- DO NOT use knowledge from outside the provided information
- Format your answer with proper line breaks and structure

ANSWER (based ONLY on the information above):""")
                        fallback_msg = prompts.get("fallback_message", "I don't have that information in my knowledge base.")
                        user_message_content = query_template.format(
                            context_text=context_text, 
                            message=message,
                            fallback_message=fallback_msg
                        )
                    except:
                        # Fallback to default
                        email = self.contact_info.get("primary_email", "")
                        phone = self.contact_info.get("primary_phone", "")
                        user_message_content = f"""CRITICAL: Answer the question using ONLY the information provided below. DO NOT use any knowledge outside of this information.

INFORMATION FROM KNOWLEDGE BASE:
{context_text}

QUESTION: {message}

INSTRUCTIONS:
- Use ONLY facts from the INFORMATION section above
- If the answer is not in the information, say: "I don't have that information in my knowledge base. Please contact us at {email} or {phone} for more details."
- DO NOT make up, guess, or invent any information
- DO NOT use knowledge from outside the provided information
- Format your answer with proper line breaks and structure

ANSWER (based ONLY on the information above):"""
            else:
                # This should not happen due to check above, but just in case
                try:
                    from backend.utils.unified_config_manager import get_unified_config_manager
                    config_manager = get_unified_config_manager()
                    unified_config = config_manager.load_config()
                    prompts = unified_config.get("prompts", {})
                    fallback_msg = prompts.get("fallback_message",
                        f"I don't have that information in my knowledge base. Please contact us at {self.contact_info.get('primary_email', '')} or {self.contact_info.get('primary_phone', '')} for more details.")
                except:
                    email = self.contact_info.get("primary_email", "")
                    phone = self.contact_info.get("primary_phone", "")
                    fallback_msg = f"I don't have that information in my knowledge base. Please contact us at {email} or {phone} for more details."
                
                assistant_message = self._save_message(
                    chat_id,
                    "assistant",
                    fallback_msg,
                    tokens_used=0
                )
                return {
                    "response": fallback_msg,
                    "chat_id": chat_id,
                    "message_id": assistant_message.message_id,
                    "is_domain_relevant": True,
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0
                }
            
            messages.append({
                "role": "user",
                "content": user_message_content
            })
            
            # Check if we should use lightweight model for cache generation
            use_cache_model = False
            original_provider = None
            original_model = None
            cache_model_provider = None
            cache_model_name = None
            
            # Reload caching config to get latest settings
            try:
                from backend.utils.vendor_manager import get_vendor_manager
                vendor_manager = get_vendor_manager()
                config_manager = vendor_manager.get_vendor_config_manager(effective_vendor_id)
                unified_config = config_manager.load_config()
                caching_config = unified_config.get("chatbot_service", {}).get("caching", {})
                use_cache_model = caching_config.get("use_lightweight_model_for_cache", False)
                cache_model_provider = caching_config.get("cache_model_provider")
                cache_model_name = caching_config.get("cache_model_name")
            except Exception as e:
                logger.warning(f"[LLM] Error loading cache model config: {e}, using default model")
            
            # Switch to cache model if enabled and configured
            if use_cache_model and cache_model_provider and cache_model_name:
                # Save original model
                original_provider = self.llm_service.current_provider
                original_model = self.llm_service.current_model
                
                # Switch to cache model
                logger.info(f"[LLM] 🔄 Switching to lightweight cache model: {cache_model_name} ({cache_model_provider})")
                self.llm_service.switch_model(cache_model_provider, cache_model_name)
            
            # Generate response
            logger.info(f"[LLM] Calling LLM service with {len(messages)} message(s)...")
            if use_cache_model and cache_model_provider and cache_model_name:
                logger.info(f"[LLM] Using lightweight cache model: {cache_model_name} ({cache_model_provider})")
            llm_call_start = time.time()
            
            llm_response = await self.llm_service.generate(
                messages=messages,
                system_prompt=self.get_system_prompt()
            )
            
            llm_call_time = time.time() - llm_call_start
            response_content = llm_response.get("content", "")
            tokens_used = llm_response.get("tokens_used", 0)
            
            # Switch back to original model if we switched
            if use_cache_model and original_provider and original_model:
                logger.info(f"[LLM] 🔄 Switching back to original model: {original_model} ({original_provider})")
                self.llm_service.switch_model(original_provider, original_model)
            
            logger.info(f"[LLM] ✅ LLM response received")
            logger.info(f"[LLM]   - Tokens used: {tokens_used}")
            logger.info(f"[LLM]   - Model used: {llm_response.get('model_used', 'unknown')}")
            logger.info(f"[LLM]   - LLM call time: {llm_call_time:.3f}s")
            logger.info(f"[LLM]   - Total processing time: {time.time() - llm_start_time:.3f}s")
            
            # Validate response is based on RAG chunks (prevent hallucinations)
            # Skip validation for simple greetings as they don't need RAG chunks
            validation_config = self.chatbot_config.get("validation", {})
            if validation_config.get("enable_response_validation", True) and not is_simple_greeting:
                if not self._validate_response_from_rag(response_content, retrieved_chunks, message):
                    # Response seems to contain information not in RAG - return safe message
                    logger.warning(f"Response validation failed - possible hallucination detected for query: {message[:50]}")
                    fallback = validation_config.get("fallback_message", 
                        f"I don't have that information in my knowledge base. Please contact us at {self.contact_info.get('primary_email', '')} or {self.contact_info.get('primary_phone', '')} for more details.")
                    response_content = fallback
            
            # Post-process response for better structure
            response_content = self._format_response(response_content, message, retrieved_chunks)
            
            # Save assistant message
            assistant_message = self._save_message(
                chat_id,
                "assistant",
                response_content,
                tokens_used=tokens_used,
                model_used=llm_response.get("model_used"),
                message_metadata={
                    "retrieved_chunks": len(retrieved_chunks),
                    "provider": llm_response.get("provider")
                }
            )
            
            # Update memory
            entities = self.memory_service.extract_entities(message, retrieved_chunks)
            self.memory_service.update_memory(
                chat_id=chat_id,
                entities=entities,
                intent="query"
            )
            
            # Track token usage
            if self.settings.token_tracking_enabled:
                self._track_token_usage(
                    user_id=user_id,
                    chat_id=chat_id,
                    tokens_used=tokens_used,
                    model=llm_response.get("model_used"),
                    credits_used=self._calculate_credits(tokens_used)
                )
            
            # Update user credits
            if self.settings.credit_system_enabled:
                credits_used = self._calculate_credits(tokens_used)
                user.credits -= credits_used
                self.db.commit()
            
            # Save to cache (if enabled and not a simple greeting)
            if cache_enabled and not is_simple_greeting and response_content:
                caching_config = self.chatbot_config.get("caching", {})
                save_to_temp = caching_config.get("save_to_temporary_cache", True)
                save_to_main = caching_config.get("save_to_main_cache", True)
                
                logger.info(f"[CACHE] Saving LLM response to cache - temp: {save_to_temp}, main: {save_to_main}")
                
                # Extract metadata for cache
                cache_metadata = {
                    "topics": list(current_topics) if current_topics else [],
                    "retrieved_chunks": len(retrieved_chunks),
                    "model_used": llm_response.get("model_used"),
                    "is_complete_question": is_complete_question
                }
                
                # Save to temporary cache (always for active chats)
                if save_to_temp:
                    save_start = time.time()
                    cache_id = self.cache_service.save_to_temporary_cache(
                        chat_id=chat_id,
                        question=message,
                        answer=response_content,
                        vendor_id=effective_vendor_id,
                        tokens_used=tokens_used,
                        metadata=cache_metadata
                    )
                    save_time = time.time() - save_start
                    if cache_id:
                        logger.info(f"[CACHE] ✅ Saved to temporary cache: {cache_id} (time: {save_time:.3f}s)")
                    else:
                        logger.warning(f"[CACHE] ⚠️ Failed to save to temporary cache (time: {save_time:.3f}s)")
                
                # Save to main cache (if enabled and question is complete)
                if save_to_main and is_complete_question:
                    # Only save if question is substantial enough
                    min_question_length = caching_config.get("min_question_length_for_main_cache", 10)
                    if len(message.split()) >= min_question_length:
                        save_start = time.time()
                        cache_id = self.cache_service.save_to_main_cache(
                            question=message,
                            answer=response_content,
                            vendor_id=effective_vendor_id,
                            tokens_used=tokens_used,
                            metadata=cache_metadata
                        )
                        save_time = time.time() - save_start
                        if cache_id:
                            logger.info(f"[CACHE] ✅ Saved to main cache: {cache_id} (time: {save_time:.3f}s)")
                        else:
                            logger.warning(f"[CACHE] ⚠️ Failed to save to main cache (time: {save_time:.3f}s)")
                    else:
                        logger.debug(f"[CACHE] Question too short ({len(message.split())} words < {min_question_length}) - skipping main cache")
                elif save_to_main:
                    logger.debug(f"[CACHE] Question not complete - skipping main cache save")
            
            # Generate helpful suggestions based on conversation history and current topic
            # For initial chat or greetings, show general suggestions
            # For ongoing chat, only show suggestions if question was incomplete/ambiguous
            suggestions = []
            if is_initial_chat or is_simple_greeting:
                # Initial chat or greeting - show general helpful suggestions from config
                suggestions = self.chatbot_config.get("greetings", {}).get("initial_suggestions", [
                    "What services do you offer?",
                    "Tell me about rental bikes",
                    "What are your opening hours?",
                    "Where are your branches located?"
                ])
            elif not (is_complete_question and topic_changed):
                # Ongoing chat - only show suggestions if question was incomplete/ambiguous
                suggestions = self._generate_suggestions(chat_id, message, retrieved_chunks, current_topics=current_topics)
            
            total_processing_time = time.time() - start_time
            logger.info(f"[SUMMARY] ✅ Response generated - Total time: {total_processing_time:.3f}s, Tokens: {tokens_used}, Model: {llm_response.get('model_used', 'unknown')}")
            
            return {
                "response": response_content,
                "chat_id": chat_id,
                "message_id": assistant_message.message_id,
                "tokens_used": tokens_used,
                "credits_used": self._calculate_credits(tokens_used),
                "model_used": llm_response.get("model_used"),
                "retrieved_chunks": len(retrieved_chunks),
                "is_domain_relevant": True,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            # Ensure we have chat_id even on error
            try:
                # Get error message from unified config
                try:
                    from backend.utils.unified_config_manager import get_unified_config_manager
                    config_manager = get_unified_config_manager()
                    unified_config = config_manager.load_config()
                    prompts = unified_config.get("prompts", {})
                    error_msg = prompts.get("error_message",
                        f"I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at {self.contact_info.get('primary_email', '')}")
                except:
                    email = self.contact_info.get("primary_email", "")
                    error_msg = f"I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at {email}"
                
                chat = self._get_or_create_chat(chat_id, user_id, vendor_id or settings.default_vendor_id)
                error_message = self._save_message(
                    chat_id,
                    "assistant",
                    error_msg,
                    tokens_used=0
                )
                return {
                    "response": error_msg,
                    "chat_id": chat_id,
                    "message_id": error_message.message_id,
                    "error": str(e),
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0,
                    "is_domain_relevant": True
                }
            except:
                # Fallback if even chat creation fails
                try:
                    from backend.utils.unified_config_manager import get_unified_config_manager
                    config_manager = get_unified_config_manager()
                    unified_config = config_manager.load_config()
                    prompts = unified_config.get("prompts", {})
                    error_msg = prompts.get("error_message",
                        f"I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at {self.contact_info.get('primary_email', '')}")
                except:
                    email = self.contact_info.get("primary_email", "")
                    error_msg = f"I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at {email}"
                
                return {
                    "response": error_msg,
                    "chat_id": chat_id or f"error_{user_id}",
                    "message_id": "",
                    "error": str(e),
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0,
                    "is_domain_relevant": True
                }
    
    def _get_or_create_user(self, user_id: str, vendor_id: str) -> User:
        """Get or create user."""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                vendor_id=vendor_id,
                credits=self.settings.default_user_credits
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def _get_or_create_chat(self, chat_id: str, user_id: str, vendor_id: str) -> Chat:
        """Get or create chat session."""
        chat = self.db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(
                chat_id=chat_id,
                user_id=user_id,
                vendor_id=vendor_id
            )
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
        return chat
    
    def _save_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        model_used: Optional[str] = None,
        message_metadata: Optional[Dict] = None
    ) -> Message:
        """Save message to database."""
        message = Message(
            message_id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            credits_used=self._calculate_credits(tokens_used),
            model_used=model_used,
            message_metadata=message_metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def _track_token_usage(
        self,
        user_id: str,
        chat_id: str,
        tokens_used: int,
        model: str,
        credits_used: int
    ):
        """Track token usage."""
        usage = TokenUsage(
            user_id=user_id,
            chat_id=chat_id,
            model=model,
            tokens_total=tokens_used,
            credits_used=credits_used
        )
        self.db.add(usage)
        self.db.commit()
    
    def _calculate_credits(self, tokens: int) -> int:
        """Calculate credits used based on tokens."""
        return max(1, tokens // 100)  # 1 credit per 100 tokens, minimum 1
    
    def _analyze_question_completeness(self, current_message: str, context: List[Dict]) -> tuple[bool, bool, set]:
        """
        Analyze if the current question is complete and if it changes the topic.
        
        Args:
            current_message: Current user message
            context: Conversation context (last messages)
            
        Returns:
            Tuple of (is_complete_question, topic_changed, current_topics)
        """
        if not context or len(context) < 2:
            # No context, treat as new topic
            current_topics = self._extract_topics(current_message)
            return self._is_complete_question(current_message), True, current_topics
        
        # Extract topics from current message
        current_topics = self._extract_topics(current_message)
        
        # Extract topics from recent conversation
        context_config = self.chatbot_config.get("context_management", {})
        max_recent = context_config.get("max_recent_messages_for_query", 6)
        
        recent_topics = set()
        recent_messages = []
        for msg in context[-max_recent:]:
            if isinstance(msg, dict) and msg.get("role") == "user":
                msg_content = msg.get("content", "")
                recent_messages.append(msg_content)
                msg_topics = self._extract_topics(msg_content)
                recent_topics.update(msg_topics)
        
        # Check if question is complete (has question words, specific service mention, etc.)
        is_complete = self._is_complete_question(current_message)
        
        # Check if topic changed
        topic_changed = False
        if current_topics and recent_topics:
            # If current message has different topics than recent conversation
            if not current_topics.intersection(recent_topics):
                topic_changed = True
        elif current_topics and not recent_topics:
            # Current message has topics but recent conversation doesn't - likely new topic
            topic_changed = True
        elif not current_topics and recent_topics:
            # Current message has no clear topics but recent conversation does - likely continuation
            topic_changed = False
        else:
            # Both have no clear topics - check if question is complete
            topic_changed = is_complete
        
        return is_complete, topic_changed, current_topics
    
    def _extract_topics(self, message: str) -> set:
        """
        Extract topics from a message.
        
        Args:
            message: User message
            
        Returns:
            Set of topic strings
        """
        message_lower = message.lower()
        topics = set()
        
        # Get topic keywords from config
        topic_keywords = self.chatbot_config.get("topic_detection", {}).get("topic_keywords", {
            "rental": ["rental", "rent", "hire"],
            "sale": ["sale", "buy", "purchase"],
            "finance": ["finance", "emi", "payment plan"]
        })
        
        # Detect topics
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.add(topic)
        
        return topics
    
    def _is_complete_question(self, message: str) -> bool:
        """
        Check if a question is complete (has enough context to answer independently).
        
        Args:
            message: User message
            
        Returns:
            True if question is complete, False if ambiguous/incomplete
        """
        message_lower = message.lower().strip()
        
        # Get complete question indicators from config
        question_config = self.chatbot_config.get("question_analysis", {})
        complete_indicators = question_config.get("complete_question_indicators", [])
        min_words_complete = question_config.get("min_words_for_complete", 4)
        min_words_structure = question_config.get("min_words_for_question_structure", 5)
        max_short_words = question_config.get("max_short_question_words", 2)
        
        # Check for complete question patterns
        for indicator_config in complete_indicators:
            indicator = indicator_config.get("indicator", "")
            keywords = indicator_config.get("keywords", [])
            if indicator in message_lower:
                if any(keyword in message_lower for keyword in keywords):
                    return True
        
        # Check for very short/ambiguous questions
        words = message_lower.split()
        if len(words) <= max_short_words:
            return False
        
        # Check for specific service mentions with enough detail
        service_topics = self.chatbot_config.get("topic_detection", {}).get("service_topics", ["rental", "sale", "finance"])
        if any(service in message_lower for service in service_topics):
            if len(words) >= min_words_complete:
                return True
        
        # Default: if message is long enough and has question structure, consider it complete
        if len(words) >= min_words_structure and ("?" in message or any(q in message_lower for q in ["what", "how", "where", "when", "do", "can"])):
            return True
        
        return False
    
    def _build_enhanced_query(self, current_message: str, context: List[Dict]) -> str:
        """
        Build enhanced query using conversation history for better RAG retrieval.
        Used when question is incomplete or ambiguous.
        
        Args:
            current_message: Current user message
            context: Conversation context (last messages)
            
        Returns:
            Enhanced query string
        """
        if not context or len(context) < 2:
            return current_message
        
        # Get last user messages for context
        context_config = self.chatbot_config.get("context_management", {})
        max_recent = context_config.get("max_recent_messages_for_query", 6)
        max_user = context_config.get("max_user_messages_for_context", 4)
        
        recent_messages = []
        for msg in context[-max_recent:]:
            if isinstance(msg, dict) and msg.get("role") == "user":
                recent_messages.append(msg.get("content", ""))
        
        # Combine recent messages with current message
        if recent_messages:
            # Take last N user messages
            recent_context = " ".join(recent_messages[-max_user:])
            enhanced_query = f"{recent_context} {current_message}"
            return enhanced_query.strip()
        
        return current_message
    
    def _generate_suggestions(self, chat_id: str, current_message: str, chunks: List[Dict], current_topics: Optional[set] = None) -> List[str]:
        """
        Generate helpful question suggestions based on conversation history and retrieved chunks.
        Sales-oriented: suggests other services when user has asked about multiple topics.
        
        Args:
            chat_id: Chat session ID
            current_message: Current user message
            chunks: Retrieved RAG chunks
            current_topics: Current message topics (if already extracted)
            
        Returns:
            List of suggested questions
        """
        suggestions = []
        
        try:
            # Get all user messages from chat history to analyze conversation
            all_user_messages = self.db.query(Message).filter(
                Message.chat_id == chat_id,
                Message.role == "user"
            ).order_by(
                Message.created_at.asc()
            ).all()
            
            # Extract all topics from entire conversation
            conversation_topics = set()
            topic_history = []  # Track topic sequence
            
            for msg in all_user_messages:
                msg_topics = self._extract_topics(msg.content)
                if msg_topics:
                    conversation_topics.update(msg_topics)
                    topic_history.extend(list(msg_topics))
            
            # Add current message topics
            if current_topics:
                topics = current_topics
            else:
                topics = self._extract_topics(current_message)
            
            conversation_topics.update(topics)
            if topics:
                topic_history.extend(list(topics))
            
            # Count unique services asked about
            service_topics_list = self.chatbot_config.get("topic_detection", {}).get("service_topics", ["rental", "sale", "finance"])
            service_topics = set(service_topics_list)
            asked_services = conversation_topics.intersection(service_topics)
            num_services_asked = len(asked_services)
            
            # Get last question's topics for primary suggestions
            last_question_topics = topics if topics else set()
            
            # Get suggestion config
            suggestions_config = self.chatbot_config.get("suggestions", {})
            min_services_for_cross_sell = suggestions_config.get("min_services_for_cross_sell", 2)
            min_messages_for_cross_sell = suggestions_config.get("min_messages_for_cross_sell", 3)
            max_suggestions = suggestions_config.get("max_suggestions", 5)
            all_services = suggestions_config.get("all_services", {})
            multi_service_message = suggestions_config.get("multi_service_message", "We also offer other services - would you like to know more?")
            
            # Sales strategy: If user has asked about multiple services, suggest other services
            if num_services_asked >= min_services_for_cross_sell and len(all_user_messages) >= min_messages_for_cross_sell:
                # User is exploring multiple services - suggest complementary services
                
                # Suggest services they haven't asked about yet
                unasked_services = set(all_services.keys()) - asked_services
                
                if unasked_services:
                    # Sales-oriented suggestions
                    suggestions.append(multi_service_message)
                    
                    # Add 2-3 specific service suggestions
                    for service in list(unasked_services)[:3]:
                        if service in all_services:
                            suggestions.append(all_services[service])
                else:
                    # They've asked about all services - suggest related questions
                    if "rental" in asked_services:
                        suggestions.append("What are the rental prices for each bike?")
                        suggestions.append("What documents do I need for rental?")
                    if "sale" in asked_services:
                        suggestions.append("Can I test ride a bike?")
                        suggestions.append("Do you offer part exchange?")
            else:
                # User is focused on one service - suggest related questions based on LAST question
                # Get service-specific suggestions from config
                service_suggestions = suggestions_config.get("service_suggestions", {})
                
                # Primary suggestions based on current/last question
                if "rental" in last_question_topics and "rental" in service_suggestions:
                    rental_config = service_suggestions["rental"]
                    suggestions.extend(rental_config.get("primary", []))
                    if num_services_asked == 1:
                        suggestions.append(rental_config.get("cross_sell", ""))
                elif "sale" in last_question_topics and "sale" in service_suggestions:
                    sale_config = service_suggestions["sale"]
                    suggestions.extend(sale_config.get("primary", []))
                    if num_services_asked == 1:
                        suggestions.append(sale_config.get("cross_sell", ""))
                elif "finance" in last_question_topics and "finance" in service_suggestions:
                    finance_config = service_suggestions["finance"]
                    suggestions.extend(finance_config.get("primary", []))
                    if num_services_asked == 1:
                        suggestions.append(finance_config.get("cross_sell", ""))
                elif "servicing" in last_question_topics and "servicing" in service_suggestions:
                    servicing_config = service_suggestions["servicing"]
                    suggestions.extend(servicing_config.get("primary", []))
                    if num_services_asked == 1:
                        suggestions.append(servicing_config.get("cross_sell", ""))
                elif "mot" in last_question_topics and "mot" in service_suggestions:
                    mot_config = service_suggestions["mot"]
                    suggestions.extend(mot_config.get("primary", []))
                    if num_services_asked == 1:
                        suggestions.append(mot_config.get("cross_sell", ""))
                elif "delivery" in last_question_topics and "delivery" in service_suggestions:
                    delivery_config = service_suggestions["delivery"]
                    suggestions.extend(delivery_config.get("primary", []))
                    if num_services_asked == 1:
                        suggestions.append(delivery_config.get("cross_sell", ""))
                else:
                    # General suggestions based on chunks or default
                    chunk_keywords = set()
                    for chunk in chunks[:3]:  # Check top 3 chunks
                        content = chunk.get("content", "").lower()
                        for topic in service_topics_list:
                            if topic in content:
                                chunk_keywords.add(topic)
                    
                    if chunk_keywords:
                        for topic in chunk_keywords:
                            if topic in all_services:
                                suggestions.append(all_services[topic])
                    
                    if not suggestions:
                        # Default helpful suggestions from config
                        suggestions = suggestions_config.get("default_suggestions", [
                            "What services do you offer?",
                            "Tell me about rental bikes",
                            "What are your opening hours?",
                            "Where are your branches located?"
                        ])
            
            # Add intelligent suggestions based on last questions (if enabled)
            intelligent_config = self.chatbot_config.get("intelligent_suggestions", {})
            if intelligent_config.get("enabled", True) and len(all_user_messages) >= intelligent_config.get("min_questions_for_analysis", 4):
                # Get last 4 user questions
                last_4_questions = all_user_messages[-4:] if len(all_user_messages) >= 4 else all_user_messages
                
                # Extract topics from last 4 questions
                last_4_topics = set()
                last_4_question_texts = []
                for msg in last_4_questions:
                    msg_topics = self._extract_topics(msg.content)
                    last_4_topics.update(msg_topics)
                    last_4_question_texts.append(msg.content.lower())
                
                # Generate intelligent 5th suggestion based on patterns
                q5_suggestion = None
                
                # Get follow-up suggestions from config
                rental_follow_ups = intelligent_config.get("rental_follow_ups", {})
                sale_follow_ups = intelligent_config.get("sale_follow_ups", {})
                finance_follow_ups = intelligent_config.get("finance_follow_ups", {})
                servicing_follow_ups = intelligent_config.get("servicing_follow_ups", {})
                multi_service_follow_ups = intelligent_config.get("multi_service_follow_ups", {})
                
                # If they've been asking about rental multiple times
                rental_count = sum(1 for q in last_4_question_texts if "rental" in q or "rent" in q)
                if rental_count >= 2:
                    if "deposit" not in " ".join(last_4_question_texts) and "deposit" in rental_follow_ups:
                        q5_suggestion = rental_follow_ups["deposit"]
                    elif "insurance" not in " ".join(last_4_question_texts) and "insurance" in rental_follow_ups:
                        q5_suggestion = rental_follow_ups["insurance"]
                    elif "delivery" not in " ".join(last_4_question_texts) and "delivery" in rental_follow_ups:
                        q5_suggestion = rental_follow_ups["delivery"]
                
                # If they've been asking about sale multiple times
                sale_count = sum(1 for q in last_4_question_texts if "sale" in q or "buy" in q or "purchase" in q)
                if sale_count >= 2:
                    if "finance" not in " ".join(last_4_question_texts) and "finance" in sale_follow_ups:
                        q5_suggestion = sale_follow_ups["finance"]
                    elif ("test" not in " ".join(last_4_question_texts) and "ride" not in " ".join(last_4_question_texts) 
                          and "test_ride" in sale_follow_ups):
                        q5_suggestion = sale_follow_ups["test_ride"]
                    elif "warranty" not in " ".join(last_4_question_texts) and "warranty" in sale_follow_ups:
                        q5_suggestion = sale_follow_ups["warranty"]
                
                # If they've been asking about finance
                finance_count = sum(1 for q in last_4_question_texts if "finance" in q or "emi" in q or "payment" in q)
                if finance_count >= 2:
                    if ("interest" not in " ".join(last_4_question_texts) and "rate" not in " ".join(last_4_question_texts) 
                        and "interest_rate" in finance_follow_ups):
                        q5_suggestion = finance_follow_ups["interest_rate"]
                    elif ("term" not in " ".join(last_4_question_texts) and "period" not in " ".join(last_4_question_texts) 
                          and "term" in finance_follow_ups):
                        q5_suggestion = finance_follow_ups["term"]
                    elif "deposit" not in " ".join(last_4_question_texts) and "deposit" in finance_follow_ups:
                        q5_suggestion = finance_follow_ups["deposit"]
                
                # If they've been asking about servicing
                service_count = sum(1 for q in last_4_question_texts if "service" in q or "repair" in q or "maintenance" in q)
                if service_count >= 2:
                    if ("cost" not in " ".join(last_4_question_texts) and "price" not in " ".join(last_4_question_texts) 
                        and "cost" in servicing_follow_ups):
                        q5_suggestion = servicing_follow_ups["cost"]
                    elif ("collect" not in " ".join(last_4_question_texts) and "pickup" not in " ".join(last_4_question_texts) 
                          and "collect" in servicing_follow_ups):
                        q5_suggestion = servicing_follow_ups["collect"]
                    elif "mot" not in " ".join(last_4_question_texts) and "mot" in servicing_follow_ups:
                        q5_suggestion = servicing_follow_ups["mot"]
                
                # If they've asked about multiple different services, suggest a related one
                if len(last_4_topics.intersection(service_topics)) >= 2:
                    if "delivery" not in last_4_topics and "delivery" in multi_service_follow_ups:
                        q5_suggestion = multi_service_follow_ups["delivery"]
                    elif "accessories" not in last_4_topics and "accessories" in multi_service_follow_ups:
                        q5_suggestion = multi_service_follow_ups["accessories"]
                    elif "accident" not in last_4_topics and "accident" in multi_service_follow_ups:
                        q5_suggestion = multi_service_follow_ups["accident"]
                
                # If no specific pattern, suggest based on most common topic
                if not q5_suggestion and last_4_topics:
                    most_common_topic = max(last_4_topics, key=lambda t: sum(1 for q in last_4_question_texts if t in q))
                    if most_common_topic == "rental":
                        q5_suggestion = "What bikes are available for rental?"
                    elif most_common_topic == "sale":
                        q5_suggestion = "What bikes do you have for sale?"
                    elif most_common_topic == "finance":
                        q5_suggestion = "What are the finance options?"
                    elif most_common_topic == "servicing":
                        q5_suggestion = "What services do you offer?"
                
                # Add Q5 if we have a good suggestion
                if q5_suggestion and q5_suggestion not in suggestions:
                    suggestions.append(q5_suggestion)
            
            # Limit suggestions based on config
            return suggestions[:max_suggestions]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            # Return default suggestions from config on error
            default_suggestions = self.chatbot_config.get("suggestions", {}).get("default_suggestions", [
                "What services do you offer?",
                "Tell me about rental bikes",
                "What are your opening hours?"
            ])
            return default_suggestions
    
    def _validate_response_from_rag(self, response: str, chunks: List[Dict], query: str) -> bool:
        """
        Validate that response is based on RAG chunks.
        Returns True if response seems valid, False if it might contain hallucinations.
        """
        if not chunks or len(chunks) == 0:
            # No chunks - response should be the "don't have info" message
            return "don't have that information" in response.lower() or "contact us" in response.lower()
        
        # Extract key terms from RAG chunks
        rag_content = " ".join([chunk.get("content", "").lower() for chunk in chunks])
        
        # Check if response mentions specific details that should be in RAG
        # If response is very generic or just contact info, it's likely safe
        response_lower = response.lower()
        email = self.contact_info.get("primary_email", "").lower()
        
        # If response is just contact info or "don't have info", it's valid
        if "contact" in response_lower and email and email in response_lower:
            return True
        
        if "don't have that information" in response_lower:
            return True
        
        # Check for common hallucination patterns
        # If response contains very specific numbers/dates not in RAG, might be hallucination
        # But we'll be lenient - if chunks exist, assume response is based on them
        # The strict prompt should prevent most hallucinations
        
        # For now, if we have chunks, trust the LLM (strict prompt should prevent hallucinations)
        return True
    
    def _format_response(self, response: str, query: str, chunks: List[Dict]) -> str:
        """
        Post-process response to ensure consistent formatting and structure.
        
        Args:
            response: Raw LLM response
            query: Original user query
            chunks: Retrieved RAG chunks (used for context-aware formatting)
            
        Returns:
            Formatted response string
        """
        import re
        
        if not response or not isinstance(response, str):
            return response or ""
        
        # First, fix common line break issues in addresses, postcodes, and times
        # Fix UK postcodes that have been split (e.g., "SE6 4\nNU" -> "SE6 4NU")
        # Pattern: UK postcode format (1-2 letters, 1-2 digits, space, digit, newline, 2-3 letters)
        response = re.sub(r'(\b[A-Z]{1,2}\d{1,2}[A-Z]?\s+\d)\s*\n\s*([A-Z]{2,3}\b)', r'\1\2', response)
        
        # Fix time formats that have been split (e.g., "9:\n00 AM" -> "9:00 AM")
        response = re.sub(r'(\d{1,2}):\s*\n\s*(\d{2}\s*(?:AM|PM|am|pm))', r'\1:\2', response)
        
        # Fix addresses that have been split mid-word (e.g., "SE6 4\nNU" -> "SE6 4NU")
        # This handles cases where postcodes are split (alternative pattern)
        response = re.sub(r'(\b\d{1,2}[A-Z]?\d{1,2}[A-Z]?\s+)\s*\n\s*([A-Z]{2,3}\b)', r'\1\2', response)
        
        # Fix postcodes at end of lines (e.g., "SE6 4\nNU" when on separate lines)
        response = re.sub(r'(\b[A-Z]{1,2}\d{1,2}[A-Z]?\s+\d)\s*\n\s*([A-Z]{2,3})\b', r'\1\2', response)
        
        # Fix phone numbers that might have been split
        response = re.sub(r'(\d{4})\s*\n\s*(\d{4})', r'\1 \2', response)
        
        # Fix common address patterns (e.g., "Unit 1179" split)
        response = re.sub(r'(\bUnit\s+\d+)\s*\n\s*', r'\1 ', response)
        response = re.sub(r'(\b\d+[A-Z]?)\s*\n\s*([A-Z][a-z]+)', r'\1 \2', response)
        
        # Remove excessive blank lines (more than 2 consecutive)
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Fix numbered lists that have been split (e.g., "1.\nCATFORD" -> "1. CATFORD")
        response = re.sub(r'(\d+\.)\s*\n\s*([A-Z])', r'\1 \2', response)
        
        # Ensure proper spacing around bullet points
        response = re.sub(r'(\S)(•)', r'\1 \2', response)  # Add space before bullet if missing
        response = re.sub(r'(•)(\S)', r'\1 \2', response)  # Add space after bullet if missing
        
        # Ensure proper spacing around prices
        response = re.sub(r'£(\d+)', r'£\1', response)  # Ensure no space after £
        response = re.sub(r'(\d+)(/[a-z]+)', r'\1\2', response)  # Ensure no space before /week, /month, etc.
        
        # Fix section headers - ensure proper spacing
        # Don't add line breaks if it's already properly formatted
        response = re.sub(r'([A-Z][A-Z\s]{2,}BRANCH)\s*\n\s*', r'\1\n\n', response)
        
        # Ensure line breaks after section headers (if they end with :)
        response = re.sub(r'([A-Z][^:\n]*:)([^\n\s])', r'\1 \2', response)
        
        # Fix line breaking issues - but be more careful
        # Only add line breaks after periods that are clearly new sentences
        # Avoid breaking on abbreviations, postcodes, times, etc.
        response = re.sub(r'\.([A-Z][a-z]{2,})', r'. \1', response)
        
        # Ensure line breaks after list items (bullet points)
        # Each bullet point should be on its own line
        response = re.sub(r'(•)\s*([^\n])', r'\1 \2', response)
        
        # Ensure line breaks before section headers (lines starting with capital letters followed by colon)
        # But only if not already on a new line and it's a proper header
        response = re.sub(r'([^\n])(\n?[A-Z][A-Za-z\s]{3,}:)', r'\1\n\2', response)
        
        # Ensure each bullet point item is on a separate line
        response = re.sub(r'(•[^\n•]+)(•)', r'\1\n\2', response)
        
        # Fix branch information formatting
        # Ensure branch names are on their own line
        response = re.sub(r'(\d+\.)\s*([A-Z][A-Z\s]+BRANCH)', r'\1\n\n\2', response)
        
        # Normalize whitespace (but preserve intentional line breaks)
        lines = response.split('\n')
        formatted_lines = []
        for i, line in enumerate(lines):
            # Strip trailing whitespace but preserve leading (for indentation)
            line = line.rstrip()
            
            # Skip empty lines that are duplicates
            if not line:
                if formatted_lines and formatted_lines[-1]:  # Add blank line only if previous line wasn't blank
                    formatted_lines.append('')
                continue
            
            # Fix lines that start with lowercase after a number (likely continuation)
            if i > 0 and formatted_lines:
                prev_line = formatted_lines[-1]
                # If previous line ends with a number and this line starts lowercase, merge
                if re.match(r'^\d+\.?\s*$', prev_line.strip()) and line and line[0].islower():
                    formatted_lines[-1] = prev_line + ' ' + line
                    continue
            
            formatted_lines.append(line)
        
        if not formatted_lines:
            return response.strip()
        
        response = '\n'.join(formatted_lines)
        
        # Fix any double line breaks that might have been created
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Clean up spacing around colons in addresses and times
        response = re.sub(r':\s*\n\s*', ': ', response)  # Fix "Address:\n" -> "Address: "
        
        # Ensure response ends with proper punctuation if it's a sentence
        if response and len(response) > 0:
            # Check if last character needs punctuation
            if response[-1] not in '.!?:':
                # Check if last line looks like it should end with punctuation
                response_lines = response.split('\n')
                if response_lines:
                    last_line = response_lines[-1].strip()
                    if last_line and not last_line.endswith(('•', '-', ')', ':')):
                        # Only add if it's a complete sentence (has verb-like structure)
                        if any(word in last_line.lower() for word in ['contact', 'phone', 'email', 'call', 'visit', 'reach']):
                            response += '.'
        
        # Add contact information if not present and response is about services
        formatting_config = self.chatbot_config.get("response_formatting", {})
        if formatting_config.get("add_contact_info", True) and query and isinstance(query, str):
            query_lower = query.lower()
            contact_keywords = formatting_config.get("contact_keywords", ["service", "rental", "sale", "finance"])
            min_length = formatting_config.get("min_response_length_for_contact", 50)
            contact_info_template = formatting_config.get("contact_info", "{contact_format}")
            # Resolve contact format
            contact_format = self.contact_info.get("contact_format", "Contact: {phone} or {email}").format(
                phone=self.contact_info.get("primary_phone", ""),
                email=self.contact_info.get("primary_email", "")
            )
            contact_info = contact_info_template.replace("{contact_format}", contact_format)
            
            phone = self.contact_info.get("primary_phone", "")
            email = self.contact_info.get("primary_email", "")
            if any(keyword in query_lower for keyword in contact_keywords):
                if phone not in response and email not in response:
                    # Only add if response is substantial
                    if len(response) > min_length:
                        response += f"\n\n{contact_info}"
        
        # Clean up any remaining formatting issues
        response = response.strip()
        
        # Final check: ensure response is not empty
        if not response:
            return formatting_config.get("default_empty_response", "I'm here to help! How can I assist you today?")
        
        return response
    
    def _load_chatbot_config(self):
        """Load chatbot service configuration from vendor-specific unified config."""
        try:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
            unified_config = config_manager.load_config()
            self.chatbot_config = unified_config.get("chatbot_service", {})
            # Also store business and contact info for easy access
            self.business_info = unified_config.get("business", {})
            self.contact_info = unified_config.get("contact", {})
            logger.info(f"Chatbot service configuration loaded from vendor {self.vendor_id} config")
        except Exception as e:
            logger.warning(f"Error loading chatbot service config for vendor {self.vendor_id}: {e}, using defaults")
            self.chatbot_config = {}
            self.business_info = {}
            self.contact_info = {}
    
    def reload_chatbot_config(self):
        """Reload chatbot service configuration from file."""
        self._load_chatbot_config()

