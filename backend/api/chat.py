"""
Chat API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.config.database import get_db_session
from backend.models.saas_models import ChatSession, ChatMessage, User, MessageSender
from backend.services.chatbot_service import ChatbotService
from loguru import logger
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])


def get_db():
    """Dependency for database session."""
    db = next(get_db_session())
    try:
        yield db
    finally:
        pass


class ChatMessageRequest(BaseModel):
    """Request model for chat message."""
    user_id: str
    chat_id: Optional[str] = None
    message: str
    vendor_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""
    response: str
    chat_id: str
    message_id: str
    tokens_used: int
    credits_used: int
    model_used: str
    retrieved_chunks: int
    is_domain_relevant: bool
    suggestions: Optional[List[str]] = []


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """Send a message to the chatbot."""
    try:
        from backend.config import get_settings
        from backend.models.saas_models import Vendor
        settings = get_settings()
        
        # Use provided vendor_id or default
        effective_vendor_id = request.vendor_id or settings.default_vendor_id
        
        # Get vendor by slug
        vendor = None
        if effective_vendor_id:
            vendor = db.query(Vendor).filter(
                Vendor.slug == effective_vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            if not vendor:
                raise HTTPException(status_code=404, detail=f"Vendor {effective_vendor_id} not found")
        
        # Get or create user (for anonymous chatbot users, we don't require password)
        # Use a dummy password hash for anonymous chatbot users
        from backend.utils.auth import hash_password
        user_obj = db.query(User).filter(User.email == request.user_id).first()
        if not user_obj and vendor:
            # Create anonymous user with dummy password (for chatbot usage)
            # Use a random password hash that will never be used for login
            dummy_password_hash = hash_password("chatbot_anonymous_user_" + str(uuid.uuid4()))
            user_obj = User(
                vendor_id=vendor.id,
                email=request.user_id,
                name=request.user_id,
                password_hash=dummy_password_hash,
                is_active=True
            )
            db.add(user_obj)
            db.commit()
            db.refresh(user_obj)
        
        # Get or create chat session
        chat_session = None
        if request.chat_id:
            chat_session = db.query(ChatSession).filter(
                ChatSession.session_uuid == request.chat_id
            ).first()
        
        if not chat_session:
            chat_session = ChatSession(
                vendor_id=vendor.id if vendor else None,
                user_id=user_obj.id if user_obj else None,
                session_uuid=str(uuid.uuid4()),
                status="open"
            )
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
        
        # Save user message
        user_message = ChatMessage(
            session_id=chat_session.id,
            vendor_id=vendor.id if vendor else None,
            sender=MessageSender.USER,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()
        
        # Call chatbot service (db is optional now since API handles persistence)
        chatbot_service = ChatbotService(db=db, vendor_id=effective_vendor_id)
        result = await chatbot_service.process_message(
            user_id=str(user_obj.id) if user_obj else request.user_id,
            chat_id=chat_session.session_uuid,
            message=request.message,
            vendor_id=effective_vendor_id
        )
        
        # Save bot response
        bot_message = ChatMessage(
            session_id=chat_session.id,
            vendor_id=vendor.id if vendor else None,
            sender=MessageSender.BOT,
            role="assistant",
            content=result.get("response", "")
        )
        db.add(bot_message)
        
        # Create usage record for tokens used
        if vendor and result.get("tokens_used", 0) > 0:
            from backend.models.saas_models import UsageRecord, ResourceType, UsageSource
            from backend.models.saas_models import Model
            from datetime import datetime
            
            # Get model ID if model name is provided
            model_id = None
            if result.get("model_used"):
                # Model table uses 'code' field for model identifier
                model = db.query(Model).filter(
                    (Model.code == result.get("model_used")) | 
                    (Model.display_name == result.get("model_used"))
                ).first()
                if model:
                    model_id = model.id
            
            usage_record = UsageRecord(
                vendor_id=vendor.id,
                user_id=user_obj.id if user_obj else None,
                model_id=model_id,
                session_id=chat_session.id,
                resource_type=ResourceType.TOKENS,
                amount=float(result.get("tokens_used", 0)),
                source=UsageSource.API,
                cost=float(result.get("credits_used", 0)),
                timestamp=datetime.utcnow()
            )
            db.add(usage_record)
        
        db.commit()
        
        return ChatMessageResponse(
            response=result.get("response", ""),
            chat_id=chat_session.session_uuid,
            message_id=str(bot_message.id),
            tokens_used=result.get("tokens_used", 0),
            credits_used=result.get("credits_used", 0),
            model_used=result.get("model_used", ""),
            retrieved_chunks=result.get("retrieved_chunks", 0),
            is_domain_relevant=result.get("is_domain_relevant", True),
            suggestions=result.get("suggestions", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{chat_id}")
async def get_chat_history(
    chat_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get chat history."""
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_uuid == chat_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == chat_session.id
        ).order_by(
            ChatMessage.created_at.asc()
        ).limit(limit).all()
        
        return {
            "chat_id": chat_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{user_id}")
async def get_user_chats(
    user_id: str,
    vendor_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all chats for a user (vendor-aware)."""
    try:
        from backend.models.saas_models import Vendor
        
        # Get user by email
        user_obj = db.query(User).filter(User.email == user_id).first()
        if not user_obj:
            return {
                "user_id": user_id,
                "vendor_id": vendor_id,
                "chats": []
            }
        
        # Filter by user and vendor
        query = db.query(ChatSession).filter(ChatSession.user_id == user_obj.id)
        if vendor_id:
            vendor = db.query(Vendor).filter(Vendor.slug == vendor_id).first()
            if vendor:
                query = query.filter(ChatSession.vendor_id == vendor.id)
        
        chats = query.order_by(ChatSession.created_at.desc()).all()
        
        return {
            "user_id": user_id,
            "vendor_id": vendor_id,
            "chats": [
                {
                    "chat_id": chat.session_uuid,
                    "title": chat.title or f"Chat {chat.id}",
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat() if chat.updated_at else chat.created_at.isoformat()
                }
                for chat in chats
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting user chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/clear/{chat_id}")
async def clear_chat_memory(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Clear conversation memory for a chat."""
    try:
        from backend.services.memory_service import MemoryService
        from backend.models.database import ConversationMemory
        
        memory_service = MemoryService(db)
        
        # Delete conversation memory
        memory = db.query(ConversationMemory).filter(
            ConversationMemory.chat_id == chat_id
        ).first()
        
        if memory:
            db.delete(memory)
            db.commit()
        
        return {
            "status": "success",
            "message": f"Memory cleared for chat {chat_id}"
        }
        
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/{chat_id}")
async def clear_chat_all(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Clear ALL data for a chat (messages, memory, everything)."""
    try:
        from backend.models.saas_models import UsageRecord
        
        # Get chat session
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_uuid == chat_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Delete all messages
        messages_deleted = db.query(ChatMessage).filter(
            ChatMessage.session_id == chat_session.id
        ).delete()
        
        # Delete token usage records
        token_usage_deleted = db.query(UsageRecord).filter(
            UsageRecord.chat_session_id == chat_session.id
        ).delete()
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"All data cleared for chat {chat_id}",
            "deleted": {
                "messages": messages_deleted,
                "token_usage": token_usage_deleted
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{chat_id}")
async def delete_chat(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Delete a chat completely (messages, token usage, temporary cache, and chat record)."""
    try:
        from backend.models.saas_models import UsageRecord
        from backend.services.cache_service import CacheService
        
        # Get chat session
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_uuid == chat_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Delete all messages
        messages_deleted = db.query(ChatMessage).filter(
            ChatMessage.session_id == chat_session.id
        ).delete()
        
        # Delete token usage records
        token_usage_deleted = db.query(UsageRecord).filter(
            UsageRecord.chat_session_id == chat_session.id
        ).delete()
        
        # Delete temporary cache entries
        cache_service = CacheService(db=db)
        temp_cache_deleted = cache_service.delete_temporary_cache_for_chat(chat_id)
        
        # Delete the chat session itself
        chat_deleted = db.query(ChatSession).filter(
            ChatSession.id == chat_session.id
        ).delete()
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Chat {chat_id} deleted successfully",
            "deleted": {
                "messages": messages_deleted,
                "token_usage": token_usage_deleted,
                "temporary_cache": temp_cache_deleted,
                "chat": chat_deleted > 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

