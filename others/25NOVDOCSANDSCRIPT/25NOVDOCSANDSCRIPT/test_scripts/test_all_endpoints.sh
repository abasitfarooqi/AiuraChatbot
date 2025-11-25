#!/bin/bash

# Comprehensive test script for all endpoints and frontend pages

echo "=========================================="
echo "AiuraChatbot - Complete System Test"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"
API_BASE="${BASE_URL}/api/v1"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local data=$4
    
    echo -n "Testing: $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "  Response: $body"
        ((FAILED++))
        return 1
    fi
}

echo "=== Frontend Pages ==="
test_endpoint "Frontend Index" "GET" "${BASE_URL}/frontend/index.html" ""
test_endpoint "Frontend Admin" "GET" "${BASE_URL}/frontend/admin.html" ""
test_endpoint "Root Redirect" "GET" "${BASE_URL}/" ""

echo ""
echo "=== API Endpoints ==="
test_endpoint "Health Check" "GET" "${BASE_URL}/health" ""
test_endpoint "Chat Message" "POST" "${API_BASE}/chat/message" '{"user_id":"test","message":"What is the rental price?"}'
test_endpoint "RAG Stats" "GET" "${API_BASE}/rag/stats" ""
test_endpoint "Current Model" "GET" "${API_BASE}/models/current" ""
test_endpoint "Available Models" "GET" "${API_BASE}/models/available" ""

echo ""
echo "=== Test Summary ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

