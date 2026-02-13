"""Configuration management for the NFL Draft Analysis Platform."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, field_validator
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # App metadata
    app_name: str = "NFL Draft Analysis Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    admin_api_key: str = Field(..., min_length=32, description="Admin API key for protected endpoints")
    
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_username: str = Field(..., description="PostgreSQL username (REQUIRED)")
    db_password: str = Field(..., min_length=8, description="PostgreSQL password (REQUIRED, min 8 chars)")
    db_database: str = "nfl_draft"
    
    # Email
    email_enabled: bool = False
    
    # Scheduler
    scheduler_enabled: bool = True
    
    # NFL.com connector settings
    nfl_com_base_url: str = "https://api.nfl.com"
    nfl_com_timeout_seconds: int = 30
    nfl_com_max_retries: int = 3
    nfl_com_retry_delay_seconds: int = 5
    
    # Logging
    logging_level: str = "INFO"
    logging_log_dir: str = "logs"
    logging_max_bytes: int = 10485760  # 10 MB
    logging_backup_count: int = 5
    logging_format: str = "json"
    
    @field_validator('db_password')
    @classmethod
    def validate_db_password(cls, v: str) -> str:
        """Ensure database password meets minimum requirements."""
        if len(v) < 8:
            raise ValueError('DB_PASSWORD must be at least 8 characters')
        return v
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL."""
        return f"postgresql://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"
    
    @property
    def nfl_com(self):
        """NFL.com connector settings as nested object."""
        class NFLComSettings:
            def __init__(self, settings):
                self.base_url = settings.nfl_com_base_url
                self.timeout_seconds = settings.nfl_com_timeout_seconds
                self.max_retries = settings.nfl_com_max_retries
                self.retry_delay_seconds = settings.nfl_com_retry_delay_seconds
        
        return NFLComSettings(self)
    
    @property
    def logging(self):
        """Logging settings as nested object."""
        class LoggingSettings:
            def __init__(self, settings):
                self.level = settings.logging_level
                self.log_dir = settings.logging_log_dir
                self.max_bytes = settings.logging_max_bytes
                self.backup_count = settings.logging_backup_count
                self.format = settings.logging_format
        
        return LoggingSettings(self)
    
    @property
    def scheduler(self):
        """Scheduler settings as nested object."""
        class SchedulerSettings:
            def __init__(self, settings):
                self.enabled = settings.scheduler_enabled
                self.timezone = "UTC"
                self.load_schedule_hour = 2
                self.load_schedule_minute = 0
                self.quality_schedule_hour = 2
                self.quality_schedule_minute = 30
        
        return SchedulerSettings(self)


# Load settings from environment
settings = Settings()
