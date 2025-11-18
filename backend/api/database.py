"""
Database management API endpoints.
Provides access to view and manage all database tables.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional, List, Dict, Any
from backend.models.database import get_session_local
from backend.models.database import (
    User, Chat, Message, ConversationMemory, TokenUsage, ModelConfig
)
from loguru import logger
from datetime import datetime

SessionLocal = get_session_local()
router = APIRouter(prefix="/database", tags=["database"])


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Get database statistics for all tables."""
    try:
        from datetime import datetime, timedelta
        
        stats = {
            "users": db.query(User).count(),
            "chats": db.query(Chat).count(),
            "messages": db.query(Message).count(),
            "conversation_memory": db.query(ConversationMemory).count(),
            "token_usage": db.query(TokenUsage).count(),
            "model_configs": db.query(ModelConfig).count()
        }
        
        # Calculate total tokens and credits
        total_tokens = db.query(func.sum(TokenUsage.tokens_total)).scalar() or 0
        total_credits = db.query(func.sum(TokenUsage.credits_used)).scalar() or 0
        
        stats["total_tokens"] = total_tokens
        stats["total_credits"] = total_credits
        
        # Calculate averages
        chat_count = stats["chats"]
        message_count = stats["messages"]
        stats["avg_messages_per_chat"] = round(message_count / chat_count, 2) if chat_count > 0 else 0
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_messages = db.query(Message).filter(Message.created_at >= yesterday).count()
        recent_chats = db.query(Chat).filter(Chat.created_at >= yesterday).count()
        recent_users = db.query(User).filter(User.created_at >= yesterday).count()
        
        stats["recent_messages_24h"] = recent_messages
        stats["recent_chats_24h"] = recent_chats
        stats["recent_users_24h"] = recent_users
        
        # Last 7 days activity
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_messages = db.query(Message).filter(Message.created_at >= week_ago).count()
        week_chats = db.query(Chat).filter(Chat.created_at >= week_ago).count()
        
        stats["messages_7d"] = week_messages
        stats["chats_7d"] = week_chats
        
        # Average tokens per message
        token_usage_count = stats["token_usage"]
        stats["avg_tokens_per_usage"] = round(total_tokens / token_usage_count, 2) if token_usage_count > 0 else 0
        
        # Get most recent activity
        latest_message = db.query(Message).order_by(Message.created_at.desc()).first()
        latest_chat = db.query(Chat).order_by(Chat.created_at.desc()).first()
        
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
            {"name": "users", "description": "User accounts and credits"},
            {"name": "chats", "description": "Chat sessions"},
            {"name": "messages", "description": "Chat messages"},
            {"name": "conversation_memory", "description": "Conversation context and memory"},
            {"name": "token_usage", "description": "Token and credit usage tracking"},
            {"name": "model_configs", "description": "LLM model configurations"}
        ]
    }


@router.get("/table/{table_name}")
async def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get data from a specific table."""
    try:
        # Map table names to models
        table_map = {
            "users": User,
            "chats": Chat,
            "messages": Message,
            "conversation_memory": ConversationMemory,
            "token_usage": TokenUsage,
            "model_configs": ModelConfig
        }
        
        if table_name not in table_map:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        model = table_map[table_name]
        query = db.query(model)
        
        # Apply search if provided
        if search:
            # Basic search - search in string/text columns
            if table_name == "users":
                query = query.filter(User.user_id.contains(search))
            elif table_name == "chats":
                query = query.filter(
                    (Chat.chat_id.contains(search)) |
                    (Chat.user_id.contains(search)) |
                    (Chat.title.contains(search) if Chat.title else False)
                )
            elif table_name == "messages":
                query = query.filter(
                    (Message.content.contains(search)) |
                    (Message.chat_id.contains(search)) |
                    (Message.message_id.contains(search))
                )
            elif table_name == "conversation_memory":
                query = query.filter(
                    (ConversationMemory.chat_id.contains(search)) |
                    (ConversationMemory.context_summary.contains(search) if ConversationMemory.context_summary else False)
                )
            elif table_name == "token_usage":
                query = query.filter(
                    (TokenUsage.user_id.contains(search)) |
                    (TokenUsage.chat_id.contains(search)) |
                    (TokenUsage.model.contains(search))
                )
            elif table_name == "model_configs":
                query = query.filter(
                    (ModelConfig.model_name.contains(search)) |
                    (ModelConfig.provider.contains(search))
                )
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        results = query.order_by(model.id.desc()).offset(offset).limit(limit).all()
        
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
    db: Session = Depends(get_db)
):
    """Get count of records in a table."""
    try:
        table_map = {
            "users": User,
            "chats": Chat,
            "messages": Message,
            "conversation_memory": ConversationMemory,
            "token_usage": TokenUsage,
            "model_configs": ModelConfig
        }
        
        if table_name not in table_map:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        count = db.query(table_map[table_name]).count()
        return {"table_name": table_name, "count": count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/full")
async def get_user_full_data(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get full data for a user including all chats, messages, and usage."""
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get all chats
        chats = db.query(Chat).filter(Chat.user_id == user_id).all()
        
        # Get all messages for user's chats
        chat_ids = [chat.chat_id for chat in chats]
        messages = db.query(Message).filter(Message.chat_id.in_(chat_ids)).all() if chat_ids else []
        
        # Get token usage
        token_usage = db.query(TokenUsage).filter(TokenUsage.user_id == user_id).all()
        
        # Get memory
        memory = db.query(ConversationMemory).filter(ConversationMemory.chat_id.in_(chat_ids)).all() if chat_ids else []
        
        return {
            "user": {
                "user_id": user.user_id,
                "vendor_id": user.vendor_id,
                "credits": user.credits,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat()
            },
            "chats": [
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat()
                }
                for chat in chats
            ],
            "messages_count": len(messages),
            "token_usage_count": len(token_usage),
            "memory_count": len(memory),
            "total_tokens": sum(usage.tokens_total for usage in token_usage),
            "total_credits": sum(usage.credits_used for usage in token_usage)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user full data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{chat_id}/full")
async def get_chat_full_data(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Get full data for a chat including all messages and memory."""
    try:
        chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")
        
        # Get all messages
        messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
        
        # Get memory
        memory = db.query(ConversationMemory).filter(ConversationMemory.chat_id == chat_id).first()
        
        # Get token usage
        token_usage = db.query(TokenUsage).filter(TokenUsage.chat_id == chat_id).all()
        
        return {
            "chat": {
                "chat_id": chat.chat_id,
                "user_id": chat.user_id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat()
            },
            "messages": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "tokens_used": msg.tokens_used,
                    "credits_used": msg.credits_used,
                    "model_used": msg.model_used,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ],
            "memory": {
                "context_summary": memory.context_summary if memory else None,
                "entities": memory.entities if memory else {},
                "intent_history": memory.intent_history if memory else [],
                "turn_count": memory.turn_count if memory else 0,
                "updated_at": memory.updated_at.isoformat() if memory else None
            } if memory else None,
            "token_usage": [
                {
                    "model": usage.model,
                    "tokens_input": usage.tokens_input,
                    "tokens_output": usage.tokens_output,
                    "tokens_total": usage.tokens_total,
                    "credits_used": usage.credits_used,
                    "created_at": usage.created_at.isoformat()
                }
                for usage in token_usage
            ],
            "stats": {
                "total_messages": len(messages),
                "total_tokens": sum(usage.tokens_total for usage in token_usage),
                "total_credits": sum(usage.credits_used for usage in token_usage)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat full data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

