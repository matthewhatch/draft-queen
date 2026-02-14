"""Database connection and session management."""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from config import settings
from backend.database.models import Base
import logging
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager."""
    
    def __init__(self):
        """Initialize database connection."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine."""
        # Build connection URL
        url = settings.database_url
        
        logger.info(f"Connecting to database: {settings.db_host}:{settings.db_port}/{settings.db_database}")
        self._initialize()
    
    def _initialize(self):
        """Initialize SQLAlchemy engine and session factory."""
        try:
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                echo=False,
                connect_args={
                    "connect_timeout": 10,
                }
            )
            
            # Register event listeners
            self._register_listeners()
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def _register_listeners(self):
        """Register SQLAlchemy event listeners."""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Enable foreign key constraints on SQLite."""
            # For PostgreSQL, this is enabled by default
            pass
    
    def create_all_tables(self):
        """Create all tables in the database."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_all_tables(self):
        """Drop all tables from the database (use with caution!)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """
        Context manager for database sessions.
        
        Usage:
            with db.session_scope() as session:
                result = session.query(Prospect).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database instance
db = DatabaseConnection()


def get_db_session() -> Session:
    """Dependency injection for database sessions in FastAPI."""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
