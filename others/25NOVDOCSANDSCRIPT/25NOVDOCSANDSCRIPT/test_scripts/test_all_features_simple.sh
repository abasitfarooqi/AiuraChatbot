#!/bin/bash

# Simple comprehensive test for all features
BASE_URL="http://localhost:8000"

echo "=========================================="
echo "Testing All Admin & Chat Features"
echo "=========================================="
echo ""

PASSED=0
FAILED=0

test_ok() {
    echo -e "\033[0;32m✓\033[0m $1"
    ((PASSED++))
}

test_fail() {
    echo -e "\033[0;31m✗\033[0m $1"
    ((FAILED++))
}

# Test Model Switching
echo "=== Model Switching ==="
CURRENT=$(curl -s $BASE_URL/api/v1/models/current)
if echo "$CURRENT" | grep -q "model"; then
    test_ok "Get current model"
    echo "  $CURRENT"
else
    test_fail "Get current model"
fi

SWITCH=$(curl -s -X POST $BASE_URL/api/v1/models/switch -H "Content-Type: application/json" -d '{"provider":"ollama","model":"qwen3:0.6b"}')
if echo "$SWITCH" | grep -q "success"; then
    test_ok "Switch model"
    echo "  $SWITCH"
else
    test_fail "Switch model"
fi

VERIFY=$(curl -s $BASE_URL/api/v1/models/current)
if echo "$VERIFY" | grep -q "qwen3:0.6b"; then
    test_ok "Verify model switch persisted"
    echo "  $VERIFY"
else
    test_fail "Verify model switch persisted"
fi

# Switch back
curl -s -X POST $BASE_URL/api/v1/models/switch -H "Content-Type: application/json" -d '{"provider":"ollama","model":"gemma3:270m"}' > /dev/null

# Test Chat
echo ""
echo "=== Chat Features ==="
CHAT_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/chat/message -H "Content-Type: application/json" -d '{"user_id":"test","message":"hi"}')
if echo "$CHAT_RESPONSE" | grep -q "response"; then
    test_ok "Send chat message"
    MODEL_USED=$(echo "$CHAT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('model_used', 'unknown'))" 2>/dev/null)
    echo "  Model used: $MODEL_USED"
else
    test_fail "Send chat message"
fi

CHAT_ID=$(echo "$CHAT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('chat_id', ''))" 2>/dev/null)
if [ ! -z "$CHAT_ID" ]; then
    HISTORY=$(curl -s $BASE_URL/api/v1/chat/history/$CHAT_ID)
    if echo "$HISTORY" | grep -q "messages"; then
        test_ok "Get chat history"
    else
        test_fail "Get chat history"
    fi
fi

# Test Model Management
echo ""
echo "=== Model Management ==="
AVAILABLE=$(curl -s $BASE_URL/api/v1/models/available)
if echo "$AVAILABLE" | grep -q "models"; then
    test_ok "Get available models"
    COUNT=$(echo "$AVAILABLE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('models', [])))" 2>/dev/null)
    echo "  Available: $COUNT models"
else
    test_fail "Get available models"
fi

# Test RAG
echo ""
echo "=== RAG Features ==="
RAG_STATS=$(curl -s $BASE_URL/api/v1/rag/stats)
if echo "$RAG_STATS" | grep -q "total_chunks"; then
    test_ok "Get RAG stats"
    CHUNKS=$(echo "$RAG_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chunks', 0))" 2>/dev/null)
    echo "  Total chunks: $CHUNKS"
else
    test_fail "Get RAG stats"
fi

# Test Pages
echo ""
echo "=== Frontend Pages ==="
for url in "/admin" "/admin.html" "/frontend/admin.html" "/" "/frontend/index.html"; do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL$url)
    if [ "$CODE" = "200" ]; then
        test_ok "$url (HTTP $CODE)"
    else
        test_fail "$url (HTTP $CODE)"
    fi
done

# Test Health
echo ""
echo "=== Health Check ==="
HEALTH=$(curl -s $BASE_URL/health)
if echo "$HEALTH" | grep -q "healthy"; then
    test_ok "Health check"
else
    test_fail "Health check"
fi

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo -e "\033[0;32mPassed: $PASSED\033[0m"
echo -e "\033[0;31mFailed: $FAILED\033[0m"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "\033[0;32m✓ All features working correctly!\033[0m"
    exit 0
else
    echo -e "\033[0;31m✗ Some features failed.\033[0m"
    exit 1
fi

