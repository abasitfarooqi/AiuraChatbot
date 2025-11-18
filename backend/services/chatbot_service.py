"""
Main Chatbot Service.
Orchestrates RAG, LLM, and Memory services for complete chatbot functionality.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.services.rag_service import RAGService
from backend.services.llm_service import LLMService
from backend.services.memory_service import MemoryService
from backend.models.database import User, Chat, Message, TokenUsage
from backend.config import get_settings
from loguru import logger
import uuid
from datetime import datetime

settings = get_settings()


class ChatbotService:
    """Main chatbot service orchestrating all components."""
    
    def __init__(self, db: Session):
        """Initialize chatbot service."""
        self.db = db
        self.rag_service = RAGService()
        self.llm_service = LLMService(db=db)  # Pass db to load active model
        self.memory_service = MemoryService(db)
        self.settings = settings
    
    def get_system_prompt(self) -> str:
        """Get system prompt for LLM."""
        return """You are the Neguinho Motors chatbot assistant. You help customers with bike rentals, sales, finance, servicing, MOT testing, delivery, accessories, and company information.

    DOMAIN RESTRICTION:
   - ONLY answer questions about Neguinho Motors services
   - For out-of-domain queries, politely redirect: "I can only assist with bike rentals, sales, finance, servicing, and company policies related to Neguinho Motors. How can I help you with our services?" """
    
    async def process_message(
        self,
        user_id: str,
        chat_id: str,
        message: str,
        vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and generate response.
        
        Args:
            user_id: User identifier
            chat_id: Chat session ID
            message: User message
            vendor_id: Optional vendor ID for multi-vendor support
        
        Returns:
            Dict with response and metadata
        """
        try:
            # Get or create user and chat first (needed for response)
            user = self._get_or_create_user(user_id, vendor_id or settings.default_vendor_id)
            chat = self._get_or_create_chat(chat_id, user_id, vendor_id or settings.default_vendor_id)
            
            # Save user message
            user_message = self._save_message(chat_id, "user", message)
            
            # Check domain relevance
            if not self.rag_service.is_domain_relevant(message):
                # Save assistant response for out-of-domain
                assistant_message = self._save_message(
                    chat_id,
                    "assistant",
                    "I can only assist with bike rentals, sales, finance, deposit, warranty, and company policies related to Neguinho Motors. How can I help you with our services?",
                    tokens_used=0
                )
                return {
                    "response": "I can only assist with bike rentals, sales, finance, deposit, warranty, and company policies related to Neguinho Motors. How can I help you with our services?",
                    "chat_id": chat_id,
                    "message_id": assistant_message.message_id,
                    "is_domain_relevant": False,
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0
                }
            
            # Get conversation context (last 3-4 messages for better context)
            context = self.memory_service.get_conversation_context(chat_id)
            
            # Check if current question is complete and topic-changing
            is_complete_question, topic_changed, current_topics = self._analyze_question_completeness(message, context)
            
            # Build query: use only current message if it's complete and topic-changing,
            # otherwise use enhanced query with conversation history
            if is_complete_question and topic_changed:
                # User asked a complete question about a different topic - use only current question
                query_for_rag = message
            else:
                # Incomplete or ambiguous question - use conversation history for context
                query_for_rag = self._build_enhanced_query(message, context)
            
            # Retrieve relevant chunks from RAG
            retrieved_chunks = self.rag_service.retrieve(
                query=query_for_rag,
                vendor_id=vendor_id or settings.default_vendor_id
            )
            
            # Build context for LLM
            context_text = ""
            if retrieved_chunks:
                context_text = "\n\n".join([
                    f"[{i+1}] {chunk['content']}"
                    for i, chunk in enumerate(retrieved_chunks)
                ])
            else:
                # Try a broader search with lower threshold
                broader_chunks = self.rag_service.retrieve(
                    query=message,
                    top_k=3,
                    vendor_id=vendor_id or settings.default_vendor_id
                )
                if broader_chunks:
                    context_text = "\n\n".join([
                        f"[{i+1}] {chunk['content']}"
                        for i, chunk in enumerate(broader_chunks)
                    ])
                else:
                    # Use general company information as fallback
                    context_text = "Neguinho Motors is a London-based motorcycle business specialising in Honda & Yamaha scooters and motorcycles. Services: bike rentals, sales, finance, servicing, MOT testing, delivery. Contact: enquiries@neguinhomotors.co.uk or 0208 314 1498. Opening hours: Monday-Saturday 9am-6pm."
            
            # Prepare messages for LLM
            messages = []
            if context:
                messages.extend(context[-10:])  # Last 10 messages for context
            
            # Add current query with better context formatting
            if context_text:
                # Enhanced prompt with detailed formatting instructions
                user_message_content = f"""Answer the question using ONLY the information provided below.

INFORMATION:
{context_text}

QUESTION: {message}

ANSWER (format with proper line breaks and structure):"""
            else:
                user_message_content = f"Question: {message}\n\nPlease provide a helpful, well-structured answer with proper formatting."
            
            messages.append({
                "role": "user",
                "content": user_message_content
            })
            
            # Generate response
            llm_response = await self.llm_service.generate(
                messages=messages,
                system_prompt=self.get_system_prompt()
            )
            
            response_content = llm_response.get("content", "")
            tokens_used = llm_response.get("tokens_used", 0)
            
            # Post-process response for better structure
            response_content = self._format_response(response_content, message, retrieved_chunks)
            
            # Save assistant message
            assistant_message = self._save_message(
                chat_id,
                "assistant",
                response_content,
                tokens_used=tokens_used,
                model_used=llm_response.get("model_used"),
                message_metadata={
                    "retrieved_chunks": len(retrieved_chunks),
                    "provider": llm_response.get("provider")
                }
            )
            
            # Update memory
            entities = self.memory_service.extract_entities(message, retrieved_chunks)
            self.memory_service.update_memory(
                chat_id=chat_id,
                entities=entities,
                intent="query"
            )
            
            # Track token usage
            if self.settings.token_tracking_enabled:
                self._track_token_usage(
                    user_id=user_id,
                    chat_id=chat_id,
                    tokens_used=tokens_used,
                    model=llm_response.get("model_used"),
                    credits_used=self._calculate_credits(tokens_used)
                )
            
            # Update user credits
            if self.settings.credit_system_enabled:
                credits_used = self._calculate_credits(tokens_used)
                user.credits -= credits_used
                self.db.commit()
            
            # Generate helpful suggestions based on conversation history and current topic
            # Only show suggestions if question was incomplete/ambiguous (not topic-changing)
            suggestions = []
            if not (is_complete_question and topic_changed):
                suggestions = self._generate_suggestions(chat_id, message, retrieved_chunks, current_topics=current_topics)
            
            return {
                "response": response_content,
                "chat_id": chat_id,
                "message_id": assistant_message.message_id,
                "tokens_used": tokens_used,
                "credits_used": self._calculate_credits(tokens_used),
                "model_used": llm_response.get("model_used"),
                "retrieved_chunks": len(retrieved_chunks),
                "is_domain_relevant": True,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            # Ensure we have chat_id even on error
            try:
                chat = self._get_or_create_chat(chat_id, user_id, vendor_id or settings.default_vendor_id)
                error_message = self._save_message(
                    chat_id,
                    "assistant",
                    "I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at enquiries@neguinhomotors.co.uk",
                    tokens_used=0
                )
                return {
                    "response": "I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at enquiries@neguinhomotors.co.uk",
                    "chat_id": chat_id,
                    "message_id": error_message.message_id,
                    "error": str(e),
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0,
                    "is_domain_relevant": True
                }
            except:
                # Fallback if even chat creation fails
                return {
                    "response": "I'm sorry, I'm experiencing technical difficulties. Please try again later or contact us at enquiries@neguinhomotors.co.uk",
                    "chat_id": chat_id or f"error_{user_id}",
                    "message_id": "",
                    "error": str(e),
                    "tokens_used": 0,
                    "credits_used": 0,
                    "model_used": "",
                    "retrieved_chunks": 0,
                    "is_domain_relevant": True
                }
    
    def _get_or_create_user(self, user_id: str, vendor_id: str) -> User:
        """Get or create user."""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                vendor_id=vendor_id,
                credits=self.settings.default_user_credits
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def _get_or_create_chat(self, chat_id: str, user_id: str, vendor_id: str) -> Chat:
        """Get or create chat session."""
        chat = self.db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(
                chat_id=chat_id,
                user_id=user_id,
                vendor_id=vendor_id
            )
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
        return chat
    
    def _save_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        model_used: Optional[str] = None,
        message_metadata: Optional[Dict] = None
    ) -> Message:
        """Save message to database."""
        message = Message(
            message_id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            credits_used=self._calculate_credits(tokens_used),
            model_used=model_used,
            message_metadata=message_metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def _track_token_usage(
        self,
        user_id: str,
        chat_id: str,
        tokens_used: int,
        model: str,
        credits_used: int
    ):
        """Track token usage."""
        usage = TokenUsage(
            user_id=user_id,
            chat_id=chat_id,
            model=model,
            tokens_total=tokens_used,
            credits_used=credits_used
        )
        self.db.add(usage)
        self.db.commit()
    
    def _calculate_credits(self, tokens: int) -> int:
        """Calculate credits used based on tokens."""
        return max(1, tokens // 100)  # 1 credit per 100 tokens, minimum 1
    
    def _analyze_question_completeness(self, current_message: str, context: List[Dict]) -> tuple[bool, bool, set]:
        """
        Analyze if the current question is complete and if it changes the topic.
        
        Args:
            current_message: Current user message
            context: Conversation context (last messages)
            
        Returns:
            Tuple of (is_complete_question, topic_changed, current_topics)
        """
        if not context or len(context) < 2:
            # No context, treat as new topic
            current_topics = self._extract_topics(current_message)
            return self._is_complete_question(current_message), True, current_topics
        
        # Extract topics from current message
        current_topics = self._extract_topics(current_message)
        
        # Extract topics from recent conversation (last 3-4 user messages)
        recent_topics = set()
        recent_messages = []
        for msg in context[-6:]:  # Get last 6 messages
            if isinstance(msg, dict) and msg.get("role") == "user":
                msg_content = msg.get("content", "")
                recent_messages.append(msg_content)
                msg_topics = self._extract_topics(msg_content)
                recent_topics.update(msg_topics)
        
        # Check if question is complete (has question words, specific service mention, etc.)
        is_complete = self._is_complete_question(current_message)
        
        # Check if topic changed
        topic_changed = False
        if current_topics and recent_topics:
            # If current message has different topics than recent conversation
            if not current_topics.intersection(recent_topics):
                topic_changed = True
        elif current_topics and not recent_topics:
            # Current message has topics but recent conversation doesn't - likely new topic
            topic_changed = True
        elif not current_topics and recent_topics:
            # Current message has no clear topics but recent conversation does - likely continuation
            topic_changed = False
        else:
            # Both have no clear topics - check if question is complete
            topic_changed = is_complete
        
        return is_complete, topic_changed, current_topics
    
    def _extract_topics(self, message: str) -> set:
        """
        Extract topics from a message.
        
        Args:
            message: User message
            
        Returns:
            Set of topic strings
        """
        message_lower = message.lower()
        topics = set()
        
        # Define topic keywords
        topic_keywords = {
            "rental": ["rental", "rent", "hire", "leasing", "weekly", "monthly rental"],
            "sale": ["sale", "buy", "purchase", "price", "cost", "for sale"],
            "finance": ["finance", "emi", "payment plan", "installment", "credit", "loan"],
            "servicing": ["service", "servicing", "repair", "maintenance", "fix"],
            "mot": ["mot", "test", "certificate"],
            "delivery": ["delivery", "deliver", "transport", "shipping"],
            "accessories": ["accessories", "accessory", "helmet", "gear", "equipment"],
            "accident": ["accident", "crash", "claim", "insurance"],
            "branch": ["branch", "location", "address", "where"],
            "opening": ["opening", "hours", "time", "when open"]
        }
        
        # Detect topics
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.add(topic)
        
        return topics
    
    def _is_complete_question(self, message: str) -> bool:
        """
        Check if a question is complete (has enough context to answer independently).
        
        Args:
            message: User message
            
        Returns:
            True if question is complete, False if ambiguous/incomplete
        """
        message_lower = message.lower().strip()
        
        # Complete question indicators
        complete_indicators = [
            # Question words with specific service mentions
            ("what", ["service", "price", "cost", "bike", "model", "opening", "hours", "branch", "location"]),
            ("how", ["much", "long", "many", "do", "can"]),
            ("where", ["are", "is", "do", "can"]),
            ("when", ["are", "is", "do", "can"]),
            ("do you", ["offer", "have", "sell", "rent", "provide"]),
            ("tell me", ["about", "more"]),
            ("can i", ["rent", "buy", "get", "test"]),
            # Specific service mentions with question structure
            ("rental", ["price", "bike", "cost", "period", "term"]),
            ("finance", ["option", "rate", "term", "deposit", "available"]),
            ("sale", ["bike", "price", "available", "model"]),
        ]
        
        # Check for complete question patterns
        for indicator, keywords in complete_indicators:
            if indicator in message_lower:
                if any(keyword in message_lower for keyword in keywords):
                    return True
        
        # Check for very short/ambiguous questions
        words = message_lower.split()
        if len(words) <= 2:
            return False
        
        # Check for specific service mentions with enough detail
        service_mentions = ["rental", "sale", "finance", "service", "servicing", "mot", "delivery"]
        if any(service in message_lower for service in service_mentions):
            if len(words) >= 4:  # Has enough words to be specific
                return True
        
        # Default: if message is long enough and has question structure, consider it complete
        if len(words) >= 5 and ("?" in message or any(q in message_lower for q in ["what", "how", "where", "when", "do", "can"])):
            return True
        
        return False
    
    def _build_enhanced_query(self, current_message: str, context: List[Dict]) -> str:
        """
        Build enhanced query using conversation history for better RAG retrieval.
        Used when question is incomplete or ambiguous.
        
        Args:
            current_message: Current user message
            context: Conversation context (last messages)
            
        Returns:
            Enhanced query string
        """
        if not context or len(context) < 2:
            return current_message
        
        # Get last 3-4 user messages for context
        recent_messages = []
        for msg in context[-6:]:  # Get last 6 messages (3 user + 3 assistant)
            if isinstance(msg, dict) and msg.get("role") == "user":
                recent_messages.append(msg.get("content", ""))
        
        # Combine recent messages with current message
        if recent_messages:
            # Take last 3-4 user messages
            recent_context = " ".join(recent_messages[-4:])
            enhanced_query = f"{recent_context} {current_message}"
            return enhanced_query.strip()
        
        return current_message
    
    def _generate_suggestions(self, chat_id: str, current_message: str, chunks: List[Dict], current_topics: Optional[set] = None) -> List[str]:
        """
        Generate helpful question suggestions based on conversation history and retrieved chunks.
        Sales-oriented: suggests other services when user has asked about multiple topics.
        
        Args:
            chat_id: Chat session ID
            current_message: Current user message
            chunks: Retrieved RAG chunks
            current_topics: Current message topics (if already extracted)
            
        Returns:
            List of suggested questions
        """
        suggestions = []
        
        try:
            # Get all user messages from chat history to analyze conversation
            all_user_messages = self.db.query(Message).filter(
                Message.chat_id == chat_id,
                Message.role == "user"
            ).order_by(
                Message.created_at.asc()
            ).all()
            
            # Extract all topics from entire conversation
            conversation_topics = set()
            topic_history = []  # Track topic sequence
            
            for msg in all_user_messages:
                msg_topics = self._extract_topics(msg.content)
                if msg_topics:
                    conversation_topics.update(msg_topics)
                    topic_history.extend(list(msg_topics))
            
            # Add current message topics
            if current_topics:
                topics = current_topics
            else:
                topics = self._extract_topics(current_message)
            
            conversation_topics.update(topics)
            if topics:
                topic_history.extend(list(topics))
            
            # Count unique services asked about
            service_topics = {"rental", "sale", "finance", "servicing", "mot", "delivery", "accessories", "accident"}
            asked_services = conversation_topics.intersection(service_topics)
            num_services_asked = len(asked_services)
            
            # Get last question's topics for primary suggestions
            last_question_topics = topics if topics else set()
            
            # Sales strategy: If user has asked about 2+ different services, suggest other services
            # This happens when 4th question (or later) is about another service
            if num_services_asked >= 2 and len(all_user_messages) >= 3:
                # User is exploring multiple services - suggest complementary services
                all_services = {
                    "rental": "Tell me about bike rental options",
                    "sale": "What bikes do you have for sale?",
                    "finance": "Do you offer finance options?",
                    "servicing": "What servicing do you offer?",
                    "mot": "Do you do MOT testing?",
                    "delivery": "Do you offer delivery service?",
                    "accessories": "What accessories do you sell?",
                    "accident": "Do you offer accident management?"
                }
                
                # Suggest services they haven't asked about yet
                unasked_services = set(all_services.keys()) - asked_services
                
                if unasked_services:
                    # Sales-oriented suggestions
                    suggestions.append("We also offer other services - would you like to know more?")
                    
                    # Add 2-3 specific service suggestions
                    for service in list(unasked_services)[:3]:
                        if service in all_services:
                            suggestions.append(all_services[service])
                else:
                    # They've asked about all services - suggest related questions
                    if "rental" in asked_services:
                        suggestions.append("What are the rental prices for each bike?")
                        suggestions.append("What documents do I need for rental?")
                    if "sale" in asked_services:
                        suggestions.append("Can I test ride a bike?")
                        suggestions.append("Do you offer part exchange?")
            else:
                # User is focused on one service - suggest related questions based on LAST question
                # Primary suggestions based on current/last question
                if "rental" in last_question_topics:
                    suggestions.append("What are the rental prices for each bike?")
                    suggestions.append("What documents do I need for rental?")
                    suggestions.append("What is the minimum rental period?")
                    # Sales approach: suggest other services if only asked about one service
                    if num_services_asked == 1:
                        suggestions.append("We also offer bike sales and finance - would you like to know more?")
                elif "sale" in last_question_topics:
                    suggestions.append("What bikes are available for sale?")
                    suggestions.append("Do you offer finance options?")
                    suggestions.append("Can I test ride a bike?")
                    if num_services_asked == 1:
                        suggestions.append("We also offer rentals and servicing - interested?")
                elif "finance" in last_question_topics:
                    suggestions.append("What is the interest rate?")
                    suggestions.append("How long is the finance term?")
                    suggestions.append("What deposit is required?")
                    if num_services_asked == 1:
                        suggestions.append("We also offer bike sales and rentals - want to know more?")
                elif "servicing" in last_question_topics:
                    suggestions.append("What services do you offer?")
                    suggestions.append("How much does a service cost?")
                    suggestions.append("Do you collect bikes for service?")
                    if num_services_asked == 1:
                        suggestions.append("We also offer MOT testing and repairs - need more info?")
                elif "mot" in last_question_topics:
                    suggestions.append("How much does an MOT cost?")
                    suggestions.append("How long does an MOT take?")
                    suggestions.append("Do you offer pre-MOT checks?")
                    if num_services_asked == 1:
                        suggestions.append("We also offer servicing and repairs - want details?")
                elif "delivery" in last_question_topics:
                    suggestions.append("How much does delivery cost?")
                    suggestions.append("How long does delivery take?")
                    suggestions.append("Do you deliver nationwide?")
                    if num_services_asked == 1:
                        suggestions.append("We also offer bike sales and rentals - interested?")
                else:
                    # General suggestions based on chunks or default
                    chunk_keywords = set()
                    for chunk in chunks[:3]:  # Check top 3 chunks
                        content = chunk.get("content", "").lower()
                        if "rental" in content:
                            chunk_keywords.add("rental")
                        if "sale" in content or "buy" in content:
                            chunk_keywords.add("sale")
                        if "finance" in content:
                            chunk_keywords.add("finance")
                        if "service" in content:
                            chunk_keywords.add("servicing")
                    
                    if chunk_keywords:
                        if "rental" in chunk_keywords:
                            suggestions.append("Tell me about rental bikes")
                        if "sale" in chunk_keywords:
                            suggestions.append("What bikes do you sell?")
                        if "finance" in chunk_keywords:
                            suggestions.append("Do you offer finance?")
                    
                    if not suggestions:
                        # Default helpful suggestions
                        suggestions = [
                            "What services do you offer?",
                            "Tell me about rental bikes",
                            "What are your opening hours?",
                            "Where are your branches located?"
                        ]
            
            # Add 5th suggestion based on last 4 questions
            if len(all_user_messages) >= 4:
                # Get last 4 user questions
                last_4_questions = all_user_messages[-4:] if len(all_user_messages) >= 4 else all_user_messages
                
                # Extract topics from last 4 questions
                last_4_topics = set()
                last_4_question_texts = []
                for msg in last_4_questions:
                    msg_topics = self._extract_topics(msg.content)
                    last_4_topics.update(msg_topics)
                    last_4_question_texts.append(msg.content.lower())
                
                # Generate intelligent 5th suggestion based on patterns
                q5_suggestion = None
                
                # If they've been asking about rental multiple times
                rental_count = sum(1 for q in last_4_question_texts if "rental" in q or "rent" in q)
                if rental_count >= 2:
                    if "deposit" not in " ".join(last_4_question_texts):
                        q5_suggestion = "What deposit is required for rental?"
                    elif "insurance" not in " ".join(last_4_question_texts):
                        q5_suggestion = "What insurance do I need for rental?"
                    elif "delivery" not in " ".join(last_4_question_texts):
                        q5_suggestion = "Do you deliver rental bikes?"
                
                # If they've been asking about sale multiple times
                sale_count = sum(1 for q in last_4_question_texts if "sale" in q or "buy" in q or "purchase" in q)
                if sale_count >= 2:
                    if "finance" not in " ".join(last_4_question_texts):
                        q5_suggestion = "Do you offer finance for bike purchases?"
                    elif "test" not in " ".join(last_4_question_texts) and "ride" not in " ".join(last_4_question_texts):
                        q5_suggestion = "Can I test ride before buying?"
                    elif "warranty" not in " ".join(last_4_question_texts):
                        q5_suggestion = "What warranty do you offer on bikes?"
                
                # If they've been asking about finance
                finance_count = sum(1 for q in last_4_question_texts if "finance" in q or "emi" in q or "payment" in q)
                if finance_count >= 2:
                    if "interest" not in " ".join(last_4_question_texts) and "rate" not in " ".join(last_4_question_texts):
                        q5_suggestion = "What is the interest rate?"
                    elif "term" not in " ".join(last_4_question_texts) and "period" not in " ".join(last_4_question_texts):
                        q5_suggestion = "How long is the finance term?"
                    elif "deposit" not in " ".join(last_4_question_texts):
                        q5_suggestion = "What deposit is required for finance?"
                
                # If they've been asking about servicing
                service_count = sum(1 for q in last_4_question_texts if "service" in q or "repair" in q or "maintenance" in q)
                if service_count >= 2:
                    if "cost" not in " ".join(last_4_question_texts) and "price" not in " ".join(last_4_question_texts):
                        q5_suggestion = "How much does a service cost?"
                    elif "collect" not in " ".join(last_4_question_texts) and "pickup" not in " ".join(last_4_question_texts):
                        q5_suggestion = "Do you collect bikes for service?"
                    elif "mot" not in " ".join(last_4_question_texts):
                        q5_suggestion = "Do you also do MOT testing?"
                
                # If they've asked about multiple different services, suggest a related one
                if len(last_4_topics.intersection(service_topics)) >= 2:
                    if "delivery" not in last_4_topics:
                        q5_suggestion = "Do you offer delivery service?"
                    elif "accessories" not in last_4_topics:
                        q5_suggestion = "What accessories do you sell?"
                    elif "accident" not in last_4_topics:
                        q5_suggestion = "Do you offer accident management?"
                
                # If no specific pattern, suggest based on most common topic
                if not q5_suggestion and last_4_topics:
                    most_common_topic = max(last_4_topics, key=lambda t: sum(1 for q in last_4_question_texts if t in q))
                    if most_common_topic == "rental":
                        q5_suggestion = "What bikes are available for rental?"
                    elif most_common_topic == "sale":
                        q5_suggestion = "What bikes do you have for sale?"
                    elif most_common_topic == "finance":
                        q5_suggestion = "What are the finance options?"
                    elif most_common_topic == "servicing":
                        q5_suggestion = "What services do you offer?"
                
                # Add Q5 if we have a good suggestion
                if q5_suggestion and q5_suggestion not in suggestions:
                    suggestions.append(q5_suggestion)
            
            # Limit to 5 suggestions
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            # Return default suggestions on error
            return [
                "What services do you offer?",
                "Tell me about rental bikes",
                "What are your opening hours?"
            ]
    
    def _format_response(self, response: str, query: str, chunks: List[Dict]) -> str:
        """
        Post-process response to ensure consistent formatting and structure.
        
        Args:
            response: Raw LLM response
            query: Original user query
            chunks: Retrieved RAG chunks (used for context-aware formatting)
            
        Returns:
            Formatted response string
        """
        import re
        
        if not response or not isinstance(response, str):
            return response or ""
        
        # Remove excessive blank lines (more than 2 consecutive)
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Ensure proper spacing around bullet points
        response = re.sub(r'(\S)(•)', r'\1 \2', response)  # Add space before bullet if missing
        response = re.sub(r'(•)(\S)', r'\1 \2', response)  # Add space after bullet if missing
        
        # Ensure proper spacing around prices
        response = re.sub(r'£(\d+)', r'£\1', response)  # Ensure no space after £
        response = re.sub(r'(\d+)(/[a-z]+)', r'\1\2', response)  # Ensure no space before /week, /month, etc.
        
        # Ensure line breaks after section headers (if they end with :)
        response = re.sub(r'([A-Z][^:]*:)([^\n])', r'\1\n\2', response)
        
        # Fix line breaking issues - ensure proper line breaks
        # Add line breaks after periods that are followed by capital letters (new sentences)
        # But avoid breaking on abbreviations like "U.K." or "A.M."
        response = re.sub(r'\.([A-Z][a-z])', r'.\n\1', response)
        
        # Ensure line breaks after list items (bullet points)
        # Each bullet point should be on its own line
        response = re.sub(r'(•)\s*([^\n])', r'\1 \2', response)
        
        # Ensure line breaks before section headers (lines starting with capital letters followed by colon)
        # But only if not already on a new line
        response = re.sub(r'([^\n])([A-Z][A-Za-z\s]{3,}:)', r'\1\n\n\2', response)
        
        # Ensure each bullet point item is on a separate line
        response = re.sub(r'(•[^\n•]+)(•)', r'\1\n\2', response)
        
        # Normalize whitespace (but preserve intentional line breaks)
        lines = response.split('\n')
        formatted_lines = []
        for line in lines:
            # Strip trailing whitespace but preserve leading (for indentation)
            line = line.rstrip()
            if line:  # Only add non-empty lines
                formatted_lines.append(line)
            elif formatted_lines and formatted_lines[-1]:  # Add blank line only if previous line wasn't blank
                formatted_lines.append('')
        
        if not formatted_lines:
            return response.strip()
        
        response = '\n'.join(formatted_lines)
        
        # Fix any double line breaks that might have been created
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        # Ensure response ends with proper punctuation if it's a sentence
        if response and len(response) > 0:
            # Check if last character needs punctuation
            if response[-1] not in '.!?:':
                # Check if last line looks like it should end with punctuation
                response_lines = response.split('\n')
                if response_lines:
                    last_line = response_lines[-1].strip()
                    if last_line and not last_line.endswith(('•', '-', ')', ':')):
                        # Only add if it's a complete sentence (has verb-like structure)
                        if any(word in last_line.lower() for word in ['contact', 'phone', 'email', 'call', 'visit', 'reach']):
                            response += '.'
        
        # Add contact information if not present and response is about services
        if query and isinstance(query, str):
            query_lower = query.lower()
            if any(keyword in query_lower for keyword in ['service', 'rental', 'sale', 'finance', 'opening', 'branch', 'contact', 'help']):
                if '0208 314 1498' not in response and 'enquiries@neguinhomotors.co.uk' not in response:
                    # Only add if response is substantial (more than 50 chars)
                    if len(response) > 50:
                        response += "\n\nContact: 0208 314 1498 or enquiries@neguinhomotors.co.uk"
        
        # Clean up any remaining formatting issues
        response = response.strip()
        
        # Final check: ensure response is not empty
        if not response:
            return "I'm here to help! How can I assist you today?"
        
        return response

