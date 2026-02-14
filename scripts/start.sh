#!/bin/bash
# Startup script for NFL Draft Queen system

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}NFL Draft Queen - Startup${NC}"
echo -e "${GREEN}================================${NC}"
echo

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check API port
if check_port 8000; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    echo "Kill existing processes: pkill -f 'python main.py'"
    exit 1
fi

# Check Frontend port
if check_port 3000; then
    echo -e "${YELLOW}⚠️  Port 3000 is already in use (will try 3001)${NC}"
fi

# Start API
echo -e "${GREEN}▶  Starting Backend API on port 8000...${NC}"
cd "$PROJECT_ROOT"
./env/bin/python main.py > /tmp/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓ API started (PID: $API_PID)${NC}"
sleep 3

# Start Frontend
echo -e "${GREEN}▶  Starting Frontend on port 3000...${NC}"
cd "$PROJECT_ROOT/frontend"
npm start > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
sleep 4

# Verify services are running
echo
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Verification${NC}"
echo -e "${GREEN}================================${NC}"

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is responding${NC}"
else
    echo -e "${RED}✗ API is not responding${NC}"
    exit 1
fi

if curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is responding${NC}"
else
    if check_port 3001; then
        echo -e "${YELLOW}✓ Frontend running on port 3001 (fallback)${NC}"
    fi
fi

echo
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}System Ready!${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "📊 Frontend:  ${YELLOW}http://localhost:3000${NC}"
echo -e "🔌 API:       ${YELLOW}http://localhost:8000${NC}"
echo -e "📖 API Docs:  ${YELLOW}http://localhost:8000/docs${NC}"
echo
echo -e "To stop: ${YELLOW}pkill -f 'python main.py' && pkill -f 'npm start'${NC}"
echo
echo "Process IDs:"
echo "  API:      $API_PID"
echo "  Frontend: $FRONTEND_PID"
