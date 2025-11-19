"""
RAG (Retrieval-Augmented Generation) Service.
Handles vector database operations, embeddings, and retrieval with filtering.
"""
import json
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Any
from pathlib import Path
from backend.config import get_settings
from loguru import logger

settings = get_settings()


class RAGService:
    """RAG service for knowledge base retrieval."""
    
    def __init__(self, vendor_id: Optional[str] = None):
        """Initialize RAG service with vector database and embedding model."""
        self.settings = settings
        self.vendor_id = vendor_id or settings.default_vendor_id
        self.embedding_model = None
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """Initialize embedding model and vector database."""
        try:
            # Initialize embedding model
            logger.info(f"Loading embedding model: {self.settings.embedding_model}")
            
            # Use offline mode if enabled
            if self.settings.embedding_offline_mode:
                from backend.services.offline_model_manager import OfflineModelManager
                model_manager = OfflineModelManager(cache_dir=self.settings.embedding_cache_dir)
                
                # Try to load from cache first
                model = model_manager.load_embedding_model_offline(self.settings.embedding_model)
                if model:
                    self.embedding_model = model
                else:
                    # Fallback to normal loading (will cache automatically)
                    logger.warning("Model not in cache, loading from Hugging Face (will cache for offline use)")
                    os.environ['TRANSFORMERS_CACHE'] = self.settings.embedding_cache_dir
                    os.environ['HF_HOME'] = self.settings.embedding_cache_dir
                    self.embedding_model = SentenceTransformer(
                        self.settings.embedding_model,
                        device=self.settings.embedding_device,
                        cache_folder=self.settings.embedding_cache_dir
                    )
            else:
                self.embedding_model = SentenceTransformer(
                    self.settings.embedding_model,
                    device=self.settings.embedding_device
                )
            
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
                metadata={"description": collection_desc, "vendor_id": self.vendor_id}
            )
            
            # Auto-load knowledge base if collection is empty
            if self.collection.count() == 0:
                logger.info(f"Collection is empty, auto-loading knowledge base for vendor {self.vendor_id}")
                try:
                    self.load_knowledge_base()
                except Exception as e:
                    logger.warning(f"Failed to auto-load knowledge base for vendor {self.vendor_id}: {e}")
            
            logger.info(f"RAG service initialized successfully for vendor {self.vendor_id} (collection: {collection_name}, chunks: {self.collection.count()})")
            
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
                
                # Generate embedding
                embedding = self.embedding_model.encode(
                    content,
                    show_progress_bar=False
                ).tolist()
                
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
                
                ids.append(chunk_id)
                documents.append(content)
                metadatas.append(metadata)
                embeddings.append(embedding)
            
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
        Retrieve relevant chunks with improved filtering for rental vs sale queries.
        """
        """
        Retrieve relevant chunks for a query.
        
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
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                query,
                show_progress_bar=False
            ).tolist()
            
            # Build where clause for filtering
            # Note: We don't filter by vendor_id since each vendor has its own collection
            # The collection itself is vendor-specific, so no need for vendor_id filter
            where_clause = {}
            if filters:
                where_clause.update(filters)
            # Removed vendor_id filter - collection is already vendor-specific
            
            # Enhanced filtering: if query mentions "rental", prioritize rental chunks
            query_lower = query.lower()
            # Note: We don't filter here, but we'll boost rental chunks in retrieval
            # The LLM prompt will handle the distinction
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause if where_clause else None
            )
            
            # Format results
            retrieved_chunks = []
            if results["ids"] and len(results["ids"][0]) > 0:
                # Apply similarity threshold (more lenient)
                # Lower threshold for better retrieval
                # Note: ChromaDB uses cosine distance, similarity = 1 - distance
                # Distance can be > 1, making similarity negative
                threshold = max(-0.5, self.settings.rag_similarity_threshold - 0.3)  # More lenient for negative similarities
                
                for i in range(len(results["ids"][0])):
                    chunk = {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "similarity": 1 - results["distances"][0][i] if results.get("distances") else None
                    }
                    
                    # Accept if similarity meets threshold OR if it's the best match (top result)
                    if chunk["similarity"] is not None:
                        if chunk["similarity"] >= threshold or i == 0:  # Always include top result
                            retrieved_chunks.append(chunk)
                    elif i == 0:  # Include top result even if similarity is None
                        retrieved_chunks.append(chunk)
                
                # If still no chunks, force include top result
                if not retrieved_chunks and len(results["ids"][0]) > 0:
                    chunk = {
                        "id": results["ids"][0][0],
                        "content": results["documents"][0][0],
                        "metadata": results["metadatas"][0][0],
                        "distance": results["distances"][0][0] if results.get("distances") else None,
                        "similarity": 1 - results["distances"][0][0] if results.get("distances") else None
                    }
                    retrieved_chunks.append(chunk)
            
            logger.debug(f"Retrieved {len(retrieved_chunks)} chunks for query: {query[:50]}...")
            return retrieved_chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
    
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

