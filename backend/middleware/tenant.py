"""
Multi-tenant middleware for vendor scoping and access control.
"""
from fastapi import Request, HTTPException, status
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger
from backend.models.saas_models import Vendor, User, VendorStatus
from backend.config.database import get_db_session


def get_vendor_from_request(request: Request, db: Session) -> Optional[Vendor]:
    """Extract vendor from request (slug, vendor_id, or API key)."""
    # Try vendor slug from path
    vendor_slug = request.path_params.get("vendor_slug") or request.path_params.get("slug")
    if vendor_slug:
        vendor = db.query(Vendor).filter(
            Vendor.slug == vendor_slug,
            Vendor.deleted_at.is_(None)
        ).first()
        if vendor:
            return vendor
    
    # Try vendor_id from query params
    vendor_id = request.query_params.get("vendor_id")
    if vendor_id:
        try:
            vendor = db.query(Vendor).filter(
                Vendor.id == int(vendor_id),
                Vendor.deleted_at.is_(None)
            ).first()
            if vendor:
                return vendor
        except (ValueError, TypeError):
            pass
    
    # Try API key header
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if api_key:
        from backend.models.saas_models import APIKey
        import hashlib
        
        # Find API key (in production, use hash comparison)
        api_key_obj = db.query(APIKey).filter(
            APIKey.revoked_at.is_(None),
            APIKey.expires_at.is_(None) | (APIKey.expires_at > datetime.utcnow())
        ).all()
        
        for key_obj in api_key_obj:
            # Hash the provided key and compare
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            if api_key_hash == key_obj.api_key_hash:
                vendor = db.query(Vendor).filter(Vendor.id == key_obj.vendor_id).first()
                if vendor:
                    return vendor
    
    return None


def require_vendor(request: Request, db: Session) -> Vendor:
    """Require vendor and raise if not found or inactive."""
    vendor = get_vendor_from_request(request, db)
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    if vendor.status == VendorStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account is blocked"
        )
    
    if vendor.status == VendorStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account is suspended"
        )
    
    if vendor.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    return vendor


def require_active_vendor(vendor: Vendor):
    """Ensure vendor is active."""
    if vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Vendor account is {vendor.status.value}"
        )


def check_quota(vendor: Vendor, resource_type: str, amount: float, db: Session) -> bool:
    """Check if vendor has quota available."""
    from backend.models.saas_models import QuotaAllocation, ResourceType
    from datetime import datetime
    
    quota = db.query(QuotaAllocation).filter(
        QuotaAllocation.vendor_id == vendor.id,
        QuotaAllocation.resource_type == ResourceType(resource_type),
        QuotaAllocation.period_start <= datetime.utcnow(),
        QuotaAllocation.period_end >= datetime.utcnow()
    ).first()
    
    if not quota:
        # No quota = unlimited (for now)
        return True
    
    remaining = float(quota.allocated_amount) - float(quota.used_amount)
    
    if remaining < amount:
        if quota.soft_limit:
            # Allow but will bill overage
            return True
        elif quota.overdraft_allowed:
            # Allow overdraft
            return True
        else:
            # Hard limit - block
            return False
    
    return True


def record_usage(
    vendor: Vendor,
    resource_type: str,
    amount: float,
    db: Session,
    user_id: Optional[int] = None,
    model_id: Optional[int] = None,
    session_id: Optional[int] = None,
    source: str = "api"
):
    """Record usage and update quota."""
    from backend.models.saas_models import UsageRecord, QuotaAllocation, ResourceType, UsageSource
    from datetime import datetime
    
    # Create usage record
    usage = UsageRecord(
        vendor_id=vendor.id,
        user_id=user_id,
        model_id=model_id,
        session_id=session_id,
        resource_type=ResourceType(resource_type),
        amount=amount,
        source=UsageSource(source),
        timestamp=datetime.utcnow()
    )
    db.add(usage)
    
    # Update quota allocation
    quota = db.query(QuotaAllocation).filter(
        QuotaAllocation.vendor_id == vendor.id,
        QuotaAllocation.resource_type == ResourceType(resource_type),
        QuotaAllocation.period_start <= datetime.utcnow(),
        QuotaAllocation.period_end >= datetime.utcnow()
    ).first()
    
    if quota:
        quota.used_amount = float(quota.used_amount) + amount
        db.add(quota)
    
    db.commit()
    logger.info(f"Recorded usage: vendor={vendor.id}, type={resource_type}, amount={amount}")


def log_audit(
    actor_type: str,
    actor_id: Optional[int],
    action: str,
    object_type: Optional[str] = None,
    object_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    db: Session = None,
    request: Optional[Request] = None,
    meta: Optional[dict] = None
):
    """Log audit event."""
    from backend.models.saas_models import AuditLog, ActorType
    from datetime import datetime
    
    if not db:
        return
    
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    
    audit = AuditLog(
        actor_type=ActorType(actor_type),
        actor_id=actor_id,
        vendor_id=vendor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        meta=meta or {},
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.utcnow()
    )
    db.add(audit)
    db.commit()

