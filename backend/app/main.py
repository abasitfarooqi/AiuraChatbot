"""
Main FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from backend.config import get_settings
from backend.api.main import api_router
from backend.models import init_database
from loguru import logger
import sys

settings = get_settings()

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    settings.log_file,
    rotation=settings.log_rotation,
    retention=settings.log_retention,
    level=settings.log_level
)

# Create FastAPI app
# Get company name for description
try:
    from backend.utils.unified_config_manager import get_unified_config_manager
    config_manager = get_unified_config_manager()
    unified_config = config_manager.load_config()
    company_name = unified_config.get("business", {}).get("company_name", "Chatbot")
    app_description = f"{company_name} Chatbot API with RAG + LLM"
except:
    app_description = "Chatbot API with RAG + LLM"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=app_description
)

# CORS middleware - Allow all origins for widget embedding (including ngrok)
# In production, restrict to specific domains
cors_origins = settings.cors_origins
if "*" in cors_origins:
    # If "*" is in the list, allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Cannot use credentials with "*"
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.api_prefix)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/frontend/{filename}")
    async def serve_frontend(filename: str):
        """Serve frontend HTML files."""
        file_path = frontend_path / filename
        if file_path.exists() and file_path.suffix == ".html":
            return FileResponse(str(file_path))
        return {"error": "File not found"}
    
    @app.get("/widget")
    async def serve_widget():
        """Serve chatbot widget for embedding."""
        widget_path = frontend_path / "widget.html"
        if widget_path.exists():
            return FileResponse(str(widget_path))
        return {"error": "Widget not found"}
    
    @app.get("/standalone-widget")
    async def serve_standalone_widget():
        """Serve standalone widget that works from file system."""
        widget_path = frontend_path / "standalone-widget.html"
        if widget_path.exists():
            return FileResponse(str(widget_path))
        return {"error": "Standalone widget not found"}
    
    @app.get("/admin")
    async def admin_redirect():
        """Redirect /admin to admin.html."""
        return FileResponse(str(frontend_path / "admin.html"))
    
    @app.get("/admin.html")
    async def admin_html():
        """Serve admin.html directly."""
        return FileResponse(str(frontend_path / "admin.html"))
    
    @app.get("/")
    async def root_redirect():
        """Redirect root to frontend."""
        return FileResponse(str(frontend_path / "index.html"))


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting up application...")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    
    # Load knowledge base into RAG
    try:
        from backend.services.rag_service import RAGService
        rag_service = RAGService()
        rag_service.load_knowledge_base()
        logger.info("Knowledge base loaded")
    except Exception as e:
        logger.warning(f"Error loading knowledge base: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version
    }

