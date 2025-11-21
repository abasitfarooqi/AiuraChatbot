#!/bin/bash

# AiuraChatbot Management Script
# Complete project management: start, stop, restart, expose

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_DIR/.server.pid"
TUNNEL_PID_FILE="$PROJECT_DIR/.tunnel.pid"

cd "$PROJECT_DIR" || exit 1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   AiuraChatbot Management System      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
}

check_server_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

check_tunnel_running() {
    if [ -f "$TUNNEL_PID_FILE" ]; then
        PID=$(cat "$TUNNEL_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$TUNNEL_PID_FILE"
            return 1
        fi
    fi
    return 1
}

start_server() {
    if check_server_running; then
        echo -e "${YELLOW}⚠️  Server is already running (PID: $(cat "$PID_FILE"))${NC}"
        return 1
    fi

    echo -e "${GREEN}🚀 Starting AiuraChatbot Server...${NC}"
    
    # Check virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Set MySQL environment variables
    export USE_MYSQL=${USE_MYSQL:-true}
    export MYSQL_USER=${MYSQL_USER:-root}
    export MYSQL_PASSWORD=${MYSQL_PASSWORD:-abc123}
    export MYSQL_DATABASE=${MYSQL_DATABASE:-aiura_chatbots}
    export MYSQL_HOST=${MYSQL_HOST:-localhost}
    export MYSQL_PORT=${MYSQL_PORT:-3306}
    
    # Set JWT secret key
    export JWT_SECRET_KEY=${JWT_SECRET_KEY:-"aiura-chatbot-secret-key-change-in-production"}
    
    echo -e "${BLUE}📊 Database: MySQL (${MYSQL_DATABASE})${NC}"
    echo -e "${BLUE}🔐 Authentication: Enabled${NC}"
    
    # Create necessary directories
    mkdir -p data logs config/vendors rag_knowledge_base
    
    # Check if database is accessible
    echo -e "${YELLOW}🔍 Checking database connection...${NC}"
    python3 -c "
from backend.config.database import get_database_engine
try:
    engine = get_database_engine()
    with engine.connect() as conn:
        print('✅ Database connection successful')
except Exception as e:
    print(f'⚠️  Database connection warning: {e}')
    print('   Server will still start, but database features may not work')
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not verify database connection${NC}"
    
    # Start server in background
    echo -e "${GREEN}Starting server process...${NC}"
    nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload > logs/server.log 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > "$PID_FILE"
    
    # Wait a moment and check if it's still running
    sleep 3
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server started successfully (PID: $SERVER_PID)${NC}"
        echo ""
        echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║   Server URLs                         ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}📍 Local URL:${NC}    http://localhost:8000"
        echo -e "${GREEN}🔐 Login Page:${NC}   http://localhost:8000/login.html"
        echo -e "${GREEN}⚙️  Admin Panel:${NC}   http://localhost:8000/admin.html"
        echo -e "${GREEN}💬 Chatbot:${NC}      http://localhost:8000/"
        echo -e "${GREEN}📚 API Docs:${NC}     http://localhost:8000/docs"
        echo -e "${GREEN}💚 Health:${NC}        http://localhost:8000/health"
        echo ""
        echo -e "${BLUE}🔑 Test Credentials:${NC}"
        echo -e "   Super Admin: ${YELLOW}admin@aiurachatbot.com${NC} / ${YELLOW}admin123${NC}"
        echo -e "   Vendor Admin: ${YELLOW}admin@neguinhomotors.co.uk${NC} / ${YELLOW}neguinho123${NC}"
        echo ""
        echo -e "${YELLOW}📝 Logs:${NC} tail -f logs/server.log"
        return 0
    else
        echo -e "${RED}❌ Server failed to start. Check logs/server.log${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_server() {
    if ! check_server_running; then
        echo -e "${YELLOW}⚠️  Server is not running${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo -e "${YELLOW}🛑 Stopping server (PID: $PID)...${NC}"
    
    kill "$PID" 2>/dev/null
    sleep 1
    
    # Force kill if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID" 2>/dev/null
    fi
    
    rm -f "$PID_FILE"
    echo -e "${GREEN}✅ Server stopped${NC}"
}

