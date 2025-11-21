"""
Cache Service for Q&A caching to reduce LLM usage.
Handles main cache (persistent per vendor) and temporary cache (per chat session).
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from backend.models.database import MainCache, TemporaryCache, Chat
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
        self.vendor_id = vendor_id or settings.default_vendor_id
        self.embedding_model = None
        self._initialize_embedding_model()
    
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
            Cache entry dict if found, None otherwise
        """
        try:
            import time
            check_start = time.time()
            effective_vendor_id = vendor_id or self.vendor_id
            
            # Get similarity threshold from config or use default
            if similarity_threshold is None:
                similarity_threshold = getattr(settings, 'cache_similarity_threshold', 0.85)
            
            # For short questions, use a lower threshold (they're harder to match)
            question_length = len(question.split())
            adaptive_threshold = similarity_threshold
            if question_length <= 3:
                # Short questions: lower threshold by 0.10
                adaptive_threshold = max(0.70, similarity_threshold - 0.10)
                logger.debug(f"[CACHE-SERVICE] Short question detected ({question_length} words), using adaptive threshold: {adaptive_threshold:.3f}")
            
            logger.debug(f"[CACHE-SERVICE] Checking cache - threshold: {adaptive_threshold:.3f}, vendor: {effective_vendor_id}, chat: {chat_id}")
            logger.debug(f"[CACHE-SERVICE] Question: '{question}'")
            
            # Generate question embedding
            question_embedding = None
            if self.embedding_model:
                embed_start = time.time()
                question_embedding = self.embedding_model.encode(
                    question,
                    show_progress_bar=False
                ).tolist()
                embed_time = time.time() - embed_start
                logger.debug(f"[CACHE-SERVICE] Generated embedding in {embed_time:.3f}s")
            else:
                logger.warning("[CACHE-SERVICE] Embedding model not available, using text-based matching only")
            
            # First check temporary cache (if chat_id provided)
            if chat_id:
                logger.debug(f"[CACHE-SERVICE] Checking temporary cache for chat {chat_id}...")
                temp_cache = self._check_temporary_cache(
                    question,
                    question_embedding,
                    chat_id,
                    effective_vendor_id,
                    adaptive_threshold
                )
                if temp_cache:
                    total_time = time.time() - check_start
                    logger.info(f"[CACHE-SERVICE] ✅ Found in TEMPORARY cache (time: {total_time:.3f}s)")
                    return temp_cache
                else:
                    logger.debug(f"[CACHE-SERVICE] Not found in temporary cache")
            
            # Then check main cache
            logger.debug(f"[CACHE-SERVICE] Checking main cache...")
            main_cache = self._check_main_cache(
                question,
                question_embedding,
                effective_vendor_id,
                adaptive_threshold
            )
            if main_cache:
                total_time = time.time() - check_start
                logger.info(f"[CACHE-SERVICE] ✅ Found in MAIN cache (time: {total_time:.3f}s)")
                return main_cache
            else:
                total_time = time.time() - check_start
                logger.debug(f"[CACHE-SERVICE] Not found in main cache (total check time: {total_time:.3f}s)")
            
            return None
            
        except Exception as e:
            logger.error(f"[CACHE-SERVICE] Error checking cache: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _check_temporary_cache(
        self,
        question: str,
        question_embedding: Optional[List[float]],
        chat_id: str,
        vendor_id: str,
        similarity_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Check temporary cache for similar question using multiple matching techniques."""
        try:
            # Get all temporary cache entries for this chat (don't require embedding)
            temp_caches = self.db.query(TemporaryCache).filter(
                and_(
                    TemporaryCache.chat_id == chat_id,
                    TemporaryCache.vendor_id == vendor_id
                )
            ).all()
            
            logger.debug(f"[CACHE-SERVICE] Found {len(temp_caches)} temporary cache entries for chat {chat_id}")
            
            if not temp_caches:
                return None
            
            # Calculate similarity with each cached question using multiple methods
            best_match = None
            best_similarity = 0.0
            best_method = None
            checked_count = 0
            
            for cache_entry in temp_caches:
                checked_count += 1
                similarities = []
                
                # Method 1: Text-based similarity (always available, good for short questions)
                text_sim = self._text_similarity(question, cache_entry.question)
                similarities.append(("text", text_sim))
                
                # Method 2: Embedding-based similarity (if available)
                if question_embedding and cache_entry.question_embedding:
                    embed_sim = self._cosine_similarity(
                        question_embedding,
                        cache_entry.question_embedding
                    )
                    similarities.append(("embedding", embed_sim))
                
                # Use the best similarity from all methods
                best_method_for_entry = max(similarities, key=lambda x: x[1])
                similarity = best_method_for_entry[1]
                
                if checked_count <= 5:  # Log first 5 for debugging
                    embed_sim_str = f"{similarities[1][1]:.3f}" if len(similarities) > 1 else "N/A"
                    logger.debug(f"[CACHE-SERVICE]   - Entry {cache_entry.cache_id}: text={text_sim:.3f}, embedding={embed_sim_str}, best={similarity:.3f} (threshold={similarity_threshold:.3f})")
                
                # Accept if any method meets threshold
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cache_entry
                    best_method = best_method_for_entry[0]
            
            logger.debug(f"[CACHE-SERVICE] Checked {checked_count} entries, best similarity: {best_similarity:.3f} (method: {best_method})")
            
            if best_match:
                # Update usage stats
                best_match.usage_count += 1
                best_match.last_used_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "cache_type": "temporary",
                    "cache_id": best_match.cache_id,
                    "question": best_match.question,
                    "answer": best_match.answer,
                    "similarity": best_similarity,
                    "usage_count": best_match.usage_count,
                    "metadata": best_match.cache_metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking temporary cache: {e}")
            return None
    
    def _check_main_cache(
        self,
        question: str,
        question_embedding: Optional[List[float]],
        vendor_id: str,
        similarity_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Check main cache for similar question using multiple matching techniques."""
        try:
            # Get all active main cache entries for this vendor (don't require embedding)
            main_caches = self.db.query(MainCache).filter(
                and_(
                    MainCache.vendor_id == vendor_id,
                    MainCache.is_active == True
                )
            ).all()
            
            logger.debug(f"[CACHE-SERVICE] Found {len(main_caches)} active main cache entries for vendor {vendor_id}")
            
            if not main_caches:
                return None
            
            # Calculate similarity with each cached question using multiple methods
            best_match = None
            best_similarity = 0.0
            best_method = None
            checked_count = 0
            
            for cache_entry in main_caches:
                checked_count += 1
                similarities = []
                
                # Method 1: Text-based similarity (always available, good for short questions)
                text_sim = self._text_similarity(question, cache_entry.question)
                similarities.append(("text", text_sim))
                
                # Method 2: Embedding-based similarity (if available)
                if question_embedding and cache_entry.question_embedding:
                    embed_sim = self._cosine_similarity(
                        question_embedding,
                        cache_entry.question_embedding
                    )
                    similarities.append(("embedding", embed_sim))
                
                # Use the best similarity from all methods
                best_method_for_entry = max(similarities, key=lambda x: x[1])
                similarity = best_method_for_entry[1]
                
                if checked_count <= 5:  # Log first 5 for debugging
                    embed_sim_str = f"{similarities[1][1]:.3f}" if len(similarities) > 1 else "N/A"
                    logger.debug(f"[CACHE-SERVICE]   - Entry {cache_entry.cache_id}: text={text_sim:.3f}, embedding={embed_sim_str}, best={similarity:.3f} (threshold={similarity_threshold:.3f})")
                
                # Accept if any method meets threshold
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cache_entry
                    best_method = best_method_for_entry[0]
            
            logger.debug(f"[CACHE-SERVICE] Checked {checked_count} entries, best similarity: {best_similarity:.3f} (method: {best_method})")
            
            if best_match:
                # Update usage stats
                best_match.usage_count += 1
                best_match.last_used_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "cache_type": "main",
                    "cache_id": best_match.cache_id,
                    "question": best_match.question,
                    "answer": best_match.answer,
                    "similarity": best_similarity,
                    "usage_count": best_match.usage_count,
                    "tokens_saved": best_match.tokens_saved,
                    "credits_saved": best_match.credits_saved,
                    "metadata": best_match.cache_metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking main cache: {e}")
            return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            dot_product = np.dot(vec1_array, vec2_array)
            norm1 = np.linalg.norm(vec1_array)
            norm2 = np.linalg.norm(vec2_array)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def save_to_temporary_cache(
        self,
        chat_id: str,
        question: str,
        answer: str,
        vendor_id: Optional[str] = None,
        tokens_used: int = 0,
        metadata: Optional[Dict] = None,
        similarity_threshold: Optional[float] = None
    ) -> Optional[str]:
        """
        Save Q&A pair to temporary cache (per chat session).
        Checks for existing similar questions to avoid duplicates.
        
        Args:
            chat_id: Chat session ID
            question: User question
            answer: Assistant answer
            vendor_id: Vendor ID
            tokens_used: Tokens used to generate this answer (for stats)
            metadata: Optional metadata
            similarity_threshold: Similarity threshold for duplicate detection
        
        Returns:
            Cache ID if saved successfully, None otherwise
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            
            # Generate embedding
            if not self.embedding_model:
                logger.warning("Embedding model not available, cannot save to cache")
                return None
            
            question_embedding = self.embedding_model.encode(
                question,
                show_progress_bar=False
            ).tolist()
            
            # Check if similar question already exists in temporary cache for this chat
            # Use a slightly lower threshold for duplicate detection to catch more similar questions
            if similarity_threshold is None:
                similarity_threshold = getattr(settings, 'cache_similarity_threshold', 0.85)
            
            # For duplicate detection, use 0.75 of the threshold (more lenient)
            # This catches questions that are very similar but might have slight wording differences
            duplicate_threshold = similarity_threshold * 0.75
            
            existing = self._check_temporary_cache(
                question,
                question_embedding,
                chat_id,
                effective_vendor_id,
                duplicate_threshold
            )
            
            if existing:
                # Update existing entry instead of creating duplicate
                cache_entry = self.db.query(TemporaryCache).filter(
                    TemporaryCache.cache_id == existing["cache_id"]
                ).first()
                
                if cache_entry:
                    # Update answer if different (might be improved)
                    if cache_entry.answer != answer:
                        cache_entry.answer = answer
                        cache_entry.updated_at = datetime.utcnow()
                    
                    # Update tokens saved if this answer is better
                    if tokens_used > cache_entry.tokens_saved:
                        cache_entry.tokens_saved = tokens_used
                    
                    self.db.commit()
                    logger.info(f"Updated temporary cache entry: {existing['cache_id']} (avoided duplicate)")
                    return existing["cache_id"]
            
            # Create new cache entry
            cache_id = f"temp_{uuid.uuid4().hex[:16]}"
            cache_entry = TemporaryCache(
                cache_id=cache_id,
                chat_id=chat_id,
                vendor_id=effective_vendor_id,
                question=question,
                answer=answer,
                question_embedding=question_embedding,
                tokens_saved=tokens_used,  # Initial save: tokens that would be saved if reused
                cache_metadata=metadata or {}
            )
            
            self.db.add(cache_entry)
            self.db.commit()
            self.db.refresh(cache_entry)
            
            logger.info(f"Saved to temporary cache: {cache_id} for chat {chat_id}")
            return cache_id
            
        except Exception as e:
            logger.error(f"Error saving to temporary cache: {e}")
            self.db.rollback()
            return None
    
    def save_to_main_cache(
        self,
        question: str,
        answer: str,
        vendor_id: Optional[str] = None,
        tokens_used: int = 0,
        similarity_threshold: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Save Q&A pair to main cache (persistent per vendor).
        
        Args:
            question: User question
            answer: Assistant answer
            vendor_id: Vendor ID
            tokens_used: Tokens used to generate this answer
            similarity_threshold: Similarity threshold for matching
            metadata: Optional metadata
        
        Returns:
            Cache ID if saved successfully, None otherwise
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            
            # Generate embedding
            if not self.embedding_model:
                logger.warning("Embedding model not available, cannot save to cache")
                return None
            
            question_embedding = self.embedding_model.encode(
                question,
                show_progress_bar=False
            ).tolist()
            
            # Check if similar question already exists
            existing = self._check_main_cache(
                question,
                question_embedding,
                effective_vendor_id,
                similarity_threshold or 0.90  # High threshold to avoid duplicates
            )
            
            if existing:
                # Update existing entry instead of creating duplicate
                cache_entry = self.db.query(MainCache).filter(
                    MainCache.cache_id == existing["cache_id"]
                ).first()
                
                if cache_entry:
                    # Update answer if different (might be improved)
                    if cache_entry.answer != answer:
                        cache_entry.answer = answer
                        cache_entry.updated_at = datetime.utcnow()
                    
                    self.db.commit()
                    logger.info(f"Updated main cache entry: {existing['cache_id']}")
                    return existing["cache_id"]
            
            # Create new cache entry
            cache_id = f"main_{uuid.uuid4().hex[:16]}"
            cache_entry = MainCache(
                cache_id=cache_id,
                vendor_id=effective_vendor_id,
                question=question,
                answer=answer,
                question_embedding=question_embedding,
                similarity_threshold=similarity_threshold or 0.85,
                tokens_saved=tokens_used,  # Initial: tokens that would be saved if reused
                credits_saved=self._calculate_credits(tokens_used),
                cache_metadata=metadata or {}
            )
            
            self.db.add(cache_entry)
            self.db.commit()
            self.db.refresh(cache_entry)
            
            logger.info(f"Saved to main cache: {cache_id} for vendor {effective_vendor_id}")
            return cache_id
            
        except Exception as e:
            logger.error(f"Error saving to main cache: {e}")
            self.db.rollback()
            return None
    
    def promote_to_main_cache(
        self,
        temp_cache_id: str,
        vendor_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Promote a temporary cache entry to main cache.
        Useful for learning from chat sessions.
        
        Args:
            temp_cache_id: Temporary cache ID
            vendor_id: Vendor ID
        
        Returns:
            Main cache ID if promoted successfully, None otherwise
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            
            # Get temporary cache entry
            temp_cache = self.db.query(TemporaryCache).filter(
                TemporaryCache.cache_id == temp_cache_id
            ).first()
            
            if not temp_cache:
                logger.warning(f"Temporary cache entry not found: {temp_cache_id}")
                return None
            
            # Save to main cache
            main_cache_id = self.save_to_main_cache(
                question=temp_cache.question,
                answer=temp_cache.answer,
                vendor_id=effective_vendor_id,
                tokens_used=temp_cache.tokens_saved,
                metadata=temp_cache.cache_metadata
            )
            
            if main_cache_id:
                logger.info(f"Promoted temporary cache {temp_cache_id} to main cache {main_cache_id}")
            
            return main_cache_id
            
        except Exception as e:
            logger.error(f"Error promoting to main cache: {e}")
            return None
    
    def delete_temporary_cache_for_chat(self, chat_id: str) -> int:
        """
        Delete all temporary cache entries for a chat session.
        Called when chat ends or is cleared.
        
        Args:
            chat_id: Chat session ID
        
        Returns:
            Number of entries deleted
        """
        try:
            deleted_count = self.db.query(TemporaryCache).filter(
                TemporaryCache.chat_id == chat_id
            ).delete()
            
            self.db.commit()
            logger.info(f"Deleted {deleted_count} temporary cache entries for chat {chat_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting temporary cache: {e}")
            self.db.rollback()
            return 0
    
    def update_cache_stats(
        self,
        cache_id: str,
        cache_type: str,
        tokens_saved: int,
        credits_saved: Optional[int] = None
    ):
        """
        Update cache statistics when a cached answer is used.
        
        Args:
            cache_id: Cache entry ID
            cache_type: "main" or "temporary"
            tokens_saved: Tokens saved by using cache
            credits_saved: Credits saved (optional)
        """
        try:
            if cache_type == "main":
                cache_entry = self.db.query(MainCache).filter(
                    MainCache.cache_id == cache_id
                ).first()
                
                if cache_entry:
                    cache_entry.tokens_saved += tokens_saved
                    if credits_saved:
                        cache_entry.credits_saved += credits_saved
                    else:
                        cache_entry.credits_saved += self._calculate_credits(tokens_saved)
                    cache_entry.last_used_at = datetime.utcnow()
            
            elif cache_type == "temporary":
                cache_entry = self.db.query(TemporaryCache).filter(
                    TemporaryCache.cache_id == cache_id
                ).first()
                
                if cache_entry:
                    cache_entry.tokens_saved += tokens_saved
                    cache_entry.last_used_at = datetime.utcnow()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating cache stats: {e}")
            self.db.rollback()
    
    def get_cache_stats(
        self,
        vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cache statistics for a vendor.
        
        Args:
            vendor_id: Vendor ID
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            effective_vendor_id = vendor_id or self.vendor_id
            
            # Main cache stats
            main_caches = self.db.query(MainCache).filter(
                MainCache.vendor_id == effective_vendor_id
            ).all()
            
            main_total = len(main_caches)
            main_active = sum(1 for c in main_caches if c.is_active)
            main_total_usage = sum(c.usage_count for c in main_caches)
            main_total_tokens_saved = sum(c.tokens_saved for c in main_caches)
            main_total_credits_saved = sum(c.credits_saved for c in main_caches)
            
            # Temporary cache stats
            temp_caches = self.db.query(TemporaryCache).filter(
                TemporaryCache.vendor_id == effective_vendor_id
            ).all()
            
            temp_total = len(temp_caches)
            temp_total_usage = sum(c.usage_count for c in temp_caches)
            temp_total_tokens_saved = sum(c.tokens_saved for c in temp_caches)
            
            # Group temporary cache by chat
            temp_by_chat = {}
            for cache in temp_caches:
                if cache.chat_id not in temp_by_chat:
                    temp_by_chat[cache.chat_id] = 0
                temp_by_chat[cache.chat_id] += 1
            
            return {
                "vendor_id": effective_vendor_id,
                "main_cache": {
                    "total_entries": main_total,
                    "active_entries": main_active,
                    "total_usage_count": main_total_usage,
                    "total_tokens_saved": main_total_tokens_saved,
                    "total_credits_saved": main_total_credits_saved
                },
                "temporary_cache": {
                    "total_entries": temp_total,
                    "active_chats": len(temp_by_chat),
                    "total_usage_count": temp_total_usage,
                    "total_tokens_saved": temp_total_tokens_saved,
                    "entries_by_chat": temp_by_chat
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def _calculate_credits(self, tokens: int) -> int:
        """Calculate credits based on tokens."""
        return max(1, tokens // 100)  # 1 credit per 100 tokens, minimum 1

