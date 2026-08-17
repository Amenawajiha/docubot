"""
Comprehensive unit tests for Database class.

This test suite covers:
- Database initialization with singleton pattern
- Connection string generation
- Engine creation
- Session creation
- Environment variable handling
- Configuration loading
- Error handling
- Singleton behavior
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch, call

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.db_generic import Database


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.utils.db_generic.logger") as mock:
        yield mock


@pytest.fixture
def mock_load_dotenv():
    """Mock dotenv loading."""
    with patch("src.utils.db_generic.load_dotenv") as mock:
        yield mock


@pytest.fixture
def mock_get_config():
    """Mock config loader."""
    with patch("src.utils.db_generic.get_config") as mock:
        mock.return_value = {
            "user": "test_user",
            "host": "localhost",
            "port": 5432
        }
        yield mock


@pytest.fixture
def mock_env_password():
    """Mock environment variable for password."""
    with patch.dict(os.environ, {"POSTGRES_PASSWORD": "test_password"}):
        yield


@pytest.fixture
def mock_env_password_with_special_chars():
    """Mock environment variable for password with special characters."""
    with patch.dict(os.environ, {"POSTGRES_PASSWORD": "p@ssw0rd@123"}):
        yield


@pytest.fixture
def mock_create_engine():
    """Mock SQLAlchemy create_engine."""
    with patch("src.utils.db_generic.create_engine") as mock:
        mock_engine = MagicMock()
        mock.return_value = mock_engine
        yield mock


@pytest.fixture
def mock_sessionmaker():
    """Mock SQLAlchemy sessionmaker."""
    with patch("src.utils.db_generic.sessionmaker") as mock:
        mock_session = MagicMock()
        mock.return_value = mock_session
        yield mock


@pytest.fixture
def reset_database_singleton():
    """Reset Database singleton state between tests."""
    Database._instances = {}
    yield
    Database._instances = {}


@pytest.fixture
def sample_database_config():
    """Sample database configuration."""
    return {
        "user": "admin",
        "host": "db.example.com",
        "port": 5432
    }


# ============================================================================
# TEST CLASS: Database Initialization
# ============================================================================


class TestDatabaseInitialization:
    """Test Database class initialization."""
    
    def test_database_initialization_success(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test successful database initialization.
        
        Testing Concept: Test happy path initialization
        """
        db = Database(db_schema="test_schema")
        
        assert db is not None
        assert db.engine is not None
        assert db.session is not None
        
        # Verify logger was called
        mock_logger.info.assert_any_call("Creating %s DB conn..", "test_schema")
        mock_logger.info.assert_any_call('Connecting to "%s" database..', "PostgreSQL")
    
    def test_database_initialization_with_custom_db_name(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test initialization with custom database name.
        
        Testing Concept: Test parameter override
        """
        db = Database(db_schema="test_schema", db_name="CustomDB")
        
        assert db is not None
        mock_logger.info.assert_any_call('Connecting to "%s" database..', "CustomDB")
    
    def test_database_calls_get_config(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that get_config is called with 'database'.
        
        Testing Concept: Test configuration loading
        """
        db = Database(db_schema="test_schema")
        
        mock_get_config.assert_called_once_with("database")
    
    def test_database_calls_create_engine(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that create_engine is called with connection string.
        
        Testing Concept: Test engine creation
        """
        db = Database(db_schema="test_schema")
        
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0]
        
        # Verify connection string format
        conn_str = call_args[0]
        assert "postgresql+psycopg2://" in conn_str
        assert "test_user" in conn_str
        assert "test_password" in conn_str
        assert "localhost" in conn_str
        assert "5432" in conn_str
        assert "test_schema" in conn_str
        assert "sslmode=require" in conn_str
    
    def test_database_calls_sessionmaker(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that sessionmaker is called with engine.
        
        Testing Concept: Test session creation
        """
        db = Database(db_schema="test_schema")
        
        mock_sessionmaker.assert_called_once()
        call_kwargs = mock_sessionmaker.call_args[1]
        
        # Verify bind parameter is the mock engine
        assert "bind" in call_kwargs
        assert call_kwargs["bind"] == mock_create_engine.return_value


# ============================================================================
# TEST CLASS: Connection String Generation
# ============================================================================


class TestConnectionStringGeneration:
    """Test connection string generation logic."""
    
    def test_connection_string_format(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that connection string has correct format.
        
        Testing Concept: Test string formatting
        """
        db = Database(db_schema="my_schema")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        # Verify all components
        assert conn_str.startswith("postgresql+psycopg2://")
        assert "test_user:test_password@localhost:5432/my_schema" in conn_str
        assert conn_str.endswith("?sslmode=require")
    
    def test_connection_string_escapes_at_symbol_in_password(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password_with_special_chars, 
        mock_create_engine, mock_sessionmaker
    ):
        """
        Test that @ symbol in password is URL-encoded.
        
        Testing Concept: Test special character handling
        """
        db = Database(db_schema="test_schema")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        # @ should be encoded as %40
        assert "p%40ssw0rd%40123" in conn_str
        # Raw @ should not appear in password portion
        password_portion = conn_str.split("://")[1].split("@")[0].split(":")[1]
        assert "@" not in password_portion
    
    def test_connection_string_uses_db_name_in_protocol(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that db_name is used in connection protocol.
        
        Testing Concept: Test parameter usage
        """
        db = Database(db_schema="test_schema", db_name="PostgreSQL")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        # db_name should be lowercased in protocol
        assert conn_str.startswith("postgresql+psycopg2://")
    
    def test_connection_string_with_different_config_values(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_create_engine, mock_sessionmaker
    ):
        """
        Test connection string with various config values.
        
        Testing Concept: Test different input values
        """
        with patch("src.utils.db_generic.get_config") as mock_config:
            mock_config.return_value = {
                "user": "prod_user",
                "host": "prod.database.com",
                "port": 25060
            }
            
            with patch.dict(os.environ, {"POSTGRES_PASSWORD": "prod_pass"}):
                db = Database(db_schema="production_db")
                
                call_args = mock_create_engine.call_args[0]
                conn_str = call_args[0]
                
                assert "prod_user" in conn_str
                assert "prod_pass" in conn_str
                assert "prod.database.com" in conn_str
                assert "25060" in conn_str
                assert "production_db" in conn_str


# ============================================================================
# TEST CLASS: Singleton Pattern
# ============================================================================


class TestDatabaseSingleton:
    """Test Database singleton pattern behavior."""
    
    def test_database_is_singleton_per_db_name(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that Database follows singleton pattern per db_name.
        
        Testing Concept: Test singleton pattern
        """
        db1 = Database(db_schema="schema1", db_name="PostgreSQL")
        db2 = Database(db_schema="schema1", db_name="PostgreSQL")
        
        # Same db_name should return same instance
        assert db1 is db2
    
    def test_database_creates_different_instances_for_different_db_names(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that different db_names create different instances.
        
        Testing Concept: Test singleton key differentiation
        """
        db1 = Database(db_schema="schema1", db_name="PostgreSQL")
        db2 = Database(db_schema="schema2", db_name="MySQL")
        
        # Different db_name should return different instances
        assert db1 is not db2
    
    def test_database_singleton_only_initializes_once(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that singleton only initializes once.
        
        Testing Concept: Test initialization count
        """
        db1 = Database(db_schema="schema1", db_name="PostgreSQL")
        db2 = Database(db_schema="schema1", db_name="PostgreSQL")
        db3 = Database(db_schema="schema1", db_name="PostgreSQL")
        
        # create_engine should only be called once
        assert mock_create_engine.call_count == 1
    
    def test_database_singleton_reuses_engine(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that singleton reuses engine.
        
        Testing Concept: Test resource reuse
        """
        db1 = Database(db_schema="schema1", db_name="PostgreSQL")
        db2 = Database(db_schema="schema1", db_name="PostgreSQL")
        
        # Same engine object
        assert db1.engine is db2.engine
    
    def test_database_singleton_reuses_session(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that singleton reuses session.
        
        Testing Concept: Test session reuse
        """
        db1 = Database(db_schema="schema1", db_name="PostgreSQL")
        db2 = Database(db_schema="schema1", db_name="PostgreSQL")
        
        # Same session object
        assert db1.session is db2.session


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestDatabaseErrorHandling:
    """Test Database error handling."""
    
    def test_database_raises_exception_when_create_engine_fails(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_sessionmaker
    ):
        """
        Test that exception is raised when create_engine fails.
        
        Testing Concept: Test exception propagation
        """
        with patch("src.utils.db_generic.create_engine") as mock_engine:
            mock_engine.side_effect = SQLAlchemyError("Connection failed")
            
            with pytest.raises(SQLAlchemyError, match="Connection failed"):
                db = Database(db_schema="test_schema")
    
    def test_database_logs_error_when_create_engine_fails(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password
    ):
        """
        Test that error is logged when create_engine fails.
        
        Testing Concept: Test error logging
        """
        with patch("src.utils.db_generic.create_engine") as mock_engine:
            test_error = SQLAlchemyError("Connection error")
            mock_engine.side_effect = test_error
            
            try:
                db = Database(db_schema="test_schema")
            except SQLAlchemyError:
                pass
            
            # Verify error was logged
            mock_logger.error.assert_called_once_with(test_error)
            
            # Verify connection string was logged
            assert mock_logger.info.call_count >= 2
    
    def test_database_raises_key_error_when_config_missing_keys(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that KeyError is raised when config is missing required keys.
        
        Testing Concept: Test missing configuration
        """
        with patch("src.utils.db_generic.get_config") as mock_config:
            # Missing 'host' key
            mock_config.return_value = {
                "user": "test_user",
                "port": 5432
            }
            
            with pytest.raises(KeyError):
                db = Database(db_schema="test_schema")
    
    def test_database_raises_type_error_when_password_is_none(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_create_engine, mock_sessionmaker
    ):
        """
        Test handling when password environment variable is not set.
        
        Testing Concept: Test missing environment variable
        """
        with patch.dict(os.environ, {}, clear=True):
            # Remove POSTGRES_PASSWORD from environment
            with pytest.raises((TypeError, AttributeError)):
                db = Database(db_schema="test_schema")
    
    def test_database_logs_connection_string_on_error(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password
    ):
        """
        Test that connection string is logged on error.
        
        Testing Concept: Test error context logging
        """
        with patch("src.utils.db_generic.create_engine") as mock_engine:
            mock_engine.side_effect = Exception("Test error")
            
            try:
                db = Database(db_schema="test_schema")
            except Exception:
                pass
            
            # Should log connection string info
            assert any("conn_str" in str(call) for call in mock_logger.info.call_args_list)


# ============================================================================
# TEST CLASS: Engine Configuration
# ============================================================================


class TestEngineConfiguration:
    """Test engine configuration options."""
    
    def test_database_creates_engine_with_echo_true(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that engine is created with echo=True.
        
        Testing Concept: Test engine parameter
        """
        db = Database(db_schema="test_schema")
        
        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs.get("echo") is True
    
    def test_database_connection_string_includes_sslmode(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that connection string includes SSL mode.
        
        Testing Concept: Test security configuration
        """
        db = Database(db_schema="test_schema")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        assert "sslmode=require" in conn_str
    
    def test_database_binds_session_to_engine(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test that session is bound to engine.
        
        Testing Concept: Test binding relationship
        """
        db = Database(db_schema="test_schema")
        
        call_kwargs = mock_sessionmaker.call_args[1]
        assert call_kwargs["bind"] == mock_create_engine.return_value


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_database_initialization_workflow(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_create_engine, mock_sessionmaker
    ):
        """
        Test complete database initialization workflow.
        
        Testing Concept: Integration test
        """
        with patch("src.utils.db_generic.get_config") as mock_config:
            mock_config.return_value = {
                "user": "admin",
                "host": "db.example.com",
                "port": 5432
            }
            
            with patch.dict(os.environ, {"POSTGRES_PASSWORD": "secure_pass"}):
                # Initialize database
                db = Database(db_schema="production_db", db_name="PostgreSQL")
                
                # Verify initialization
                assert db is not None
                assert db.engine is not None
                assert db.session is not None
                
                # Verify configuration was loaded
                mock_config.assert_called_once_with("database")
                
                # Verify engine was created
                mock_create_engine.assert_called_once()
                
                # Verify session was created
                mock_sessionmaker.assert_called_once()
    
    def test_multiple_database_connections(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test creating multiple database connections.
        
        Testing Concept: Test multi-instance scenario
        """
        # Create different database instances
        db1 = Database(db_schema="schema1", db_name="PostgreSQL")
        db2 = Database(db_schema="schema2", db_name="MySQL")
        db3 = Database(db_schema="schema1", db_name="PostgreSQL")  # Same as db1
        
        # Verify singleton behavior
        assert db1 is db3  # Same db_name
        assert db1 is not db2  # Different db_name
        
        # Verify multiple engines were created (one per unique db_name)
        assert mock_create_engine.call_count == 2


# ============================================================================
# TEST CLASS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases."""
    
    def test_database_with_empty_db_schema(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test database with empty schema name.
        
        Testing Concept: Test empty input
        """
        db = Database(db_schema="", db_name="PostgreSQL")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        # Empty schema should still create connection string
        assert "postgresql+psycopg2://" in conn_str
    
    def test_database_with_special_characters_in_schema(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test database with special characters in schema name.
        
        Testing Concept: Test special character handling
        """
        db = Database(db_schema="test-schema_123", db_name="PostgreSQL")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        assert "test-schema_123" in conn_str
    
    def test_database_with_unicode_schema_name(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, mock_sessionmaker
    ):
        """
        Test database with unicode characters in schema name.
        
        Testing Concept: Test unicode handling
        """
        db = Database(db_schema="測試_schema", db_name="PostgreSQL")
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        assert "測試_schema" in conn_str
    
    def test_database_with_very_long_password(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_create_engine, mock_sessionmaker
    ):
        """
        Test database with very long password.
        
        Testing Concept: Test boundary values
        """
        long_password = "a" * 1000
        
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": long_password}):
            db = Database(db_schema="test_schema")
            
            call_args = mock_create_engine.call_args[0]
            conn_str = call_args[0]
            
            # Long password should be included
            assert len(conn_str) > 1000
    
    def test_database_with_password_containing_multiple_at_symbols(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_create_engine, mock_sessionmaker
    ):
        """
        Test password with multiple @ symbols.
        
        Testing Concept: Test multiple special characters
        """
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "p@ss@w@rd"}):
            db = Database(db_schema="test_schema")
            
            call_args = mock_create_engine.call_args[0]
            conn_str = call_args[0]
            
            # All @ symbols should be encoded
            assert "p%40ss%40w%40rd" in conn_str


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("db_name,expected_protocol", [
        ("PostgreSQL", "postgresql+psycopg2://"),
        ("MySQL", "mysql+psycopg2://"),
        ("Oracle", "oracle+psycopg2://"),
        ("SQLite", "sqlite+psycopg2://"),
    ])
    def test_database_with_various_db_names(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine, 
        mock_sessionmaker, db_name, expected_protocol
    ):
        """
        Test database with various db_name values.
        
        Testing Concept: Parameterized db_name testing
        """
        db = Database(db_schema="test_schema", db_name=db_name)
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        assert conn_str.startswith(expected_protocol)
    
    @pytest.mark.parametrize("schema_name", [
        "simple_schema",
        "schema-with-dashes",
        "schema_with_underscores",
        "Schema123",
        "UPPERCASE_SCHEMA",
    ])
    def test_database_with_various_schema_names(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_get_config, mock_env_password, mock_create_engine,
        mock_sessionmaker, schema_name
    ):
        """
        Test database with various schema names.
        
        Testing Concept: Parameterized schema testing
        """
        # Clear singleton for each iteration
        Database._instances = {}
        
        db = Database(db_schema=schema_name)
        
        call_args = mock_create_engine.call_args[0]
        conn_str = call_args[0]
        
        assert schema_name in conn_str
    
    @pytest.mark.parametrize("config_values", [
        {"user": "user1", "host": "host1.com", "port": 5432},
        {"user": "admin", "host": "localhost", "port": 3306},
        {"user": "root", "host": "192.168.1.1", "port": 5433},
    ])
    def test_database_with_various_config_values(
        self, reset_database_singleton, mock_logger, mock_load_dotenv,
        mock_env_password, mock_create_engine, mock_sessionmaker, config_values
    ):
        """
        Test database with various configuration values.
        
        Testing Concept: Parameterized config testing
        """
        with patch("src.utils.db_generic.get_config") as mock_config:
            mock_config.return_value = config_values
            
            Database._instances = {}  # Reset
            db = Database(db_schema="test_schema")
            
            call_args = mock_create_engine.call_args[0]
            conn_str = call_args[0]
            
            assert config_values["user"] in conn_str
            assert config_values["host"] in conn_str
            assert str(config_values["port"]) in conn_str


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.utils.db_generic",
        "--cov-report=term-missing"
    ])

