"""
Conversation Memory Service.
Manages per-user, per-chat conversation context and memory.
Dynamic and vendor-agnostic - all configuration from vendor config.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.models.saas_models import ChatMessage, ChatSession, ConversationMemory, Vendor
from backend.config import get_settings
from loguru import logger
from datetime import datetime

settings = get_settings()


class MemoryService:
    """Service for managing conversation memory and context."""
    
    def __init__(self, db: Session, vendor_id: Optional[str] = None):
        """Initialize memory service with database session and vendor ID."""
        self.db = db
        self.settings = settings
        self.vendor_id = vendor_id or settings.default_vendor_id
        self._load_memory_config()
    
    def _load_memory_config(self):
        """Load memory configuration from vendor-specific unified config."""
        try:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
            unified_config = config_manager.load_config()
            
            # Get memory config from chatbot_service section
            chatbot_config = unified_config.get("chatbot_service", {})
            self.memory_config = chatbot_config.get("memory", {})
            
            # Get entity extraction config
            self.entity_config = chatbot_config.get("entity_extraction", {})
            
            # Get topic detection config
            self.topic_config = chatbot_config.get("topic_detection", {})
            
            logger.debug(f"Memory config loaded for vendor {self.vendor_id}")
        except Exception as e:
            logger.warning(f"Error loading memory config for vendor {self.vendor_id}: {e}, using defaults")
            self.memory_config = {}
            self.entity_config = {}
            self.topic_config = {}
    
    def get_conversation_context(
        self,
        chat_id: str,
        max_turns: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation context for a chat.
        
        Args:
            chat_id: Chat session UUID (session_uuid from ChatSession)
            max_turns: Maximum number of turns to retrieve
        
        Returns:
            List of messages in format [{"role": "user", "content": "..."}, ...]
        """
        try:
            max_turns = max_turns or self.memory_config.get("max_turns", 20) or self.settings.memory_max_turns
            
            # First, find the ChatSession by session_uuid
            chat_session = self.db.query(ChatSession).filter(
                ChatSession.session_uuid == chat_id
            ).first()
            
            if not chat_session:
                logger.debug(f"Chat session {chat_id} not found")
                return []
            
            # Get recent messages for this chat session
            messages = self.db.query(ChatMessage).filter(
                ChatMessage.session_id == chat_session.id
            ).order_by(
                ChatMessage.created_at.desc()
            ).limit(max_turns * 2).all()  # *2 because we have user + assistant messages
            
            # Reverse to get chronological order
            messages = list(reversed(messages))
            
            # Format as conversation context
            context = []
            for msg in messages:
                context.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
    
    def get_or_create_memory(self, chat_id: str, chat_user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get or create conversation memory for a chat.
        
        Args:
            chat_id: Chat session UUID
            chat_user_id: Optional chat_user ID for chat_user-specific memory
            
        Returns:
            Dict with memory data
        """
        try:
            # Get vendor ID
            vendor = self.db.query(Vendor).filter(Vendor.slug == self.vendor_id).first()
            if not vendor:
                logger.warning(f"Vendor {self.vendor_id} not found")
                return self._get_default_memory(chat_id)
            
            vendor_id_int = vendor.id
            
            # Find chat session
            chat_session = self.db.query(ChatSession).filter(
                ChatSession.session_uuid == chat_id
            ).first()
            
            # Get chat_user_id from chat_session if not provided
            if not chat_user_id and chat_session:
                chat_user_id = chat_session.chat_user_id
            
            # Get or create memory (vendor + chat_id unique, but store chat_user_id for filtering)
            memory = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor_id_int,
                ConversationMemory.chat_id == chat_id
            ).first()
            
            if not memory:
                # Create new memory
                memory = ConversationMemory(
                    vendor_id=vendor_id_int,
                    chat_user_id=chat_user_id,
                    chat_id=chat_id,
                    session_id=chat_session.id if chat_session else None,
                    entities={},
                    intent_history=[],
                    topics=[],
                    turn_count=0,
                    context_summary=None,
                    is_active=True,
                    last_accessed_at=datetime.utcnow()
                )
                self.db.add(memory)
                self.db.commit()
                self.db.refresh(memory)
                logger.debug(f"Created new memory for chat {chat_id} (chat_user: {chat_user_id}, vendor: {vendor_id_int})")
            else:
                # Update chat_user_id if it changed
                if chat_user_id and memory.chat_user_id != chat_user_id:
                    memory.chat_user_id = chat_user_id
                # Update last accessed
                memory.last_accessed_at = datetime.utcnow()
                self.db.commit()
            
            return {
                "chat_id": chat_id,
                "chat_user_id": memory.chat_user_id,
                "entities": memory.entities or {},
                "intent_history": memory.intent_history or [],
                "topics": memory.topics or [],
                "turn_count": memory.turn_count,
                "context_summary": memory.context_summary,
                "memory_id": memory.id
            }
            
        except Exception as e:
            logger.error(f"Error getting or creating memory: {e}")
            return self._get_default_memory(chat_id)
    
    def _get_default_memory(self, chat_id: str) -> Dict[str, Any]:
        """Get default memory structure."""
        return {
            "chat_id": chat_id,
            "entities": {},
            "intent_history": [],
            "topics": [],
            "turn_count": 0,
            "context_summary": None
        }
    
    def update_memory(
        self,
        chat_id: str,
        entities: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
        topics: Optional[List[str]] = None,
        summary: Optional[str] = None,
        increment_turn: bool = True,
        chat_user_id: Optional[int] = None
    ):
        """
        Update conversation memory with new information.
        
        Args:
            chat_id: Chat session UUID
            entities: Extracted entities to update
            intent: Detected intent
            topics: Conversation topics
            summary: Context summary
            increment_turn: Whether to increment turn count
            chat_user_id: Optional chat_user ID
        """
        try:
            # Get vendor ID
            vendor = self.db.query(Vendor).filter(Vendor.slug == self.vendor_id).first()
            if not vendor:
                logger.warning(f"Vendor {self.vendor_id} not found")
                return
            
            vendor_id_int = vendor.id
            
            # Get chat_user_id from chat_session if not provided
            if not chat_user_id:
                chat_session = self.db.query(ChatSession).filter(
                    ChatSession.session_uuid == chat_id
                ).first()
                if chat_session:
                    chat_user_id = chat_session.chat_user_id
            
            # Get existing memory
            memory = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor_id_int,
                ConversationMemory.chat_id == chat_id
            ).first()
            
            if not memory:
                # Create if doesn't exist
                chat_session = self.db.query(ChatSession).filter(
                    ChatSession.session_uuid == chat_id
                ).first()
                
                memory = ConversationMemory(
                    vendor_id=vendor_id_int,
                    chat_user_id=chat_user_id,
                    chat_id=chat_id,
                    session_id=chat_session.id if chat_session else None,
                    entities={},
                    intent_history=[],
                    topics=[],
                    turn_count=0,
                    is_active=True
                )
                self.db.add(memory)
            else:
                # Update chat_user_id if it changed
                if chat_user_id and memory.chat_user_id != chat_user_id:
                    memory.chat_user_id = chat_user_id
            
            # Update entities
            if entities:
                current_entities = memory.entities or {}
                current_entities.update(entities)
                memory.entities = current_entities
            
            # Update intent history
            if intent:
                intent_history = memory.intent_history or []
                intent_history.append({
                    "intent": intent,
                    "timestamp": datetime.utcnow().isoformat()
                })
                # Keep only last N intents
                max_intents = self.memory_config.get("max_intent_history", 50)
                memory.intent_history = intent_history[-max_intents:]
            
            # Update topics
            if topics:
                current_topics = memory.topics or []
                # Add new topics (avoid duplicates)
                for topic in topics:
                    if topic not in current_topics:
                        current_topics.append(topic)
                # Keep only last N topics
                max_topics = self.memory_config.get("max_topics", 20)
                memory.topics = current_topics[-max_topics:]
            
            # Update summary
            if summary:
                memory.context_summary = summary
            
            # Increment turn count
            if increment_turn:
                memory.turn_count = (memory.turn_count or 0) + 1
            
            memory.last_accessed_at = datetime.utcnow()
            self.db.commit()
            logger.debug(f"Updated memory for chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            self.db.rollback()
    
    def extract_entities(self, query: str, retrieved_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Extract entities from query and retrieved chunks.
        Dynamic extraction based on vendor configuration.
        
        Args:
            query: User query
            retrieved_chunks: RAG chunks
            
        Returns:
            Dict of extracted entities
        """
        entities = {}
        query_lower = query.lower()
        
        # Get entity extraction config from vendor config
        entity_types = self.entity_config.get("entity_types", {})
        
        # Extract each entity type dynamically
        for entity_type, config in entity_types.items():
            keywords = config.get("keywords", [])
            patterns = config.get("patterns", [])
            
            # Check keywords
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    entities[entity_type] = keyword
                    break
            
            # Check patterns (regex patterns if needed)
            if not entities.get(entity_type) and patterns:
                import re
                for pattern in patterns:
                    match = re.search(pattern, query_lower)
                    if match:
                        entities[entity_type] = match.group(0)
                        break
        
        # Also extract from retrieved chunks if enabled
        if self.entity_config.get("extract_from_chunks", True) and retrieved_chunks:
            for chunk in retrieved_chunks[:3]:  # Check top 3 chunks
                content = chunk.get("content", "").lower()
                metadata = chunk.get("metadata", {})
                
                # Extract from chunk metadata
                for entity_type in entity_types.keys():
                    if not entities.get(entity_type):
                        # Check if chunk metadata contains entity
                        if entity_type in metadata:
                            entities[entity_type] = metadata[entity_type]
        
        return entities
    
    def should_summarize(self, chat_id: str) -> bool:
        """Check if conversation should be summarized."""
        if not self.memory_config.get("summary_enabled", False):
            return False
        
        try:
            vendor = self.db.query(Vendor).filter(Vendor.slug == self.vendor_id).first()
            if not vendor:
                return False
            
            memory = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor.id,
                ConversationMemory.chat_id == chat_id
            ).first()
            
            if not memory:
                return False
            
            threshold = self.memory_config.get("summary_threshold", 15)
            return memory.turn_count >= threshold
            
        except Exception as e:
            logger.debug(f"Error checking if should summarize: {e}")
            return False
    
    def create_summary(self, chat_id: str, messages: List[Dict[str, str]]) -> str:
        """
        Create summary of conversation.
        In production, this would use LLM to summarize.
        
        Args:
            chat_id: Chat session UUID
            messages: List of messages
            
        Returns:
            Summary string
        """
        # Simple summary for now
        # In production, this would call LLM service
        summary = f"Conversation with {len(messages)} messages. "
        if messages:
            summary += f"Last topic: {messages[-1].get('content', '')[:100]}"
        
        # Update memory with summary
        self.update_memory(chat_id, summary=summary, increment_turn=False)
        
        return summary
    
    def clear_memory(self, chat_id: str) -> bool:
        """
        Clear memory for a chat session.
        
        Args:
            chat_id: Chat session UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            vendor = self.db.query(Vendor).filter(Vendor.slug == self.vendor_id).first()
            if not vendor:
                return False
            
            memory = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor.id,
                ConversationMemory.chat_id == chat_id
            ).first()
            
            if memory:
                self.db.delete(memory)
                self.db.commit()
                logger.info(f"Cleared memory for chat {chat_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            self.db.rollback()
            return False
    
    def clear_all_memories(self, vendor_id: Optional[str] = None) -> int:
        """
        Clear all memories for a vendor.
        
        Args:
            vendor_id: Optional vendor ID (uses service vendor_id if not provided)
            
        Returns:
            Number of memories deleted
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor = self.db.query(Vendor).filter(Vendor.slug == effective_vendor_id).first()
            if not vendor:
                return 0
            
            deleted_count = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor.id
            ).delete()
            
            self.db.commit()
            logger.info(f"Cleared {deleted_count} memories for vendor {effective_vendor_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing all memories: {e}")
            self.db.rollback()
            return 0
    
    def get_memory_stats(self, vendor_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get memory statistics for a vendor.
        
        Args:
            vendor_id: Optional vendor ID
            
        Returns:
            Dict with statistics
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor = self.db.query(Vendor).filter(Vendor.slug == effective_vendor_id).first()
            if not vendor:
                return {"total": 0, "active": 0}
            
            total = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor.id
            ).count()
            
            active = self.db.query(ConversationMemory).filter(
                ConversationMemory.vendor_id == vendor.id,
                ConversationMemory.is_active == True
            ).count()
            
            return {
                "total": total,
                "active": active,
                "inactive": total - active
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"total": 0, "active": 0}