start_tunnel() {
    if ! check_server_running; then
        echo -e "${RED}❌ Server is not running. Start server first with: ./scripts/manage.sh start${NC}"
        return 1
    fi
    
    if check_tunnel_running; then
        echo -e "${YELLOW}⚠️  Tunnel is already running (PID: $(cat "$TUNNEL_PID_FILE"))${NC}"
        return 1
    fi
    
    # Check if cloudflared is installed
    if ! command -v cloudflared &> /dev/null; then
        echo -e "${RED}❌ cloudflared is not installed!${NC}"
        echo ""
        echo "Install it with:"
        echo "  brew install cloudflare/cloudflare/cloudflared"
        echo ""
        echo "Or download from:"
        echo "  https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        return 1
    fi
    
    echo -e "${GREEN}🌐 Starting Cloudflare Tunnel...${NC}"
    
    # Start tunnel in background
    nohup cloudflared tunnel --url http://localhost:8000 > logs/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo $TUNNEL_PID > "$TUNNEL_PID_FILE"
    
    # Wait for tunnel URL (check multiple times)
    echo -e "${YELLOW}⏳ Waiting for tunnel URL...${NC}"
    
    TUNNEL_URL=""
    for i in {1..10}; do
        sleep 2
        # Try multiple patterns to find URL
        TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' logs/tunnel.log 2>/dev/null | head -1)
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
        # Also check for the formatted output
        TUNNEL_URL=$(grep -A 1 "Your quick Tunnel has been created" logs/tunnel.log 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
        if [ -n "$TUNNEL_URL" ]; then
            break
        fi
    done
    
    if ps -p $TUNNEL_PID > /dev/null 2>&1; then
        if [ -n "$TUNNEL_URL" ]; then
            echo -e "${GREEN}✅ Tunnel started successfully${NC}"
            echo ""
            echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${BLUE}║  🌍 Your Public Chatbot URL (Use in Laravel/Frontend)    ║${NC}"
            echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "${GREEN}Public URLs:${NC}"
            echo -e "   • Main:      ${YELLOW}$TUNNEL_URL${NC}"
            echo -e "   • Login:     ${YELLOW}$TUNNEL_URL/login.html${NC}"
            echo -e "   • Admin:     ${YELLOW}$TUNNEL_URL/admin.html${NC}"
            echo -e "   • API Base:  ${YELLOW}$TUNNEL_URL/api/v1${NC}"
            echo -e "   • API Docs:  ${YELLOW}$TUNNEL_URL/docs${NC}"
            echo -e "   • Health:     ${YELLOW}$TUNNEL_URL/health${NC}"
            echo ""
            echo -e "${BLUE}📋 Laravel .env Configuration:${NC}"
            echo -e "   ${YELLOW}CHATBOT_API_URL=$TUNNEL_URL${NC}"
            echo -e "   ${YELLOW}CHATBOT_API_BASE=$TUNNEL_URL/api/v1${NC}"
            echo ""
            echo -e "${BLUE}🔑 Authentication:${NC}"
            echo -e "   Use vendor API endpoints with Bearer token authentication"
            echo -e "   Login at: ${YELLOW}$TUNNEL_URL/login.html${NC}"
            echo ""
            echo -e "${BLUE}📝 Logs:${NC} tail -f logs/tunnel.log"
            echo ""
            echo "$TUNNEL_URL" > "$PROJECT_DIR/.tunnel_url"
            return 0
        else
            echo -e "${YELLOW}⚠️  Tunnel started but URL not found in logs yet.${NC}"
            echo -e "${YELLOW}📝 Checking logs/tunnel.log for URL...${NC}"
            echo ""
            # Show last few lines of log
            tail -5 logs/tunnel.log | grep -E 'https://|trycloudflare' || echo "URL may appear in a few seconds..."
            echo ""
            echo -e "${YELLOW}💡 Run: tail -f logs/tunnel.log${NC}"
            echo -e "${YELLOW}💡 Or check the log file manually for the URL${NC}"
            return 0
        fi
    else
        echo -e "${RED}❌ Tunnel failed to start. Check logs/tunnel.log${NC}"
        rm -f "$TUNNEL_PID_FILE"
        return 1
    fi
}

stop_tunnel() {
    if ! check_tunnel_running; then
        echo -e "${YELLOW}⚠️  Tunnel is not running${NC}"
        return 1
    fi
    
    PID=$(cat "$TUNNEL_PID_FILE")
    echo -e "${YELLOW}🛑 Stopping tunnel (PID: $PID)...${NC}"
    
    kill "$PID" 2>/dev/null
    sleep 1
    
    # Force kill if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID" 2>/dev/null
    fi
    
    rm -f "$TUNNEL_PID_FILE"
    rm -f "$PROJECT_DIR/.tunnel_url"
    echo -e "${GREEN}✅ Tunnel stopped${NC}"
}

restart_server() {
    echo -e "${YELLOW}🔄 Restarting server...${NC}"
    stop_server
    sleep 2
    start_server
}

status() {
    print_header
    
    if check_server_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Server: Running (PID: $PID)${NC}"
        echo ""
        echo -e "   ${BLUE}Local URLs:${NC}"
        echo -e "   • Main:      http://localhost:8000"
        echo -e "   • Login:     http://localhost:8000/login.html"
        echo -e "   • Admin:     http://localhost:8000/admin.html"
        echo -e "   • Chatbot:   http://localhost:8000/"
        echo -e "   • API Docs:  http://localhost:8000/docs"
        echo -e "   • Health:    http://localhost:8000/health"
        echo ""
        echo -e "   ${BLUE}Database:${NC} MySQL (${MYSQL_DATABASE:-aiura_chatbots})"
        echo -e "   ${BLUE}Auth:${NC}     JWT Token-based"
    else
        echo -e "${RED}❌ Server: Stopped${NC}"
    fi
    
    echo ""
    
    if check_tunnel_running; then
        PID=$(cat "$TUNNEL_PID_FILE")
        echo -e "${GREEN}✅ Tunnel: Running (PID: $PID)${NC}"
        
        # Try to get URL from saved file or logs
        TUNNEL_URL=""
        if [ -f "$PROJECT_DIR/.tunnel_url" ]; then
            TUNNEL_URL=$(cat "$PROJECT_DIR/.tunnel_url")
        else
            # Try to extract from logs
            TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' logs/tunnel.log 2>/dev/null | head -1)
        fi
        
        if [ -n "$TUNNEL_URL" ]; then
            echo ""
            echo -e "   ${BLUE}Public URLs:${NC}"
            echo -e "   • Main:      $TUNNEL_URL"
            echo -e "   • Login:     $TUNNEL_URL/login.html"
            echo -e "   • Admin:     $TUNNEL_URL/admin.html"
            echo -e "   • API Base:  $TUNNEL_URL/api/v1"
            echo -e "   • API Docs:  $TUNNEL_URL/docs"
            echo -e "   • Health:    $TUNNEL_URL/health"
            echo ""
            echo -e "   ${YELLOW}Laravel .env Configuration:${NC}"
            echo -e "   ${YELLOW}CHATBOT_API_URL=$TUNNEL_URL${NC}"
            echo -e "   ${YELLOW}CHATBOT_API_BASE=$TUNNEL_URL/api/v1${NC}"
        else
            echo -e "   ${YELLOW}URL not found. Check logs/tunnel.log${NC}"
        fi
    else
        echo -e "${RED}❌ Tunnel: Stopped${NC}"
        # Still show URL if it exists in logs
        TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' logs/tunnel.log 2>/dev/null | head -1)
        if [ -n "$TUNNEL_URL" ]; then
            echo -e "   ${YELLOW}Last known URL: $TUNNEL_URL${NC}"
            echo -e "   ${YELLOW}(Tunnel is stopped - restart with: ./scripts/manage.sh expose)${NC}"
        fi
    fi
    
    echo ""
    
    # Show database and auth status
    if check_server_running; then
        echo -e "${BLUE}📊 System Information:${NC}"
        source venv/bin/activate 2>/dev/null
        export USE_MYSQL=${USE_MYSQL:-true}
        export MYSQL_USER=${MYSQL_USER:-root}
        export MYSQL_PASSWORD=${MYSQL_PASSWORD:-abc123}
        export MYSQL_DATABASE=${MYSQL_DATABASE:-aiura_chatbots}
        
        python3 -c "
from backend.config.database import get_db_session
from backend.models.saas_models import Admin, Vendor, User
try:
    db = next(get_db_session())
    admin_count = db.query(Admin).count()
    vendor_count = db.query(Vendor).filter(Vendor.deleted_at.is_(None)).count()
    user_count = db.query(User).filter(User.deleted_at.is_(None)).count()
    print(f'   • Admins: {admin_count}')
    print(f'   • Vendors: {vendor_count}')
    print(f'   • Users: {user_count}')
    db.close()
except Exception as e:
    print(f'   ⚠️  Could not query database: {e}')
" 2>/dev/null || echo -e "   ${YELLOW}⚠️  Database query failed${NC}"
    fi
    
    echo ""
}

expose() {
    # Start server if not running
    if ! check_server_running; then
        echo -e "${YELLOW}Server not running. Starting server first...${NC}"
        start_server
        sleep 3
    fi
    
    # Start tunnel
    start_tunnel
}

# Main command handler
case "${1:-}" in
    start)
        print_header
        start_server
        ;;
    stop)
        print_header
        stop_server
        
        # Check if tunnel is running and prompt user
        if check_tunnel_running; then
            PID=$(cat "$TUNNEL_PID_FILE")
            echo ""
            echo -e "${YELLOW}⚠️  Tunnel is running (PID: $PID)${NC}"
            echo -e "${YELLOW}Do you want to stop the tunnel as well? (y/n)${NC}"
            read -r response
            case "$response" in
                [yY]|[yY][eE][sS])
                    stop_tunnel
                    ;;
                *)
                    echo -e "${BLUE}ℹ️  Tunnel left running${NC}"
                    ;;
            esac
        fi
        ;;
    restart)
        print_header
        restart_server
        ;;
    expose)
        print_header
        expose
        ;;
    tunnel)
        print_header
        case "${2:-}" in
            start)
                start_tunnel
                ;;
            stop)
                stop_tunnel
                ;;
            *)
                echo "Usage: $0 tunnel {start|stop}"
                exit 1
                ;;
        esac
        ;;
    status)
        status
        ;;
    setup)
        print_header
        echo -e "${GREEN}🔧 Setting up authentication and test data...${NC}"
        source venv/bin/activate
        export USE_MYSQL=${USE_MYSQL:-true}
        export MYSQL_USER=${MYSQL_USER:-root}
        export MYSQL_PASSWORD=${MYSQL_PASSWORD:-abc123}
        export MYSQL_DATABASE=${MYSQL_DATABASE:-aiura_chatbots}
        python3 scripts/setup_test_auth.py
        ;;
    *)
        print_header
        echo "Usage: $0 {start|stop|restart|expose|tunnel|status|setup}"
        echo ""
        echo "Commands:"
        echo "  start     - Start the chatbot server (with MySQL & authentication)"
        echo "  stop      - Stop the chatbot server (prompts to stop tunnel)"
        echo "  restart   - Restart the chatbot server"
        echo "  expose    - Start server + Cloudflare tunnel (full live setup)"
        echo "  tunnel    - Manage tunnel (start|stop)"
        echo "  status    - Show server, tunnel, and database status"
        echo "  setup     - Setup test users and vendors (run once)"
        echo ""
        echo "Examples:"
        echo "  ./scripts/manage.sh setup      # Setup test data (run once)"
        echo "  ./scripts/manage.sh start      # Start server only"
        echo "  ./scripts/manage.sh expose     # Start server + tunnel (recommended)"
        echo "  ./scripts/manage.sh status    # Check status"
        echo "  ./scripts/manage.sh stop       # Stop server"
        echo ""
        echo "🔑 Default Credentials:"
        echo "  Super Admin: admin@aiurachatbot.com / admin123"
        echo "  Vendor Admin: admin@neguinhomotors.co.uk / neguinho123"
        exit 1
        ;;
esac

