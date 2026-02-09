"""Main entry point and application initialization."""

import logging
import logging.handlers
import os
from pathlib import Path
from config import settings
from backend.database import db
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.api.routes import query_router, export_router

# Configure logging
def setup_logging():
    """Configure application logging."""
    log_dir = Path(settings.logging.log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.logging.level))
    
    # File handler with rotation
    log_file = log_dir / "pipeline.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=settings.logging.max_bytes,
        backupCount=settings.logging.backup_count,
    )
    
    # Formatter
    if settings.logging.format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger


# Initialize logging
logger = setup_logging()


class PipelineScheduler:
    """Manages scheduled data pipeline jobs."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler(timezone=settings.scheduler.timezone)
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Configure scheduled jobs."""
        if not settings.scheduler.enabled:
            logger.info("Scheduler is disabled")
            return
        
        # Schedule daily NFL.com data load
        self.scheduler.add_job(
            self._daily_load_job,
            'cron',
            hour=settings.scheduler.load_schedule_hour,
            minute=settings.scheduler.load_schedule_minute,
            id='daily_load',
            name='Daily NFL.com Data Load',
            replace_existing=True,
        )
        
        # Schedule daily quality checks
        self.scheduler.add_job(
            self._daily_quality_job,
            'cron',
            hour=settings.scheduler.quality_schedule_hour,
            minute=settings.scheduler.quality_schedule_minute,
            id='daily_quality',
            name='Daily Quality Checks',
            replace_existing=True,
        )
        
        logger.info(f"Scheduler jobs configured:")
        logger.info(f"  - Daily load: {settings.scheduler.load_schedule_hour:02d}:{settings.scheduler.load_schedule_minute:02d} UTC")
        logger.info(f"  - Quality checks: {settings.scheduler.quality_schedule_hour:02d}:{settings.scheduler.quality_schedule_minute:02d} UTC")
    
    def _daily_load_job(self):
        """Daily data load job."""
        logger.info(f"[{datetime.utcnow()}] Starting daily NFL.com data load job")
        
        try:
            from data_pipeline.loaders import load_nfl_com_data
            
            result = load_nfl_com_data()
            logger.info(
                f"Daily load completed: "
                f"Inserted: {result['total_inserted']}, "
                f"Updated: {result['total_updated']}, "
                f"Failed: {result['total_failed']}"
            )
        
        except Exception as e:
            logger.error(f"Daily load job failed: {e}", exc_info=True)
            # TODO: Send alert email
    
    def _daily_quality_job(self):
        """Daily quality check job."""
        logger.info(f"[{datetime.utcnow()}] Starting daily quality checks")
        
        try:
            from data_pipeline.quality import run_quality_checks
            
            result = run_quality_checks()
            logger.info(
                f"Quality checks completed: "
                f"{result['checks_passed']} passed, "
                f"{result['checks_failed']} failed"
            )
        
        except Exception as e:
            logger.error(f"Quality check job failed: {e}", exc_info=True)
            # TODO: Send alert email
    
    def start(self):
        """Start the scheduler."""
        try:
            self.scheduler.start()
            logger.info("Pipeline scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("Pipeline scheduler shutdown")
        except Exception as e:
            logger.error(f"Failed to shutdown scheduler: {e}")


# Global scheduler instance
scheduler: PipelineScheduler = None


# FastAPI Application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    initialize_app()
    yield
    # Shutdown
    shutdown_app()


app = FastAPI(
    title=settings.app_name,
    description="NFL Draft Prospect Analysis Platform",
    version=settings.app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_router)
app.include_router(export_router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": "ok" if db.health_check() else "error"
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API documentation link."""
    return {
        "message": f"Welcome to {settings.app_name} v{settings.app_version}",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


def initialize_app():

    """Initialize application components."""
    global scheduler
    
    # Skip initialization if running tests
    if os.getenv("TESTING") == "true":
        logger.info("Test mode detected - skipping scheduler initialization")
        return
    
    logger.info("=" * 80)
    logger.info(f"Initializing {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info("=" * 80)
    
    # Check database connectivity
    if db.health_check():
        logger.info("✓ Database connection OK")
    else:
        logger.error("✗ Database connection failed")
        raise RuntimeError("Failed to connect to database")
    
    # Initialize scheduler
    if settings.scheduler.enabled:
        scheduler = PipelineScheduler()
        scheduler.start()
        logger.info("✓ Pipeline scheduler initialized")
    else:
        logger.info("Pipeline scheduler disabled")
    
    logger.info("Application initialization complete")


def shutdown_app():
    """Shutdown application components."""
    global scheduler
    
    logger.info("Shutting down application...")
    
    if scheduler:
        scheduler.shutdown()
    
    logger.info("Application shutdown complete")


if __name__ == "__main__":
    """Run as standalone script."""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        shutdown_app()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        initialize_app()
        
        # Keep the app running
        logger.info("Application running. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        shutdown_app()
        sys.exit(1)
