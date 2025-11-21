"""
Vendor-specific API endpoints for separate frontend integration.
These endpoints are designed for vendors to integrate their own frontends.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from backend.config.database import get_db_session
from backend.models.saas_models import Vendor, ChatSession, ChatMessage, User, MessageSender
from backend.middleware.auth import get_current_user_or_vendor
from backend.middleware.tenant import get_vendor_from_request, require_vendor
from fastapi import Request

router = APIRouter(prefix="/vendor-api", tags=["vendor-api"])


# Request/Response models
class ChatMessageRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    response: str
    chat_id: str
    suggestions: Optional[List[str]] = None


class ChatHistoryResponse(BaseModel):
    chat_id: str
    messages: List[Dict[str, Any]]
    total_messages: int


class VendorInfoResponse(BaseModel):
    vendor_id: int
    vendor_slug: str
    vendor_name: str
    company_name: Optional[str]
    status: str
    config: Optional[Dict[str, Any]] = None


# ========== VENDOR INFO ==========

@router.get("/info", response_model=VendorInfoResponse)
async def get_vendor_info(
    request: Request,
    db: Session = Depends(get_db_session),
    user_vendor: tuple = Depends(get_current_user_or_vendor)
):
    """Get vendor information for the authenticated vendor."""
    user, vendor = user_vendor
    
    # If no vendor from token, try to get from request (API key, etc.)
    if not vendor:
        vendor = get_vendor_from_request(request, db)
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vendor authentication required"
        )
    
    # Load vendor config
    config = None
    try:
        from backend.utils.unified_config_manager import UnifiedConfigManager
        config_manager = UnifiedConfigManager()
        config = config_manager.get_vendor_config(vendor.slug)
    except Exception as e:
        logger.warning(f"Could not load config for vendor {vendor.slug}: {e}")
    
    return VendorInfoResponse(
        vendor_id=vendor.id,
        vendor_slug=vendor.slug,
        vendor_name=vendor.name,
        company_name=vendor.company_name,
        status=vendor.status.value,
        config=config
    )


# ========== CHAT ENDPOINTS ==========

@router.post("/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request_data: ChatMessageRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    user_vendor: tuple = Depends(get_current_user_or_vendor)
):
    """Send a chat message (vendor-specific endpoint)."""
    user, vendor = user_vendor
    
    # If no vendor from token, try to get from request
    if not vendor:
        vendor = get_vendor_from_request(request, db)
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vendor authentication required"
        )
    
    # Require active vendor
    require_vendor(request, db)
    
    # Get or create chat session
    chat_session = None
    if request_data.chat_id:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_uuid == request_data.chat_id,
            ChatSession.vendor_id == vendor.id
        ).first()
    
    if not chat_session:
        import uuid
        chat_session = ChatSession(
            vendor_id=vendor.id,
            user_id=user.id if user else None,
            session_uuid=str(uuid.uuid4()),
            status="open"
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
    
    # Get or create user
    user_obj = user
    if not user_obj and request_data.user_id:
        user_obj = db.query(User).filter(
            User.vendor_id == vendor.id,
            User.email == request_data.user_id  # Using email as user_id for simplicity
        ).first()
    
    # Save user message
    user_message = ChatMessage(
        session_id=chat_session.id,
        vendor_id=vendor.id,
        sender=MessageSender.USER,
        role="user",
        content=request_data.message
    )
    db.add(user_message)
    db.commit()
    
    # Call chatbot service
    try:
        from backend.services.chatbot_service import ChatbotService
        chatbot = ChatbotService()
        
        # Prepare context
        context = {
            "vendor_id": vendor.slug,
            "chat_id": chat_session.session_uuid,
            "user_id": user_obj.id if user_obj else None
        }
        
        # Get response
        response_data = await chatbot.process_message(
            message=request_data.message,
            chat_id=chat_session.session_uuid,
            vendor_id=vendor.slug,
            user_id=str(user_obj.id) if user_obj else None
        )
        
        # Save bot response
        bot_message = ChatMessage(
            session_id=chat_session.id,
            vendor_id=vendor.id,
            sender=MessageSender.BOT,
            role="assistant",
            content=response_data.get("response", "")
        )
        db.add(bot_message)
        db.commit()
        
        return ChatMessageResponse(
            response=response_data.get("response", ""),
            chat_id=chat_session.session_uuid,
            suggestions=response_data.get("suggestions")
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/chat/history/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    chat_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    user_vendor: tuple = Depends(get_current_user_or_vendor)
):
    """Get chat history for a specific chat."""
    user, vendor = user_vendor
    
    if not vendor:
        vendor = get_vendor_from_request(request, db)
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vendor authentication required"
        )
    
    chat_session = db.query(ChatSession).filter(
        ChatSession.session_uuid == chat_id,
        ChatSession.vendor_id == vendor.id
    ).first()
    
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == chat_session.id
    ).order_by(ChatMessage.created_at).all()
    
    messages_data = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]
    
    return ChatHistoryResponse(
        chat_id=chat_id,
        messages=messages_data,
        total_messages=len(messages_data)
    )


@router.get("/chat/sessions")
async def list_chat_sessions(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session),
    user_vendor: tuple = Depends(get_current_user_or_vendor)
):
    """List chat sessions for the vendor."""
    user, vendor = user_vendor
    
    if not vendor:
        vendor = get_vendor_from_request(request, db)
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vendor authentication required"
        )
    
    sessions = db.query(ChatSession).filter(
        ChatSession.vendor_id == vendor.id
    ).order_by(ChatSession.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "sessions": [
            {
                "chat_id": session.session_uuid,
                "title": session.title,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "message_count": len(session.messages)
            }
            for session in sessions
        ],
        "total": db.query(ChatSession).filter(ChatSession.vendor_id == vendor.id).count()
    }


@router.get("/endpoints")
async def get_vendor_endpoints(
    request: Request,
    db: Session = Depends(get_db_session),
    user_vendor: tuple = Depends(get_current_user_or_vendor)
):
    """Get available API endpoints for the vendor."""
    user, vendor = user_vendor
    
    if not vendor:
        vendor = get_vendor_from_request(request, db)
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vendor authentication required"
        )
    
    base_url = str(request.base_url).rstrip("/")
    
    return {
        "vendor_slug": vendor.slug,
        "base_url": base_url,
        "endpoints": {
            "info": f"{base_url}/api/v1/vendor-api/info",
            "send_message": f"{base_url}/api/v1/vendor-api/chat/message",
            "chat_history": f"{base_url}/api/v1/vendor-api/chat/history/{{chat_id}}",
            "list_sessions": f"{base_url}/api/v1/vendor-api/chat/sessions",
            "endpoints": f"{base_url}/api/v1/vendor-api/endpoints"
        },
        "authentication": {
            "type": "Bearer Token",
            "header": "Authorization: Bearer <token>",
            "note": "Use vendor admin login token or API key"
        }
    }

