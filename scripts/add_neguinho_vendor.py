#!/usr/bin/env python3
"""
Add Neguinho Motors as the first vendor in the SaaS database.
Sets up complete vendor configuration, knowledge base, quotas, and model assignments.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from backend.config.database import get_session_local
from backend.models.saas_models import (
    Vendor, Model, Role, User, VendorModelAssignment, QuotaAllocation,
    KnowledgeBase, VendorConfig, VendorStatus, ResourceType
)
from passlib.context import CryptContext
from loguru import logger
import json

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def add_neguinho_vendor(db: Session):
    """Add Neguinho Motors as the first vendor with complete setup."""
    
    # Check if vendor already exists
    existing = db.query(Vendor).filter(Vendor.slug == "neguinho_motors").first()
    if existing:
        logger.info(f"Vendor 'neguinho_motors' already exists (ID: {existing.id})")
        return existing
    
    # Get default model (Mistral or first available)
    default_model = db.query(Model).filter(Model.code == "mistral").first()
    if not default_model:
        default_model = db.query(Model).order_by(Model.id).first()
    
    if not default_model:
        raise Exception("No models available. Please run init_saas_db.py first.")
    
    # Create vendor
    vendor = Vendor(
        slug="neguinho_motors",
        name="Neguinho Motors",
        company_name="Neguinho Motors Ltd",
        business_type="motorcycle_dealership",
        plan_code="pro",  # Start with pro plan
        status=VendorStatus.ACTIVE,
        default_model_id=default_model.id,
        credit_balance=1000.00,  # Initial credits
        config_path="config/vendors/neguinho_motors/unified_config.json",
        rag_path="rag_knowledge_base/neguinho_motors/knowledge_base.json",
        chroma_collection="neguinho_motors_kb",
        meta={
            "company_number": "11600635",
            "registered_address": "9-13 Catford Hill, London, SE6 4NU",
            "primary_phone": "0208 314 1498",
            "primary_email": "enquiries@neguinhomotors.co.uk",
            "trading_names": ["NGN Motors", "Neguinho Motors", "NGN"],
            "incorporated": "October 2018"
        }
    )
    
    db.add(vendor)
    db.flush()  # Get vendor ID
    
    logger.info(f"Created vendor: {vendor.name} (ID: {vendor.id})")
    
    # Assign default model
    model_assignment = VendorModelAssignment(
        vendor_id=vendor.id,
        model_id=default_model.id,
        is_default=True,
        enabled=True,
        priority_order=1
    )
    db.add(model_assignment)
    logger.info(f"Assigned default model: {default_model.display_name}")
    
    # Assign lightweight model for cache (Phi-2)
    cache_model = db.query(Model).filter(Model.code == "phi").first()
    if cache_model:
        cache_assignment = VendorModelAssignment(
            vendor_id=vendor.id,
            model_id=cache_model.id,
            is_default=False,
            enabled=True,
            priority_order=2
        )
        db.add(cache_assignment)
        logger.info(f"Assigned cache model: {cache_model.display_name}")
    
    # Create quota allocations (monthly)
    period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    quotas = [
        {
            "resource_type": ResourceType.TOKENS,
            "allocated_amount": 1000000,  # 1M tokens/month
            "soft_limit": True
        },
        {
            "resource_type": ResourceType.MESSAGES,
            "allocated_amount": 10000,  # 10K messages/month
            "soft_limit": True
        },
        {
            "resource_type": ResourceType.EMBEDDINGS_STORAGE_MB,
            "allocated_amount": 500,  # 500 MB
            "soft_limit": True
        },
        {
            "resource_type": ResourceType.STORAGE_MB,
            "allocated_amount": 1000,  # 1 GB
            "soft_limit": True
        },
        {
            "resource_type": ResourceType.CONCURRENT_SESSIONS,
            "allocated_amount": 50,  # 50 concurrent sessions
            "soft_limit": False
        }
    ]
    
    for quota_data in quotas:
        quota = QuotaAllocation(
            vendor_id=vendor.id,
            resource_type=quota_data["resource_type"],
            allocated_amount=quota_data["allocated_amount"],
            used_amount=0.0,
            period_start=period_start,
            period_end=period_end,
            billing_cycle="monthly",
            soft_limit=quota_data["soft_limit"],
            overdraft_allowed=True
        )
        db.add(quota)
        logger.info(f"Created quota: {quota_data['resource_type'].value} = {quota_data['allocated_amount']}")
    
    # Create knowledge base entry
    knowledge_base = KnowledgeBase(
        vendor_id=vendor.id,
        name="Neguinho Motors Knowledge Base",
        description="Complete knowledge base for Neguinho Motors including company info, services, branches, and policies",
        is_public=False,
        vector_db_collection="neguinho_motors_kb",
        meta={
            "source": "rag_knowledge_base/neguinho_motors/knowledge_base.json",
            "last_updated": "2025-01-27",
            "chunks_count": 0  # Will be updated when KB is loaded
        }
    )
    db.add(knowledge_base)
    logger.info("Created knowledge base entry")
    
    # Create vendor config entries
    config_entries = [
        {
            "key_name": "chatbot_settings",
            "value": {
                "greetings": ["hi", "hello", "hey"],
                "fallback_message": "I don't have that information in my cache. Please try rephrasing your question or contact us for assistance.",
                "enable_cache": True,
                "enable_llm": True
            }
        },
        {
            "key_name": "cache_settings",
            "value": {
                "enable_cache": True,
                "cache_ttl_seconds": 86400,
                "use_lightweight_model_for_cache": True,
                "cache_model_provider": "ollama",
                "cache_model_name": "phi"
            }
        },
        {
            "key_name": "business_info",
            "value": {
                "company_name": "Neguinho Motors Ltd",
                "company_number": "11600635",
                "primary_phone": "0208 314 1498",
                "primary_email": "enquiries@neguinhomotors.co.uk",
                "registered_address": "9-13 Catford Hill, London, SE6 4NU"
            }
        }
    ]
    
    for config_data in config_entries:
        config = VendorConfig(
            vendor_id=vendor.id,
            key_name=config_data["key_name"],
            value=config_data["value"],
            environment="production"
        )
        db.add(config)
        logger.info(f"Created config: {config_data['key_name']}")
    
    # Create default vendor admin user
    vendor_admin_role = db.query(Role).filter(Role.name == "vendor_admin").first()
    if vendor_admin_role:
        # Hash password (use simple password to avoid bcrypt issues)
        password = "neguinho2025"
        # Ensure password is within bcrypt limit
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        
        try:
            password_hash = pwd_context.hash(password)
        except Exception as e:
            logger.warning(f"Password hashing failed: {e}, using plain text (CHANGE IMMEDIATELY)")
            password_hash = f"PLAIN:{password}"  # Temporary, must be changed
        
        vendor_user = User(
            vendor_id=vendor.id,
            email="admin@neguinhomotors.co.uk",
            password_hash=password_hash,
            name="Neguinho Motors Admin",
            is_active=True,
            is_blocked=False,
            meta={
                "role": "vendor_admin",
                "created_by": "system"
            }
        )
        db.add(vendor_user)
        db.flush()
        
        # Assign vendor_admin role
        from backend.models.saas_models import UserRole
        user_role = UserRole(
            user_id=vendor_user.id,
            role_id=vendor_admin_role.id,
            vendor_id=vendor.id
        )
        db.add(user_role)
        logger.info(f"Created vendor admin user: {vendor_user.email}")
        logger.warning(f"Default password: {password} - Please change this immediately!")
    
    db.commit()
    db.refresh(vendor)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Neguinho Motors vendor setup complete!")
    logger.info("=" * 60)
    logger.info(f"Vendor ID: {vendor.id}")
    logger.info(f"Slug: {vendor.slug}")
    logger.info(f"Name: {vendor.name}")
    logger.info(f"Status: {vendor.status.value}")
    logger.info(f"Plan: {vendor.plan_code}")
    logger.info(f"Credits: £{vendor.credit_balance}")
    logger.info(f"Default Model: {default_model.display_name}")
    logger.info(f"Config Path: {vendor.config_path}")
    logger.info(f"RAG Path: {vendor.rag_path}")
    logger.info("")
    logger.info("Vendor Admin User:")
    logger.info(f"  Email: admin@neguinhomotors.co.uk")
    logger.info(f"  Password: neguinho2025")
    logger.warning("⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
    logger.info("")
    
    return vendor


def main():
    """Main function."""
    logger.info("Adding Neguinho Motors as first vendor...")
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        vendor = add_neguinho_vendor(db)
        logger.info("✓ Setup complete!")
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

