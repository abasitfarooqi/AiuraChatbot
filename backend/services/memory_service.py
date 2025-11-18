"""
Conversation Memory Service.
Manages per-user, per-chat conversation context and memory.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.models.database import ConversationMemory, Chat, Message
from backend.config import get_settings
from loguru import logger

settings = get_settings()


class MemoryService:
    """Service for managing conversation memory and context."""
    
    def __init__(self, db: Session):
        """Initialize memory service with database session."""
        self.db = db
        self.settings = settings
    
    def get_conversation_context(
        self,
        chat_id: str,
        max_turns: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation context for a chat.
        
        Args:
            chat_id: Chat session ID
            max_turns: Maximum number of turns to retrieve
        
        Returns:
            List of messages in format [{"role": "user", "content": "..."}, ...]
        """
        try:
            max_turns = max_turns or self.settings.memory_max_turns
            
            # Get recent messages
            messages = self.db.query(Message).filter(
                Message.chat_id == chat_id
            ).order_by(
                Message.created_at.desc()
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
    
    def get_or_create_memory(self, chat_id: str) -> ConversationMemory:
        """Get or create conversation memory for a chat."""
        try:
            memory = self.db.query(ConversationMemory).filter(
                ConversationMemory.chat_id == chat_id
            ).first()
            
            if not memory:
                memory = ConversationMemory(
                    chat_id=chat_id,
                    entities={},
                    intent_history=[],
                    turn_count=0
                )
                self.db.add(memory)
                self.db.commit()
                self.db.refresh(memory)
            
            return memory
            
        except Exception as e:
            logger.error(f"Error getting/creating memory: {e}")
            self.db.rollback()
            raise
    
    def update_memory(
        self,
        chat_id: str,
        entities: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
        summary: Optional[str] = None
    ):
        """Update conversation memory with new information."""
        try:
            memory = self.get_or_create_memory(chat_id)
            
            if entities:
                # Merge entities
                current_entities = memory.entities or {}
                current_entities.update(entities)
                memory.entities = current_entities
            
            if intent:
                # Add intent to history
                intent_history = memory.intent_history or []
                intent_history.append({
                    "intent": intent,
                    "timestamp": str(memory.updated_at)
                })
                memory.intent_history = intent_history[-10:]  # Keep last 10 intents
            
            if summary:
                memory.context_summary = summary
            
            memory.turn_count += 1
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            self.db.rollback()
    
    def extract_entities(self, query: str, retrieved_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Extract entities from query and retrieved chunks.
        Simple extraction based on keywords and patterns.
        """
        entities = {}
        query_lower = query.lower()
        
        # Extract bike models
        bike_models = ["honda", "yamaha", "pcx", "vision", "forza", "nmax", "xmax", "cb", "yzf", "mt"]
        for model in bike_models:
            if model in query_lower:
                entities["bike_model"] = model
                break
        
        # Extract service type
        service_keywords = {
            "rental": ["rent", "hire", "rental"],
            "sale": ["buy", "purchase", "sale", "price"],
            "finance": ["finance", "emi", "instalment", "payment plan"],
            "servicing": ["service", "repair", "maintenance"],
            "mot": ["mot", "test", "certificate"]
        }
        
        for service, keywords in service_keywords.items():
            if any(kw in query_lower for kw in keywords):
                entities["service_type"] = service
                break
        
        # Extract location
        locations = ["catford", "tooting", "sutton", "london"]
        for location in locations:
            if location in query_lower:
                entities["location"] = location
                break
        
        return entities
    
    def should_summarize(self, chat_id: str) -> bool:
        """Check if conversation should be summarized."""
        if not self.settings.memory_summary_enabled:
            return False
        
        memory = self.get_or_create_memory(chat_id)
        return memory.turn_count >= self.settings.memory_summary_threshold
    
    def create_summary(self, chat_id: str, messages: List[Dict[str, str]]) -> str:
        """
        Create summary of conversation (placeholder - would use LLM in production).
        """
        # In production, this would call LLM to summarize
        # For now, return a simple summary
        summary = f"Conversation with {len(messages)} messages. "
        if messages:
            summary += f"Last topic: {messages[-1].get('content', '')[:100]}"
        return summary

