"""
Multi-Vector Search (MVS) Service.
Handles dense (semantic) and sparse (keyword) embeddings for hybrid search.
"""
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger
from backend.config import get_settings

settings = get_settings()


class SparseEmbeddingGenerator:
    """Generates sparse embeddings using BM25/TF-IDF for keyword matching."""
    
    def __init__(self, corpus: Optional[List[str]] = None):
        """Initialize sparse embedding generator."""
        self.corpus = corpus or []
        self.vocab = {}
        self.idf = {}
        self.avg_doc_length = 0.0
        self._build_index()
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words (lowercase, alphanumeric only)."""
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _build_index(self):
        """Build vocabulary and IDF index from corpus."""
        if not self.corpus:
            return
        
        # Tokenize all documents
        tokenized_docs = [self._tokenize(doc) for doc in self.corpus]
        
        # Calculate average document length
        doc_lengths = [len(doc) for doc in tokenized_docs]
        self.avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
        
        # Build vocabulary (all unique terms)
        all_terms = set()
        for doc in tokenized_docs:
            all_terms.update(doc)
        
        self.vocab = {term: idx for idx, term in enumerate(sorted(all_terms))}
        
        # Calculate IDF (Inverse Document Frequency)
        doc_count = len(tokenized_docs)
        term_doc_freq = Counter()
        
        for doc in tokenized_docs:
            unique_terms = set(doc)
            for term in unique_terms:
                term_doc_freq[term] += 1
        
        # IDF = log((N - df + 0.5) / (df + 0.5))
        # where N = total docs, df = document frequency
        for term, df in term_doc_freq.items():
            self.idf[term] = np.log((doc_count - df + 0.5) / (df + 0.5))
    
    def generate_bm25(self, text: str, k1: float = 1.5, b: float = 0.75) -> Dict[str, float]:
        """
        Generate BM25 sparse embedding for text.
        
        Args:
            text: Input text
            k1: Term frequency saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        
        Returns:
            Dictionary mapping terms to BM25 scores
        """
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        
        # Count term frequencies
        term_freq = Counter(tokens)
        
        # Calculate BM25 scores
        sparse_vector = {}
        doc_length = len(tokens)
        
        for term, tf in term_freq.items():
            if term in self.idf:
                # BM25 formula: idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_length / avg_doc_length)))
                idf_score = self.idf[term]
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / self.avg_doc_length)) if self.avg_doc_length > 0 else tf + k1
                bm25_score = idf_score * (numerator / denominator)
                sparse_vector[term] = float(bm25_score)
        
        return sparse_vector
    
    def generate_tfidf(self, text: str) -> Dict[str, float]:
        """
        Generate TF-IDF sparse embedding for text.
        
        Returns:
            Dictionary mapping terms to TF-IDF scores
        """
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        
        # Count term frequencies
        term_freq = Counter(tokens)
        doc_length = len(tokens)
        
        # Calculate TF-IDF scores
        sparse_vector = {}
        for term, tf in term_freq.items():
            if term in self.idf:
                # TF = term_frequency / document_length
                tf_score = tf / doc_length if doc_length > 0 else 0
                # TF-IDF = TF * IDF
                tfidf_score = tf_score * self.idf[term]
                sparse_vector[term] = float(tfidf_score)
        
        return sparse_vector
    
    def update_corpus(self, new_docs: List[str]):
        """Update corpus and rebuild index."""
        self.corpus.extend(new_docs)
        self._build_index()


class MVSService:
    """Multi-Vector Search service for hybrid dense + sparse retrieval."""
    
    def __init__(self, vendor_id: Optional[str] = None):
        """Initialize MVS service."""
        self.vendor_id = vendor_id or settings.default_vendor_id
        self.dense_model = None
        self.sparse_generator = None
        self._initialize()
    
    def _initialize(self):
        """Initialize embedding models."""
        try:
            # Initialize dense embedding model (existing SentenceTransformer)
            logger.info(f"Loading dense embedding model: {settings.embedding_model}")
            
            if settings.embedding_offline_mode:
                from backend.services.offline_model_manager import OfflineModelManager
                model_manager = OfflineModelManager(cache_dir=settings.embedding_cache_dir)
                model = model_manager.load_embedding_model_offline(settings.embedding_model)
                if model:
                    self.dense_model = model
                else:
                    import os
                    os.environ['TRANSFORMERS_CACHE'] = settings.embedding_cache_dir
                    os.environ['HF_HOME'] = settings.embedding_cache_dir
                    self.dense_model = SentenceTransformer(
                        settings.embedding_model,
                        device=settings.embedding_device,
                        cache_folder=settings.embedding_cache_dir
                    )
            else:
                self.dense_model = SentenceTransformer(
                    settings.embedding_model,
                    device=settings.embedding_device
                )
            
            # Sparse generator will be initialized when corpus is loaded
            self.sparse_generator = None
            
            logger.info("MVS service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing MVS service: {e}")
            raise
    
    def generate_dense_embedding(self, text: str) -> List[float]:
        """Generate dense embedding using SentenceTransformer."""
        if not self.dense_model:
            raise ValueError("Dense embedding model not initialized")
        
        embedding = self.dense_model.encode(
            text,
            show_progress_bar=False
        ).tolist()
        
        return embedding
    
    def generate_sparse_embedding(self, text: str, method: str = "bm25") -> Dict[str, float]:
        """
        Generate sparse embedding using BM25 or TF-IDF.
        
        Args:
            text: Input text
            method: "bm25" or "tfidf"
        
        Returns:
            Dictionary mapping terms to scores
        """
        if not self.sparse_generator:
            # Initialize with empty corpus (will be updated when KB is loaded)
            self.sparse_generator = SparseEmbeddingGenerator()
        
        if method == "bm25":
            return self.sparse_generator.generate_bm25(text)
        elif method == "tfidf":
            return self.sparse_generator.generate_tfidf(text)
        else:
            raise ValueError(f"Unknown sparse method: {method}")
    
    def initialize_sparse_index(self, corpus: List[str]):
        """Initialize sparse embedding generator with corpus."""
        self.sparse_generator = SparseEmbeddingGenerator(corpus)
        logger.info(f"Initialized sparse index with {len(corpus)} documents")
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two dense vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def sparse_similarity(self, sparse1: Dict[str, float], sparse2: Dict[str, float]) -> float:
        """Calculate similarity between two sparse vectors (dot product)."""
        # Get common terms
        common_terms = set(sparse1.keys()) & set(sparse2.keys())
        
        if not common_terms:
            return 0.0
        
        # Dot product of sparse vectors
        similarity = sum(sparse1[term] * sparse2[term] for term in common_terms)
        
        # Normalize by magnitudes
        norm1 = np.sqrt(sum(v ** 2 for v in sparse1.values()))
        norm2 = np.sqrt(sum(v ** 2 for v in sparse2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(similarity / (norm1 * norm2))
    
    def reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine dense and sparse search results using Reciprocal Rank Fusion (RRF).
        
        Args:
            dense_results: List of results from dense search with 'id' and 'similarity'
            sparse_results: List of results from sparse search with 'id' and 'similarity'
            k: RRF parameter (default 60)
        
        Returns:
            Ranked list of results with combined scores
        """
        scores = {}
        result_map = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results, 1):
            chunk_id = result.get('id') or result.get('chunk_id')
            if not chunk_id:
                continue
            
            rrf_score = 1.0 / (k + rank)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score
            
            # Store result if not already stored
            if chunk_id not in result_map:
                result_map[chunk_id] = result.copy()
                result_map[chunk_id]['dense_rank'] = rank
                result_map[chunk_id]['dense_score'] = result.get('similarity', 0.0)
        
        # Process sparse results
        for rank, result in enumerate(sparse_results, 1):
            chunk_id = result.get('id') or result.get('chunk_id')
            if not chunk_id:
                continue
            
            rrf_score = 1.0 / (k + rank)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score
            
            # Update result if exists, otherwise create
            if chunk_id in result_map:
                result_map[chunk_id]['sparse_rank'] = rank
                result_map[chunk_id]['sparse_score'] = result.get('similarity', 0.0)
            else:
                result_map[chunk_id] = result.copy()
                result_map[chunk_id]['sparse_rank'] = rank
                result_map[chunk_id]['sparse_score'] = result.get('similarity', 0.0)
        
        # Sort by combined RRF score
        ranked_results = []
        for chunk_id, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            result = result_map[chunk_id]
            result['rrf_score'] = rrf_score
            result['combined_similarity'] = rrf_score  # For compatibility
            ranked_results.append(result)
        
        return ranked_results
    
    def weighted_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Combine dense and sparse results using weighted fusion.
        
        Args:
            dense_results: List of results from dense search
            sparse_results: List of results from sparse search
            dense_weight: Weight for dense similarity (default 0.6)
            sparse_weight: Weight for sparse similarity (default 0.4)
        
        Returns:
            Ranked list of results with combined scores
        """
        scores = {}
        result_map = {}
        
        # Normalize weights
        total_weight = dense_weight + sparse_weight
        dense_weight = dense_weight / total_weight
        sparse_weight = sparse_weight / total_weight
        
        # Process dense results
        for result in dense_results:
            chunk_id = result.get('id') or result.get('chunk_id')
            if not chunk_id:
                continue
            
            similarity = result.get('similarity', 0.0)
            weighted_score = similarity * dense_weight
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weighted_score
            
            if chunk_id not in result_map:
                result_map[chunk_id] = result.copy()
                result_map[chunk_id]['dense_score'] = similarity
        
        # Process sparse results
        for result in sparse_results:
            chunk_id = result.get('id') or result.get('chunk_id')
            if not chunk_id:
                continue
            
            similarity = result.get('similarity', 0.0)
            weighted_score = similarity * sparse_weight
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weighted_score
            
            if chunk_id in result_map:
                result_map[chunk_id]['sparse_score'] = similarity
            else:
                result_map[chunk_id] = result.copy()
                result_map[chunk_id]['sparse_score'] = similarity
        
        # Sort by combined score
        ranked_results = []
        for chunk_id, combined_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            result = result_map[chunk_id]
            result['combined_similarity'] = combined_score
            ranked_results.append(result)
        
        return ranked_results

