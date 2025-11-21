"""
Database configuration and connection management for MySQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from typing import Generator
from loguru import logger
import os
from backend.config.settings import get_settings

settings = get_settings()


def get_mysql_database_url() -> str:
    """Get MySQL database URL from environment or settings."""
    # Check environment variables first
    db_host = os.getenv("MYSQL_HOST", "localhost")
    db_port = os.getenv("MYSQL_PORT", "3306")
    db_user = os.getenv("MYSQL_USER", "aiura_chatbot")
    db_password = os.getenv("MYSQL_PASSWORD", "abc123")
    db_name = os.getenv("MYSQL_DATABASE", "aiura_chatbots")
    
    # If password is empty, don't include it in URL
    if not db_password:
        database_url = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    else:
        database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    
    # Return URL (already constructed above)
    return database_url


def get_database_engine():
    """Get database engine with connection pooling."""
    # Use MySQL if configured, otherwise fall back to SQLite
    if os.getenv("USE_MYSQL", "false").lower() == "true":
        database_url = get_mysql_database_url()
        logger.info(f"Using MySQL database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    else:
        database_url = settings.database_url
        logger.info(f"Using SQLite database: {database_url}")
    
    # MySQL-specific engine options
    engine_kwargs = {
        "echo": settings.database_echo,
        "poolclass": QueuePool,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600,  # Recycle connections after 1 hour
    }
    
    # SQLite-specific options
    if "sqlite" in database_url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs.pop("poolclass", None)
        engine_kwargs.pop("pool_size", None)
        engine_kwargs.pop("max_overflow", None)
        engine_kwargs.pop("pool_pre_ping", None)
        engine_kwargs.pop("pool_recycle", None)
    
    engine = create_engine(database_url, **engine_kwargs)
    return engine


def get_session_local():
    """Get database session factory."""
    engine = get_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def get_db_session():
    """Dependency for FastAPI to get database session."""
    from typing import Generator
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database tables."""
    from backend.models.saas_models import Base
    engine = get_database_engine()
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def create_database_if_not_exists():
    """Create MySQL database if it doesn't exist."""
    import pymysql
    from sqlalchemy import text
    
    db_host = os.getenv("MYSQL_HOST", "localhost")
    db_port = int(os.getenv("MYSQL_PORT", "3306"))
    db_user = os.getenv("MYSQL_USER", "aiura_chatbot")
    db_password = os.getenv("MYSQL_PASSWORD", "")
    db_name = os.getenv("MYSQL_DATABASE", "aiura_chatbots")
    
    if os.getenv("USE_MYSQL", "false").lower() != "true":
        return  # Skip for SQLite
    
    try:
        # Connect to MySQL server (without database)
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logger.info(f"Database '{db_name}' ready")
        
        connection.close()
    except Exception as e:
        logger.warning(f"Could not create database (may already exist or insufficient permissions): {e}")

