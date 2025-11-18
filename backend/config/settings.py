"""
Application settings and configuration management.
All settings are loaded from environment variables or .env file.
No hardcoded values.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
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
    
    # LLM Configuration
    llm_provider: str = "ollama"  # ollama, openai, m4
    llm_model: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4000
    llm_top_p: float = 0.9
    llm_top_k: int = 40
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # RAG Configuration
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.2  # Lower threshold for better retrieval
    rag_enable_filtering: bool = True
    rag_enable_reranking: bool = False
    
    # Conversation Memory
    memory_enabled: bool = True
    memory_max_turns: int = 20
    memory_summary_enabled: bool = False
    memory_summary_threshold: int = 15
    
    # Domain Restriction
    domain_restriction_enabled: bool = True
    domain_keywords: str = "rental,sale,finance,deposit,warranty,policy,servicing,mot,delivery,accessories,neguinho,ngn,honda,yamaha,bike,motorcycle,scooter,opening,hours,branch,location,contact,phone,email,address"
    
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
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
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

