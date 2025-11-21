"""
Comprehensive multi-tenant SaaS database models for AiuraChatbot platform.
Implements full admin/vendor control, multi-tenancy, quotas, billing, security, and product features.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, 
    JSON, BigInteger, Numeric, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
# Use Integer for SQLite compatibility, BigInteger for MySQL
try:
    from sqlalchemy.dialects.mysql import BIGINT
    PrimaryKeyType = BIGINT
except:
    PrimaryKeyType = Integer
from datetime import datetime
import enum

Base = declarative_base()


# Enums
class VendorStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    DELETED = "deleted"


class ResourceType(str, enum.Enum):
    TOKENS = "tokens"
    MESSAGES = "messages"
    EMBEDDINGS_STORAGE_MB = "embeddings_storage_mb"
    STORAGE_MB = "storage_mb"
    CONCURRENT_SESSIONS = "concurrent_sessions"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ChatSessionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class MessageSender(str, enum.Enum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"
    AGENT = "agent"


class ActorType(str, enum.Enum):
    ADMIN = "admin"
    VENDOR_USER = "vendor_user"
    SYSTEM = "system"


class UsageSource(str, enum.Enum):
    API = "api"
    UI = "ui"
    WEBHOOK = "webhook"


# Core Platform Models
class Admin(Base):
    """Platform super admin accounts."""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_super = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships - removed complex relationship, use query filters instead


class Model(Base):
    """Central registry of available LLM models."""
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "gpt-4", "mistral-7b"
    display_name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # openai, ollama, anthropic, self-hosted
    capabilities = Column(JSON, default=dict)  # {"chat": true, "embeddings": false, "streaming": true}
    default_max_tokens = Column(Integer, default=4000)
    price_per_1k_tokens = Column(Numeric(10, 6), default=0.0)  # Cost per 1k tokens
    latency_estimate_ms = Column(Integer, nullable=True)
    is_cache_model = Column(Boolean, default=False)  # For cache-only responses
    is_active = Column(Boolean, default=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor_assignments = relationship("VendorModelAssignment", back_populates="model", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="model")


class Vendor(Base):
    """Vendor/tenant accounts."""
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    business_type = Column(String(100), nullable=True)
    plan_code = Column(String(50), nullable=True, index=True)  # free, hobby, pro, enterprise
    status = Column(Enum(VendorStatus), default=VendorStatus.ACTIVE, nullable=False, index=True)
    billing_customer_id = Column(String(255), nullable=True, index=True)  # Stripe customer ID
    default_model_id = Column(Integer, ForeignKey("models.id"), nullable=True)  # Changed to Integer for MySQL compatibility
    credit_balance = Column(Numeric(12, 2), default=0.0, nullable=False)  # Available credits
    config_path = Column(String(500), nullable=True)
    rag_path = Column(String(500), nullable=True)
    chroma_collection = Column(String(255), nullable=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    default_model = relationship("Model", foreign_keys=[default_model_id])
    users = relationship("User", back_populates="vendor", cascade="all, delete-orphan")
    vendor_configs = relationship("VendorConfig", back_populates="vendor", cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBase", back_populates="vendor", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="vendor", cascade="all, delete-orphan")
    vendor_model_assignments = relationship("VendorModelAssignment", back_populates="vendor", cascade="all, delete-orphan")
    quota_allocations = relationship("QuotaAllocation", back_populates="vendor", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="vendor")
    invoices = relationship("Invoice", back_populates="vendor", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="vendor", cascade="all, delete-orphan")
    vendor_endpoints = relationship("VendorEndpoint", back_populates="vendor", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="vendor", cascade="all, delete-orphan")
    rate_limits = relationship("RateLimit", back_populates="vendor", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="vendor")
    
    __table_args__ = (
        Index("idx_vendor_status_deleted", "status", "deleted_at"),
    )


class Role(Base):
    """RBAC roles."""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False, index=True)  # vendor_admin, vendor_user, vendor_manager, support_agent
    description = Column(Text, nullable=True)
    permissions = Column(JSON, default=dict)  # {"can_manage_users": true, "can_view_analytics": true}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


class User(Base):
    """Users (vendor users or platform users)."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    two_fa_enabled = Column(Boolean, default=False)
    two_fa_secret = Column(String(255), nullable=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="users")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user")
    # audit_logs relationship removed - query with filters instead
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "email", name="uq_vendor_email"),
        Index("idx_user_vendor_active", "vendor_id", "is_active", "deleted_at"),
    )


