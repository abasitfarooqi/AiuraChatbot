"""
Super Admin API endpoints for platform control.
Full vendor management, quotas, billing, model assignments, and analytics.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from loguru import logger

from backend.config.database import get_db_session
from backend.models.saas_models import (
    Admin, Vendor, User, Role, Model, VendorModelAssignment, QuotaAllocation,
    UsageRecord, Invoice, Payment, ChatSession, ChatMessage, KnowledgeBase,
    APIKey, AuditLog, VendorStatus, ResourceType, InvoiceStatus, PaymentStatus
)
from backend.middleware.tenant import log_audit

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for requests/responses
class VendorCreate(BaseModel):
    slug: str
    name: str
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    plan_code: Optional[str] = "free"
    default_model_id: Optional[int] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    plan_code: Optional[str] = None
    status: Optional[str] = None
    default_model_id: Optional[int] = None
    credit_balance: Optional[float] = None


class QuotaAllocationCreate(BaseModel):
    resource_type: str
    allocated_amount: float
    period_start: datetime
    period_end: datetime
    billing_cycle: str = "monthly"
    soft_limit: bool = True
    overdraft_allowed: bool = False


class ModelAssignmentCreate(BaseModel):
    model_id: int
    is_default: bool = False
    max_concurrency: Optional[int] = None
    max_tokens_per_request: Optional[int] = None
    enabled: bool = True
    priority_order: int = 0


class CreditAdjustment(BaseModel):
    amount: float
    reason: str
    metadata: Optional[Dict[str, Any]] = None


# Import auth middleware
from backend.middleware.auth import get_current_admin as get_current_admin_auth, get_current_super_admin


# ========== VENDOR MANAGEMENT ==========

@router.get("/vendors", response_model=Dict[str, Any])
async def list_vendors(
    status_filter: Optional[str] = Query(None, alias="status"),
    plan_code: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """List all vendors with filters and pagination."""
    query = db.query(Vendor).filter(Vendor.deleted_at.is_(None))
    
    if status_filter:
        query = query.filter(Vendor.status == VendorStatus(status_filter))
    if plan_code:
        query = query.filter(Vendor.plan_code == plan_code)
    if search:
        query = query.filter(
            or_(
                Vendor.slug.ilike(f"%{search}%"),
                Vendor.name.ilike(f"%{search}%"),
                Vendor.company_name.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    vendors = query.order_by(desc(Vendor.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for vendor in vendors:
        # Get current quota usage
        quota_usage = db.query(
            func.sum(UsageRecord.amount).label("tokens_used")
        ).filter(
            UsageRecord.vendor_id == vendor.id,
            UsageRecord.resource_type == ResourceType.TOKENS,
            UsageRecord.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).scalar() or 0
        
        # Get active sessions count
        active_sessions = db.query(ChatSession).filter(
            ChatSession.vendor_id == vendor.id,
            ChatSession.status == "open"
        ).count()
        
        result.append({
            "id": vendor.id,
            "slug": vendor.slug,
            "name": vendor.name,
            "company_name": vendor.company_name,
            "plan_code": vendor.plan_code,
            "status": vendor.status.value,
            "credit_balance": float(vendor.credit_balance),
            "tokens_used_30d": float(quota_usage),
            "active_sessions": active_sessions,
            "created_at": vendor.created_at.isoformat(),
            "updated_at": vendor.updated_at.isoformat()
        })
    
    return {
        "vendors": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/vendors/{vendor_id}", response_model=Dict[str, Any])
async def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Get detailed vendor information."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get quota allocations
    quotas = db.query(QuotaAllocation).filter(
        QuotaAllocation.vendor_id == vendor.id,
        QuotaAllocation.period_end >= datetime.utcnow()
    ).all()
    
    # Get model assignments
    model_assignments = db.query(VendorModelAssignment).filter(
        VendorModelAssignment.vendor_id == vendor.id
    ).all()
    
    # Get recent usage
    recent_usage = db.query(
        func.sum(UsageRecord.amount).label("total"),
        UsageRecord.resource_type
    ).filter(
        UsageRecord.vendor_id == vendor.id,
        UsageRecord.timestamp >= datetime.utcnow() - timedelta(days=30)
    ).group_by(UsageRecord.resource_type).all()
    
    # Get active sessions
    active_sessions = db.query(ChatSession).filter(
        ChatSession.vendor_id == vendor.id,
        ChatSession.status == "open"
    ).limit(10).all()
    
    return {
        "id": vendor.id,
        "slug": vendor.slug,
        "name": vendor.name,
        "company_name": vendor.company_name,
        "business_type": vendor.business_type,
        "plan_code": vendor.plan_code,
        "status": vendor.status.value,
        "credit_balance": float(vendor.credit_balance),
        "default_model_id": vendor.default_model_id,
        "billing_customer_id": vendor.billing_customer_id,
        "quotas": [
            {
                "resource_type": q.resource_type.value,
                "allocated": float(q.allocated_amount),
                "used": float(q.used_amount),
                "remaining": float(q.allocated_amount - q.used_amount),
                "period_start": q.period_start.isoformat(),
                "period_end": q.period_end.isoformat()
            }
            for q in quotas
        ],
        "model_assignments": [
            {
                "model_id": ma.model_id,
                "is_default": ma.is_default,
                "enabled": ma.enabled,
                "priority_order": ma.priority_order
            }
            for ma in model_assignments
        ],
        "usage_30d": {
            u.resource_type.value: float(u.total)
            for u in recent_usage
        },
        "active_sessions_count": len(active_sessions),
        "created_at": vendor.created_at.isoformat(),
        "updated_at": vendor.updated_at.isoformat()
    }


@router.post("/vendors", response_model=Dict[str, Any])
async def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Create a new vendor."""
    # Check if slug exists
    existing = db.query(Vendor).filter(Vendor.slug == vendor_data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vendor slug already exists")
    
    vendor = Vendor(
        slug=vendor_data.slug,
        name=vendor_data.name,
        company_name=vendor_data.company_name,
        business_type=vendor_data.business_type,
        plan_code=vendor_data.plan_code or "free",
        status=VendorStatus.ACTIVE,
        default_model_id=vendor_data.default_model_id,
        credit_balance=0.0
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    log_audit(
        actor_type="admin",
        actor_id=admin.id,
        action="vendor.created",
        object_type="vendor",
        object_id=vendor.id,
        db=db,
        meta={"slug": vendor.slug, "name": vendor.name}
    )
    
    return {
        "id": vendor.id,
        "slug": vendor.slug,
        "name": vendor.name,
        "status": vendor.status.value,
        "created_at": vendor.created_at.isoformat()
    }


@router.patch("/vendors/{vendor_id}", response_model=Dict[str, Any])
async def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Update vendor information."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    changes = {}
    if vendor_data.name is not None:
        vendor.name = vendor_data.name
        changes["name"] = vendor_data.name
    if vendor_data.company_name is not None:
        vendor.company_name = vendor_data.company_name
        changes["company_name"] = vendor_data.company_name
    if vendor_data.business_type is not None:
        vendor.business_type = vendor_data.business_type
        changes["business_type"] = vendor_data.business_type
    if vendor_data.plan_code is not None:
        vendor.plan_code = vendor_data.plan_code
        changes["plan_code"] = vendor_data.plan_code
    if vendor_data.status is not None:
        vendor.status = VendorStatus(vendor_data.status)
        changes["status"] = vendor_data.status
    if vendor_data.default_model_id is not None:
        vendor.default_model_id = vendor_data.default_model_id
        changes["default_model_id"] = vendor_data.default_model_id
    if vendor_data.credit_balance is not None:
        vendor.credit_balance = vendor_data.credit_balance
        changes["credit_balance"] = vendor_data.credit_balance
    
    vendor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vendor)
    
    log_audit(
        actor_type="admin",
        actor_id=admin.id,
        action="vendor.updated",
        object_type="vendor",
        object_id=vendor.id,
        vendor_id=vendor.id,
        db=db,
        meta=changes
    )
    
    return {
        "id": vendor.id,
        "slug": vendor.slug,
        "name": vendor.name,
        "status": vendor.status.value,
        "updated_at": vendor.updated_at.isoformat()
    }


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(
    vendor_id: int,
    hard_delete: bool = Query(False),
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Delete vendor (soft delete by default)."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    if hard_delete:
        # Hard delete - remove all related data
        db.delete(vendor)
        action = "vendor.deleted_hard"
    else:
        # Soft delete
        vendor.deleted_at = datetime.utcnow()
        vendor.status = VendorStatus.DELETED
        action = "vendor.deleted_soft"
    
    db.commit()
    
    log_audit(
        actor_type="admin",
        actor_id=admin.id,
        action=action,
        object_type="vendor",
        object_id=vendor_id,
        db=db,
        meta={"hard_delete": hard_delete}
    )
    
    return {"message": "Vendor deleted successfully"}


# ========== QUOTA MANAGEMENT ==========

@router.post("/vendors/{vendor_id}/quotas", response_model=Dict[str, Any])
async def create_quota(
    vendor_id: int,
    quota_data: QuotaAllocationCreate,
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Create quota allocation for vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    quota = QuotaAllocation(
        vendor_id=vendor_id,
        resource_type=ResourceType(quota_data.resource_type),
        allocated_amount=quota_data.allocated_amount,
        used_amount=0.0,
        period_start=quota_data.period_start,
        period_end=quota_data.period_end,
        billing_cycle=quota_data.billing_cycle,
        soft_limit=quota_data.soft_limit,
        overdraft_allowed=quota_data.overdraft_allowed
    )
    db.add(quota)
    db.commit()
    db.refresh(quota)
    
    log_audit(
        actor_type="admin",
        actor_id=admin.id,
        action="quota.created",
        object_type="quota",
        object_id=quota.id,
        vendor_id=vendor_id,
        db=db,
        meta={
            "resource_type": quota_data.resource_type,
            "allocated_amount": quota_data.allocated_amount
        }
    )
    
    return {
        "id": quota.id,
        "resource_type": quota.resource_type.value,
        "allocated_amount": float(quota.allocated_amount),
        "used_amount": float(quota.used_amount),
        "period_start": quota.period_start.isoformat(),
        "period_end": quota.period_end.isoformat()
    }


@router.post("/vendors/{vendor_id}/credits/adjust", response_model=Dict[str, Any])
async def adjust_credits(
    vendor_id: int,
    adjustment: CreditAdjustment,
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Adjust vendor credit balance."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    old_balance = float(vendor.credit_balance)
    vendor.credit_balance = old_balance + adjustment.amount
    vendor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vendor)
    
    log_audit(
        actor_type="admin",
        actor_id=admin.id,
        action="credits.adjusted",
        object_type="vendor",
        object_id=vendor_id,
        vendor_id=vendor_id,
        db=db,
        meta={
            "old_balance": old_balance,
            "adjustment": adjustment.amount,
            "new_balance": float(vendor.credit_balance),
            "reason": adjustment.reason
        }
    )
    
    return {
        "vendor_id": vendor_id,
        "old_balance": old_balance,
        "adjustment": adjustment.amount,
        "new_balance": float(vendor.credit_balance),
        "reason": adjustment.reason
    }


# ========== MODEL ASSIGNMENT ==========

@router.post("/vendors/{vendor_id}/models/assign", response_model=Dict[str, Any])
async def assign_model(
    vendor_id: int,
    assignment: ModelAssignmentCreate,
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Assign model to vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    model = db.query(Model).filter(Model.id == assignment.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check if assignment exists
    existing = db.query(VendorModelAssignment).filter(
        VendorModelAssignment.vendor_id == vendor_id,
        VendorModelAssignment.model_id == assignment.model_id
    ).first()
    
    if existing:
        # Update existing
        existing.is_default = assignment.is_default
        existing.max_concurrency = assignment.max_concurrency
        existing.max_tokens_per_request = assignment.max_tokens_per_request
        existing.enabled = assignment.enabled
        existing.priority_order = assignment.priority_order
        existing.updated_at = datetime.utcnow()
        assignment_id = existing.id
    else:
        # Create new
        new_assignment = VendorModelAssignment(
            vendor_id=vendor_id,
            model_id=assignment.model_id,
            is_default=assignment.is_default,
            max_concurrency=assignment.max_concurrency,
            max_tokens_per_request=assignment.max_tokens_per_request,
            enabled=assignment.enabled,
            priority_order=assignment.priority_order
        )
        db.add(new_assignment)
        assignment_id = new_assignment.id
    
    # If this is default, unset other defaults
    if assignment.is_default:
        db.query(VendorModelAssignment).filter(
            VendorModelAssignment.vendor_id == vendor_id,
            VendorModelAssignment.model_id != assignment.model_id
        ).update({"is_default": False})
    
    db.commit()
    
    log_audit(
        actor_type="admin",
        actor_id=admin.id,
        action="model.assigned",
        object_type="vendor_model_assignment",
        object_id=assignment_id,
        vendor_id=vendor_id,
        db=db,
        meta={
            "model_id": assignment.model_id,
            "is_default": assignment.is_default,
            "enabled": assignment.enabled
        }
    )
    
    return {
        "vendor_id": vendor_id,
        "model_id": assignment.model_id,
        "is_default": assignment.is_default,
        "enabled": assignment.enabled
    }


# ========== USAGE ANALYTICS ==========

@router.get("/vendors/{vendor_id}/usage", response_model=Dict[str, Any])
async def get_vendor_usage(
    vendor_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Get vendor usage analytics."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.deleted_at.is_(None)).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily usage breakdown
    daily_usage = db.query(
        func.date(UsageRecord.timestamp).label("date"),
        UsageRecord.resource_type,
        func.sum(UsageRecord.amount).label("total")
    ).filter(
        UsageRecord.vendor_id == vendor_id,
        UsageRecord.timestamp >= start_date
    ).group_by(
        func.date(UsageRecord.timestamp),
        UsageRecord.resource_type
    ).order_by(desc("date")).all()
    
    # Total usage by resource type
    total_usage = db.query(
        UsageRecord.resource_type,
        func.sum(UsageRecord.amount).label("total"),
        func.sum(UsageRecord.cost).label("total_cost")
    ).filter(
        UsageRecord.vendor_id == vendor_id,
        UsageRecord.timestamp >= start_date
    ).group_by(UsageRecord.resource_type).all()
    
    return {
        "vendor_id": vendor_id,
        "period_days": days,
        "start_date": start_date.isoformat(),
        "daily_usage": [
            {
                "date": str(d.date),
                "resource_type": d.resource_type.value,
                "total": float(d.total)
            }
            for d in daily_usage
        ],
        "total_usage": {
            u.resource_type.value: {
                "amount": float(u.total),
                "cost": float(u.total_cost or 0)
            }
            for u in total_usage
        }
    }


# ========== AUDIT LOGS ==========

@router.get("/audit-logs", response_model=Dict[str, Any])
async def get_audit_logs(
    vendor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db_session),
    admin: Admin = Depends(get_current_super_admin)
):
    """Get audit logs with filters."""
    query = db.query(AuditLog)
    
    if vendor_id:
        query = query.filter(AuditLog.vendor_id == vendor_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if actor_type:
        query = query.filter(AuditLog.actor_type == actor_type)
    
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "actor_type": log.actor_type.value,
                "actor_id": log.actor_id,
                "vendor_id": log.vendor_id,
                "action": log.action,
                "object_type": log.object_type,
                "object_id": log.object_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
                "meta": log.meta
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }

