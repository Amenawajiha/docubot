import pytest
from sqlalchemy.dialects import sqlite, postgresql
from app.data.models import JSONB

def test_jsonb_variant_compilation():
    """
    Test that the database-agnostic JSONB variant compiles to:
    - JSON for SQLite
    - JSONB for PostgreSQL
    
    This ensures that tests using SQLite can run without the PostgreSQL JSONB CompileError.
    """
    # Compile for SQLite
    sqlite_compiled = JSONB.compile(dialect=sqlite.dialect())
    assert str(sqlite_compiled) == "JSON", f"Expected JSON for SQLite, got {sqlite_compiled}"

    # Compile for PostgreSQL
    pg_compiled = JSONB.compile(dialect=postgresql.dialect())
    assert str(pg_compiled) == "JSONB", f"Expected JSONB for PostgreSQL, got {pg_compiled}"