class UserRole(Base):
    """User-role assignments (RBAC)."""
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    vendor = relationship("Vendor")
    
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "vendor_id", name="uq_user_role_vendor"),
    )


class ModelConfig(Base):
    """Model configuration stored in database (replaces old ModelConfig from database.py)."""
    __tablename__ = "model_configs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False)  # Match models.id type (Integer)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True)  # NULL = global config, match vendors.id type (Integer)
    
    # LLM Configuration
    max_tokens = Column(Integer, nullable=False, default=4000)
    temperature = Column(Numeric(3, 2), nullable=False, default=0.7)
    top_p = Column(Numeric(3, 2), nullable=False, default=0.9)
    top_k = Column(Integer, nullable=False, default=40)
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    model = relationship("Model", foreign_keys=[model_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    
    __table_args__ = (
        UniqueConstraint("model_id", "vendor_id", name="uq_model_config_model_vendor"),
        Index("idx_model_config_model", "model_id"),
        Index("idx_model_config_vendor", "vendor_id"),
        Index("idx_model_config_active", "is_active"),
    )


class VendorModelAssignment(Base):
    """Model assignments per vendor with limits."""
    __tablename__ = "vendor_model_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    is_default = Column(Boolean, default=False, nullable=False)
    max_concurrency = Column(Integer, nullable=True)  # Max concurrent requests
    max_tokens_per_request = Column(Integer, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    priority_order = Column(Integer, default=0, nullable=False)  # Higher = higher priority
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="vendor_model_assignments")
    model = relationship("Model", back_populates="vendor_assignments")
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "model_id", name="uq_vendor_model"),
        Index("idx_vendor_model_enabled", "vendor_id", "enabled", "priority_order"),
    )


class ModelCache(Base):
    """Model response cache per vendor."""
    __tablename__ = "model_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    input_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash of input
    response_reference = Column(Text, nullable=True)  # Pointer to stored response or vector ID
    hits = Column(BigInteger, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    ttl_seconds = Column(Integer, default=86400, nullable=False)  # 24 hours default
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor")
    model = relationship("Model")
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "model_id", "input_hash", name="uq_vendor_model_hash"),
        Index("idx_cache_ttl", "last_used_at", "ttl_seconds"),
    )


class QuotaAllocation(Base):
    """Vendor-level quota allocations."""
    __tablename__ = "quota_allocations"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    resource_type = Column(Enum(ResourceType), nullable=False, index=True)
    allocated_amount = Column(Numeric(20, 2), nullable=False)
    used_amount = Column(Numeric(20, 2), default=0.0, nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    billing_cycle = Column(String(20), nullable=False)  # monthly, annual
    soft_limit = Column(Boolean, default=True, nullable=False)  # True = allow overage with billing
    overdraft_allowed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="quota_allocations")
    
    __table_args__ = (
        Index("idx_quota_vendor_period", "vendor_id", "resource_type", "period_start", "period_end"),
    )


