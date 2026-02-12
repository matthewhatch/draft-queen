#!/bin/bash
# PostgreSQL initialization script
# Runs on first database startup to set up schema and migrations

set -e

echo "=========================================="
echo "Initializing Draft Queen Database"
echo "=========================================="

# Create extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable UUID extension
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Create schema
    CREATE SCHEMA IF NOT EXISTS public;
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON SCHEMA public TO "$POSTGRES_USER";
    
    -- Create basic tables (Alembic migrations will handle the rest)
    CREATE TABLE IF NOT EXISTS public.alembic_version (
        version_num varchar(32) not null,
        constraint alembic_version_pkc primary key (version_num)
    );
    
    COMMENT ON TABLE public.alembic_version IS 'Alembic migration tracking table';
EOSQL

echo "=========================================="
echo "Database initialized successfully"
echo "=========================================="

# Alembic migrations will be run by the application
# on startup or via separate migration command
