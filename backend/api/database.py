"""
Database management API endpoints.
Provides access to view and manage all database tables.
Uses SaaS models for multi-tenant support.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc
from typing import Optional, List, Dict, Any
from backend.config.database import get_db_session
from backend.models.saas_models import (
    Vendor, User, ChatSession, ChatMessage, KnowledgeBase, KBDocument,
    UsageRecord, Model, VendorModelAssignment, QuotaAllocation, BillingPlan,
    Invoice, Payment, APIKey, AuditLog, ResourceType
)
from loguru import logger
from datetime import datetime, timedelta

router = APIRouter(prefix="/database", tags=["database"])


def get_db():
    """Dependency for database session."""
    db = next(get_db_session())
    try:
        yield db
    finally:
        db.close()


@router.get("/stats")
async def get_database_stats(
    vendor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get database statistics for all tables. Can be filtered by vendor_id."""
    try:
        # Base queries
        users_query = db.query(User)
        chats_query = db.query(ChatSession)
        messages_query = db.query(ChatMessage)
        usage_query = db.query(UsageRecord)
        
        # Filter by vendor if provided
        if vendor_id:
            users_query = users_query.filter(User.vendor_id == vendor_id)
            chats_query = chats_query.filter(ChatSession.vendor_id == vendor_id)
            messages_query = messages_query.filter(ChatMessage.vendor_id == vendor_id)
            usage_query = usage_query.filter(UsageRecord.vendor_id == vendor_id)
        
        stats = {
            "vendors": db.query(Vendor).count(),
            "users": users_query.count(),
            "chats": chats_query.count(),
            "messages": messages_query.count(),
            "knowledge_bases": db.query(KnowledgeBase).count() if not vendor_id else db.query(KnowledgeBase).filter(KnowledgeBase.vendor_id == vendor_id).count(),
            "kb_documents": db.query(KBDocument).count() if not vendor_id else db.query(KBDocument).filter(KBDocument.vendor_id == vendor_id).count(),
            "token_usage": usage_query.count(),
            "models": db.query(Model).count(),
        }
        
        # Calculate total tokens and credits from usage records
        token_usage_records = usage_query.filter(UsageRecord.resource_type == ResourceType.TOKENS).all()
        total_tokens = sum(float(record.amount) for record in token_usage_records)
        total_credits = sum(float(record.cost) for record in token_usage_records)
        
        stats["total_tokens"] = int(total_tokens)
        stats["total_credits"] = float(total_credits)
        
        # Calculate averages
        chat_count = stats["chats"]
        message_count = stats["messages"]
        stats["avg_messages_per_chat"] = round(message_count / chat_count, 2) if chat_count > 0 else 0
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_messages = messages_query.filter(ChatMessage.created_at >= yesterday).count()
        recent_chats = chats_query.filter(ChatSession.created_at >= yesterday).count()
        recent_users = users_query.filter(User.created_at >= yesterday).count()
        
        stats["recent_messages_24h"] = recent_messages
        stats["recent_chats_24h"] = recent_chats
        stats["recent_users_24h"] = recent_users
        
        # Last 7 days activity
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_messages = messages_query.filter(ChatMessage.created_at >= week_ago).count()
        week_chats = chats_query.filter(ChatSession.created_at >= week_ago).count()
        
        stats["messages_7d"] = week_messages
        stats["chats_7d"] = week_chats
        
        # Average tokens per usage
        token_usage_count = stats["token_usage"]
        stats["avg_tokens_per_usage"] = round(total_tokens / token_usage_count, 2) if token_usage_count > 0 else 0
        
        # Get most recent activity
        latest_message = messages_query.order_by(desc(ChatMessage.created_at)).first()
        latest_chat = chats_query.order_by(desc(ChatSession.created_at)).first()
        
        stats["latest_message_time"] = latest_message.created_at.isoformat() if latest_message else None
        stats["latest_chat_time"] = latest_chat.created_at.isoformat() if latest_chat else None
        
        return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def get_tables_list():
    """Get list of all database tables."""
    return {
        "tables": [
            {"name": "vendors", "description": "Vendor/tenant accounts"},
            {"name": "users", "description": "User accounts"},
            {"name": "chat_sessions", "description": "Chat sessions"},
            {"name": "chat_messages", "description": "Chat messages"},
            {"name": "knowledge_bases", "description": "Knowledge bases per vendor"},
            {"name": "kb_documents", "description": "Documents in knowledge bases"},
            {"name": "usage_records", "description": "Usage tracking (tokens, messages, etc.)"},
            {"name": "models", "description": "LLM model registry"},
            {"name": "quota_allocations", "description": "Quota allocations per vendor"},
            {"name": "billing_plans", "description": "Billing plan definitions"},
            {"name": "invoices", "description": "Invoices"},
            {"name": "payments", "description": "Payment records"},
            {"name": "api_keys", "description": "API keys for vendor access"},
            {"name": "audit_logs", "description": "Audit trail"}
        ]
    }


