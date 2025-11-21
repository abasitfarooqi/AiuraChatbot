"""
Authentication API endpoints for admin and vendor admin login.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from loguru import logger

from backend.config.database import get_db_session
from backend.models.saas_models import Admin, User, Vendor, UserRole, Role
from backend.utils.auth import hash_password, verify_password, create_access_token
from backend.middleware.auth import get_current_admin, get_current_vendor_admin

router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response models
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class VendorAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    vendor_slug: Optional[str] = None  # Optional: if not provided, will use vendor from user record


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: Optional[int] = None
    user_id: Optional[int] = None
    vendor_id: Optional[int] = None
    vendor_slug: Optional[str] = None
    name: Optional[str] = None
    is_super: Optional[bool] = None
    expires_in: int = 86400  # 24 hours in seconds


class VerifyTokenResponse(BaseModel):
    valid: bool
    admin_id: Optional[int] = None
    user_id: Optional[int] = None
    vendor_id: Optional[int] = None
    type: Optional[str] = None
    is_super: Optional[bool] = None


# ========== ADMIN AUTHENTICATION ==========

@router.post("/admin/login", response_model=LoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    db: Session = Depends(get_db_session)
):
    """Login for super admin or platform admin."""
    admin = db.query(Admin).filter(
        Admin.email == request.email.lower(),
        Admin.deleted_at.is_(None)
    ).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(request.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login
    admin.last_login_at = datetime.utcnow()
    db.commit()
    
    # Create token
    token_data = {
        "admin_id": admin.id,
        "email": admin.email,
        "type": "admin",
        "is_super": admin.is_super
    }
    access_token = create_access_token(token_data)
    
    logger.info(f"Admin login: {admin.email} (super: {admin.is_super})")
    
    return LoginResponse(
        access_token=access_token,
        admin_id=admin.id,
        name=admin.name,
        is_super=admin.is_super
    )


@router.post("/vendor-admin/login", response_model=LoginResponse)
async def vendor_admin_login(
    request: VendorAdminLoginRequest,
    db: Session = Depends(get_db_session)
):
    """Login for vendor admin (User with vendor_admin role)."""
    # Find user by email
    user = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_active == True,
        User.is_blocked == False,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify user has vendor_admin role
    vendor_admin_role = db.query(Role).filter(Role.name == "vendor_admin").first()
    if not vendor_admin_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vendor admin role not configured"
        )
    
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role_id == vendor_admin_role.id
    ).first()
    
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have vendor admin role"
        )
    
    # Get vendor
    vendor_id = user.vendor_id or user_role.vendor_id
    if request.vendor_slug:
        # If vendor_slug provided, verify it matches user's vendor
        vendor = db.query(Vendor).filter(
            Vendor.slug == request.vendor_slug,
            Vendor.status == "active",
            Vendor.deleted_at.is_(None)
        ).first()
        if not vendor or vendor.id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vendor slug does not match user's vendor"
            )
    else:
        vendor = db.query(Vendor).filter(
            Vendor.id == vendor_id,
            Vendor.status == "active",
            Vendor.deleted_at.is_(None)
        ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found or inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Create token
    token_data = {
        "user_id": user.id,
        "vendor_id": vendor.id,
        "vendor_slug": vendor.slug,
        "email": user.email,
        "type": "vendor_admin"
    }
    access_token = create_access_token(token_data)
    
    logger.info(f"Vendor admin login: {user.email} (vendor: {vendor.slug})")
    
    return LoginResponse(
        access_token=access_token,
        user_id=user.id,
        vendor_id=vendor.id,
        vendor_slug=vendor.slug,
        name=user.name
    )


@router.get("/verify", response_model=VerifyTokenResponse)
async def verify_token(
    authorization: Optional[str] = Header(None)
):
    """Verify if current token is valid and return admin info."""
    from backend.utils.auth import get_token_from_header, decode_access_token
    from backend.config.database import get_db_session
    
    token = get_token_from_header(authorization)
    if not token:
        return VerifyTokenResponse(valid=False)
    
    try:
        payload = decode_access_token(token)
        admin_id = payload.get("admin_id")
        admin_type = payload.get("type")
        
        if admin_id and admin_type == "admin":
            db = next(get_db_session())
            try:
                admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
                if admin:
                    return VerifyTokenResponse(
                        valid=True,
                        admin_id=admin.id,
                        type="admin",
                        is_super=admin.is_super
                    )
            finally:
                pass
        
        return VerifyTokenResponse(valid=False)
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")
        return VerifyTokenResponse(valid=False)


@router.get("/vendor-admin/verify", response_model=VerifyTokenResponse)
async def verify_vendor_admin_token(
    authorization: Optional[str] = Header(None)
):
    """Verify if current vendor admin token is valid."""
    from backend.utils.auth import get_token_from_header, decode_access_token
    from backend.config.database import get_db_session
    
    token = get_token_from_header(authorization)
    if not token:
        return VerifyTokenResponse(valid=False)
    
    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        vendor_id = payload.get("vendor_id")
        user_type = payload.get("type")
        
        if user_id and vendor_id and user_type == "vendor_admin":
            db = next(get_db_session())
            try:
                user = db.query(User).filter(
                    User.id == user_id,
                    User.vendor_id == vendor_id,
                    User.is_active == True,
                    User.is_blocked == False,
                    User.deleted_at.is_(None)
                ).first()
                
                if user:
                    vendor = db.query(Vendor).filter(
                        Vendor.id == vendor_id,
                        Vendor.status == "active",
                        Vendor.deleted_at.is_(None)
                    ).first()
                    
                    if vendor:
                        return VerifyTokenResponse(
                            valid=True,
                            user_id=user.id,
                            vendor_id=vendor.id,
                            type="vendor_admin"
                        )
            finally:
                pass
        
        return VerifyTokenResponse(valid=False)
    except Exception as e:
        logger.debug(f"Vendor admin token verification failed: {e}")
        return VerifyTokenResponse(valid=False)


@router.post("/logout")
async def logout():
    """Logout (client should discard token)."""
    # In a stateless JWT system, logout is handled client-side by discarding the token
    # For enhanced security, you could implement a token blacklist in Redis
    return {"status": "success", "message": "Token should be discarded on client side"}


@router.get("/me")
async def get_current_user_info(
    admin: Optional[Admin] = Depends(get_current_admin)
):
    """Get current authenticated admin information."""
    if admin:
        return {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "is_super": admin.is_super,
            "type": "admin",
            "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )


@router.get("/vendor-admin/me")
async def get_current_vendor_admin_info(
    user_vendor: tuple = Depends(get_current_vendor_admin)
):
    """Get current authenticated vendor admin information."""
    user, vendor = user_vendor
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "vendor_id": vendor.id,
        "vendor_slug": vendor.slug,
        "vendor_name": vendor.name,
        "type": "vendor_admin",
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
    }