class UsageRecord(Base):
    """Atomic usage events for metering and billing."""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    model_id = Column(Integer, ForeignKey("models.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    resource_type = Column(Enum(ResourceType), nullable=False, index=True)
    amount = Column(Numeric(20, 2), nullable=False)  # Tokens, messages, bytes, etc.
    source = Column(Enum(UsageSource), nullable=False, index=True)
    cost = Column(Numeric(12, 6), default=0.0, nullable=False)  # Calculated cost
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="usage_records")
    user = relationship("User", back_populates="usage_records")
    model = relationship("Model", back_populates="usage_records")
    session = relationship("ChatSession", foreign_keys=[session_id])
    
    __table_args__ = (
        Index("idx_usage_vendor_timestamp", "vendor_id", "timestamp"),
        Index("idx_usage_billing_period", "vendor_id", "resource_type", "timestamp"),
    )


class BillingPlan(Base):
    """Billing plan definitions."""
    __tablename__ = "billing_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)  # free, hobby, pro, enterprise
    name = Column(String(255), nullable=False)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    annual_price = Column(Numeric(10, 2), nullable=True)
    included_tokens = Column(BigInteger, default=0, nullable=False)
    included_conversations = Column(BigInteger, default=0, nullable=False)
    included_storage_mb = Column(BigInteger, default=0, nullable=False)
    overage_price_per_1k_tokens = Column(Numeric(10, 6), default=0.0, nullable=False)
    features = Column(JSON, default=dict)  # {"sso": true, "dedicated_db": false, "white_label": false}
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Invoice(Base):
    """Invoices for vendors."""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    line_items = Column(JSON, default=list)  # [{"description": "...", "amount": 100.00, "quantity": 1}]
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax = Column(Numeric(12, 2), default=0.0, nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    issued_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_invoice_vendor_status", "vendor_id", "status"),
    )


class Payment(Base):
    """Payment records."""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    payment_gateway_id = Column(String(255), nullable=True, index=True)  # Stripe payment intent ID
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    payment_method = Column(String(50), nullable=True)  # card, bank_transfer, credit
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    
    __table_args__ = (
        Index("idx_payment_vendor_status", "vendor_id", "status"),
    )


class ChatSession(Base):
    """Chat sessions."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    session_uuid = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    title = Column(String(500), nullable=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    status = Column(Enum(ChatSessionStatus), default=ChatSessionStatus.OPEN, nullable=False, index=True)
    total_tokens_used = Column(BigInteger, default=0, nullable=False)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    model = relationship("Model")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    usage_records = relationship("UsageRecord", foreign_keys="UsageRecord.session_id", overlaps="session")
    
    __table_args__ = (
        Index("idx_session_vendor_status", "vendor_id", "status", "created_at"),
    )


class ChatMessage(Base):
    """Chat messages."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    sender = Column(Enum(MessageSender), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # system, user, assistant
    content = Column(Text, nullable=False)  # Long text content
    content_json = Column(JSON, nullable=True)  # Structured content if needed
    tokens_used = Column(BigInteger, default=0, nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    is_flagged = Column(Boolean, default=False, nullable=False, index=True)
    flag_reason = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    vendor = relationship("Vendor")
    model = relationship("Model")
    
    __table_args__ = (
        Index("idx_message_vendor_session", "vendor_id", "session_id", "created_at"),
        # Note: CHECK constraint with subquery removed for SQLite compatibility
        # Enforce vendor_id matching at application level
    )


class KnowledgeBase(Base):
    """Knowledge bases per vendor."""
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    vector_db_collection = Column(String(255), nullable=True)  # ChromaDB collection name
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="knowledge_bases")
    documents = relationship("KBDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "name", name="uq_vendor_kb_name"),
    )


class KBDocument(Base):
    """Documents in knowledge bases."""
    __tablename__ = "kb_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility  # Denormalized
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # Long text content
    source_url = Column(String(1000), nullable=True)
    checksum = Column(String(64), nullable=True, index=True)  # SHA256 for deduplication
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    vendor = relationship("Vendor")
    embedding_refs = relationship("KBEmbeddingRef", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_doc_vendor_kb", "vendor_id", "knowledge_base_id"),
    )


class KBEmbeddingRef(Base):
    """References to embeddings in vector DB."""
    __tablename__ = "kb_embeddings_refs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    kb_document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    vector_id = Column(String(255), nullable=False, index=True)  # ID in vector DB (ChromaDB, Pinecone, etc.)
    chunk_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor")
    document = relationship("KBDocument", back_populates="embedding_refs")
    
    __table_args__ = (
        Index("idx_embedding_vendor_doc", "vendor_id", "kb_document_id"),
    )


class VendorConfig(Base):
    """Flexible per-vendor configuration."""
    __tablename__ = "vendor_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    key_name = Column(String(255), nullable=False)
    value = Column(JSON, nullable=True)  # Flexible JSON value
    environment = Column(String(20), default="production", nullable=False)  # production, staging
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="vendor_configs")
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "key_name", "environment", name="uq_vendor_config_key_env"),
    )


class VendorEndpoint(Base):
    """Vendor webhook endpoints."""
    __tablename__ = "vendor_endpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    secret_token_hash = Column(String(255), nullable=True)  # Hashed webhook secret
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="vendor_endpoints")
    webhook_deliveries = relationship("WebhookDelivery", back_populates="endpoint", cascade="all, delete-orphan")