@router.get("/table/{table_name}")
async def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    vendor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get data from a specific table. Can be filtered by vendor_id."""
    try:
        # Map table names to SaaS models
        table_map = {
            "vendors": Vendor,
            "users": User,
            "chat_sessions": ChatSession,
            "chat_messages": ChatMessage,
            "knowledge_bases": KnowledgeBase,
            "kb_documents": KBDocument,
            "usage_records": UsageRecord,
            "models": Model,
            "quota_allocations": QuotaAllocation,
            "billing_plans": BillingPlan,
            "invoices": Invoice,
            "payments": Payment,
            "api_keys": APIKey,
            "audit_logs": AuditLog
        }
        
        if table_name not in table_map:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        model = table_map[table_name]
        query = db.query(model)
        
        # Filter by vendor if provided and table has vendor_id
        if vendor_id and hasattr(model, 'vendor_id'):
            query = query.filter(model.vendor_id == vendor_id)
        
        # Apply search if provided
        if search:
            # Basic search - search in string/text columns
            if table_name == "vendors":
                query = query.filter(
                    (Vendor.slug.ilike(f"%{search}%")) |
                    (Vendor.name.ilike(f"%{search}%")) |
                    (Vendor.company_name.ilike(f"%{search}%"))
                )
            elif table_name == "users":
                query = query.filter(User.email.ilike(f"%{search}%") if hasattr(User, 'email') else False)
            elif table_name == "chat_sessions":
                query = query.filter(
                    (ChatSession.session_uuid.ilike(f"%{search}%")) |
                    (ChatSession.title.ilike(f"%{search}%") if ChatSession.title else False)
                )
            elif table_name == "chat_messages":
                query = query.filter(ChatMessage.content.ilike(f"%{search}%"))
            elif table_name == "knowledge_bases":
                query = query.filter(
                    (KnowledgeBase.name.ilike(f"%{search}%")) |
                    (KnowledgeBase.description.ilike(f"%{search}%") if KnowledgeBase.description else False)
                )
            elif table_name == "kb_documents":
                query = query.filter(
                    (KBDocument.title.ilike(f"%{search}%")) |
                    (KBDocument.content.ilike(f"%{search}%"))
                )
            elif table_name == "models":
                query = query.filter(
                    (Model.name.ilike(f"%{search}%")) |
                    (Model.provider.ilike(f"%{search}%"))
                )
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        results = query.order_by(desc(model.id)).offset(offset).limit(limit).all()
        
        # Convert to dict
        data = []
        for row in results:
            row_dict = {}
            for column in model.__table__.columns:
                value = getattr(row, column.name)
                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()
                # Handle JSON columns
                elif isinstance(value, dict) or isinstance(value, list):
                    value = value
                # Handle Enum types
                elif hasattr(value, 'value'):
                    value = value.value
                row_dict[column.name] = value
            data.append(row_dict)
        
        return {
            "table_name": table_name,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": data,
            "columns": [col.name for col in model.__table__.columns]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/{table_name}/count")
async def get_table_count(
    table_name: str,
    vendor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get count of records in a table. Can be filtered by vendor_id."""
    try:
        table_map = {
            "vendors": Vendor,
            "users": User,
            "chat_sessions": ChatSession,
            "chat_messages": ChatMessage,
            "knowledge_bases": KnowledgeBase,
            "kb_documents": KBDocument,
            "usage_records": UsageRecord,
            "models": Model,
            "quota_allocations": QuotaAllocation,
            "billing_plans": BillingPlan,
            "invoices": Invoice,
            "payments": Payment,
            "api_keys": APIKey,
            "audit_logs": AuditLog
        }
        
        if table_name not in table_map:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        model = table_map[table_name]
        query = db.query(model)
        
        # Filter by vendor if provided
        if vendor_id and hasattr(model, 'vendor_id'):
            query = query.filter(model.vendor_id == vendor_id)
        
        count = query.count()
        return {"table_name": table_name, "count": count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/full")
async def get_user_full_data(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get full data for a user including all chats, messages, and usage."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get all chat sessions for this user
        # Note: ChatSession now uses chat_user_id, not user_id
        # This endpoint may need to be updated to use chat_users
        from backend.models.saas_models import ChatUser
        chat_user = db.query(ChatUser).filter(ChatUser.id == user_id).first()
        if chat_user:
            chats = db.query(ChatSession).filter(ChatSession.chat_user_id == chat_user.id).all()
        else:
            chats = []
        
        # Get all messages for user's chats
        session_ids = [chat.id for chat in chats]
        messages = db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).all() if session_ids else []
        
        # Get usage records
        usage_records = db.query(UsageRecord).filter(UsageRecord.user_id == user_id).all()
        
        # Calculate totals
        total_tokens = sum(float(record.amount) for record in usage_records if record.resource_type == ResourceType.TOKENS)
        total_credits = sum(float(record.cost) for record in usage_records)
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "vendor_id": user.vendor_id,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            },
            "chats": [
                {
                    "id": chat.id,
                    "session_uuid": chat.session_uuid,
                    "title": chat.title,
                    "vendor_id": chat.vendor_id,
                    "status": chat.status.value if hasattr(chat.status, 'value') else str(chat.status),
                    "total_tokens_used": int(chat.total_tokens_used) if chat.total_tokens_used else 0,
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                    "updated_at": chat.updated_at.isoformat() if chat.updated_at else None
                }
                for chat in chats
            ],
            "messages_count": len(messages),
            "usage_records_count": len(usage_records),
            "total_tokens": int(total_tokens),
            "total_credits": float(total_credits)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user full data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_uuid}/full")
