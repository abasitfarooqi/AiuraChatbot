"""
Authentication middleware for protecting routes.
"""
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from backend.config.database import get_db_session
from backend.models.saas_models import Admin, User, Vendor
from backend.utils.auth import decode_access_token, get_token_from_header


async def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db_session)
) -> Admin:
    """Get current authenticated admin (super admin or vendor admin)."""
    token = get_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    admin_id = payload.get("admin_id")
    admin_type = payload.get("type")  # "super_admin" or "vendor_admin"
    
    if not admin_id or admin_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token for admin access"
        )
    
    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return admin


async def get_current_super_admin(
    admin: Admin = Depends(get_current_admin)
) -> Admin:
    """Get current authenticated super admin only."""
    if not admin.is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return admin


async def get_current_vendor_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db_session)
):
    """Get current authenticated vendor admin (User with vendor_admin role)."""
    """Get current authenticated vendor admin (User with vendor_admin role)."""
    token = get_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    vendor_id = payload.get("vendor_id")
    user_type = payload.get("type")
    
    if not user_id or user_type != "vendor_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token for vendor admin access"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.vendor_id == vendor_id,
        User.is_active == True,
        User.is_blocked == False,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor admin not found"
        )
    
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
    
    return user, vendor


async def get_current_user_or_vendor(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db_session)
):
    """Get current user or vendor from token (for API endpoints)."""
    """Get current user or vendor from token (for API endpoints)."""
    token = get_token_from_header(authorization)
    if not token:
        return None, None
    
    try:
        payload = decode_access_token(token)
        user_type = payload.get("type")
        
        if user_type == "vendor_admin":
            user_id = payload.get("user_id")
            vendor_id = payload.get("vendor_id")
            user = db.query(User).filter(User.id == user_id).first()
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            return user, vendor
        elif user_type == "api_key":
            vendor_id = payload.get("vendor_id")
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            return None, vendor
    except:
        return None, None
    
    return None, None

