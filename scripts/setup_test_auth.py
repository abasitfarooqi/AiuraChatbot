#!/usr/bin/env python3
"""
Setup script to create test users, vendors, and verify authentication.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config.database import get_db_session
from backend.models.saas_models import (
    Admin, Vendor, User, Role, UserRole, Model, VendorModelAssignment
)
from backend.utils.auth import hash_password
from sqlalchemy.orm import Session
from datetime import datetime
import os

# Set MySQL environment
os.environ.setdefault("USE_MYSQL", "true")
os.environ.setdefault("MYSQL_USER", "root")
os.environ.setdefault("MYSQL_PASSWORD", "abc123")
os.environ.setdefault("MYSQL_DATABASE", "aiura_chatbots")


def create_test_super_admin(db: Session):
    """Create or update test super admin."""
    email = "admin@aiurachatbot.com"
    password = "admin123"
    
    admin = db.query(Admin).filter(Admin.email == email).first()
    if admin:
        print(f"✅ Super admin already exists: {email}")
        # Update password
        admin.password_hash = hash_password(password)
        admin.is_super = True
        db.commit()
        print(f"   Password updated")
    else:
        admin = Admin(
            email=email,
            password_hash=hash_password(password),
            name="Super Admin",
            is_super=True
        )
        db.add(admin)
        db.commit()
        print(f"✅ Created super admin: {email} / {password}")
    
    return admin


def create_vendor_admin_role(db: Session):
    """Create vendor_admin role if it doesn't exist."""
    role = db.query(Role).filter(Role.name == "vendor_admin").first()
    if not role:
        role = Role(
            name="vendor_admin",
            description="Vendor administrator with full access to vendor settings",
            permissions={
                "can_manage_users": True,
                "can_view_analytics": True,
                "can_manage_config": True,
                "can_manage_knowledge_base": True
            }
        )
        db.add(role)
        db.commit()
        print("✅ Created vendor_admin role")
    else:
        print("✅ vendor_admin role already exists")
    return role


def create_test_vendor(db: Session, vendor_slug: str, vendor_name: str, company_name: str):
    """Create or get test vendor."""
    vendor = db.query(Vendor).filter(Vendor.slug == vendor_slug).first()
    if vendor:
        print(f"✅ Vendor already exists: {vendor_slug}")
        return vendor
    
    # Get default model
    default_model = db.query(Model).filter(Model.is_active == True).first()
    
    vendor = Vendor(
        slug=vendor_slug,
        name=vendor_name,
        company_name=company_name,
        business_type="motorcycle_dealership",
        plan_code="free",
        status="active",
        default_model_id=default_model.id if default_model else None,
        credit_balance=1000.0
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    # Assign default model to vendor
    if default_model:
        assignment = VendorModelAssignment(
            vendor_id=vendor.id,
            model_id=default_model.id,
            is_default=True,
            enabled=True
        )
        db.add(assignment)
        db.commit()
    
    print(f"✅ Created vendor: {vendor_slug} ({vendor_name})")
    return vendor


def create_test_vendor_admin(db: Session, vendor: Vendor, email: str, password: str, name: str):
    """Create test vendor admin user."""
    # Check if user exists
    user = db.query(User).filter(
        User.email == email,
        User.vendor_id == vendor.id
    ).first()
    
    if user:
        print(f"✅ Vendor admin already exists: {email}")
        # Update password
        user.password_hash = hash_password(password)
        user.is_active = True
        user.is_blocked = False
        db.commit()
        print(f"   Password updated")
    else:
        user = User(
            vendor_id=vendor.id,
            email=email,
            password_hash=hash_password(password),
            name=name,
            is_active=True,
            is_blocked=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ Created vendor admin user: {email} / {password}")
    
    # Assign vendor_admin role
    vendor_admin_role = db.query(Role).filter(Role.name == "vendor_admin").first()
    if vendor_admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == vendor_admin_role.id,
            UserRole.vendor_id == vendor.id
        ).first()
        
        if not user_role:
            user_role = UserRole(
                user_id=user.id,
                role_id=vendor_admin_role.id,
                vendor_id=vendor.id
            )
            db.add(user_role)
            db.commit()
            print(f"✅ Assigned vendor_admin role to {email}")
        else:
            print(f"✅ Role already assigned to {email}")
    
    return user


def main():
    """Main setup function."""
    print("=" * 60)
    print("🔧 Setting up test authentication...")
    print("=" * 60)
    
    db = next(get_db_session())
    
    try:
        # 1. Create super admin
        print("\n1. Creating super admin...")
        super_admin = create_test_super_admin(db)
        
        # 2. Create vendor_admin role
        print("\n2. Creating vendor_admin role...")
        vendor_admin_role = create_vendor_admin_role(db)
        
        # 3. Create Neguinho Motors vendor
        print("\n3. Creating Neguinho Motors vendor...")
        neguinho_vendor = create_test_vendor(
            db,
            vendor_slug="neguinho_motors",
            vendor_name="Neguinho Motors",
            company_name="Neguinho Motors Ltd"
        )
        
        # 4. Create vendor admin for Neguinho Motors
        print("\n4. Creating vendor admin for Neguinho Motors...")
        neguinho_admin = create_test_vendor_admin(
            db,
            vendor=neguinho_vendor,
            email="admin@neguinhomotors.co.uk",
            password="neguinho123",
            name="Neguinho Admin"
        )
        
        # 5. Verify setup
        print("\n5. Verifying setup...")
        admin_count = db.query(Admin).count()
        vendor_count = db.query(Vendor).filter(Vendor.deleted_at.is_(None)).count()
        user_count = db.query(User).filter(User.deleted_at.is_(None)).count()
        
        print(f"\n✅ Setup complete!")
        print(f"\n📊 Summary:")
        print(f"   - Super Admins: {admin_count}")
        print(f"   - Vendors: {vendor_count}")
        print(f"   - Users: {user_count}")
        
        print(f"\n🔐 Test Credentials:")
        print(f"\n   Super Admin:")
        print(f"   Email: admin@aiurachatbot.com")
        print(f"   Password: admin123")
        
        print(f"\n   Vendor Admin (Neguinho Motors):")
        print(f"   Email: admin@neguinhomotors.co.uk")
        print(f"   Password: neguinho123")
        print(f"   Vendor Slug: neguinho_motors")
        
        print(f"\n🌐 Access URLs:")
        print(f"   Login: http://127.0.0.1:8000/login.html")
        print(f"   Admin Panel: http://127.0.0.1:8000/admin.html")
        print(f"   Chatbot: http://127.0.0.1:8000/")
        
        print(f"\n🎉 Ready to test!")
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

