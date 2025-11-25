#!/bin/bash

# Comprehensive test script for all admin and chat features
# Tests model switching, chat functionality, and admin panel features

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Testing All Admin & Chat Features"
echo "=========================================="
echo ""

PASSED=0
FAILED=0

test_feature() {
    local description=$1
    local command=$2
    
    echo -e "${BLUE}Testing: $description${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        echo ""
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        echo ""
        return 1
    fi
}

# Test 1: Model Switching
test_feature "Model Switching - Get Current Model" \
    "curl -s $BASE_URL/api/v1/models/current | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"model\" in d and \"provider\" in d; print(f\"  Current: {d[\"model\"]} ({d[\"provider\"]})\")'"

CURRENT_MODEL=$(curl -s $BASE_URL/api/v1/models/current | python3 -c "import sys, json; print(json.load(sys.stdin).get('model', ''))" 2>/dev/null)
OTHER_MODEL="qwen3:0.6b"
if [ "$CURRENT_MODEL" = "qwen3:0.6b" ]; then
    OTHER_MODEL="gemma3:270m"
fi

test_feature "Model Switching - Switch Model" \
    "curl -s -X POST $BASE_URL/api/v1/models/switch -H 'Content-Type: application/json' -d '{\"provider\":\"ollama\",\"model\":\"$OTHER_MODEL\"}' | python3 -c 'import sys, json; d=json.load(sys.stdin); assert d.get(\"status\") == \"success\"; print(f\"  Switched to: {d.get(\"model\")}\")'"

test_feature "Model Switching - Verify Switch Persisted" \
    "curl -s $BASE_URL/api/v1/models/current | python3 -c 'import sys, json; d=json.load(sys.stdin); assert d.get(\"model\") == \"$OTHER_MODEL\"; print(f\"  Verified: {d.get(\"model\")}\")'"

# Switch back
curl -s -X POST $BASE_URL/api/v1/models/switch -H "Content-Type: application/json" -d "{\"provider\":\"ollama\",\"model\":\"$CURRENT_MODEL\"}" > /dev/null

# Test 2: Chat Features
test_feature "Chat - Send Message" \
    "curl -s -X POST $BASE_URL/api/v1/chat/message -H 'Content-Type: application/json' -d '{\"user_id\":\"test_user\",\"message\":\"hi\"}' | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"response\" in d and \"chat_id\" in d; print(f\"  Response: {d[\"response\"][:50]}...\")'"

CHAT_ID=$(curl -s -X POST $BASE_URL/api/v1/chat/message -H "Content-Type: application/json" -d '{"user_id":"test_user","message":"test"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('chat_id', ''))" 2>/dev/null)

if [ ! -z "$CHAT_ID" ]; then
    test_feature "Chat - Get Chat History" \
        "curl -s $BASE_URL/api/v1/chat/history/$CHAT_ID | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"messages\" in d; print(f\"  Messages: {len(d[\"messages\"])}\")'"
    
    test_feature "Chat - Multi-turn Conversation" \
        "curl -s -X POST $BASE_URL/api/v1/chat/message -H 'Content-Type: application/json' -d '{\"user_id\":\"test_user\",\"chat_id\":\"$CHAT_ID\",\"message\":\"what is your name?\"}' | python3 -c 'import sys, json; d=json.load(sys.stdin); assert len(d.get(\"response\", \"\")) > 0; print(f\"  Response: {d[\"response\"][:50]}...\")'"
fi

test_feature "Chat - Get User Chats" \
    "curl -s $BASE_URL/api/v1/chat/chats/test_user | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"chats\" in d; print(f\"  Total chats: {len(d[\"chats\"])}\")'"

# Test 3: Model Management
test_feature "Models - Get Available Models" \
    "curl -s $BASE_URL/api/v1/models/available | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"models\" in d and len(d[\"models\"]) > 0; print(f\"  Available: {len(d[\"models\"])} models\")'"

# Test 4: RAG Features
test_feature "RAG - Get Stats" \
    "curl -s $BASE_URL/api/v1/rag/stats | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"total_chunks\" in d; print(f\"  Chunks: {d.get(\"total_chunks\", 0)}\")'"

# Test 5: Admin Panel Pages
test_feature "Admin Panel - /admin page" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/admin | grep -q '200'"

test_feature "Admin Panel - /admin.html page" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/admin.html | grep -q '200'"

test_feature "Admin Panel - /frontend/admin.html page" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/frontend/admin.html | grep -q '200'"

# Test 6: Chat Interface Pages
test_feature "Chat Interface - Root page" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/ | grep -q '200'"

test_feature "Chat Interface - /frontend/index.html page" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/frontend/index.html | grep -q '200'"

# Test 7: Health & Info
test_feature "Health Check" \
    "curl -s $BASE_URL/health | python3 -c 'import sys, json; d=json.load(sys.stdin); assert d.get(\"status\") == \"healthy\"; print(f\"  Status: {d.get(\"status\")}\")'"

# Test 8: Model Used in Chat
test_feature "Chat - Verify Model Used" \
    "curl -s -X POST $BASE_URL/api/v1/chat/message -H 'Content-Type: application/json' -d '{\"user_id\":\"model_test\",\"message\":\"test\"}' | python3 -c 'import sys, json; d=json.load(sys.stdin); assert \"model_used\" in d and len(d.get(\"model_used\", \"\")) > 0; print(f\"  Model used: {d.get(\"model_used\")}\")'"

echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All features working correctly!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some features failed. Please check the output above.${NC}"
    exit 1
fi

