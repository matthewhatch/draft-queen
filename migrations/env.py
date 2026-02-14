"""Alembic migrations configuration."""

# This file is created by `alembic init migrations`
# Run: alembic revision --autogenerate -m "Create initial schema"
# Then: alembic upgrade head

import sys
from pathlib import Path

# Add src directory to path for migrations to find backend module
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import logging

# Import models for autogeneration
from backend.database.models import Base
from data_pipeline.models.prospect_grades import ProspectGrade  # noqa: F401

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger('alembic.env')

# Setup SQLAlchemy URL
from config import settings
sqlalchemy_url = settings.database_url
config.set_main_option('sqlalchemy.url', sqlalchemy_url)

# Model's MetaData object for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_section(config.config_ini_section)['sqlalchemy.url']
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)

    configuration['sqlalchemy.url'] = sqlalchemy_url

    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.QueuePool,
        pool_size=10,
        max_overflow=20,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
