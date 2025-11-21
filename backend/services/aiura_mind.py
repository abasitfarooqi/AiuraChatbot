"""
AiuraMind Service - Intelligent Business Data to RAG & Config Generator.
Takes business data (JSON or text) and generates optimized knowledge base and unified config.
"""
import json
import re
import time
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime
from loguru import logger
from backend.services.llm_service import LLMService
from backend.utils.unified_config_manager import UnifiedConfigManager


class AiuraMindService:
    """Service to generate knowledge base and config from business data."""
    
    def __init__(
        self,
        db=None,
        vendor_id: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        generation_depth: Optional[str] = "extensive",
        max_tokens: Optional[int] = 32000,
        temperature: Optional[float] = 0.2
    ):
        """Initialize AiuraMind service."""
        self.db = db
        self.vendor_id = vendor_id
        self.llm_service = LLMService(db=db) if db else None
        # Store custom model settings for AiuraMind
        self.model_provider = model_provider
        self.model_name = model_name
        self.generation_depth = generation_depth or "extensive"
        self.max_tokens = max_tokens or 32000
        self.temperature = temperature if temperature is not None else 0.2
    
    async def generate_from_business_data(
        self,
        business_data: str,
        vendor_id: str,
        vendor_name: str,
        company_name: str,
        business_type: str = "general",
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate knowledge base and unified config from business data.
        
        Args:
            business_data: Business information in JSON or plain text
            vendor_id: Vendor identifier
            vendor_name: Display name for vendor
            company_name: Company name
            business_type: Type of business
            progress_callback: Optional callback function to report progress
        
        Returns:
            Dict with generated config and knowledge_base, including progress info
        """
        start_time = time.time()
        progress_info = {
            "current_step": "initializing",
            "progress_percentage": 0,
            "elapsed_time": 0,
            "estimated_time_remaining": None,
            "step_details": {}
        }
        
        def update_progress(step: str, percentage: int, details: Optional[Dict] = None):
            elapsed = time.time() - start_time
            progress_info["current_step"] = step
            progress_info["progress_percentage"] = percentage
            progress_info["elapsed_time"] = round(elapsed, 2)
            
            # Estimate remaining time based on current progress
            if percentage > 0:
                estimated_total = elapsed / (percentage / 100)
                estimated_remaining = estimated_total - elapsed
                progress_info["estimated_time_remaining"] = round(estimated_remaining, 2)
            else:
                progress_info["estimated_time_remaining"] = None
            
            if details:
                progress_info["step_details"] = details
            
            # Log progress
            remaining_str = f" (~{progress_info['estimated_time_remaining']:.1f}s remaining)" if progress_info['estimated_time_remaining'] else ""
            logger.info(f"[AiuraMind Progress] {step} - {percentage}% - {elapsed:.1f}s elapsed{remaining_str}")
            
            # Call progress callback if provided
            if progress_callback:
                try:
                    progress_callback(progress_info.copy())
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
        
        try:
            # Step 1: Parse input data (5%)
            update_progress("parsing_input_data", 5, {"action": "Parsing business data..."})
            parsed_data = self._parse_input_data(business_data)
            logger.info(f"✅ Parsed input data for vendor {vendor_id}")
            
            # Step 2: Generate unified config (5% - 45%)
            update_progress("generating_config", 10, {"action": "Generating unified configuration..."})
            logger.info(f"🔄 Generating unified config for vendor {vendor_id} (this may take 30-60 seconds)")
            config_start = time.time()
            unified_config = await self._generate_unified_config(
                parsed_data, vendor_id, vendor_name, company_name, business_type
            )
            config_time = time.time() - config_start
            update_progress("config_generated", 45, {
                "action": "Configuration generated",
                "time_taken": round(config_time, 2),
                "sections": len(unified_config.keys()) if isinstance(unified_config, dict) else 0
            })
            logger.info(f"✅ Unified config generated in {config_time:.1f}s")
            
            # Step 3: Generate knowledge base (45% - 90%)
            update_progress("generating_knowledge_base", 50, {"action": "Generating knowledge base chunks..."})
            logger.info(f"🔄 Generating knowledge base for vendor {vendor_id} (this may take 60-120 seconds)")
            kb_start = time.time()
            knowledge_base = await self._generate_knowledge_base(
                parsed_data, vendor_id, company_name, unified_config
            )
            kb_time = time.time() - kb_start
            chunks_count = len(knowledge_base.get("chunks", [])) if isinstance(knowledge_base, dict) else 0
            update_progress("knowledge_base_generated", 90, {
                "action": "Knowledge base generated",
                "time_taken": round(kb_time, 2),
                "chunks_created": chunks_count
            })
            logger.info(f"✅ Knowledge base generated in {kb_time:.1f}s with {chunks_count} chunks")
            
            # Step 4: Generate additional vendor-specific config files (90% - 100%)
            update_progress("generating_additional_files", 95, {"action": "Generating additional config files..."})
            additional_files = self._generate_additional_config_files(
                unified_config, vendor_id, company_name
            )
            update_progress("completed", 100, {
                "action": "All files generated successfully",
                "files_created": len(additional_files) if isinstance(additional_files, dict) else 0
            })
            
            total_time = time.time() - start_time
            logger.info(f"✅ AiuraMind completed in {total_time:.1f}s total")
            
            return {
                "status": "success",
                "vendor_id": vendor_id,
                "unified_config": unified_config,
                "knowledge_base": knowledge_base,
                "additional_files": additional_files,
                "message": "Successfully generated config, knowledge base, and additional config files",
                "progress": {
                    "total_time_seconds": round(total_time, 2),
                    "config_generation_time": round(config_time, 2),
                    "kb_generation_time": round(kb_time, 2),
                    "chunks_created": chunks_count,
                    "config_sections": len(unified_config.keys()) if isinstance(unified_config, dict) else 0,
                    "additional_files_created": len(additional_files) if isinstance(additional_files, dict) else 0
                }
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Error generating from business data after {elapsed:.1f}s: {e}")
            update_progress("error", 0, {
                "action": "Error occurred",
                "error": str(e),
                "elapsed_time": round(elapsed, 2)
            })
            raise
    
    def _generate_additional_config_files(
        self,
        unified_config: Dict[str, Any],
        vendor_id: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Generate vendor-specific system_prompts.json, chatbot_service_config.json, and app_config.json with timestamps."""
        try:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            
            # Get vendor name and sanitize for filename (vendor is a dict)
            vendor = vendor_manager.get_vendor(vendor_id)
            vendor_name = vendor.get("vendor_name", vendor_id) if isinstance(vendor, dict) else (vendor.vendor_name if hasattr(vendor, 'vendor_name') else vendor_id)
            # Sanitize vendor name for filename (remove spaces, special chars, keep only alphanumeric and underscores)
            vendor_name_safe = re.sub(r'[^a-zA-Z0-9_]', '_', vendor_name).lower()
            
            # Create timestamped directory within vendor folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            vendor_dir = vendor_manager.vendors_dir / vendor_id
            timestamped_dir = vendor_dir / "generated" / timestamp
            timestamped_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract sections from unified_config
            prompts = unified_config.get("prompts", {})
            chatbot_service = unified_config.get("chatbot_service", {})
            application = unified_config.get("application", {})
            database = unified_config.get("database", {})
            vector_database = unified_config.get("vector_database", {})
            embedding = unified_config.get("embedding", {})
            llm = unified_config.get("llm", {})
            openai_config = unified_config.get("openai", {})
            rag = unified_config.get("rag", {})
            memory = unified_config.get("memory", {})
            domain_restriction = unified_config.get("domain_restriction", {})
            credits = unified_config.get("credits", {})
            multi_vendor = unified_config.get("multi_vendor", {})
            logging = unified_config.get("logging", {})
            cors = unified_config.get("cors", {})
            security = unified_config.get("security", {})
            frontend = unified_config.get("frontend", {})
            contact = unified_config.get("contact", {})
            company = unified_config.get("business", {})
            branches = unified_config.get("branches", [])
            
            # Generate system_prompts.json (both in timestamped folder with vendor name and main location)
            system_prompts_path = vendor_manager.get_vendor_system_prompts_path(vendor_id)
            system_prompts_path.parent.mkdir(parents=True, exist_ok=True)
            system_prompts_timestamped = timestamped_dir / f"system_prompts_{vendor_name_safe}_{timestamp}.json"
            
            system_prompts = {
                "main_system_prompt": prompts.get("main_system_prompt", ""),
                "greeting_prompt": prompts.get("greeting_prompt", ""),
                "query_prompt": prompts.get("query_prompt", ""),
                "fallback_message": prompts.get("fallback_message", ""),
                "out_of_domain_message": prompts.get("out_of_domain_message", ""),
                "error_message": prompts.get("error_message", ""),
                "generated_at": datetime.now().isoformat(),
                "vendor_id": vendor_id
            }
            with open(system_prompts_path, "w", encoding="utf-8") as f:
                json.dump(system_prompts, f, indent=2, ensure_ascii=False)
            with open(system_prompts_timestamped, "w", encoding="utf-8") as f:
                json.dump(system_prompts, f, indent=2, ensure_ascii=False)
            
            # Generate chatbot_service_config.json (both in timestamped folder with vendor name and main location)
            chatbot_service_path = vendor_manager.get_vendor_chatbot_service_config_path(vendor_id)
            chatbot_service_path.parent.mkdir(parents=True, exist_ok=True)
            chatbot_service_timestamped = timestamped_dir / f"chatbot_service_config_{vendor_name_safe}_{timestamp}.json"
            
            chatbot_service_with_meta = chatbot_service.copy()
            chatbot_service_with_meta["generated_at"] = datetime.now().isoformat()
            chatbot_service_with_meta["vendor_id"] = vendor_id
            
            with open(chatbot_service_path, "w", encoding="utf-8") as f:
                json.dump(chatbot_service_with_meta, f, indent=2, ensure_ascii=False)
            with open(chatbot_service_timestamped, "w", encoding="utf-8") as f:
                json.dump(chatbot_service_with_meta, f, indent=2, ensure_ascii=False)
            
            # Generate app_config.json (both in timestamped folder with vendor name and main location)
            app_config_path = vendor_manager.get_vendor_app_config_path(vendor_id)
            app_config_path.parent.mkdir(parents=True, exist_ok=True)
            app_config_timestamped = timestamped_dir / f"app_config_{vendor_name_safe}_{timestamp}.json"
            
            app_config = {
                "application": application,
                "database": database,
                "vector_database": vector_database,
                "embedding": embedding,
                "llm": llm,
                "openai": openai_config,
                "rag": rag,
                "memory": memory,
                "domain_restriction": domain_restriction,
                "credits": credits,
                "multi_vendor": multi_vendor,
                "logging": logging,
                "cors": cors,
                "security": security,
                "frontend": frontend,
                "contact": contact,
                "company": {
                    "name": company.get("company_name", company_name),
                    "company_number": company.get("company_number", ""),
                    "registered_address": company.get("registered_address", ""),
                    "trading_names": company.get("trading_names", [])
                },
                "branches": branches,
                "generated_at": datetime.now().isoformat(),
                "vendor_id": vendor_id
            }
            with open(app_config_path, "w", encoding="utf-8") as f:
                json.dump(app_config, f, indent=2, ensure_ascii=False)
            with open(app_config_timestamped, "w", encoding="utf-8") as f:
                json.dump(app_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Generated vendor-specific config files for {vendor_id} in {timestamped_dir}")
            
            return {
                "system_prompts": str(system_prompts_path),
                "chatbot_service_config": str(chatbot_service_path),
                "app_config": str(app_config_path),
                "timestamped_dir": str(timestamped_dir),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error generating additional config files: {e}")
            return {}
    
    def _parse_input_data(self, data: str) -> Dict[str, Any]:
        """Parse input data (JSON or text)."""
        # Try JSON first
        try:
            if isinstance(data, str):
                parsed = json.loads(data)
            else:
                parsed = data
            return parsed if isinstance(parsed, dict) else {"raw_text": data}
        except json.JSONDecodeError:
            # Not JSON, treat as text
            return {"raw_text": data}
    
    async def _generate_unified_config(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        vendor_name: str,
        company_name: str,
        business_type: str
    ) -> Dict[str, Any]:
        """Generate unified config using LLM."""
        if not self.llm_service:
            # Fallback to template-based generation
            return self._generate_config_template(parsed_data, vendor_id, vendor_name, company_name, business_type)
        
        # Switch to custom model if specified
        original_provider = None
        original_model = None
        if self.model_provider and self.model_name:
            original_provider = self.llm_service.current_provider
            original_model = self.llm_service.current_model
            self.llm_service.switch_model(self.model_provider, self.model_name)
            logger.info(f"AiuraMind using model: {self.model_provider}/{self.model_name} for config generation")
        
        # Use LLM to generate config
        prompt = self._build_config_generation_prompt(parsed_data, vendor_id, vendor_name, company_name, business_type)
        
        try:
            # For extensive depth, use full max_tokens. For others, use proportional amount
            depth_multipliers = {
                "basic": 0.5,
                "standard": 0.75,
                "comprehensive": 1.0,
                "extensive": 1.0  # Use full max_tokens for extensive
            }
            multiplier = depth_multipliers.get(self.generation_depth, 1.0)
            adjusted_max_tokens = int(self.max_tokens * multiplier)
            
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=adjusted_max_tokens,
                temperature=self.temperature
            )
            
            # Restore original model if we switched
            if original_provider and original_model:
                self.llm_service.switch_model(original_provider, original_model)
            
            # Parse LLM response
            config_text = response.get("content", "") if isinstance(response, dict) else str(response)
            
            # Extract JSON from response
            config_json = self._extract_json_from_text(config_text)
            
            if config_json:
                # Validate and enhance config
                return self._enhance_config(config_json, vendor_id, vendor_name, company_name, business_type)
            else:
                # Fallback to template
                logger.warning("LLM response didn't contain valid JSON, using template")
                return self._generate_config_template(parsed_data, vendor_id, vendor_name, company_name, business_type)
                
        except Exception as e:
            logger.warning(f"Error using LLM for config generation: {e}, using template")
            # Restore original model if we switched
            if original_provider and original_model:
                self.llm_service.switch_model(original_provider, original_model)
            return self._generate_config_template(parsed_data, vendor_id, vendor_name, company_name, business_type)
    
    async def _generate_knowledge_base(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        company_name: str,
        unified_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate knowledge base chunks using LLM."""
        if not self.llm_service:
            # Fallback to template-based generation
            return self._generate_kb_template(parsed_data, vendor_id, company_name)
        
        # Switch to custom model if specified
        original_provider = None
        original_model = None
        if self.model_provider and self.model_name:
            original_provider = self.llm_service.current_provider
            original_model = self.llm_service.current_model
            self.llm_service.switch_model(self.model_provider, self.model_name)
            logger.info(f"AiuraMind using model: {self.model_provider}/{self.model_name} for KB generation")
        
        # Use LLM to generate knowledge base
        prompt = self._build_kb_generation_prompt(parsed_data, vendor_id, company_name, unified_config)
        
        try:
            # For extensive depth, use full max_tokens. For others, use proportional amount
            depth_multipliers = {
                "basic": 0.5,
                "standard": 0.75,
                "comprehensive": 1.0,
                "extensive": 1.0  # Use full max_tokens for extensive
            }
            multiplier = depth_multipliers.get(self.generation_depth, 1.0)
            adjusted_max_tokens = int(self.max_tokens * multiplier)
            
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=adjusted_max_tokens,
                temperature=self.temperature
            )
            
            # Restore original model if we switched
            if original_provider and original_model:
                self.llm_service.switch_model(original_provider, original_model)
            
            # Parse LLM response
            kb_text = response.get("content", "") if isinstance(response, dict) else str(response)
            
            # Extract JSON from response
            kb_json = self._extract_json_from_text(kb_text)
            
            if kb_json:
                # Validate and enhance KB
                return self._enhance_knowledge_base(kb_json, vendor_id, company_name)
            else:
                # Fallback to template
                logger.warning("LLM response didn't contain valid JSON, using template")
                return self._generate_kb_template(parsed_data, vendor_id, company_name)
                
        except Exception as e:
            logger.warning(f"Error using LLM for KB generation: {e}, using template")
            # Restore original model if we switched
            if original_provider and original_model:
                self.llm_service.switch_model(original_provider, original_model)
            return self._generate_kb_template(parsed_data, vendor_id, company_name)
    
    def _get_depth_instructions(self) -> str:
        """Get instructions based on generation depth setting."""
        depth_instructions = {
            "basic": "Generate a minimal, essential configuration with only core fields. Keep it concise.",
            "standard": "Generate a complete, well-structured configuration with all standard sections and reasonable detail.",
            "comprehensive": "Generate a detailed, thorough configuration with all sections fully populated, including examples, detailed prompts, and comprehensive settings.",
            "extensive": "Generate an extremely detailed, exhaustive configuration with maximum depth. Include all possible fields, detailed examples, comprehensive prompts, extensive service configurations, multiple branches, detailed contact information, and all advanced settings. This should be production-ready and complete."
        }
        return depth_instructions.get(self.generation_depth, depth_instructions["standard"])
    
    def _build_config_generation_prompt(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        vendor_name: str,
        company_name: str,
        business_type: str
    ) -> str:
        """Build prompt for comprehensive config generation."""
        data_str = json.dumps(parsed_data, indent=2) if isinstance(parsed_data, dict) else str(parsed_data)
        today = datetime.now().strftime("%Y-%m-%d")
        depth_instructions = self._get_depth_instructions()
        
        return f"""You are an expert at creating comprehensive chatbot configurations for businesses. Generate a complete, production-ready unified_config.json structure based on the business data provided.

BUSINESS DATA:
{data_str}

REQUIREMENTS:
- Vendor ID: {vendor_id}
- Vendor Name: {vendor_name}
- Company Name: {company_name}
- Business Type: {business_type}
- Generation Depth: {self.generation_depth}
- Date: {today}

{depth_instructions}

Generate a COMPLETE unified_config.json with ALL these sections (do not skip any):

1. metadata:
   - version: "3.0.0"
   - last_updated: "{today}"
   - description: "Unified configuration for multi-vendor, multi-business chatbot"
   - vendor_id: "{vendor_id}"
   - business_type: "{business_type}"

2. business:
   - company_name: "{company_name}"
   - company_number: (extract if available)
   - trading_names: (array of trading names/aliases)
   - registered_address: (extract if available)
   - business_description: (comprehensive description)
   - core_activities: (array of main business activities)
   - services_list: (array of all services offered - be comprehensive)

3. contact:
   - primary_phone: (extract phone number)
   - primary_email: (extract email)
   - customer_service_email: (if available)
   - whatsapp_available: true/false
   - contact_format: "Contact: {{phone}} or {{email}}"

4. branches: (array of branch/location objects if available)
   Each branch should have:
   - name, address, phone, postcode
   - opening_hours: (object with monday-sunday)
   - services: (array of services at this branch)
   - parking_available: true/false

5. application: (default settings)
6. database: (SQLite default)
7. vector_database: (ChromaDB with vendor-specific collection name)
8. embedding: (sentence-transformers model, offline mode)
9. llm: (ollama settings, offline mode)
10. openai: (disabled by default)
11. rag: (top_k: 5, similarity_threshold: 0.2)
12. memory: (enabled, max_turns: 20)
13. domain_restriction: (enabled, auto_generate_keywords: true, keywords array)
14. credits: (token tracking, credit system enabled)
15. multi_vendor: (enabled: false, default_vendor_id)
16. logging: (INFO level, log rotation)
17. cors: (origins: ["*"])
18. security: (secret key placeholder)
19. frontend: (frontend URL)
20. prompts: (COMPREHENSIVE system prompts with variables)
    - main_system_prompt: (detailed, includes {{company_name}}, {{services_list}})
    - greeting_prompt: (with {{message}} variable)
    - query_prompt: (with {{context_text}}, {{message}}, {{fallback_message}})
    - fallback_message: (with contact info)
    - out_of_domain_message: (with services list)
    - error_message: (with contact info)

21. chatbot_service: (EXTENSIVE configuration)
    - greetings:
      - simple_greetings: (array of greeting words)
      - initial_suggestions: (array of helpful suggestions)
    - topic_detection:
      - topic_keywords: (object mapping topics to keyword arrays)
      - service_topics: (array of service topic names)
    - question_analysis:
      - complete_question_indicators: (array of indicator objects with keywords)
      - min_words_for_complete: 4
      - min_words_for_question_structure: 5
      - max_short_question_words: 2
    - suggestions:
      - service_suggestions: (object with suggestions per service)
      - all_services: (object mapping services to question strings)
      - default_suggestions: (array)
      - multi_service_message: (string)
      - max_suggestions: 5
      - min_services_for_cross_sell: 2
      - min_messages_for_cross_sell: 3
    - intelligent_suggestions: (enabled, follow-ups per service)
    - response_formatting:
      - add_contact_info: true
      - contact_keywords: (array)
      - min_response_length_for_contact: 50
      - contact_info: (string with phone and email)
      - default_empty_response: (string)
    - context_management:
      - max_context_messages: 10
      - max_recent_messages_for_query: 6
      - max_user_messages_for_context: 4
    - validation:
      - enable_response_validation: true
      - fallback_message: (string)
    - caching:
      - enabled: true
      - use_cache_for_responses: true
      - fallback_to_llm_on_cache_miss: true
      - similarity_threshold: 0.85
      - save_to_temporary_cache: true
      - save_to_main_cache: true
      - min_question_length_for_main_cache: 10
      - cache_miss_message: (string)
      - use_lightweight_model_for_cache: false
      - disable_llm_completely: false

CRITICAL REQUIREMENTS:
- Extract ALL services from business data and create comprehensive service lists
- Create detailed, business-specific system prompts
- Use variables in prompts: {{company_name}}, {{services_list}}, {{contact_phone}}, {{contact_email}}
- Generate comprehensive topic_keywords for ALL services mentioned
- Create complete_question_indicators for common question patterns
- Generate service_suggestions for each service with primary and cross_sell suggestions
- Include all_services mapping with question strings
- Make chatbot_service configuration comprehensive and production-ready
- Include caching configuration with all settings
- Ensure all prompts are specific to the business type and services

Return ONLY valid JSON, no markdown, no code blocks, no explanations, just the complete JSON object."""

    def _build_kb_generation_prompt(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        company_name: str,
        unified_config: Dict[str, Any]
    ) -> str:
        """Build prompt for knowledge base generation with detailed structure requirements."""
        data_str = json.dumps(parsed_data, indent=2) if isinstance(parsed_data, dict) else str(parsed_data)
        services = unified_config.get("business", {}).get("services_list", [])
        branches = unified_config.get("branches", [])
        contact = unified_config.get("contact", {})
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build domain name from vendor_id (remove underscores, use lowercase)
        domain_name = vendor_id.replace("_", "").lower()
        
        return f"""You are an expert at creating RAG-optimized knowledge bases for chatbots with symbolic mapping, comprehensive tags, and detailed metadata. Generate a complete knowledge_base.json structure based on the business data provided.

BUSINESS DATA:
{data_str}

COMPANY: {company_name}
VENDOR ID: {vendor_id}
DOMAIN: {domain_name}
SERVICES: {', '.join(services) if services else 'General business services'}
BRANCHES: {len(branches)} branch(es) available
CONTACT: {contact.get('primary_phone', 'N/A')} / {contact.get('primary_email', 'N/A')}

CRITICAL REQUIREMENTS - FOLLOW EXACTLY:

1. SYMBOL NAMING CONVENTION (MANDATORY):
   - Use format: CATEGORY_NUMBER (e.g., COMPANY_001, BRANCH_001, SERVICE_001, PRODUCT_001, CONTACT_001, OPENING_001, POLICY_001, FALLBACK_001, GENERAL_001)
   - Categories: COMPANY, BRANCH, [SERVICE_NAME], PRODUCT, POLICY, CONTACT, OPENING, FALLBACK, GENERAL, [ITEM_NAME] (if applicable)
   - Number format: 001, 002, 003... (always 3 digits with leading zeros)
   - Each chunk MUST have a unique symbol

2. KEYWORD FORMAT (MANDATORY):
   - Use snake_case (lowercase with underscores)
   - Be descriptive and specific (e.g., "company_info", "main_branch", "service_overview", "service_prices", "product_details")
   - Should match the main topic of the chunk
   - Examples: "company_info", "branch_location_summary", "service_comprehensive", "payment_methods", "service_overview"

3. TAGS ARRAY (MANDATORY - MINIMUM 3-8 TAGS PER CHUNK):
   - Include ALL relevant tags that customers might use to ask questions
   - Include variations, synonyms, and related terms
   - Include specific product names, locations, services mentioned
   - Examples for service: ["service", "overview", "information", "details", "help", "assist", "support"]
   - Examples for branch: ["branch", "location", "address", "opening_hours", "contact", "where", "store"]
   - Be comprehensive - more tags = better retrieval

4. MAPPING STRUCTURE (MANDATORY):
   - category: Main category (e.g., "company", "branches", "services", "products", "policies", "contact", "general")
   - subcategory: Specific subcategory (e.g., "general", "main_branch", "service_name", "product_name", "warranty", "returns", "payment", "delivery")
   - priority: "high" (core info), "medium" (secondary), "low" (optional), "critical" (system-level)
   - domain: "{domain_name}" (use lowercase vendor_id without underscores)

5. METADATA STRUCTURE (MANDATORY):
   - source: Where data comes from (e.g., "company", "branches", "services.[service_name]", "products.[product_name]", "policies.warranty", "system")
   - last_verified: "{today}" (use current date)
   - confidence: "high" (verified info), "medium" (likely accurate), "low" (uncertain)
   - vendor_id: "{vendor_id}" (always include)
   - requires_update: false (default, set to true if data might change)
   - Additional fields: Add service_type, location, postcode, product_name, price_type, etc. as relevant

6. CONTENT REQUIREMENTS (MANDATORY):
   - Minimum 2-5 sentences, ideally 3-8 sentences
   - Be comprehensive, detailed, and self-contained
   - Include all relevant information (prices, terms, contact info, etc.)
   - Format with proper structure (use line breaks, lists, sections)
   - Answer-focused: content should directly answer customer questions
   - Include specific details: prices, addresses, phone numbers, terms, conditions

7. CHUNK ORGANIZATION (MANDATORY):
   Generate chunks in this order and structure:
   
   A. COMPANY INFORMATION (1-2 chunks):
      - COMPANY_001: Company overview (name, description, core activities, contact basics)
   
   B. BRANCHES/LOCATIONS (1 chunk per branch + 1 summary):
      - BRANCH_001, BRANCH_002, etc.: Individual branch details (address, phone, opening hours, services)
      - BRANCH_XXX: Summary chunk listing all branches
   
   C. SERVICES (Multiple chunks per service):
      - [SERVICE]_001: Service overview (what it is, general info)
      - [SERVICE]_002: Pricing information (if available)
      - [SERVICE]_003: Terms/conditions (if applicable)
      - [SERVICE]_004: Requirements/documents (if applicable)
      - [SERVICE]_005: Payment methods (if applicable)
      - [SERVICE]_006: Fees/charges (if applicable)
      - [SERVICE]_007: Comprehensive summary (all details combined)
      - Continue with additional service-specific chunks as needed
   
   D. PRODUCTS/ITEMS (if applicable):
      - PRODUCT_[NAME]_001: Product-specific information (pricing, features, availability)
   
   E. POLICIES (if available):
      - POLICY_001: Warranty policy
      - POLICY_002: Returns/refund policy
      - Continue as needed
   
   F. CONTACT INFORMATION:
      - CONTACT_001: Complete contact information
   
   G. OPENING HOURS:
      - OPENING_001: All branches opening hours
   
   H. FALLBACK CHUNKS:
      - FALLBACK_001: General fallback (redirect to customer service)
      - FALLBACK_002: Price/quote fallback (redirect to service desk)
   
   I. GENERAL CHUNKS:
      - GENERAL_001: Bot introduction
      - GENERAL_002: Services overview
   
   J. DOMAIN RESTRICTION:
      - DOMAIN_RESTRICTION_001: Domain boundary definition

8. MINIMUM REQUIREMENTS:
   - Minimum 20-40 chunks (aim for comprehensive coverage)
   - At least 1 chunk per service offered
   - At least 1 chunk per branch/location
   - Include comprehensive chunks that combine multiple related details
   - Include fallback chunks for customer service redirection

EXAMPLE CHUNK STRUCTURE (follow this format exactly):
{{
  "symbol": "SERVICE_001",
  "keyword": "service_overview",
  "tags": ["service", "overview", "information", "details", "help", "assist", "support"],
  "mapping": {{
    "category": "services",
    "subcategory": "service_name",
    "priority": "high",
    "domain": "{domain_name}"
  }},
  "metadata": {{
    "source": "services.service_name",
    "service_type": "service_name",
    "last_verified": "{today}",
    "confidence": "high",
    "requires_update": false,
    "vendor_id": "{vendor_id}"
  }},
  "content": "Service overview and general information. This service provides comprehensive solutions for your needs. Key features include detailed support, flexible options, and professional assistance. Terms and conditions apply. For specific pricing, availability, and detailed information, please contact us. Our team is available to answer any questions and help you get started."
}}

Generate the complete knowledge base following ALL requirements above. Return ONLY valid JSON with this exact structure:
{{
  "metadata": {{
    "version": "2.0.0",
    "last_updated": "{today}",
    "description": "RAG-optimised knowledge base with symbolic mapping, tags, and comprehensive metadata for {company_name} chatbot",
    "chunking_strategy": "semantic_chunks_with_metadata",
    "embedding_model": "configurable",
    "vector_db": "chromadb",
    "vendor_id": "{vendor_id}"
  }},
  "chunks": [
    // Array of chunks following the structure above
  ]
}}

Return ONLY valid JSON, no markdown, no code blocks, no explanations, just the JSON object."""

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response text."""
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        # Try parsing entire text as JSON
        try:
            return json.loads(text)
        except:
            pass
        
        return None
    
    def _generate_config_template(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        vendor_name: str,
        company_name: str,
        business_type: str
    ) -> Dict[str, Any]:
        """Generate config template when LLM is not available."""
        # Load default config structure
        config_manager = UnifiedConfigManager()
        config = config_manager._get_default_config()
        
        # Update with vendor-specific data
        config["metadata"]["vendor_id"] = vendor_id
        config["metadata"]["business_type"] = business_type
        config["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        config["business"]["company_name"] = company_name
        
        # Extract services from parsed_data
        if "services" in parsed_data:
            services = parsed_data["services"]
            if isinstance(services, list):
                config["business"]["services_list"] = services
            elif isinstance(services, str):
                config["business"]["services_list"] = [s.strip() for s in services.split(",")]
        elif "raw_text" in parsed_data:
            # Try to extract services from text (generic extraction)
            text = parsed_data["raw_text"].lower()
            services = []
            # Generic service extraction - look for common service indicators
            if "service" in text or "support" in text:
                services.append("services")
            if "sale" in text or "buy" in text or "purchase" in text:
                services.append("sales")
            if "consult" in text or "advice" in text:
                services.append("consultation")
            config["business"]["services_list"] = services if services else ["general services"]
        
        # Extract contact info
        if "contact" in parsed_data:
            contact = parsed_data["contact"]
            if isinstance(contact, dict):
                config["contact"]["primary_phone"] = contact.get("phone", "")
                config["contact"]["primary_email"] = contact.get("email", "")
        
        # Update prompts with company name
        prompts = config.get("prompts", {})
        prompts["main_system_prompt"] = prompts["main_system_prompt"].replace("{company_name}", company_name)
        prompts["fallback_message"] = prompts["fallback_message"].replace("{company_name}", company_name)
        
        return config
    
    def _generate_kb_template(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Generate comprehensive KB template when LLM is not available."""
        today = datetime.now().strftime("%Y-%m-%d")
        domain_name = vendor_id.replace("_", "").lower()
        chunks = []
        chunk_idx = 1
        
        # Extract data
        company_desc = parsed_data.get("description", "") or parsed_data.get("raw_text", "")[:500]
        services = parsed_data.get("services", [])
        if isinstance(services, str):
            services = [s.strip() for s in services.split(",")]
        elif not isinstance(services, list):
            services = []
        
        contact = parsed_data.get("contact", {})
        phone = contact.get("phone", "") if isinstance(contact, dict) else ""
        email = contact.get("email", "") if isinstance(contact, dict) else ""
        branches = parsed_data.get("branches", [])
        if not isinstance(branches, list):
            branches = []
        
        # 1. Company info chunk
        chunks.append({
            "symbol": "COMPANY_001",
            "keyword": "company_info",
            "tags": ["company", "business", "about", "information", company_name.lower().replace(" ", "_")],
            "mapping": {
                "category": "company",
                "subcategory": "general",
                "priority": "high",
                "domain": domain_name
            },
            "metadata": {
                "source": "company",
                "last_verified": today,
                "confidence": "high",
                "requires_update": False,
                "vendor_id": vendor_id
            },
            "content": f"{company_name}. {company_desc}. Contact: {phone or 'N/A'} or {email or 'N/A'}"
        })
        chunk_idx += 1
        
        # 2. Services overview chunk
        if services:
            services_text = ", ".join(services)
            chunks.append({
                "symbol": "GENERAL_001",
                "keyword": "services_overview",
                "tags": ["services", "what", "can", "assist", "support", "overview", "help", "offerings"] + [s.lower() for s in services[:5]],
                "mapping": {
                    "category": "general",
                    "subcategory": "services",
                    "priority": "high",
                    "domain": domain_name
                },
                "metadata": {
                    "source": "company",
                    "last_verified": today,
                    "confidence": "high",
                    "requires_update": False,
                    "vendor_id": vendor_id
                },
                "content": f"{company_name} offers comprehensive services: {services_text}. We are here to help you with all your needs. Contact us for more information: {phone or 'N/A'} or {email or 'N/A'}."
            })
            chunk_idx += 1
            
            # 3. Individual service chunks
            for service in services[:10]:  # Limit to 10 services
                service_lower = service.lower().replace(" ", "_")
                chunks.append({
                    "symbol": f"{service_lower.upper()[:8]}_001",
                    "keyword": f"{service_lower}_overview",
                    "tags": [service.lower(), "service", "overview", "information", "details", "help", "assist"],
                    "mapping": {
                        "category": "services",
                        "subcategory": service_lower,
                        "priority": "high",
                        "domain": domain_name
                    },
                    "metadata": {
                        "source": f"services.{service_lower}",
                        "service_type": service_lower,
                        "last_verified": today,
                        "confidence": "medium",
                        "requires_update": False,
                        "vendor_id": vendor_id
                    },
                    "content": f"{company_name} offers {service} services. For detailed information, pricing, and availability, please contact us at {phone or 'N/A'} or {email or 'N/A'}. Our team will be happy to assist you."
                })
                chunk_idx += 1
        
        # 4. Branches chunks
        if branches:
            for idx, branch in enumerate(branches[:10], 1):  # Limit to 10 branches
                branch_name = branch.get("name", f"Branch {idx}") if isinstance(branch, dict) else str(branch)
                branch_name_safe = branch_name.lower().replace(" ", "_")
                chunks.append({
                    "symbol": f"BRANCH_{idx:03d}",
                    "keyword": f"{branch_name_safe}_branch",
                    "tags": ["branch", "location", branch_name.lower(), "address", "opening_hours", "contact", "where"],
                    "mapping": {
                        "category": "branches",
                        "subcategory": branch_name_safe,
                        "priority": "high",
                        "domain": domain_name
                    },
                    "metadata": {
                        "source": "branches",
                        "location": branch_name,
                        "last_verified": today,
                        "confidence": "high",
                        "vendor_id": vendor_id
                    },
                    "content": f"{branch_name} Branch: {branch.get('address', 'Address available on request') if isinstance(branch, dict) else 'Location available'}. Phone: {branch.get('phone', phone) if isinstance(branch, dict) else phone or 'N/A'}. Email: {email or 'N/A'}. Opening hours and services available - contact for details."
                })
                chunk_idx += 1
            
            # Branch summary chunk
            chunks.append({
                "symbol": f"BRANCH_{chunk_idx:03d}",
                "keyword": "branches_location_summary",
                "tags": ["branch", "branches", "location", "where", "situated", "address", "how_many", "all_branches", "locations"],
                "mapping": {
                    "category": "branches",
                    "subcategory": "summary",
                    "priority": "high",
                    "domain": domain_name
                },
                "metadata": {
                    "source": "branches",
                    "last_verified": today,
                    "confidence": "high",
                    "vendor_id": vendor_id
                },
                "content": f"{company_name} has {len(branches)} branch(es). For specific branch locations, addresses, opening hours, and services, please contact us at {phone or 'N/A'} or {email or 'N/A'}."
            })
            chunk_idx += 1
        
        # 5. Contact information chunk
        if phone or email:
            chunks.append({
                "symbol": "CONTACT_001",
                "keyword": "contact_information",
                "tags": ["contact", "phone", "email", "address", "location", "reach", "get_in_touch", "how_to_contact"],
                "mapping": {
                    "category": "company",
                    "subcategory": "contact",
                    "priority": "high",
                    "domain": domain_name
                },
                "metadata": {
                    "source": "company",
                    "last_verified": today,
                    "confidence": "high",
                    "vendor_id": vendor_id
                },
                "content": f"Contact Information: Phone: {phone or 'Available on request'}. Email: {email or 'Available on request'}. {company_name} is here to help. Reach out to us for any questions, inquiries, or assistance."
            })
            chunk_idx += 1
        
        # 6. General bot introduction chunk
        chunks.append({
            "symbol": "GENERAL_002",
            "keyword": "bot_introduction",
            "tags": ["greeting", "introduction", "name", "who", "what", "help", "assistant", "chatbot"],
            "mapping": {
                "category": "general",
                "subcategory": "introduction",
                "priority": "high",
                "domain": domain_name
            },
            "metadata": {
                "source": "system",
                "last_verified": today,
                "confidence": "high",
                "vendor_id": vendor_id
            },
            "content": f"I'm the {company_name} chatbot assistant. I can help you with {', '.join(services) if services else 'our services'}. I'm here to assist you with questions about our services, prices, policies, and more. How can I help you today?"
        })
        chunk_idx += 1
        
        # 7. Fallback chunk
        chunks.append({
            "symbol": "FALLBACK_001",
            "keyword": "fallback_general",
            "tags": ["fallback", "redirect", "customer_service", "support", "help", "contact"],
            "mapping": {
                "category": "fallback",
                "subcategory": "general",
                "priority": "high",
                "domain": domain_name
            },
            "metadata": {
                "source": "fallback_strategy",
                "last_verified": today,
                "confidence": "high",
                "vendor_id": vendor_id
            },
            "content": f"If information not available: Redirect to customer service team. Contact: phone {phone or 'N/A'}, email {email or 'N/A'}. Response: 'That isn't listed on my system at the moment, but our customer service team can confirm that for you right away. You can reach them on {phone or 'phone'}, or by email at {email or 'email'}. Would you like me to pass your name and question over to them now?'"
        })
        chunk_idx += 1
        
        # 8. Domain restriction chunk
        chunks.append({
            "symbol": "DOMAIN_RESTRICTION_001",
            "keyword": "domain_boundary",
            "tags": ["domain", "restriction", "boundary", "out_of_scope", "limits"],
            "mapping": {
                "category": "system",
                "subcategory": "domain_restriction",
                "priority": "critical",
                "domain": domain_name
            },
            "metadata": {
                "source": "system",
                "last_verified": today,
                "confidence": "high",
                "vendor_id": vendor_id
            },
            "content": f"Domain restriction: This chatbot can ONLY answer questions about {', '.join(services) if services else 'our services'} related to {company_name}. For any query outside this domain, respond: 'I can only assist with {', '.join(services) if services else 'our services'} related to {company_name}. How can I help you with our services?'"
        })
        
        return {
            "metadata": {
                "version": "2.0.0",
                "last_updated": today,
                "description": f"RAG-optimised knowledge base with symbolic mapping, tags, and comprehensive metadata for {company_name} chatbot",
                "chunking_strategy": "semantic_chunks_with_metadata",
                "embedding_model": "configurable",
                "vector_db": "chromadb",
                "vendor_id": vendor_id
            },
            "chunks": chunks
        }
    
    def _enhance_config(
        self,
        config: Dict[str, Any],
        vendor_id: str,
        vendor_name: str,
        company_name: str,
        business_type: str
    ) -> Dict[str, Any]:
        """Enhance and validate generated config by merging with default structure to ensure all sections are present."""
        from backend.utils.unified_config_manager import UnifiedConfigManager
        
        # Get default config structure as base
        config_manager = UnifiedConfigManager()
        default_config = config_manager._get_default_config()
        
        # Deep merge: use generated config values where present, fall back to defaults
        def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            """Deep merge two dictionaries, with override taking precedence."""
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        # Merge generated config into default structure
        enhanced_config = deep_merge(default_config, config)
        
        # Ensure metadata is correct
        enhanced_config["metadata"]["vendor_id"] = vendor_id
        enhanced_config["metadata"]["business_type"] = business_type
        enhanced_config["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        enhanced_config["metadata"]["version"] = enhanced_config["metadata"].get("version", "3.0.0")
        
        # Ensure business section has company_name
        if "business" not in enhanced_config:
            enhanced_config["business"] = {}
        enhanced_config["business"]["company_name"] = company_name
        
        # Ensure all required sections exist with defaults if missing
        required_sections = {
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
                "chroma_collection_name": f"{vendor_id}_kb"
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
                "knowledge_base_path": f"./rag_knowledge_base/{vendor_id}/knowledge_base.json"
            },
            "memory": {
                "enabled": True,
                "max_turns": 20,
                "summary_enabled": False,
                "summary_threshold": 15
            },
            "domain_restriction": {
                "enabled": True,
                "auto_generate_keywords": True,
                "keywords": []
            },
            "credits": {
                "token_tracking_enabled": True,
                "credit_system_enabled": True,
                "default_user_credits": 1000,
                "credit_cost_per_message": 10
            },
            "multi_vendor": {
                "enabled": False,
                "default_vendor_id": vendor_id
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
            },
            "branches": []
        }
        
        # Ensure all required sections exist
        for section, default_value in required_sections.items():
            if section not in enhanced_config:
                enhanced_config[section] = default_value.copy() if isinstance(default_value, dict) else default_value
            elif isinstance(default_value, dict) and isinstance(enhanced_config[section], dict):
                # Merge defaults into existing section
                for key, val in default_value.items():
                    if key not in enhanced_config[section]:
                        enhanced_config[section][key] = val
        
        # Ensure prompts section has all required fields
        if "prompts" not in enhanced_config:
            enhanced_config["prompts"] = {}
        
        prompts_defaults = {
            "main_system_prompt": f"You are the {company_name} chatbot assistant. You help customers with their inquiries.\n\nCRITICAL RULES:\n1. ONLY use information provided in the INFORMATION section\n2. NEVER make up or guess information\n3. Be helpful, friendly, and professional\n4. If you don't know something, direct customers to contact us",
            "greeting_prompt": f"The user just said: \"{{message}}\"\n\nRespond with a friendly greeting and offer to help with {company_name} services.",
            "query_prompt": "CRITICAL: Answer the question using ONLY the information provided below.\n\nINFORMATION FROM KNOWLEDGE BASE:\n{context_text}\n\nQUESTION: {message}\n\nANSWER (based ONLY on the information above):",
            "fallback_message": f"I don't have that information in my knowledge base. Please contact us for more details.",
            "out_of_domain_message": f"I can help you with {company_name} services. How can I assist you?",
            "error_message": f"I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us."
        }
        
        for key, default_val in prompts_defaults.items():
            if key not in enhanced_config["prompts"] or not enhanced_config["prompts"][key]:
                enhanced_config["prompts"][key] = default_val
        
        # Ensure chatbot_service section has comprehensive structure
        if "chatbot_service" not in enhanced_config:
            enhanced_config["chatbot_service"] = {}
        
        chatbot_service_defaults = {
            "greetings": {
                "simple_greetings": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"],
                "initial_suggestions": ["What services do you offer?", "Tell me about your services", "What are your opening hours?", "Where are you located?"]
            },
            "topic_detection": {
                "topic_keywords": {},
                "service_topics": []
            },
            "question_analysis": {
                "complete_question_indicators": [],
                "min_words_for_complete": 4,
                "min_words_for_question_structure": 5,
                "max_short_question_words": 2
            },
            "suggestions": {
                "service_suggestions": {},
                "all_services": {},
                "default_suggestions": ["What services do you offer?", "Tell me about your services"],
                "multi_service_message": "We also offer other services - would you like to know more?",
                "max_suggestions": 5,
                "min_services_for_cross_sell": 2,
                "min_messages_for_cross_sell": 3
            },
            "intelligent_suggestions": {
                "enabled": True,
                "min_questions_for_analysis": 4
            },
            "response_formatting": {
                "add_contact_info": True,
                "contact_keywords": ["service", "contact", "help"],
                "min_response_length_for_contact": 50,
                "contact_info": f"Contact: {enhanced_config.get('contact', {}).get('primary_phone', 'N/A')} or {enhanced_config.get('contact', {}).get('primary_email', 'N/A')}",
                "default_empty_response": "I'm here to help! How can I assist you today?"
            },
            "context_management": {
                "max_context_messages": 10,
                "max_recent_messages_for_query": 6,
                "max_user_messages_for_context": 4
            },
            "validation": {
                "enable_response_validation": True,
                "fallback_message": enhanced_config.get("prompts", {}).get("fallback_message", "I don't have that information.")
            },
            "caching": {
                "enabled": True,
                "use_cache_for_responses": True,
                "fallback_to_llm_on_cache_miss": True,
                "similarity_threshold": 0.85,
                "save_to_temporary_cache": True,
                "save_to_main_cache": True,
                "min_question_length_for_main_cache": 10,
                "cache_miss_message": "I don't have that information in my cache. Please try rephrasing your question or contact us for assistance.",
                "use_lightweight_model_for_cache": False,
                "disable_llm_completely": False
            }
        }
        
        # Merge chatbot_service defaults
        for key, default_val in chatbot_service_defaults.items():
            if key not in enhanced_config["chatbot_service"]:
                enhanced_config["chatbot_service"][key] = default_val.copy() if isinstance(default_val, dict) else default_val
            elif isinstance(default_val, dict) and isinstance(enhanced_config["chatbot_service"][key], dict):
                for subkey, subval in default_val.items():
                    if subkey not in enhanced_config["chatbot_service"][key]:
                        enhanced_config["chatbot_service"][key][subkey] = subval.copy() if isinstance(subval, dict) else subval
        
        logger.info(f"Enhanced config for {vendor_id}: {len(enhanced_config)} top-level sections")
        
        return enhanced_config
    
    def _enhance_knowledge_base(
        self,
        kb: Dict[str, Any],
        vendor_id: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Enhance and validate generated knowledge base to ensure complete structure."""
        today = datetime.now().strftime("%Y-%m-%d")
        domain_name = vendor_id.replace("_", "").lower()
        
        # Ensure metadata with all required fields
        if "metadata" not in kb:
            kb["metadata"] = {}
        kb["metadata"]["version"] = kb["metadata"].get("version", "2.0.0")
        kb["metadata"]["vendor_id"] = vendor_id
        kb["metadata"]["last_updated"] = kb["metadata"].get("last_updated", today)
        kb["metadata"]["description"] = kb["metadata"].get("description", 
            f"RAG-optimised knowledge base with symbolic mapping, tags, and comprehensive metadata for {company_name} chatbot")
        kb["metadata"]["chunking_strategy"] = kb["metadata"].get("chunking_strategy", "semantic_chunks_with_metadata")
        kb["metadata"]["embedding_model"] = kb["metadata"].get("embedding_model", "configurable")
        kb["metadata"]["vector_db"] = kb["metadata"].get("vector_db", "chromadb")
        
        # Ensure chunks
        if "chunks" not in kb:
            kb["chunks"] = []
        
        # Enhance each chunk to ensure complete structure
        for idx, chunk in enumerate(kb["chunks"]):
            # Ensure symbol (generate if missing)
            if "symbol" not in chunk or not chunk["symbol"]:
                # Try to infer from keyword or generate default
                keyword = chunk.get("keyword", "").upper().replace("_", "")
                if keyword:
                    chunk["symbol"] = f"{keyword}_{idx+1:03d}"
                else:
                    chunk["symbol"] = f"CHUNK_{idx+1:03d}"
            
            # Ensure keyword (generate from symbol if missing)
            if "keyword" not in chunk or not chunk["keyword"]:
                symbol = chunk.get("symbol", "")
                if symbol:
                    # Convert symbol to keyword (e.g., COMPANY_001 -> company_info)
                    parts = symbol.split("_")
                    chunk["keyword"] = "_".join(parts[:-1]).lower() if len(parts) > 1 else symbol.lower()
                else:
                    chunk["keyword"] = f"chunk_{idx+1}"
            
            # Ensure tags (minimum 3 tags)
            if "tags" not in chunk or not chunk["tags"] or len(chunk["tags"]) < 3:
                # Generate tags from keyword and content
                keyword = chunk.get("keyword", "")
                content = chunk.get("content", "").lower()
                tags = set()
                
                # Add keyword parts as tags
                if keyword:
                    tags.add(keyword)
                    for part in keyword.split("_"):
                        if len(part) > 2:
                            tags.add(part)
                
                # Extract common words from content
                common_words = ["company", "service", "contact", "branch", "location", "price", 
                               "sale", "product", "delivery", "opening", "hours", "phone", "email", "support"]
                for word in common_words:
                    if word in content:
                        tags.add(word)
                
                chunk["tags"] = list(tags)[:8] if tags else ["general", "information", "help"]
            
            # Ensure mapping structure
            if "mapping" not in chunk:
                chunk["mapping"] = {}
            
            chunk["mapping"]["category"] = chunk["mapping"].get("category", "general")
            chunk["mapping"]["subcategory"] = chunk["mapping"].get("subcategory", "general")
            chunk["mapping"]["priority"] = chunk["mapping"].get("priority", "medium")
            chunk["mapping"]["domain"] = chunk["mapping"].get("domain", domain_name)
            
            # Ensure metadata structure
            if "metadata" not in chunk:
                chunk["metadata"] = {}
            
            chunk["metadata"]["vendor_id"] = vendor_id
            chunk["metadata"]["last_verified"] = chunk["metadata"].get("last_verified", today)
            chunk["metadata"]["confidence"] = chunk["metadata"].get("confidence", "medium")
            chunk["metadata"]["requires_update"] = chunk["metadata"].get("requires_update", False)
            
            # Ensure source if missing
            if "source" not in chunk["metadata"]:
                # Infer from category
                category = chunk["mapping"].get("category", "")
                if category == "company":
                    chunk["metadata"]["source"] = "company"
                elif category == "branches":
                    chunk["metadata"]["source"] = "branches"
                elif category == "services":
                    chunk["metadata"]["source"] = f"services.{chunk['mapping'].get('subcategory', 'general')}"
                else:
                    chunk["metadata"]["source"] = "company"
            
            # Ensure content is not empty
            if "content" not in chunk or not chunk["content"] or len(chunk["content"].strip()) < 10:
                logger.warning(f"Chunk {chunk.get('symbol', idx)} has empty or very short content, skipping")
                continue
        
        # Remove any chunks with invalid content
        kb["chunks"] = [chunk for chunk in kb["chunks"] 
                       if chunk.get("content") and len(chunk["content"].strip()) >= 10]
        
        # Sort chunks by symbol for consistency
        kb["chunks"].sort(key=lambda x: x.get("symbol", ""))
        
        logger.info(f"Enhanced knowledge base: {len(kb['chunks'])} chunks with complete structure")
        
        return kb

