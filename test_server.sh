#!/bin/bash
# Comprehensive test script for Qwen AI Server
# Usage: ./test_server.sh

API_URL="http://95.215.56.197/generate"
TOKEN="d8sB_86T6KfMX4h3R1un3FR2QV4ajHyd4cVZFCKkODY"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to make API call
test_api() {
    local title="$1"
    local prompt="$2"
    local max_tokens="$3"
    local temp="$4"

    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Test: $title${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "Prompt: ${YELLOW}$prompt${NC}"
    echo -e "Params: max_tokens=$max_tokens, temperature=$temp"
    echo ""

    curl -s -X POST $API_URL \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"prompt\": \"$prompt\", \"max_tokens\": $max_tokens, \"temperature\": $temp, \"stream\": false}" | \
      jq -r '.text // .detail // .'

    echo -e "\n"
    sleep 2
}

# Health check
echo -e "${GREEN}>>> Health Check${NC}"
curl -s http://95.215.56.197/health | jq
echo -e "\n"
sleep 1

# Test 1: Code Generation (Low temp)
test_api \
    "Code Generation - Python Function" \
    "Write a Python function to calculate factorial of a number. Include docstring and example usage." \
    250 \
    0.3

# Test 2: Code Generation - JavaScript
test_api \
    "Code Generation - JavaScript" \
    "Write a JavaScript async function to fetch data from an API and handle errors properly." \
    200 \
    0.3

# Test 3: Code Review
test_api \
    "Code Review - Security Issues" \
    "Review this SQL query for security issues: SELECT * FROM users WHERE id = user_input. What is wrong and how to fix it?" \
    200 \
    0.4

# Test 4: Algorithm Explanation
test_api \
    "Algorithm Explanation - Binary Search" \
    "Explain how binary search algorithm works. Use simple language and give time complexity." \
    200 \
    0.5

# Test 5: Technical Comparison
test_api \
    "Technical Comparison - SQL vs NoSQL" \
    "Compare SQL and NoSQL databases. Give 3 key differences and when to use each." \
    250 \
    0.5

# Test 6: Debugging Help
test_api \
    "Debugging - TypeError" \
    "I get TypeError: Cannot read property length of undefined in JavaScript. What are the common causes and how to fix it?" \
    200 \
    0.4

# Test 7: Best Practices
test_api \
    "Best Practices - API Design" \
    "List 5 best practices for designing RESTful APIs. Format as numbered list." \
    250 \
    0.5

# Test 8: Creative - Story (High temp)
test_api \
    "Creative Writing - Short Story" \
    "Write a very short story about a robot learning to code. Make it inspiring." \
    300 \
    0.9

# Test 9: Creative - Poem
test_api \
    "Creative Writing - Haiku" \
    "Write a haiku about artificial intelligence and the future." \
    80 \
    0.8

# Test 10: Business - Email
test_api \
    "Business Writing - Professional Email" \
    "Write a professional email to inform the team about server maintenance scheduled for tomorrow at 2 AM UTC." \
    200 \
    0.6

# Test 11: Technical Writing - Documentation
test_api \
    "Technical Documentation - README" \
    "Write a brief README.md section explaining how to install and run a FastAPI application." \
    250 \
    0.4

# Test 12: Problem Solving - System Design
test_api \
    "System Design - URL Shortener" \
    "Design a URL shortening service like bit.ly. Describe the key components and database schema." \
    300 \
    0.5

# Test 13: Data Structures
test_api \
    "Data Structures - Hash Table" \
    "Explain what a hash table is and when to use it. Include advantages and disadvantages." \
    200 \
    0.5

# Test 14: DevOps Question
test_api \
    "DevOps - Docker vs VM" \
    "Explain the difference between Docker containers and Virtual Machines. Which is better for microservices?" \
    250 \
    0.5

# Test 15: Security
test_api \
    "Security - OWASP Top 10" \
    "What is SQL Injection and how to prevent it? Give a code example in Python." \
    250 \
    0.4

# Test 16: Math/Logic
test_api \
    "Math Problem - Step by Step" \
    "Solve step by step: If a server handles 1000 requests per second and each request takes 100ms, how many concurrent requests are being processed?" \
    200 \
    0.4

# Test 17: Translation/Rewriting
test_api \
    "Text Improvement - Professional Tone" \
    "Rewrite this in professional tone: Hey can u fix the bug asap its breaking prod" \
    100 \
    0.3

# Test 18: Short Answer (Very precise)
test_api \
    "Quick Answer - Definition" \
    "What is Kubernetes? Answer in one sentence." \
    50 \
    0.2

# Test 19: List Generation
test_api \
    "List Generation - Programming Languages" \
    "List 5 programming languages best suited for machine learning with one-line explanation for each." \
    200 \
    0.5

# Test 20: Streaming Test
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Test: Streaming Mode${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "Prompt: ${YELLOW}Tell me a short joke about programmers${NC}"
echo ""

curl -N -X POST $API_URL \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me a short joke about programmers", "max_tokens": 100, "temperature": 0.8, "stream": true}'

echo -e "\n"

# Summary
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Server: $API_URL"
echo "Total tests: 20"
echo ""
echo "Temperature guide:"
echo "  0.2-0.4: Precise, factual answers (code, definitions)"
echo "  0.5-0.6: Balanced (explanations, comparisons)"
echo "  0.7-0.9: Creative (stories, poems)"
