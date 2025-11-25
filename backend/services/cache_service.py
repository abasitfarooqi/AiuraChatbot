"""
Cache Service for Q&A caching to reduce LLM usage.
Handles main cache (persistent per vendor) and temporary cache (per chat session).
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from backend.models.saas_models import MainCache, TemporaryCache
from backend.config import get_settings
from loguru import logger
import uuid
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
import re
from difflib import SequenceMatcher

settings = get_settings()


class CacheService:
    """Service for managing Q&A caches to optimise LLM usage."""
    
    def __init__(self, db: Session, vendor_id: Optional[str] = None):
        """Initialise cache service."""
        self.db = db
        self.vendor_id = vendor_id or settings.default_vendor_id  # Keep as slug for compatibility
        self.vendor_db_id = None  # Will store Integer vendor.id
        self.embedding_model = None
        self._initialize_embedding_model()
        self._load_vendor_id()
    
    def _load_vendor_id(self):
        """Load vendor database ID from vendor slug."""
        if self.db and self.vendor_id:
            try:
                from backend.models.saas_models import Vendor
                vendor = self.db.query(Vendor).filter(
                    Vendor.slug == self.vendor_id,
                    Vendor.deleted_at.is_(None)
                ).first()
                if vendor:
                    self.vendor_db_id = vendor.id
            except Exception as e:
                logger.warning(f"Could not load vendor ID for {self.vendor_id}: {e}")
    
    def _initialize_embedding_model(self):
        """Initialise embedding model for similarity matching."""
        try:
            # Use the same embedding model as RAG service
            embedding_model_name = getattr(settings, 'embedding_model_name', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(embedding_model_name)
            logger.info(f"Cache service embedding model initialised: {embedding_model_name}")
        except Exception as e:
            logger.error(f"Error initialising embedding model for cache: {e}")
            self.embedding_model = None
    
    def _normalize_question(self, question: str) -> str:
        """
        Normalize question for better matching.
        Removes punctuation, converts to lowercase, removes extra spaces.
        """
        # Convert to lowercase
        normalized = question.lower().strip()
        
        # Remove punctuation (keep spaces)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def _extract_keywords(self, question: str) -> set:
        """
        Extract important keywords from question.
        Removes common stop words.
        """
        # Common stop words to ignore
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'may', 'might', 'must', 'can', 'you', 'your', 'yours',
            'i', 'me', 'my', 'we', 'our', 'ours', 'they', 'them', 'their',
            'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
            'where', 'when', 'why', 'how', 'about', 'for', 'to', 'of', 'in',
            'on', 'at', 'by', 'with', 'from', 'as', 'if', 'or', 'and', 'but'
        }
        
        normalized = self._normalize_question(question)
        words = normalized.split()
        
        # Filter out stop words and short words (less than 2 chars)
        keywords = {w for w in words if len(w) >= 2 and w not in stop_words}
        
        return keywords
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using SequenceMatcher (fuzzy matching).
        Useful for short questions or when embeddings might miss variations.
        """
        try:
            norm1 = self._normalize_question(text1)
            norm2 = self._normalize_question(text2)
            
            # Use SequenceMatcher for fuzzy matching
            similarity = SequenceMatcher(None, norm1, norm2).ratio()
            
            # Also check keyword overlap
            keywords1 = self._extract_keywords(text1)
            keywords2 = self._extract_keywords(text2)
            
            if keywords1 and keywords2:
                # Jaccard similarity for keywords
                intersection = keywords1.intersection(keywords2)
                union = keywords1.union(keywords2)
                keyword_similarity = len(intersection) / len(union) if union else 0.0
                
                # Combine both similarities (weighted average)
                combined = (similarity * 0.6) + (keyword_similarity * 0.4)
                return combined
            
            return similarity
            
        except Exception as e:
            logger.debug(f"Error calculating text similarity: {e}")
            return 0.0
    
    def check_cache(
        self,
        question: str,
        chat_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        similarity_threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a similar question exists in cache.
        Uses multiple matching techniques: embeddings, text similarity, and keyword matching.
        Checks temporary cache first, then main cache.
        
        Args:
            question: User question
            chat_id: Optional chat ID for temporary cache lookup
            vendor_id: Vendor ID (defaults to service vendor_id)
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            Cache entry dict with 'answer', 'cache_type', 'cache_id', 'similarity' if found, None otherwise
        """
        if not self.db:
            return None
        
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            effective_vendor_db_id = self._get_vendor_db_id(effective_vendor_id)
            
            if not effective_vendor_db_id:
                return None
            
            threshold = similarity_threshold or 0.85
            
            # Generate question embedding for similarity search
            question_embedding = None
            if self.embedding_model:
                try:
                    question_embedding = self.embedding_model.encode(question).tolist()
                except Exception as e:
                    logger.debug(f"Error generating embedding for cache check: {e}")
            
            # Check temporary cache first (if chat_id provided)
            # Note: TemporaryCache.chat_id stores session_uuid (String) directly
            if chat_id:
                try:
                    temp_caches = self.db.query(TemporaryCache).filter(
                        TemporaryCache.chat_id == chat_id,  # chat_id is session_uuid (String)
                        TemporaryCache.vendor_id == effective_vendor_db_id
                    ).all()
                    
                    best_match = None
                    best_similarity = 0.0
                    
                    for cache in temp_caches:
                        similarity = 0.0
                        
                        # Try embedding similarity first
                        if question_embedding and cache.question_embedding:
                            try:
                                cache_emb = cache.question_embedding
                                if isinstance(cache_emb, str):
                                    import json
                                    cache_emb = json.loads(cache_emb)
                                similarity = float(np.dot(question_embedding, cache_emb) / (np.linalg.norm(question_embedding) * np.linalg.norm(cache_emb)))
                            except Exception as e:
                                logger.debug(f"Error calculating embedding similarity: {e}")
                        
                        # Fallback to text similarity if embedding similarity is low
                        if similarity < threshold:
                            text_sim = self._text_similarity(question, cache.question)
                            similarity = max(similarity, text_sim)
                        
                        if similarity >= threshold and similarity > best_similarity:
                            best_similarity = similarity
                            best_match = cache
                    
                    if best_match:
                            # Update usage stats
                            best_match.usage_count += 1
                            best_match.last_used_at = datetime.utcnow()
                            self.db.commit()
                            
                            return {
                                "answer": best_match.answer,
                                "cache_type": "temporary",
                                "cache_id": best_match.cache_id,
                                "similarity": best_similarity
                            }
                except Exception as e:
                    logger.debug(f"Error checking temporary cache: {e}")
            
            # Check main cache
            try:
                main_caches = self.db.query(MainCache).filter(
                    MainCache.vendor_id == effective_vendor_db_id,
                    MainCache.is_active == True
                ).all()
                
                best_match = None
                best_similarity = 0.0
                
                for cache in main_caches:
                    similarity = 0.0
                    
                    # Try embedding similarity first
                    if question_embedding and cache.question_embedding:
                        try:
                            cache_emb = cache.question_embedding
                            if isinstance(cache_emb, str):
                                import json
                                cache_emb = json.loads(cache_emb)
                            similarity = float(np.dot(question_embedding, cache_emb) / (np.linalg.norm(question_embedding) * np.linalg.norm(cache_emb)))
                        except Exception as e:
                            logger.debug(f"Error calculating embedding similarity: {e}")
                    
                    # Fallback to text similarity if embedding similarity is low
                    if similarity < threshold:
                        text_sim = self._text_similarity(question, cache.question)
                        similarity = max(similarity, text_sim)
                    
                    if similarity >= threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = cache
                
                if best_match:
                    # Update usage stats
                    best_match.usage_count += 1
                    best_match.last_used_at = datetime.utcnow()
                    self.db.commit()
                    
                    return {
                        "answer": best_match.answer,
                        "cache_type": "main",
                        "cache_id": best_match.cache_id,
                        "similarity": best_similarity
                    }
            except Exception as e:
                logger.debug(f"Error checking main cache: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None
    
    def _calculate_credits(self, tokens: int) -> int:
        """Calculate credits based on tokens."""
        return max(1, tokens // 100)  # 1 credit per 100 tokens, minimum 1
    
    def _get_vendor_db_id(self, vendor_id: Optional[str] = None) -> Optional[int]:
        """Get vendor database ID from vendor slug."""
        if not self.db:
            return None
        
        effective_vendor_id = vendor_id or self.vendor_id
        if not effective_vendor_id:
            return None
        
        try:
            from backend.models.saas_models import Vendor
            vendor = self.db.query(Vendor).filter(
                Vendor.slug == effective_vendor_id,
                Vendor.deleted_at.is_(None)
            ).first()
            return vendor.id if vendor else None
        except Exception as e:
            logger.debug(f"Error getting vendor DB ID for {effective_vendor_id}: {e}")
            return None
    
    def save_to_temporary_cache(
        self,
        chat_id: str,
        question: str,
        answer: str,
        vendor_id: Optional[str] = None,
        tokens_used: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.85
    ) -> Optional[str]:
        """Save Q&A pair to temporary cache."""
        if not self.db:
            logger.warning("No database session available for saving temporary cache")
            return None
        
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor_db_id = self._get_vendor_db_id(effective_vendor_id)
            
            if not vendor_db_id:
                logger.warning(f"Could not find vendor DB ID for {effective_vendor_id}")
                return None
            
            # Note: We store session_uuid directly as chat_id (String), not the chat session ID (Integer)
            # We don't require the chat session to exist - it might be created after the cache entry
            from backend.models.saas_models import ChatSession
            chat_session = self.db.query(ChatSession).filter(
                ChatSession.session_uuid == chat_id
            ).first()
            
            if not chat_session:
                logger.debug(f"Chat session {chat_id} not found yet - will save cache entry anyway with session_uuid as chat_id")
            
            # Generate embedding for question
            question_embedding = None
            if self.embedding_model:
                try:
                    question_embedding = self.embedding_model.encode(question).tolist()
                except Exception as e:
                    logger.debug(f"Error generating embedding: {e}")
            
            # Create cache entry
            # Note: TemporaryCache.chat_id is String(100) and stores session_uuid directly
            cache_id = f"temp_{uuid.uuid4().hex[:16]}"
            cache_entry = TemporaryCache(
                cache_id=cache_id,
                chat_id=chat_id,  # Store session_uuid (String), not chat_session.id (Integer)
                vendor_id=vendor_db_id,
                question=question,
                answer=answer,
                question_embedding=question_embedding,
                similarity_threshold=similarity_threshold,
                tokens_saved=tokens_used,
                cache_metadata=metadata or {}
            )
            
            self.db.add(cache_entry)
            self.db.commit()
            self.db.refresh(cache_entry)
            
            logger.debug(f"Saved to temporary cache: {cache_id}")
            return cache_id
            
        except Exception as e:
            logger.error(f"Error saving to temporary cache: {e}")
            if self.db:
                self.db.rollback()
            return None
    
    def save_to_main_cache(
        self,
        question: str,
        answer: str,
        vendor_id: Optional[str] = None,
        tokens_used: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.85
    ) -> Optional[str]:
        """Save Q&A pair to main cache."""
        if not self.db:
            logger.warning("No database session available for saving main cache")
            return None
        
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor_db_id = self._get_vendor_db_id(effective_vendor_id)
            
            if not vendor_db_id:
                logger.warning(f"Could not find vendor DB ID for {effective_vendor_id}")
                return None
            
            # Generate embedding for question
            question_embedding = None
            if self.embedding_model:
                try:
                    question_embedding = self.embedding_model.encode(question).tolist()
                except Exception as e:
                    logger.debug(f"Error generating embedding: {e}")
            
            # Create cache entry
            cache_id = f"main_{uuid.uuid4().hex[:16]}"
            cache_entry = MainCache(
                cache_id=cache_id,
                vendor_id=vendor_db_id,
                question=question,
                answer=answer,
                question_embedding=question_embedding,
                similarity_threshold=similarity_threshold,
                tokens_saved=tokens_used,
                credits_saved=self._calculate_credits(tokens_used),
                cache_metadata=metadata or {}
            )
            
            self.db.add(cache_entry)
            self.db.commit()
            self.db.refresh(cache_entry)
            
            logger.debug(f"Saved to main cache: {cache_id}")
            return cache_id
            
        except Exception as e:
            logger.error(f"Error saving to main cache: {e}")
            if self.db:
                self.db.rollback()
            return None
    
    def promote_to_main_cache(
        self,
        temp_cache_id: str,
        vendor_id: Optional[str] = None
    ) -> Optional[str]:
        """Promote a temporary cache entry to main cache."""
        if not self.db:
            logger.warning("No database session available for promoting cache")
            return None
        
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor_db_id = self._get_vendor_db_id(effective_vendor_id)
            
            if not vendor_db_id:
                logger.warning(f"Could not find vendor DB ID for {effective_vendor_id}")
                return None
            
            # Find temporary cache entry
            temp_entry = self.db.query(TemporaryCache).filter(
                TemporaryCache.cache_id == temp_cache_id
            ).first()
            
            if not temp_entry:
                logger.warning(f"Temporary cache entry {temp_cache_id} not found")
                return None
            
            # Create main cache entry from temporary
            cache_id = f"main_{uuid.uuid4().hex[:16]}"
            main_entry = MainCache(
                cache_id=cache_id,
                vendor_id=vendor_db_id,
                question=temp_entry.question,
                answer=temp_entry.answer,
                question_embedding=temp_entry.question_embedding,
                similarity_threshold=temp_entry.similarity_threshold,
                tokens_saved=temp_entry.tokens_saved,
                credits_saved=self._calculate_credits(temp_entry.tokens_saved),
                cache_metadata=temp_entry.cache_metadata
            )
            
            self.db.add(main_entry)
            self.db.commit()
            self.db.refresh(main_entry)
            
            logger.info(f"Promoted temporary cache {temp_cache_id} to main cache {cache_id}")
            return cache_id
            
        except Exception as e:
            logger.error(f"Error promoting cache: {e}")
            if self.db:
                self.db.rollback()
            return None
    
    def get_cache_stats(self, vendor_id: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics for a vendor."""
        if not self.db:
            return {
                "main_cache": {
                    "total_entries": 0,
                    "active_entries": 0,
                    "total_usage_count": 0,
                    "total_tokens_saved": 0,
                    "total_credits_saved": 0
                },
                "temporary_cache": {
                    "total_entries": 0,
                    "active_chats": 0,
                    "total_usage_count": 0,
                    "total_tokens_saved": 0
                }
            }
        
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            vendor_db_id = self._get_vendor_db_id(effective_vendor_id)
            
            if not vendor_db_id:
                return {
                    "main_cache": {
                        "total_entries": 0,
                        "active_entries": 0,
                        "total_usage_count": 0,
                        "total_tokens_saved": 0,
                        "total_credits_saved": 0
                    },
                    "temporary_cache": {
                        "total_entries": 0,
                        "active_chats": 0,
                        "total_usage_count": 0,
                        "total_tokens_saved": 0
                    }
                }
            
            # Main cache stats
            main_cache_query = self.db.query(MainCache).filter(MainCache.vendor_id == vendor_db_id)
            main_total = main_cache_query.count()
            main_active = main_cache_query.filter(MainCache.is_active == True).count()
            
            main_stats = main_cache_query.all()
            main_usage_count = sum(entry.usage_count for entry in main_stats)
            main_tokens_saved = sum(entry.tokens_saved for entry in main_stats)
            main_credits_saved = sum(entry.credits_saved for entry in main_stats)
            
            # Temporary cache stats
            temp_cache_query = self.db.query(TemporaryCache).filter(TemporaryCache.vendor_id == vendor_db_id)
            temp_total = temp_cache_query.count()
            
            # Get unique chat sessions
            from sqlalchemy import distinct
            temp_chats = self.db.query(distinct(TemporaryCache.chat_id)).filter(
                TemporaryCache.vendor_id == vendor_db_id
            ).count()
            
            temp_stats = temp_cache_query.all()
            temp_usage_count = sum(entry.usage_count for entry in temp_stats)
            temp_tokens_saved = sum(entry.tokens_saved for entry in temp_stats)
            
            return {
                "main_cache": {
                    "total_entries": main_total,
                    "active_entries": main_active,
                    "total_usage_count": main_usage_count,
                    "total_tokens_saved": main_tokens_saved,
                    "total_credits_saved": main_credits_saved
                },
                "temporary_cache": {
                    "total_entries": temp_total,
                    "active_chats": temp_chats,
                    "total_usage_count": temp_usage_count,
                    "total_tokens_saved": temp_tokens_saved
                }
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "main_cache": {
                    "total_entries": 0,
                    "active_entries": 0,
                    "total_usage_count": 0,
                    "total_tokens_saved": 0,
                    "total_credits_saved": 0
                },
                "temporary_cache": {
                    "total_entries": 0,
                    "active_chats": 0,
                    "total_usage_count": 0,
                    "total_tokens_saved": 0
                }
            }

