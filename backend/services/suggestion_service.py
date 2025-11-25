"""
Suggestion Service.
Manages cached suggestions with TTL for vendors and users.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.models.saas_models import SuggestionCache, Vendor, User
from backend.config import get_settings
from loguru import logger
from datetime import datetime, timedelta
import hashlib
import json

settings = get_settings()


class SuggestionService:
    """Service for managing cached suggestions with TTL."""
    
    def __init__(self, db: Session, vendor_id: Optional[str] = None):
        """Initialize suggestion service with database session and vendor ID."""
        self.db = db
        self.vendor_id = vendor_id or settings.default_vendor_id
        self._load_suggestion_config()
    
    def _load_suggestion_config(self):
        """Load suggestion configuration from vendor-specific unified config."""
        try:
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
            unified_config = config_manager.load_config()
            
            chatbot_config = unified_config.get("chatbot_service", {})
            self.suggestion_config = chatbot_config.get("suggestions", {})
            
            # Get TTL from config (default 1 hour)
            self.default_ttl_seconds = self.suggestion_config.get("cache_ttl_seconds", 3600)
            
            logger.debug(f"Suggestion config loaded for vendor {self.vendor_id}")
        except Exception as e:
            logger.warning(f"Error loading suggestion config for vendor {self.vendor_id}: {e}, using defaults")
            self.suggestion_config = {}
            self.default_ttl_seconds = 3600  # 1 hour default
    
    def _generate_context_hash(self, chat_id: str, message: str, chunks: List[Dict], topics: Optional[set] = None) -> str:
        """Generate hash from context for cache key."""
        context_data = {
            "chat_id": chat_id,
            "message": message[:100],  # First 100 chars
            "chunk_count": len(chunks),
            "topics": sorted(list(topics)) if topics else []
        }
        context_str = json.dumps(context_data, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()
    
    def get_cached_suggestions(
        self,
        chat_id: str,
        message: str,
        chunks: List[Dict],
        topics: Optional[set] = None,
        chat_user_id: Optional[int] = None
    ) -> Optional[List[str]]:
        """
        Get cached suggestions if available and not expired.
        
        Args:
            chat_id: Chat session UUID
            message: Current message
            chunks: Retrieved chunks
            topics: Current topics
            chat_user_id: Optional chat_user ID
            
        Returns:
            List of suggestions if cached and valid, None otherwise
        """
        try:
            vendor = self.db.query(Vendor).filter(Vendor.slug == self.vendor_id).first()
            if not vendor:
                return None
            
            vendor_id_int = vendor.id
            
            # Generate context hash
            context_hash = self._generate_context_hash(chat_id, message, chunks, topics)
            
            # Query for cached suggestions
            query = self.db.query(SuggestionCache).filter(
                SuggestionCache.vendor_id == vendor_id_int,
                SuggestionCache.is_active == True
            )
            
            # Filter by context hash or chat_id
            query = query.filter(
                (SuggestionCache.context_hash == context_hash) |
                (SuggestionCache.chat_id == chat_id)
            )
            
            # Optional chat_user filter
            if chat_user_id:
                query = query.filter(
                    (SuggestionCache.chat_user_id == chat_user_id) |
                    (SuggestionCache.chat_user_id.is_(None))  # Also get vendor-wide suggestions
                )
            
            cached = query.order_by(SuggestionCache.last_used_at.desc()).first()
            
            if cached:
                # Check if expired
                if cached.expires_at and cached.expires_at < datetime.utcnow():
                    # Expired - delete it
                    self.db.delete(cached)
                    self.db.commit()
                    return None
                
                # Update usage
                cached.usage_count += 1
                cached.last_used_at = datetime.utcnow()
                self.db.commit()
                
                logger.debug(f"Using cached suggestions for chat {chat_id} (usage: {cached.usage_count})")
                return cached.suggestions or []
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached suggestions: {e}")
            return None
    
    def cache_suggestions(
        self,
        suggestions: List[str],
        chat_id: str,
        message: str,
        chunks: List[Dict],
        topics: Optional[set] = None,
        chat_user_id: Optional[int] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache suggestions with TTL.
        
        Args:
            suggestions: List of suggestion strings
            chat_id: Chat session UUID
            message: Current message
            chunks: Retrieved chunks
            topics: Current topics
            chat_user_id: Optional chat_user ID
            ttl_seconds: Optional TTL override
            
        Returns:
            True if cached successfully
        """
        try:
            if not suggestions:
                return False
            
            vendor = self.db.query(Vendor).filter(Vendor.slug == self.vendor_id).first()
            if not vendor:
                return False
            
            vendor_id_int = vendor.id
            
            # Generate context hash
            context_hash = self._generate_context_hash(chat_id, message, chunks, topics)
            
            # Use provided TTL or default
            ttl = ttl_seconds or self.default_ttl_seconds
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            # Check if already exists
            existing = self.db.query(SuggestionCache).filter(
                SuggestionCache.vendor_id == vendor_id_int,
                SuggestionCache.context_hash == context_hash,
                SuggestionCache.chat_id == chat_id
            ).first()
            
            if existing:
                # Update existing
                existing.suggestions = suggestions
                existing.expires_at = expires_at
                existing.ttl_seconds = ttl
                existing.last_used_at = datetime.utcnow()
                if chat_user_id:
                    existing.chat_user_id = chat_user_id
            else:
                # Create new
                cached = SuggestionCache(
                    vendor_id=vendor_id_int,
                    chat_user_id=chat_user_id,
                    chat_id=chat_id,
                    suggestions=suggestions,
                    context_hash=context_hash,
                    expires_at=expires_at,
                    ttl_seconds=ttl,
                    is_active=True,
                    last_used_at=datetime.utcnow()
                )
                self.db.add(cached)
            
            self.db.commit()
            logger.debug(f"Cached {len(suggestions)} suggestions for chat {chat_id} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error caching suggestions: {e}")
            self.db.rollback()
            return False
    
    def clear_expired_suggestions(self, vendor_id: Optional[str] = None) -> int:
        """
        Clear expired suggestions.
        
        Args:
            vendor_id: Optional vendor ID (uses service vendor_id if not provided)
            
        Returns:
            Number of suggestions deleted
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor = self.db.query(Vendor).filter(Vendor.slug == effective_vendor_id).first()
            if not vendor:
                return 0
            
            deleted_count = self.db.query(SuggestionCache).filter(
                SuggestionCache.vendor_id == vendor.id,
                SuggestionCache.expires_at < datetime.utcnow()
            ).delete()
            
            self.db.commit()
            logger.info(f"Cleared {deleted_count} expired suggestions for vendor {effective_vendor_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing expired suggestions: {e}")
            self.db.rollback()
            return 0
    
    def clear_all_suggestions(self, vendor_id: Optional[str] = None, chat_user_id: Optional[int] = None) -> int:
        """
        Clear all suggestions for a vendor/chat_user.
        
        Args:
            vendor_id: Optional vendor ID
            chat_user_id: Optional chat_user ID
            
        Returns:
            Number of suggestions deleted
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor = self.db.query(Vendor).filter(Vendor.slug == effective_vendor_id).first()
            if not vendor:
                return 0
            
            query = self.db.query(SuggestionCache).filter(
                SuggestionCache.vendor_id == vendor.id
            )
            
            if chat_user_id:
                query = query.filter(SuggestionCache.chat_user_id == chat_user_id)
            
            deleted_count = query.delete()
            self.db.commit()
            logger.info(f"Cleared {deleted_count} suggestions for vendor {effective_vendor_id}" + (f", chat_user {chat_user_id}" if chat_user_id else ""))
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing suggestions: {e}")
            self.db.rollback()
            return 0

