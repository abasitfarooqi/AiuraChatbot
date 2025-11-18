"""
Database models for chat history, user sessions, and conversation memory.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from backend.config import get_settings

settings = get_settings()

Base = declarative_base()


class User(Base):
    """User model for multi-user support."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    vendor_id = Column(String, default=settings.default_vendor_id)
    credits = Column(Integer, default=settings.default_user_credits)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    """Chat session model."""
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    vendor_id = Column(String, default=settings.default_vendor_id)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """Message model for conversation history."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, nullable=False)
    chat_id = Column(String, ForeignKey("chats.chat_id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    model_used = Column(String, nullable=True)
    message_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")


class ConversationMemory(Base):
    """Conversation memory for context tracking."""
    __tablename__ = "conversation_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("chats.chat_id"), nullable=False, index=True)
    context_summary = Column(Text, nullable=True)
    entities = Column(JSON, default=dict)  # Extracted entities (bike model, service type, etc.)
    intent_history = Column(JSON, default=list)  # Track conversation intents
    turn_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TokenUsage(Base):
    """Token usage tracking for analytics."""
    __tablename__ = "token_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    chat_id = Column(String, nullable=True, index=True)
    model = Column(String, nullable=False)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ModelConfig(Base):
    """Model configuration storage."""
    __tablename__ = "model_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, nullable=False, index=True)
    provider = Column(String, nullable=False)  # ollama, openai, m4
    base_url = Column(String, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    top_p = Column(Float, default=0.9)
    top_k = Column(Integer, default=40)
    is_active = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    model_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database setup
def get_database_engine():
    """Get database engine."""
    return create_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
    )


def get_session_local():
    """Get database session factory."""
    engine = get_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_database():
    """Initialize database tables."""
    engine = get_database_engine()
    Base.metadata.create_all(bind=engine)

