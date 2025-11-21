#!/usr/bin/env python3
"""
Initialize SaaS database with all tables and seed data.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from backend.config.database import (
    get_database_engine, get_session_local, create_database_if_not_exists, init_database
)
from backend.models.saas_models import (
    Base, Admin, Vendor, Model, Role, BillingPlan, VendorStatus
)
from passlib.context import CryptContext
from datetime import datetime
from loguru import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_default_models(db: Session):
    """Create default LLM models."""
    models = [
        {
            "code": "mistral",
            "display_name": "Mistral 7B",
            "provider": "ollama",
            "capabilities": {"chat": True, "embeddings": False, "streaming": True},
            "default_max_tokens": 4000,
            "price_per_1k_tokens": 0.0,  # Free for self-hosted
            "is_cache_model": False,
            "is_active": True,
            "meta": {}
        },
        {
            "code": "llama2",
            "display_name": "Llama 2",
            "provider": "ollama",
            "capabilities": {"chat": True, "embeddings": False, "streaming": True},
            "default_max_tokens": 4000,
            "price_per_1k_tokens": 0.0,
            "is_cache_model": False,
            "is_active": True
        },
        {
            "code": "phi",
            "display_name": "Phi-2 (Lightweight)",
            "provider": "ollama",
            "capabilities": {"chat": True, "embeddings": False, "streaming": True},
            "default_max_tokens": 2000,
            "price_per_1k_tokens": 0.0,
            "is_cache_model": True,  # For cache responses
            "is_active": True
        },
        {
            "code": "gpt-4-turbo",
            "display_name": "GPT-4 Turbo",
            "provider": "openai",
            "capabilities": {"chat": True, "embeddings": False, "streaming": True},
            "default_max_tokens": 4000,
            "price_per_1k_tokens": 0.01,  # $0.01 per 1k tokens
            "is_cache_model": False,
            "is_active": True
        }
    ]
    
    for model_data in models:
        existing = db.query(Model).filter(Model.code == model_data["code"]).first()
        if not existing:
            model = Model(**model_data)
            db.add(model)
            logger.info(f"Created model: {model_data['code']}")
    
    db.commit()


def create_default_roles(db: Session):
    """Create default RBAC roles."""
    roles = [
        {
            "name": "vendor_admin",
            "description": "Full access to vendor account and settings",
            "permissions": {
                "can_manage_users": True,
                "can_manage_kb": True,
                "can_view_analytics": True,
                "can_manage_api_keys": True,
                "can_manage_billing": True
            }
        },
        {
            "name": "vendor_user",
            "description": "Standard vendor user with chat access",
            "permissions": {
                "can_manage_users": False,
                "can_manage_kb": False,
                "can_view_analytics": True,
                "can_manage_api_keys": False,
                "can_manage_billing": False
            }
        },
        {
            "name": "vendor_manager",
            "description": "Vendor manager with limited admin access",
            "permissions": {
                "can_manage_users": True,
                "can_manage_kb": True,
                "can_view_analytics": True,
                "can_manage_api_keys": True,
                "can_manage_billing": False
            }
        },
        {
            "name": "support_agent",
            "description": "Support agent with read-only access",
            "permissions": {
                "can_manage_users": False,
                "can_manage_kb": False,
                "can_view_analytics": True,
                "can_manage_api_keys": False,
                "can_manage_billing": False
            }
        }
    ]
    
    for role_data in roles:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            logger.info(f"Created role: {role_data['name']}")
    
    db.commit()


def create_default_billing_plans(db: Session):
    """Create default billing plans."""
    plans = [
        {
            "code": "free",
            "name": "Free Tier",
            "monthly_price": 0.0,
            "annual_price": 0.0,
            "included_tokens": 10000,
            "included_conversations": 100,
            "included_storage_mb": 100,
            "overage_price_per_1k_tokens": 0.0,
            "features": {
                "sso": False,
                "dedicated_db": False,
                "white_label": False,
                "priority_support": False
            },
            "is_active": True
        },
        {
            "code": "hobby",
            "name": "Hobby",
            "monthly_price": 29.0,
            "annual_price": 290.0,
            "included_tokens": 100000,
            "included_conversations": 1000,
            "included_storage_mb": 1000,
            "overage_price_per_1k_tokens": 0.001,
            "features": {
                "sso": False,
                "dedicated_db": False,
                "white_label": False,
                "priority_support": False
            },
            "is_active": True
        },
        {
            "code": "pro",
            "name": "Professional",
            "monthly_price": 99.0,
            "annual_price": 990.0,
            "included_tokens": 1000000,
            "included_conversations": 10000,
            "included_storage_mb": 10000,
            "overage_price_per_1k_tokens": 0.0005,
            "features": {
                "sso": True,
                "dedicated_db": False,
                "white_label": True,
                "priority_support": True
            },
            "is_active": True
        },
        {
            "code": "enterprise",
            "name": "Enterprise",
            "monthly_price": 499.0,
            "annual_price": 4990.0,
            "included_tokens": 10000000,
            "included_conversations": 100000,
            "included_storage_mb": 100000,
            "overage_price_per_1k_tokens": 0.0002,
            "features": {
                "sso": True,
                "dedicated_db": True,
                "white_label": True,
                "priority_support": True,
                "custom_sla": True
            },
            "is_active": True
        }
    ]
    
    for plan_data in plans:
        existing = db.query(BillingPlan).filter(BillingPlan.code == plan_data["code"]).first()
        if not existing:
            plan = BillingPlan(**plan_data)
            db.add(plan)
            logger.info(f"Created billing plan: {plan_data['code']}")
    
    db.commit()


def create_super_admin(db: Session, email: str = "admin@aiurachatbot.com", password: str = "admin123"):
    """Create super admin account."""
    existing = db.query(Admin).filter(Admin.email == email).first()
    if existing:
        logger.info(f"Super admin already exists: {email}")
        return existing
    
    # Hash password (bcrypt has 72 byte limit)
    password_to_hash = password[:72] if len(password) > 72 else password
    
    admin = Admin(
        email=email,
        password_hash=pwd_context.hash(password_to_hash),
        name="Super Admin",
        is_super=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    logger.info(f"Created super admin: {email}")
    logger.warning(f"Default password: {password} - Please change this immediately!")
    
    return admin


def main():
    """Main initialization function."""
    logger.info("Initializing SaaS database...")
    
    # Create database if using MySQL
    create_database_if_not_exists()
    
    # Initialize tables
    logger.info("Creating database tables...")
    init_database()
    
    # Get database session
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        # Create default data
        logger.info("Creating default models...")
        create_default_models(db)
        
        logger.info("Creating default roles...")
        create_default_roles(db)
        
        logger.info("Creating default billing plans...")
        create_default_billing_plans(db)
        
        logger.info("Creating super admin...")
        create_super_admin(db)
        
        logger.info("✓ Database initialization complete!")
        logger.info("")
        logger.info("Super Admin Credentials:")
        logger.info("  Email: admin@aiurachatbot.com")
        logger.info("  Password: admin123")
        logger.warning("⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
        
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

