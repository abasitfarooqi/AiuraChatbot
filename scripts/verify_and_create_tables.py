#!/usr/bin/env python3
"""
Verify all required tables exist and create missing ones.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.config.database import get_database_engine
from backend.models.saas_models import (
    Base, ChatUser, ChatSession, ChatMessage, ConversationMemory, SuggestionCache,
    MainCache, TemporaryCache, Vendor, User, Model, KnowledgeBase, KBDocument,
    KBEmbeddingRef, VendorConfig, VendorEndpoint, APIKey, RateLimit, WebhookDelivery,
    ModelPreset, AuditLog, FeatureFlag, SupportTicket, IPAllowlist, Notification,
    DataExportRequest, ModelCache, QuotaAllocation, UsageRecord, BillingPlan,
    Invoice, Payment, ModelConfig, VendorModelAssignment, Role, UserRole, Admin
)
from loguru import logger
from sqlalchemy import inspect

def verify_and_create_tables():
    """Verify all required tables exist and create missing ones."""
    try:
        logger.info("Verifying database tables...")
        
        engine = get_database_engine()
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # All required tables from saas_models
        required_tables = {
            "admins", "models", "vendors", "roles", "users", "user_roles",
            "model_configs", "vendor_model_assignments", "model_cache",
            "quota_allocations", "usage_records", "billing_plans", "invoices",
            "payments", "chat_users", "chat_sessions", "chat_messages",
            "knowledge_bases", "kb_documents", "kb_embeddings_refs",
            "vendor_configs", "vendor_endpoints", "api_keys", "rate_limits",
            "webhook_deliveries", "model_presets", "audit_logs", "feature_flags",
            "support_tickets", "ip_allowlist", "notifications", "data_export_requests",
            "main_cache", "temporary_cache", "conversation_memories", "suggestion_cache"
        }
        
        missing_tables = required_tables - existing_tables
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            logger.info("Creating missing tables...")
            
            # Create missing tables
            for table_name in missing_tables:
                try:
                    # Map table names to models
                    model_map = {
                        "chat_users": ChatUser,
                        "chat_sessions": ChatSession,
                        "chat_messages": ChatMessage,
                        "conversation_memories": ConversationMemory,
                        "suggestion_cache": SuggestionCache,
                        "main_cache": MainCache,
                        "temporary_cache": TemporaryCache,
                        "vendors": Vendor,
                        "users": User,
                        "models": Model,
                        "knowledge_bases": KnowledgeBase,
                        "kb_documents": KBDocument,
                        "kb_embeddings_refs": KBEmbeddingRef,
                        "vendor_configs": VendorConfig,
                        "vendor_endpoints": VendorEndpoint,
                        "api_keys": APIKey,
                        "rate_limits": RateLimit,
                        "webhook_deliveries": WebhookDelivery,
                        "model_presets": ModelPreset,
                        "audit_logs": AuditLog,
                        "feature_flags": FeatureFlag,
                        "support_tickets": SupportTicket,
                        "ip_allowlist": IPAllowlist,
                        "notifications": Notification,
                        "data_export_requests": DataExportRequest,
                        "model_cache": ModelCache,
                        "quota_allocations": QuotaAllocation,
                        "usage_records": UsageRecord,
                        "billing_plans": BillingPlan,
                        "invoices": Invoice,
                        "payments": Payment,
                        "model_configs": ModelConfig,
                        "vendor_model_assignments": VendorModelAssignment,
                        "roles": Role,
                        "user_roles": UserRole,
                        "admins": Admin
                    }
                    
                    if table_name in model_map:
                        model = model_map[table_name]
                        model.__table__.create(engine, checkfirst=True)
                        logger.info(f"✅ Created table: {table_name}")
                    else:
                        logger.warning(f"⚠️  No model found for table: {table_name}")
                        
                except Exception as e:
                    logger.error(f"❌ Error creating table {table_name}: {e}")
        else:
            logger.info("✅ All required tables exist!")
        
        # Check for old/duplicate tables
        old_tables = {"conversation_memory", "chats", "messages", "token_usage"}
        found_old = old_tables.intersection(existing_tables)
        if found_old:
            logger.warning(f"⚠️  Found old/legacy tables (can be removed after migration): {found_old}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Table verification complete!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error verifying tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_and_create_tables()

