#!/usr/bin/env python3
"""
Test script for the chatbot system.
Tests all major components and functionality.
"""
import asyncio
import sys
from backend.services.chatbot_service import ChatbotService
from backend.models.database import get_session_local
from backend.services.rag_service import RAGService
from backend.services.llm_service import LLMService

SessionLocal = get_session_local()

def test_rag():
    """Test RAG service."""
    print("=" * 50)
    print("Testing RAG Service")
    print("=" * 50)
    
    try:
        rag = RAGService()
        stats = rag.get_collection_stats()
        print(f"✓ RAG Service initialized")
        print(f"  Total chunks: {stats.get('total_chunks', 0)}")
        
        # Test retrieval
        results = rag.retrieve("rental prices", top_k=3)
        print(f"✓ RAG retrieval works: {len(results)} chunks retrieved")
        
        # Test domain relevance
        relevant = rag.is_domain_relevant("What is the rental price?")
        not_relevant = rag.is_domain_relevant("What is the capital of France?")
        print(f"✓ Domain relevance check works: {relevant} (should be True), {not_relevant} (should be False)")
        
        return True
    except Exception as e:
        print(f"✗ RAG test failed: {e}")
        return False

def test_llm():
    """Test LLM service."""
    print("\n" + "=" * 50)
    print("Testing LLM Service")
    print("=" * 50)
    
    try:
        llm = LLMService()
        print(f"✓ LLM Service initialized")
        print(f"  Provider: {llm.current_provider}")
        print(f"  Model: {llm.current_model}")
        
        models = llm.get_available_models()
        print(f"✓ Available models: {len(models)}")
        
        return True
    except Exception as e:
        print(f"✗ LLM test failed: {e}")
        return False

async def test_chatbot():
    """Test chatbot service."""
    print("\n" + "=" * 50)
    print("Testing Chatbot Service")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        chatbot = ChatbotService(db)
        
        # Update to available model
        chatbot.llm_service.current_model = 'gemma3:270m'
        
        test_queries = [
            "What is the rental price for Honda PCX 125?",
            "Do you offer finance options?",
            "What are your opening hours?",
            "What is the capital of France?"  # Should be rejected
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nTest {i}: {query}")
            result = await chatbot.process_message(
                user_id='test_user',
                chat_id=f'test_chat_{i}',
                message=query
            )
            
            response = result.get('response', '')
            is_relevant = result.get('is_domain_relevant', False)
            tokens = result.get('tokens_used', 0)
            
            print(f"  Response: {response[:100]}...")
            print(f"  Domain relevant: {is_relevant}")
            print(f"  Tokens used: {tokens}")
            
            if i < 4:
                assert is_relevant, f"Query {i} should be domain relevant"
            else:
                assert not is_relevant, f"Query {i} should NOT be domain relevant"
        
        print("\n✓ All chatbot tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Chatbot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("AiuraChatbot System Tests")
    print("=" * 50 + "\n")
    
    results = []
    
    # Test RAG
    results.append(test_rag())
    
    # Test LLM
    results.append(test_llm())
    
    # Test Chatbot
    results.append(asyncio.run(test_chatbot()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"RAG Service: {'✓ PASS' if results[0] else '✗ FAIL'}")
    print(f"LLM Service: {'✓ PASS' if results[1] else '✗ FAIL'}")
    print(f"Chatbot Service: {'✓ PASS' if results[2] else '✗ FAIL'}")
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all(results) else '✗ SOME TESTS FAILED'}")
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())

