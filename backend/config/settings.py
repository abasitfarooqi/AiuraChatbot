"""
Application settings and configuration management.
Settings are loaded from unified JSON config first, then environment variables.
Unified config takes priority for offline/local operation.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
from backend.utils.unified_config_manager import get_unified_config_manager


class Settings(BaseSettings):
    """Application settings loaded from unified JSON config or environment variables."""
    
    def __init__(self, **kwargs):
        """Initialize settings from unified config first, then env vars."""
        # Load unified config
        config_manager = get_unified_config_manager()
        config = config_manager.load_config()
        
        # Set defaults from JSON config
        app_config = config.get("application", {})
        db_config = config.get("database", {})
        vec_config = config.get("vector_database", {})
        emb_config = config.get("embedding", {})
        llm_config = config.get("llm", {})
        openai_config = config.get("openai", {})
        rag_config = config.get("rag", {})
        mem_config = config.get("memory", {})
        domain_config = config.get("domain_restriction", {})
        credits_config = config.get("credits", {})
        vendor_config = config.get("multi_vendor", {})
        log_config = config.get("logging", {})
        cors_config = config.get("cors", {})
        sec_config = config.get("security", {})
        frontend_config = config.get("frontend", {})
        
        # Set values from JSON (can be overridden by env vars)
        kwargs.setdefault("environment", app_config.get("environment", "development"))
        kwargs.setdefault("debug", app_config.get("debug", True))
        kwargs.setdefault("app_name", app_config.get("app_name", "AiuraChatbot"))
        kwargs.setdefault("app_version", app_config.get("app_version", "1.0.0"))
        kwargs.setdefault("api_host", app_config.get("api_host", "0.0.0.0"))
        kwargs.setdefault("api_port", app_config.get("api_port", 8000))
        kwargs.setdefault("api_prefix", app_config.get("api_prefix", "/api/v1"))
        
        kwargs.setdefault("database_url", db_config.get("database_url", "sqlite:///./data/chatbot.db"))
        kwargs.setdefault("database_echo", db_config.get("database_echo", False))
        
        kwargs.setdefault("chroma_db_path", vec_config.get("chroma_db_path", "./data/chroma_db"))
        # Resolve collection name variable if present
        collection_name = vec_config.get("chroma_collection_name", "chatbot_kb")
        if "{company_name_lower}" in collection_name:
            business = config.get("business", {})
            company_lower = business.get("company_name", "company").lower().replace(" ", "_").replace(".", "")
            collection_name = collection_name.replace("{company_name_lower}", company_lower)
        kwargs.setdefault("chroma_collection_name", collection_name)
        
        kwargs.setdefault("embedding_model", emb_config.get("model", "sentence-transformers/all-MiniLM-L6-v2"))
        kwargs.setdefault("embedding_device", emb_config.get("device", "cpu"))
        kwargs.setdefault("embedding_batch_size", emb_config.get("batch_size", 32))
        kwargs.setdefault("embedding_cache_dir", emb_config.get("cache_dir", "./models/embeddings"))
        kwargs.setdefault("embedding_offline_mode", emb_config.get("offline_mode", True))
        
        kwargs.setdefault("llm_provider", llm_config.get("provider", "ollama"))
        kwargs.setdefault("llm_model", llm_config.get("model", "mistral"))
        kwargs.setdefault("llm_base_url", llm_config.get("base_url", "http://localhost:11434"))
        kwargs.setdefault("llm_temperature", llm_config.get("temperature", 0.7))
        kwargs.setdefault("llm_max_tokens", llm_config.get("max_tokens", 4000))
        kwargs.setdefault("llm_top_p", llm_config.get("top_p", 0.9))
        kwargs.setdefault("llm_top_k", llm_config.get("top_k", 40))
        kwargs.setdefault("llm_offline_mode", llm_config.get("offline_mode", True))
        
        kwargs.setdefault("openai_api_key", openai_config.get("api_key"))
        kwargs.setdefault("openai_model", openai_config.get("model", "gpt-4-turbo-preview"))
        kwargs.setdefault("openai_enabled", openai_config.get("enabled", False))
        
        kwargs.setdefault("rag_top_k", rag_config.get("top_k", 5))
        kwargs.setdefault("rag_similarity_threshold", rag_config.get("similarity_threshold", 0.2))
        kwargs.setdefault("rag_enable_filtering", rag_config.get("enable_filtering", True))
        kwargs.setdefault("rag_enable_reranking", rag_config.get("enable_reranking", False))
        kwargs.setdefault("rag_knowledge_base_path", rag_config.get("knowledge_base_path", "./rag_knowledge_base.json"))
        
        kwargs.setdefault("memory_enabled", mem_config.get("enabled", True))
        kwargs.setdefault("memory_max_turns", mem_config.get("max_turns", 20))
        kwargs.setdefault("memory_summary_enabled", mem_config.get("summary_enabled", False))
        kwargs.setdefault("memory_summary_threshold", mem_config.get("summary_threshold", 15))
        
        kwargs.setdefault("domain_restriction_enabled", domain_config.get("enabled", True))
        domain_keywords_list = domain_config.get("keywords", [])
        kwargs.setdefault("domain_keywords", ",".join(domain_keywords_list) if domain_keywords_list else "rental,sale,finance")
        
        kwargs.setdefault("token_tracking_enabled", credits_config.get("token_tracking_enabled", True))
        kwargs.setdefault("credit_system_enabled", credits_config.get("credit_system_enabled", True))
        kwargs.setdefault("default_user_credits", credits_config.get("default_user_credits", 1000))
        kwargs.setdefault("credit_cost_per_message", credits_config.get("credit_cost_per_message", 10))
        
        kwargs.setdefault("multi_vendor_enabled", vendor_config.get("enabled", False))
        kwargs.setdefault("default_vendor_id", vendor_config.get("default_vendor_id", "default"))
        
        kwargs.setdefault("log_level", log_config.get("log_level", "INFO"))
        kwargs.setdefault("log_file", log_config.get("log_file", "./logs/chatbot.log"))
        kwargs.setdefault("log_rotation", log_config.get("log_rotation", "10 MB"))
        kwargs.setdefault("log_retention", log_config.get("log_retention", "30 days"))
        
        cors_origins = cors_config.get("origins", ["*"])
        kwargs.setdefault("cors_origins", cors_origins if isinstance(cors_origins, list) else [cors_origins])
        kwargs.setdefault("cors_credentials", cors_config.get("credentials", True))
        
        kwargs.setdefault("secret_key", sec_config.get("secret_key", "your-secret-key-change-in-production"))
        kwargs.setdefault("access_token_expire_minutes", sec_config.get("access_token_expire_minutes", 1440))
        
        kwargs.setdefault("frontend_url", frontend_config.get("frontend_url", "http://localhost:5173"))
        
        super().__init__(**kwargs)
    
    # Application
    environment: str = "development"
    debug: bool = True
    app_name: str = "AiuraChatbot"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Database
    database_url: str = "sqlite:///./data/chatbot.db"
    database_echo: bool = False
    
    # Vector Database
    chroma_db_path: str = "./data/chroma_db"
    chroma_collection_name: str = "neguinho_motors_kb"
    
    # Embedding Model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_cache_dir: str = "./models/embeddings"
    embedding_offline_mode: bool = True
    
    # LLM Configuration
    llm_provider: str = "ollama"
    llm_model: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4000
    llm_top_p: float = 0.9
    llm_top_k: int = 40
    llm_offline_mode: bool = True
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_enabled: bool = False
    
    # RAG Configuration
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.2
    rag_enable_filtering: bool = True
    rag_enable_reranking: bool = False
    rag_knowledge_base_path: str = "./rag_knowledge_base.json"
    
    # Conversation Memory
    memory_enabled: bool = True
    memory_max_turns: int = 20
    memory_summary_enabled: bool = False
    memory_summary_threshold: int = 15
    
    # Domain Restriction
    domain_restriction_enabled: bool = True
    domain_keywords: str = "rental,sale,finance,deposit,warranty,policy,servicing,mot,delivery,accessories,neguinho,ngn,honda,yamaha,bike,motorcycle,scooter,opening,hours,branch,branches,location,locations,where,situated,situate,address,contact,phone,email,how many,catford,tooting,sutton"
    
    # Token & Credit Management
    token_tracking_enabled: bool = True
    credit_system_enabled: bool = True
    default_user_credits: int = 1000
    credit_cost_per_message: int = 10
    
    # Multi-Vendor Support
    multi_vendor_enabled: bool = False
    default_vendor_id: str = "default"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/chatbot.log"
    log_rotation: str = "10 MB"
    log_retention: str = "30 days"
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_credentials: bool = True
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 1440
    
    # Frontend
    frontend_url: str = "http://localhost:5173"
    
    @property
    def domain_keywords_list(self) -> List[str]:
        """Convert domain keywords string to list."""
        return [kw.strip().lower() for kw in self.domain_keywords.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

