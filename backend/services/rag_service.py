"""
RAG (Retrieval-Augmented Generation) Service with Multi-Vector Search (MVS).
Handles vector database operations, embeddings, and hybrid retrieval with filtering.
"""
import json
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Any
from pathlib import Path
from backend.config import get_settings
from backend.services.mvs_service import MVSService
from loguru import logger

settings = get_settings()


class RAGService:
    """RAG service for knowledge base retrieval with Multi-Vector Search support."""
    
    def __init__(self, vendor_id: Optional[str] = None):
        """Initialize RAG service with vector database and embedding model."""
        self.settings = settings
        self.vendor_id = vendor_id or settings.default_vendor_id
        self.embedding_model = None
        self.mvs_service = None
        self.client = None
        self.collection = None
        self.mvs_enabled = False
        self._initialize()
    
    def _initialize(self):
        """Initialize embedding model, MVS service, and vector database."""
        try:
            # Initialize MVS service (includes dense embedding model)
            logger.info("Initializing MVS service...")
            self.mvs_service = MVSService(vendor_id=self.vendor_id)
            self.embedding_model = self.mvs_service.dense_model  # Use MVS dense model
            
            # Check if MVS is enabled in config
            try:
                from backend.utils.vendor_manager import get_vendor_manager
                vendor_manager = get_vendor_manager()
                config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
                unified_config = config_manager.load_config()
                mvs_config = unified_config.get("rag", {}).get("mvs", {})
                self.mvs_enabled = mvs_config.get("enabled", False)
            except Exception as e:
                logger.warning(f"Could not load MVS config, defaulting to disabled: {e}")
                self.mvs_enabled = False
            
            logger.info(f"MVS enabled: {self.mvs_enabled}")
            
            # Initialize ChromaDB
            db_path = Path(self.settings.chroma_db_path)
            db_path.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(db_path),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Get or create collection - use vendor-specific collection
            collection_name = self.settings.chroma_collection_name
            collection_desc = "Knowledge Base"
            
            try:
                from backend.utils.vendor_manager import get_vendor_manager
                vendor_manager = get_vendor_manager()
                # Get vendor-specific collection name
                collection_name = vendor_manager.get_vendor_chroma_collection(self.vendor_id)
                # Get company name for metadata
                config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
                unified_config = config_manager.load_config()
                company_name = unified_config.get("business", {}).get("company_name", "Company")
                collection_desc = f"{company_name} Knowledge Base"
            except Exception as e:
                logger.warning(f"Error loading vendor config for collection: {e}, using default")
            
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": collection_desc, "vendor_id": self.vendor_id, "mvs_enabled": str(self.mvs_enabled)}
            )
            
            # Auto-load knowledge base if collection is empty
            if self.collection.count() == 0:
                logger.info(f"Collection is empty, auto-loading knowledge base for vendor {self.vendor_id}")
                try:
                    self.load_knowledge_base()
                except Exception as e:
                    logger.warning(f"Failed to auto-load knowledge base for vendor {self.vendor_id}: {e}")
            
            logger.info(f"RAG service initialized successfully for vendor {self.vendor_id} (collection: {collection_name}, chunks: {self.collection.count()}, MVS: {self.mvs_enabled})")
            
        except Exception as e:
            logger.error(f"Error initializing RAG service: {e}")
            raise
    
    def load_knowledge_base(self, kb_path: Optional[str] = None):
        """Load knowledge base from JSON and create embeddings."""
        try:
            # If no path provided, use vendor-specific path
            if kb_path is None:
                from backend.utils.vendor_manager import get_vendor_manager
                vendor_manager = get_vendor_manager()
                kb_path = str(vendor_manager.get_vendor_rag_path(self.vendor_id))
            
            kb_file = Path(kb_path)
            if not kb_file.exists():
                logger.warning(f"Knowledge base file not found: {kb_path}")
                return False
            
            with open(kb_file, "r", encoding="utf-8") as f:
                kb_data = json.load(f)
            
            chunks = kb_data.get("chunks", [])
            if not chunks:
                logger.warning("No chunks found in knowledge base")
                return False
            
            # Check if collection already has data
            existing_count = self.collection.count()
            if existing_count > 0:
                # Check if we need to reload (if chunk count doesn't match)
                expected_count = len(chunks)
                if existing_count == expected_count:
                    logger.info(f"Collection already has {existing_count} chunks. Skipping load.")
                    return True
                else:
                    logger.info(f"Collection has {existing_count} chunks but expected {expected_count}. Reloading...")
                    # Clear collection - use vendor-specific collection name
                    from backend.utils.vendor_manager import get_vendor_manager
                    vendor_manager = get_vendor_manager()
                    collection_name = vendor_manager.get_vendor_chroma_collection(self.vendor_id)
                    self.client.delete_collection(name=collection_name)
                    
                    # Get company name for metadata
                    try:
                        config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
                        unified_config = config_manager.load_config()
                        company_name = unified_config.get("business", {}).get("company_name", "Company")
                        collection_desc = f"{company_name} Knowledge Base"
                    except:
                        collection_desc = "Knowledge Base"
                    
                    self.collection = self.client.get_or_create_collection(
                        name=collection_name,
                        metadata={"description": collection_desc, "vendor_id": self.vendor_id}
                    )
            
            # Initialize sparse index if MVS is enabled
            if self.mvs_enabled:
                corpus = [chunk.get("content", "") for chunk in chunks if chunk.get("content")]
                self.mvs_service.initialize_sparse_index(corpus)
                logger.info(f"Initialized sparse index with {len(corpus)} documents")
            
            # Process chunks
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for chunk in chunks:
                chunk_id = chunk.get("symbol", f"chunk_{len(ids)}")
                content = chunk.get("content", "")
                
                if not content:
                    continue
                
                # Generate dense embedding
                dense_embedding = self.mvs_service.generate_dense_embedding(content)
                
                # Generate sparse embedding if MVS is enabled
                sparse_embedding = None
                if self.mvs_enabled:
                    try:
                        sparse_embedding = self.mvs_service.generate_sparse_embedding(content, method="bm25")
                    except Exception as e:
                        logger.warning(f"Failed to generate sparse embedding for chunk {chunk_id}: {e}")
                
                # Prepare metadata
                metadata = {
                    "symbol": chunk.get("symbol", ""),
                    "keyword": chunk.get("keyword", ""),
                    "tags": ",".join(chunk.get("tags", [])),
                    "category": chunk.get("mapping", {}).get("category", ""),
                    "subcategory": chunk.get("mapping", {}).get("subcategory", ""),
                    "priority": chunk.get("mapping", {}).get("priority", ""),
                    "domain": chunk.get("mapping", {}).get("domain", ""),
                    "vendor_id": chunk.get("metadata", {}).get("vendor_id", settings.default_vendor_id),
                    "source": chunk.get("metadata", {}).get("source", ""),
                    "confidence": chunk.get("metadata", {}).get("confidence", "medium")
                }
                
                # Store sparse embedding in metadata if MVS is enabled
                if self.mvs_enabled and sparse_embedding:
                    metadata["sparse_embedding"] = json.dumps(sparse_embedding)
                    metadata["sparse_model"] = "bm25"
                
                ids.append(chunk_id)
                documents.append(content)
                metadatas.append(metadata)
                embeddings.append(dense_embedding)
            
            # Add to collection in batches
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_docs = documents[i:i + batch_size]
                batch_metas = metadatas[i:i + batch_size]
                batch_embeds = embeddings[i:i + batch_size]
                
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas,
                    embeddings=batch_embeds
                )
            
            logger.info(f"Loaded {len(ids)} chunks into vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return False
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        vendor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using Multi-Vector Search (MVS) if enabled, otherwise single embedding.
        
        Args:
            query: User query string
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"category": "services"})
            vendor_id: Vendor ID for multi-vendor filtering
        
        Returns:
            List of retrieved chunks with metadata
        """
        try:
            top_k = top_k or self.settings.rag_top_k
            
            # Use MVS hybrid search if enabled
            if self.mvs_enabled:
                return self._retrieve_mvs(query, top_k, filters)
            else:
                return self._retrieve_single(query, top_k, filters)
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
    
    def _retrieve_single(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve using single dense embedding (legacy method)."""
        # Generate query embedding
        query_embedding = self.mvs_service.generate_dense_embedding(query)
        
        # Build where clause for filtering
        where_clause = {}
        if filters:
            where_clause.update(filters)
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause if where_clause else None
        )
        
        # Format results
        retrieved_chunks = []
        if results["ids"] and len(results["ids"][0]) > 0:
            threshold = max(-0.5, self.settings.rag_similarity_threshold - 0.3)
            
            for i in range(len(results["ids"][0])):
                chunk = {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                    "similarity": 1 - results["distances"][0][i] if results.get("distances") else None
                }
                
                if chunk["similarity"] is not None:
                    if chunk["similarity"] >= threshold or i == 0:
                        retrieved_chunks.append(chunk)
                elif i == 0:
                    retrieved_chunks.append(chunk)
            
            if not retrieved_chunks and len(results["ids"][0]) > 0:
                chunk = {
                    "id": results["ids"][0][0],
                    "content": results["documents"][0][0],
                    "metadata": results["metadatas"][0][0],
                    "distance": results["distances"][0][0] if results.get("distances") else None,
                    "similarity": 1 - results["distances"][0][0] if results.get("distances") else None
                }
                retrieved_chunks.append(chunk)
        
        logger.debug(f"Retrieved {len(retrieved_chunks)} chunks (single embedding) for query: {query[:50]}...")
        return retrieved_chunks
    
    def _retrieve_mvs(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve using Multi-Vector Search (dense + sparse hybrid)."""
        try:
            # Get MVS config
            from backend.utils.vendor_manager import get_vendor_manager
            vendor_manager = get_vendor_manager()
            config_manager = vendor_manager.get_vendor_config_manager(self.vendor_id)
            unified_config = config_manager.load_config()
            mvs_config = unified_config.get("rag", {}).get("mvs", {})
            
            fusion_method = mvs_config.get("fusion_method", "rrf")
            dense_weight = mvs_config.get("dense_weight", 0.6)
            sparse_weight = mvs_config.get("sparse_weight", 0.4)
            rrf_k = mvs_config.get("rrf_k", 60)
            
            # Step 1: Generate multi-vectors for query
            query_dense = self.mvs_service.generate_dense_embedding(query)
            query_sparse = self.mvs_service.generate_sparse_embedding(query, method="bm25")
            
            # Step 2: Dense search (ChromaDB)
            where_clause = {}
            if filters:
                where_clause.update(filters)
            
            dense_results_raw = self.collection.query(
                query_embeddings=[query_dense],
                n_results=top_k * 2,  # Get more results for fusion
                where=where_clause if where_clause else None
            )
            
            # Format dense results
            dense_results = []
            if dense_results_raw["ids"] and len(dense_results_raw["ids"][0]) > 0:
                for i in range(len(dense_results_raw["ids"][0])):
                    chunk = {
                        "id": dense_results_raw["ids"][0][i],
                        "chunk_id": dense_results_raw["ids"][0][i],
                        "content": dense_results_raw["documents"][0][i],
                        "metadata": dense_results_raw["metadatas"][0][i],
                        "distance": dense_results_raw["distances"][0][i] if dense_results_raw.get("distances") else None,
                        "similarity": 1 - dense_results_raw["distances"][0][i] if dense_results_raw.get("distances") else None
                    }
                    dense_results.append(chunk)
            
            # Step 3: Sparse search (in-memory)
            sparse_results = []
            if query_sparse:
                # Get all chunks from collection
                all_chunks = self.collection.get()
                
                # Calculate sparse similarity for each chunk
                chunk_scores = []
                for i, chunk_id in enumerate(all_chunks["ids"]):
                    chunk_metadata = all_chunks["metadatas"][i] if all_chunks.get("metadatas") else {}
                    chunk_content = all_chunks["documents"][i] if all_chunks.get("documents") else ""
                    
                    # Get stored sparse embedding
                    stored_sparse = chunk_metadata.get("sparse_embedding")
                    if stored_sparse:
                        try:
                            chunk_sparse = json.loads(stored_sparse)
                            similarity = self.mvs_service.sparse_similarity(query_sparse, chunk_sparse)
                            
                            chunk_scores.append({
                                "id": chunk_id,
                                "chunk_id": chunk_id,
                                "content": chunk_content,
                                "metadata": chunk_metadata,
                                "similarity": similarity
                            })
                        except Exception as e:
                            logger.debug(f"Error parsing sparse embedding for chunk {chunk_id}: {e}")
                
                # Sort by similarity and take top K
                chunk_scores.sort(key=lambda x: x["similarity"], reverse=True)
                sparse_results = chunk_scores[:top_k * 2]
            
            # Step 4: Fuse results
            if fusion_method == "rrf":
                ranked_chunks = self.mvs_service.reciprocal_rank_fusion(
                    dense_results, sparse_results, k=rrf_k
                )
            else:
                ranked_chunks = self.mvs_service.weighted_fusion(
                    dense_results, sparse_results,
                    dense_weight=dense_weight, sparse_weight=sparse_weight
                )
            
            # Step 5: Apply threshold and return top K
            threshold = max(-0.5, self.settings.rag_similarity_threshold - 0.3)
            retrieved_chunks = []
            
            for chunk in ranked_chunks[:top_k]:
                similarity = chunk.get("combined_similarity") or chunk.get("rrf_score") or chunk.get("similarity", 0.0)
                if similarity >= threshold or len(retrieved_chunks) == 0:  # Always include top result
                    retrieved_chunks.append(chunk)
            
            # Ensure at least one result
            if not retrieved_chunks and ranked_chunks:
                retrieved_chunks.append(ranked_chunks[0])
            
            logger.debug(f"Retrieved {len(retrieved_chunks)} chunks (MVS hybrid) for query: {query[:50]}...")
            return retrieved_chunks
            
        except Exception as e:
            logger.error(f"Error in MVS retrieval: {e}")
            # Fallback to single embedding
            return self._retrieve_single(query, top_k, filters)
    
    def is_domain_relevant(self, query: str) -> bool:
        """Check if query is relevant to the domain."""
        if not self.settings.domain_restriction_enabled:
            return True
        
        query_lower = query.lower().strip()
        
        # Very short queries or greetings should be allowed to pass through
        # They'll be handled by the LLM with context
        greeting_words = ["hi", "hello", "hey", "help", "how are you", "how are", "what's up", "whats up", "good morning", "good afternoon", "good evening"]
        if len(query_lower) <= 3 or any(greeting in query_lower for greeting in greeting_words):
            return True
        
        # Check if query is clearly out of domain
        out_of_domain_keywords = [
            "capital", "country", "weather", "joke", "recipe", "movie", 
            "sport", "football", "cricket", "politics", "news", "stock",
            "bitcoin", "crypto", "university", "school", "education"
        ]
        
        for keyword in out_of_domain_keywords:
            if keyword in query_lower:
                return False
        
        # If query contains company-related terms, it's likely relevant
        # Get company terms from unified config
        try:
            from backend.utils.unified_config_manager import get_unified_config_manager
            config_manager = get_unified_config_manager()
            unified_config = config_manager.load_config()
            business = unified_config.get("business", {})
            company_name = business.get("company_name", "").lower()
            trading_names = [name.lower() for name in business.get("trading_names", [])]
            # Extract key words from company name
            company_terms = [company_name] + trading_names
            # Add common business terms
            company_terms.extend(["motorcycle", "bike", "scooter", "vehicle", "motorbike"])
        except:
            company_terms = ["motorcycle", "bike", "scooter"]
        
        for term in company_terms:
            if term and term in query_lower:
                return True
        
        # Check domain keywords
        domain_keywords = self.settings.domain_keywords_list
        
        # Check if any domain keyword appears in query
        for keyword in domain_keywords:
            if keyword in query_lower:
                return True
        
        # Check for synonyms and related terms
        synonyms = {
            "rental": ["rent", "hire", "leasing", "renting", "rentals"],
            "sale": ["buy", "purchase", "selling", "sales", "price", "cost"],
            "finance": ["payment", "emi", "installment", "credit", "loan"],
            "service": ["servicing", "repair", "maintenance", "fix"],
            "help": ["assist", "support", "information", "details", "tell me", "explain"],
            "location": ["where", "situated", "situate", "located", "address", "place", "places"],
            "branch": ["branches", "location", "locations", "store", "stores", "shop", "shops"]
        }
        
        for main_term, syn_list in synonyms.items():
            if any(syn in query_lower for syn in syn_list):
                return True
        
        # If query asks about "you", "your", "company", "business" - likely relevant
        if any(word in query_lower for word in ["you", "your", "company", "business", "services", "what can", "how can"]):
            return True
        
        # Default: allow through and let RAG/LLM decide
        # Better to be permissive and let the system handle it
        return True
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.settings.chroma_collection_name,
                "embedding_model": self.settings.embedding_model
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

