"""
AiuraMind Service - Intelligent Business Data to RAG & Config Generator.
Takes business data (JSON or text) and generates optimized knowledge base and unified config.
"""
import json
import re
from typing import Dict, Any, Optional, List
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
        business_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Generate knowledge base and unified config from business data.
        
        Args:
            business_data: Business information in JSON or plain text
            vendor_id: Vendor identifier
            vendor_name: Display name for vendor
            company_name: Company name
            business_type: Type of business
        
        Returns:
            Dict with generated config and knowledge_base
        """
        try:
            # Parse input data (try JSON first, fallback to text)
            parsed_data = self._parse_input_data(business_data)
            
            # Generate unified config
            logger.info(f"Generating unified config for vendor {vendor_id}")
            unified_config = await self._generate_unified_config(
                parsed_data, vendor_id, vendor_name, company_name, business_type
            )
            
            # Generate knowledge base
            logger.info(f"Generating knowledge base for vendor {vendor_id}")
            knowledge_base = await self._generate_knowledge_base(
                parsed_data, vendor_id, company_name, unified_config
            )
            
            # Generate additional vendor-specific config files
            logger.info(f"Generating vendor-specific config files for vendor {vendor_id}")
            additional_files = self._generate_additional_config_files(
                unified_config, vendor_id, company_name
            )
            
            return {
                "status": "success",
                "vendor_id": vendor_id,
                "unified_config": unified_config,
                "knowledge_base": knowledge_base,
                "additional_files": additional_files,
                "message": "Successfully generated config, knowledge base, and additional config files"
            }
            
        except Exception as e:
            logger.error(f"Error generating from business data: {e}")
            raise
    
    def _generate_additional_config_files(
        self,
        unified_config: Dict[str, Any],
        vendor_id: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Generate vendor-specific system_prompts.json, chatbot_service_config.json, and app_config.json."""
        try:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            
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
            
            # Generate system_prompts.json
            system_prompts_path = vendor_manager.get_vendor_system_prompts_path(vendor_id)
            system_prompts_path.parent.mkdir(parents=True, exist_ok=True)
            system_prompts = {
                "main_system_prompt": prompts.get("main_system_prompt", ""),
                "greeting_prompt": prompts.get("greeting_prompt", ""),
                "query_prompt": prompts.get("query_prompt", ""),
                "fallback_message": prompts.get("fallback_message", ""),
                "out_of_domain_message": prompts.get("out_of_domain_message", ""),
                "error_message": prompts.get("error_message", "")
            }
            with open(system_prompts_path, "w", encoding="utf-8") as f:
                json.dump(system_prompts, f, indent=2, ensure_ascii=False)
            
            # Generate chatbot_service_config.json
            chatbot_service_path = vendor_manager.get_vendor_chatbot_service_config_path(vendor_id)
            chatbot_service_path.parent.mkdir(parents=True, exist_ok=True)
            with open(chatbot_service_path, "w", encoding="utf-8") as f:
                json.dump(chatbot_service, f, indent=2, ensure_ascii=False)
            
            # Generate app_config.json
            app_config_path = vendor_manager.get_vendor_app_config_path(vendor_id)
            app_config_path.parent.mkdir(parents=True, exist_ok=True)
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
                "branches": branches
            }
            with open(app_config_path, "w", encoding="utf-8") as f:
                json.dump(app_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Generated vendor-specific config files for {vendor_id}")
            
            return {
                "system_prompts": str(system_prompts_path),
                "chatbot_service_config": str(chatbot_service_path),
                "app_config": str(app_config_path)
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
        """Build prompt for config generation."""
        data_str = json.dumps(parsed_data, indent=2) if isinstance(parsed_data, dict) else str(parsed_data)
        
        return f"""You are an expert at creating chatbot configurations for businesses. Generate a complete unified_config.json structure based on the business data provided.

BUSINESS DATA:
{data_str}

REQUIREMENTS:
- Vendor ID: {vendor_id}
- Vendor Name: {vendor_name}
- Company Name: {company_name}
- Business Type: {business_type}

Generate a complete unified_config.json with these sections:
1. metadata (version, vendor_id, business_type, last_updated)
2. business (company_name, services_list, core_activities, branches if available)
3. contact (primary_phone, primary_email, contact_format)
4. branches (if location data available)
5. application (default settings)
6. database (default SQLite)
7. vector_database (ChromaDB settings)
8. embedding (sentence-transformers model)
9. llm (ollama settings)
10. rag (RAG settings)
11. memory (conversation memory)
12. domain_restriction (enabled with auto keywords)
13. prompts (system prompts with variables like {{company_name}}, {{services_list}})
14. chatbot_service (greetings, suggestions, topic detection, response formatting)

IMPORTANT:
- Extract all services from the business data
- Create appropriate system prompts
- Use variables in prompts: {{company_name}}, {{services_list}}, {{contact_phone}}, {{contact_email}}
- Make prompts specific to the business type
- Include all relevant chatbot service configurations

Return ONLY valid JSON, no markdown, no code blocks, just the JSON object."""

    def _build_kb_generation_prompt(
        self,
        parsed_data: Dict[str, Any],
        vendor_id: str,
        company_name: str,
        unified_config: Dict[str, Any]
    ) -> str:
        """Build prompt for knowledge base generation."""
        data_str = json.dumps(parsed_data, indent=2) if isinstance(parsed_data, dict) else str(parsed_data)
        services = unified_config.get("business", {}).get("services_list", [])
        
        return f"""You are an expert at creating RAG-optimized knowledge bases for chatbots. Generate a complete knowledge_base.json structure based on the business data provided.

BUSINESS DATA:
{data_str}

COMPANY: {company_name}
VENDOR ID: {vendor_id}
SERVICES: {', '.join(services) if services else 'General business services'}

Generate a comprehensive knowledge base with chunks covering:
1. Company information (name, description, core activities)
2. All services offered (detailed information for each service)
3. Contact information (phone, email, addresses)
4. Branches/locations (if available)
5. Pricing information (if available)
6. Policies (warranty, returns, etc. if available)
7. Opening hours (if available)
8. General FAQs and helpful information

Each chunk should have:
- symbol: Unique identifier (e.g., COMPANY_001, SERVICE_001)
- keyword: Main keyword for the chunk
- tags: Array of relevant tags
- mapping: {{category, subcategory, priority, domain}}
- metadata: {{source, last_verified, confidence, vendor_id}}
- content: Detailed, comprehensive content (2-5 sentences minimum)

IMPORTANT:
- Create 15-30 chunks minimum
- Make content detailed and answer-focused
- Use tags that match how customers might ask questions
- Priority: "high" for core info, "medium" for secondary, "low" for optional
- Content should be self-contained and informative
- Include fallback chunks for redirecting to customer service

Return ONLY valid JSON with this structure:
{{
  "metadata": {{
    "version": "2.0.0",
    "vendor_id": "{vendor_id}",
    "description": "Knowledge base for {company_name}",
    "chunking_strategy": "semantic_chunks_with_metadata"
  }},
  "chunks": [
    {{
      "symbol": "COMPANY_001",
      "keyword": "company_info",
      "tags": ["company", "about", "information"],
      "mapping": {{"category": "company", "subcategory": "general", "priority": "high", "domain": "{vendor_id}"}},
      "metadata": {{"source": "company", "last_verified": "{datetime.now().strftime('%Y-%m-%d')}", "confidence": "high", "vendor_id": "{vendor_id}"}},
      "content": "Detailed company information..."
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no code blocks, just the JSON object."""

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
            # Try to extract services from text
            text = parsed_data["raw_text"].lower()
            services = []
            if "rental" in text or "hire" in text:
                services.append("rentals")
            if "sale" in text or "buy" in text:
                services.append("sales")
            if "service" in text or "repair" in text:
                services.append("servicing")
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
        """Generate KB template when LLM is not available."""
        chunks = []
        
        # Company info chunk
        company_desc = parsed_data.get("description", "") or parsed_data.get("raw_text", "")[:200]
        chunks.append({
            "symbol": "COMPANY_001",
            "keyword": "company_info",
            "tags": ["company", "business", "about", "information"],
            "mapping": {
                "category": "company",
                "subcategory": "general",
                "priority": "high",
                "domain": vendor_id
            },
            "metadata": {
                "source": "company",
                "last_verified": datetime.now().strftime("%Y-%m-%d"),
                "confidence": "high",
                "vendor_id": vendor_id
            },
            "content": f"{company_name}. {company_desc}"
        })
        
        # Services chunk
        services = parsed_data.get("services", [])
        if services:
            services_text = ", ".join(services) if isinstance(services, list) else str(services)
            chunks.append({
                "symbol": "SERVICE_001",
                "keyword": "services",
                "tags": ["services", "what we do", "offerings"],
                "mapping": {
                    "category": "services",
                    "subcategory": "general",
                    "priority": "high",
                    "domain": vendor_id
                },
                "metadata": {
                    "source": "company",
                    "last_verified": datetime.now().strftime("%Y-%m-%d"),
                    "confidence": "high",
                    "vendor_id": vendor_id
                },
                "content": f"{company_name} offers: {services_text}. Please contact us for more information."
            })
        
        return {
            "metadata": {
                "version": "2.0.0",
                "vendor_id": vendor_id,
                "description": f"Knowledge base for {company_name}",
                "chunking_strategy": "semantic_chunks_with_metadata",
                "last_updated": datetime.now().strftime("%Y-%m-%d")
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
        """Enhance and validate generated config."""
        # Ensure required fields
        if "metadata" not in config:
            config["metadata"] = {}
        config["metadata"]["vendor_id"] = vendor_id
        config["metadata"]["business_type"] = business_type
        config["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        if "business" not in config:
            config["business"] = {}
        config["business"]["company_name"] = company_name
        
        # Ensure prompts exist
        if "prompts" not in config:
            config["prompts"] = {}
        
        # Ensure chatbot_service exists
        if "chatbot_service" not in config:
            config["chatbot_service"] = {}
        
        return config
    
    def _enhance_knowledge_base(
        self,
        kb: Dict[str, Any],
        vendor_id: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Enhance and validate generated knowledge base."""
        # Ensure metadata
        if "metadata" not in kb:
            kb["metadata"] = {}
        kb["metadata"]["vendor_id"] = vendor_id
        kb["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure chunks
        if "chunks" not in kb:
            kb["chunks"] = []
        
        # Add vendor_id to all chunks
        for chunk in kb["chunks"]:
            if "metadata" not in chunk:
                chunk["metadata"] = {}
            chunk["metadata"]["vendor_id"] = vendor_id
            
            if "mapping" not in chunk:
                chunk["mapping"] = {}
            chunk["mapping"]["domain"] = vendor_id
        
        return kb