class APIKey(Base):
    """API keys for vendor API access."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    key_name = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), nullable=False, index=True)  # Hashed API key (show raw only once)
    scopes = Column(JSON, default=list)  # ["chat:read", "chat:write", "kb:read"]
    allowed_ips = Column(JSON, default=list)  # IP allowlist
    last_used_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="api_keys")
    rate_limits = relationship("RateLimit", back_populates="api_key", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "key_name", name="uq_vendor_api_key_name"),
        Index("idx_api_key_active", "vendor_id", "revoked_at", "expires_at"),
    )


class RateLimit(Base):
    """Rate limits per vendor or API key."""
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    limit_type = Column(String(50), nullable=False)  # requests_per_minute, tokens_per_hour
    limit_value = Column(Integer, nullable=False)
    window_seconds = Column(Integer, nullable=False)  # Time window for limit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="rate_limits")
    api_key = relationship("APIKey", back_populates="rate_limits")


class WebhookDelivery(Base):
    """Webhook delivery logs."""
    __tablename__ = "webhook_deliveries"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    endpoint_id = Column(Integer, ForeignKey("vendor_endpoints.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)  # Changed to Integer for MySQL compatibility
    payload_summary = Column(Text, nullable=True)
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, index=True)  # success, failed, retrying
    retry_count = Column(Integer, default=0, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    endpoint = relationship("VendorEndpoint", back_populates="webhook_deliveries")
    vendor = relationship("Vendor")


class ModelPreset(Base):
    """Model configuration presets for quick switching."""
    __tablename__ = "model_presets"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    model_id = Column(BigInteger, ForeignKey("models.id", ondelete="CASCADE"), nullable=True)  # Optional: preset for specific model
    vendor_id = Column(BigInteger, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True)  # Optional: preset for specific vendor
    
    # LLM Configuration
    max_tokens = Column(Integer, nullable=False, default=4000)
    temperature = Column(Numeric(3, 2), nullable=False, default=0.7)
    top_p = Column(Numeric(3, 2), nullable=False, default=0.9)
    top_k = Column(Integer, nullable=False, default=40)
    
    # Metadata
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(BigInteger, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    model = relationship("Model", foreign_keys=[model_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    creator = relationship("Admin", foreign_keys=[created_by])
    
    __table_args__ = (
        Index("idx_model_preset_model", "model_id"),
        Index("idx_model_preset_vendor", "vendor_id"),
        Index("idx_model_preset_active", "is_active", "deleted_at"),
    )


class AuditLog(Base):
    """Immutable audit trail."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    actor_type = Column(Enum(ActorType), nullable=False, index=True)
    actor_id = Column(BigInteger, nullable=True, index=True)  # admin_id or user_id
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    action = Column(String(100), nullable=False, index=True)  # vendor.created, user.blocked, quota.updated
    object_type = Column(String(50), nullable=True, index=True)  # vendor, user, quota
    object_id = Column(BigInteger, nullable=True, index=True)
    meta = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships - simplified (actor_id is polymorphic, query with filters)
    vendor = relationship("Vendor", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_vendor_action", "vendor_id", "action", "created_at"),
        Index("idx_audit_actor", "actor_type", "actor_id", "created_at"),
    )


class FeatureFlag(Base):
    """Feature flags for gating features."""
    __tablename__ = "feature_flags"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    key = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    enabled_globally = Column(Boolean, default=False, nullable=False)
    vendor_overrides = Column(JSON, default=dict)  # {vendor_id: true/false or config}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SupportTicket(Base):
    """Support tickets / helpdesk."""
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="open", nullable=False, index=True)  # open, in_progress, resolved, closed
    priority = Column(String(20), default="medium", nullable=False)  # low, medium, high, urgent
    assigned_to = Column(Integer, ForeignKey("admins.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    vendor = relationship("Vendor")
    user = relationship("User")
    assigned_admin = relationship("Admin")


class IPAllowlist(Base):
    """IP allowlist/blocklist."""
    __tablename__ = "ip_allowlist"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    is_allowed = Column(Boolean, default=True, nullable=False)  # True = allowlist, False = blocklist
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    vendor = relationship("Vendor")
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "ip_address", name="uq_vendor_ip"),
    )


class Notification(Base):
    """Notifications (in-app and email logs)."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    type = Column(String(50), nullable=False, index=True)  # quota_warning, invoice_issued, system_alert
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    vendor = relationship("Vendor")
    user = relationship("User")
    admin = relationship("Admin")
    
    __table_args__ = (
        Index("idx_notification_unread", "user_id", "is_read", "created_at"),
        Index("idx_notification_vendor", "vendor_id", "type", "created_at"),
    )


class DataExportRequest(Base):
    """Data export requests for compliance."""
    __tablename__ = "data_export_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Changed to Integer for MySQL compatibility
    request_type = Column(String(50), nullable=False)  # gdpr_export, full_export, partial_export
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    file_path = Column(String(1000), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    meta = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    vendor = relationship("Vendor")
    user = relationship("User")