async def get_chat_full_data(
    session_uuid: str,
    db: Session = Depends(get_db)
):
    """Get full data for a chat session including all messages and usage."""
    try:
        chat = db.query(ChatSession).filter(ChatSession.session_uuid == session_uuid).first()
        if not chat:
            raise HTTPException(status_code=404, detail=f"Chat session {session_uuid} not found")
        
        # Get all messages for this session
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == chat.id).order_by(ChatMessage.created_at).all()
        
        # Get usage records for this session
        usage_records = db.query(UsageRecord).filter(UsageRecord.session_id == chat.id).all()
        
        # Calculate totals
        total_tokens = sum(float(record.amount) for record in usage_records if record.resource_type == ResourceType.TOKENS)
        total_credits = sum(float(record.cost) for record in usage_records)
        
        return {
            "chat": {
                "id": chat.id,
                "session_uuid": chat.session_uuid,
                "user_id": chat.user_id,
                "vendor_id": chat.vendor_id,
                "title": chat.title,
                "status": chat.status.value if hasattr(chat.status, 'value') else str(chat.status),
                "total_tokens_used": int(chat.total_tokens_used) if chat.total_tokens_used else 0,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "sender": msg.sender.value if hasattr(msg.sender, 'value') else str(msg.sender),
                    "tokens_used": int(msg.tokens_used) if msg.tokens_used else 0,
                    "model_id": msg.model_id,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ],
            "usage_records": [
                {
                    "id": record.id,
                    "resource_type": record.resource_type.value if hasattr(record.resource_type, 'value') else str(record.resource_type),
                    "amount": float(record.amount),
                    "cost": float(record.cost),
                    "model_id": record.model_id,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None
                }
                for record in usage_records
            ],
            "stats": {
                "total_messages": len(messages),
                "total_tokens": int(total_tokens),
                "total_credits": float(total_credits)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat full data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

