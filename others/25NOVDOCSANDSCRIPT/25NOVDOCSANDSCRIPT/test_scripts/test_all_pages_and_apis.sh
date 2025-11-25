#!/bin/bash

# Comprehensive test script for all pages and APIs
# Tests all endpoints and frontend pages

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Testing All Pages and APIs"
echo "=========================================="
echo ""

# Test counter
PASSED=0
FAILED=0

test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓${NC} $description (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (HTTP $http_code)"
        echo "  Response: $body"
        ((FAILED++))
        return 1
    fi
}

test_page() {
    local url=$1
    local description=$2
    
    response=$(curl -s -w "\n%{http_code}" "$url")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d' | head -n1)
    
    if [ "$http_code" -eq 200 ] && echo "$body" | grep -q "<!DOCTYPE html\|<html"; then
        echo -e "${GREEN}✓${NC} $description (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (HTTP $http_code)"
        ((FAILED++))
        return 1
    fi
}

echo "=== FRONTEND PAGES ==="
echo ""

test_page "$BASE_URL/" "Root page (/)"
test_page "$BASE_URL/frontend/index.html" "Chat page (/frontend/index.html)"
test_page "$BASE_URL/frontend/admin.html" "Admin page (/frontend/admin.html)"
test_page "$BASE_URL/admin.html" "Admin page (/admin.html)"
test_page "$BASE_URL/admin" "Admin page (/admin)"

echo ""
echo "=== API ENDPOINTS ==="
echo ""

# Health & Info
test_endpoint "GET" "/health" "Health check"
test_endpoint "GET" "/" "Root API endpoint"
test_endpoint "GET" "/docs" "Swagger UI documentation"

echo ""
echo "=== CHAT API ==="
echo ""

# Chat endpoints
test_endpoint "POST" "/api/v1/chat/message" "Send chat message" \
    '{"user_id":"test_user","message":"hi"}'

# Get chat history (will fail if no chat_id exists, that's ok)
CHAT_ID=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test_user","message":"test"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('chat_id', ''))" 2>/dev/null)

if [ ! -z "$CHAT_ID" ]; then
    test_endpoint "GET" "/api/v1/chat/history/$CHAT_ID" "Get chat history"
    test_endpoint "GET" "/api/v1/chat/chats/test_user" "Get user chats"
fi

echo ""
echo "=== MODEL API ==="
echo ""

test_endpoint "GET" "/api/v1/models/current" "Get current model"
test_endpoint "GET" "/api/v1/models/available" "Get available models"
test_endpoint "GET" "/api/v1/models/available?provider=ollama" "Get Ollama models"

# Try to switch model (use existing model to avoid errors)
CURRENT_MODEL=$(curl -s "$BASE_URL/api/v1/models/current" | python3 -c "import sys, json; print(json.load(sys.stdin).get('model', 'gemma3:270m'))" 2>/dev/null)
test_endpoint "POST" "/api/v1/models/switch" "Switch model" \
    "{\"provider\":\"ollama\",\"model\":\"$CURRENT_MODEL\"}"

echo ""
echo "=== RAG API ==="
echo ""

test_endpoint "GET" "/api/v1/rag/stats" "Get RAG stats"

echo ""
echo "=== SUMMARY ==="
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi

