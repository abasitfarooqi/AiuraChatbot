"""
Chat API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.models.database import get_session_local
SessionLocal = get_session_local()
from backend.services.chatbot_service import ChatbotService
from loguru import logger

router = APIRouter(prefix="/chat", tags=["chat"])


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        import time
        from backend.config import get_settings
        settings = get_settings()
        
        # Use provided vendor_id or default
        effective_vendor_id = request.vendor_id or settings.default_vendor_id
        chatbot_service = ChatbotService(db, vendor_id=effective_vendor_id)
        
        # Generate chat_id if not provided
        chat_id = request.chat_id or f"chat_{request.user_id}_{int(time.time())}"
        
        result = await chatbot_service.process_message(
            user_id=request.user_id,
            chat_id=chat_id,
            message=request.message,
            vendor_id=effective_vendor_id
        )
        
        return ChatMessageResponse(
            response=result["response"],
            chat_id=result["chat_id"],
            message_id=result.get("message_id", ""),
            tokens_used=result.get("tokens_used", 0),
            credits_used=result.get("credits_used", 0),
            model_used=result.get("model_used", ""),
            retrieved_chunks=result.get("retrieved_chunks", 0),
            is_domain_relevant=result.get("is_domain_relevant", True),
            suggestions=result.get("suggestions", [])
        )
        
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
        from backend.models.database import Message
        
        messages = db.query(Message).filter(
            Message.chat_id == chat_id
        ).order_by(
            Message.created_at.asc()
        ).limit(limit).all()
        
        return {
            "chat_id": chat_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "tokens_used": msg.tokens_used
                }
                for msg in messages
            ]
        }
        
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
        from backend.models.database import Chat
        from backend.config import get_settings
        settings = get_settings()
        
        # Use provided vendor_id or default
        effective_vendor_id = vendor_id or settings.default_vendor_id
        
        # Filter by user_id and vendor_id
        query = db.query(Chat).filter(Chat.user_id == user_id)
        if effective_vendor_id:
            query = query.filter(Chat.vendor_id == effective_vendor_id)
        
        chats = query.order_by(Chat.updated_at.desc()).all()
        
        return {
            "user_id": user_id,
            "vendor_id": effective_vendor_id,
            "chats": [
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat()
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
        from backend.models.database import Message, ConversationMemory, Chat, TokenUsage
        
        # Delete all messages
        messages_deleted = db.query(Message).filter(
            Message.chat_id == chat_id
        ).delete()
        
        # Delete conversation memory
        memory_deleted = db.query(ConversationMemory).filter(
            ConversationMemory.chat_id == chat_id
        ).delete()
        
        # Delete token usage records
        token_usage_deleted = db.query(TokenUsage).filter(
            TokenUsage.chat_id == chat_id
        ).delete()
        
        # Optionally delete the chat record itself (uncomment if you want to delete chat too)
        # chat_deleted = db.query(Chat).filter(Chat.chat_id == chat_id).delete()
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"All data cleared for chat {chat_id}",
            "deleted": {
                "messages": messages_deleted,
                "memory": memory_deleted,
                "token_usage": token_usage_deleted
            }
        }
        
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{chat_id}")
async def delete_chat(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Delete a chat completely (messages, memory, token usage, and chat record)."""
    try:
        from backend.models.database import Message, ConversationMemory, Chat, TokenUsage
        
        # Delete all messages
        messages_deleted = db.query(Message).filter(
            Message.chat_id == chat_id
        ).delete()
        
        # Delete conversation memory
        memory_deleted = db.query(ConversationMemory).filter(
            ConversationMemory.chat_id == chat_id
        ).delete()
        
        # Delete token usage records
        token_usage_deleted = db.query(TokenUsage).filter(
            TokenUsage.chat_id == chat_id
        ).delete()
        
        # Delete the chat record itself
        chat_deleted = db.query(Chat).filter(Chat.chat_id == chat_id).delete()
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Chat {chat_id} deleted successfully",
            "deleted": {
                "messages": messages_deleted,
                "memory": memory_deleted,
                "token_usage": token_usage_deleted,
                "chat": chat_deleted > 0
            }
        }
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

