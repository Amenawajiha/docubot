"""
Comprehensive unit tests for SQLAlchemy ORM schemas.

This test suite covers:
- ORM model instantiation and attributes
- Column types and constraints
- Default values and server defaults
- Indexes and table arguments
- Schema configuration
- String representation
- Database operations (mocked)
- Edge cases and validation
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import JSON, Column, DateTime, Index, Integer, Text, inspect
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.chat.schemas import Base, ConversationORM


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def sample_conversation_data():
    """
    Provide sample conversation data for testing.
    
    Testing Concept: Fixture for reusable test data
    """
    return {
        "user_id": 123,
        "content": "What is a Schengen visa?",
        "timestamp": datetime(2024, 1, 15, 10, 30, 0),
        "meta_data": {"confidence": 0.95, "source": "chatbot"}
    }


@pytest.fixture
def conversation_instance(sample_conversation_data):
    """
    Create a ConversationORM instance for testing.
    
    Testing Concept: Fixture that provides test objects
    """
    return ConversationORM(**sample_conversation_data)


@pytest.fixture
def mock_session():
    """
    Mock SQLAlchemy session.
    
    Testing Concept: Mock database session to avoid real DB operations
    """
    session = MagicMock(spec=Session)
    session.add = MagicMock()
    session.commit = MagicMock()
    session.query = MagicMock()
    session.delete = MagicMock()
    session.flush = MagicMock()
    return session


# ============================================================================
# TEST CLASS: Model Instantiation and Attributes
# ============================================================================


class TestConversationORMInstantiation:
    """Test ConversationORM model creation and basic attributes."""
    
    def test_conversation_orm_instantiation_with_all_fields(
        self, sample_conversation_data
    ):
        """
        Test creating ConversationORM with all fields.
        
        Testing Concept: Happy path - normal instantiation
        """
        conversation = ConversationORM(**sample_conversation_data)
        
        assert conversation.user_id == 123
        assert conversation.content == "What is a Schengen visa?"
        assert conversation.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert conversation.meta_data == {"confidence": 0.95, "source": "chatbot"}
    
    def test_conversation_orm_instantiation_with_required_fields_only(self):
        """
        Test creating ConversationORM with only required fields.
        
        Testing Concept: Test minimal valid input
        """
        conversation = ConversationORM(
            user_id=456,
            content="Test message",
            timestamp=datetime.now()
        )
        
        assert conversation.user_id == 456
        assert conversation.content == "Test message"
        assert conversation.meta_data is None  # Optional field
    
    def test_conversation_orm_id_not_set_before_persistence(self):
        """
        Test that ID is None before saving to database.
        
        Testing Concept: Test autoincrement behavior before persistence
        Python Concept: Attributes can be None until DB assigns them
        """
        conversation = ConversationORM(
            user_id=789,
            content="Message",
            timestamp=datetime.now()
        )
        
        # ID should be None before persisting
        assert conversation.id is None
    
    def test_conversation_orm_with_none_meta_data(self):
        """
        Test that meta_data can be None (nullable).
        
        Testing Concept: Test nullable field
        """
        conversation = ConversationORM(
            user_id=100,
            content="Test",
            timestamp=datetime.now(),
            meta_data=None
        )
        
        assert conversation.meta_data is None
    
    def test_conversation_orm_with_empty_meta_data(self):
        """
        Test that meta_data can be empty dict.
        
        Testing Concept: Test empty JSON value
        """
        conversation = ConversationORM(
            user_id=200,
            content="Test",
            timestamp=datetime.now(),
            meta_data={}
        )
        
        assert conversation.meta_data == {}
    
    def test_conversation_orm_with_complex_meta_data(self):
        """
        Test that meta_data can store complex JSON structures.
        
        Testing Concept: Test JSON column with nested data
        """
        complex_meta = {
            "confidence": 0.95,
            "sources": ["doc1", "doc2"],
            "metadata": {
                "language": "en",
                "country": "US"
            }
        }
        
        conversation = ConversationORM(
            user_id=300,
            content="Test",
            timestamp=datetime.now(),
            meta_data=complex_meta
        )
        
        assert conversation.meta_data == complex_meta
        assert conversation.meta_data["metadata"]["language"] == "en"


# ============================================================================
# TEST CLASS: Column Definitions and Types
# ============================================================================


class TestConversationORMColumns:
    """Test column definitions, types, and constraints."""
    
    def test_table_name_is_conversations(self):
        """
        Test that table name is set correctly.
        
        Testing Concept: Verify ORM configuration
        """
        assert ConversationORM.__tablename__ == "conversations"
    
    def test_table_schema_is_visa(self):
        """
        Test that table is in 'visa' schema.
        
        Testing Concept: Verify schema configuration
        """
        # Check table_args for schema
        assert ConversationORM.__table_args__[1]["schema"] == "visa"
    
    def test_id_column_is_primary_key_and_autoincrement(self):
        """
        Test that id column is primary key with autoincrement.
        
        Testing Concept: Test primary key configuration
        Python Concept: Using inspect to examine SQLAlchemy metadata
        """
        mapper = inspect(ConversationORM)
        id_column = mapper.columns["id"]
        
        assert id_column.primary_key is True
        assert id_column.autoincrement is True
        assert isinstance(id_column.type, Integer)
    
    def test_user_id_column_is_integer_not_nullable(self):
        """
        Test user_id column configuration.
        
        Testing Concept: Test column constraints
        """
        mapper = inspect(ConversationORM)
        user_id_column = mapper.columns["user_id"]
        
        assert isinstance(user_id_column.type, Integer)
        assert user_id_column.nullable is False
        assert user_id_column.index is True  # Has index
    
    def test_content_column_is_text_not_nullable(self):
        """
        Test content column configuration.
        
        Testing Concept: Test text column type
        """
        mapper = inspect(ConversationORM)
        content_column = mapper.columns["content"]
        
        assert isinstance(content_column.type, Text)
        assert content_column.nullable is False
    
    def test_timestamp_column_is_datetime_with_timezone(self):
        """
        Test timestamp column has timezone awareness.
        
        Testing Concept: Test timezone-aware datetime column
        """
        mapper = inspect(ConversationORM)
        timestamp_column = mapper.columns["timestamp"]
        
        assert isinstance(timestamp_column.type, DateTime)
        assert timestamp_column.type.timezone is True
        assert timestamp_column.nullable is False
    
    def test_timestamp_has_default_value(self):
        """
        Test timestamp column has Python default (datetime.utcnow).
        
        Testing Concept: Test default value configuration
        """
        mapper = inspect(ConversationORM)
        timestamp_column = mapper.columns["timestamp"]
        
        # Has Python-side default
        assert timestamp_column.default is not None
        # Also has server-side default (func.now())
        assert timestamp_column.server_default is not None
    
    def test_meta_data_column_is_json_nullable(self):
        """
        Test meta_data column configuration.
        
        Testing Concept: Test JSON column type
        """
        mapper = inspect(ConversationORM)
        meta_data_column = mapper.columns["meta_data"]
        
        assert isinstance(meta_data_column.type, JSON)
        assert meta_data_column.nullable is True


# ============================================================================
# TEST CLASS: Indexes and Table Arguments
# ============================================================================


class TestConversationORMIndexes:
    """Test indexes and table-level configurations."""
    
    def test_composite_index_exists(self):
        """
        Test that composite index on (user_id, timestamp) exists.
        
        Testing Concept: Test index configuration
        """
        # Check __table_args__ for index definition
        table_args = ConversationORM.__table_args__
        
        # First element should be the index
        assert len(table_args) >= 1
        composite_index = table_args[0]
        
        assert isinstance(composite_index, Index)
        assert composite_index.name == "idx_user_timestamp"
    
    def test_composite_index_columns(self):
        """
        Test that composite index includes correct columns.
        
        Testing Concept: Verify index column order
        """
        table_args = ConversationORM.__table_args__
        composite_index = table_args[0]
        
        # Get column names from index
        column_names = [col.name for col in composite_index.columns]
        
        assert "user_id" in column_names
        assert "timestamp" in column_names
    
    def test_table_args_includes_schema_option(self):
        """
        Test that __table_args__ includes schema configuration.
        
        Testing Concept: Test table-level options
        """
        table_args = ConversationORM.__table_args__
        
        # Last element should be dict with schema
        schema_config = table_args[-1]
        
        assert isinstance(schema_config, dict)
        assert "schema" in schema_config
        assert schema_config["schema"] == "visa"


# ============================================================================
# TEST CLASS: String Representation
# ============================================================================


class TestConversationORMRepr:
    """Test __repr__ method."""
    
    def test_repr_includes_user_id_and_timestamp(self, conversation_instance):
        """
        Test that __repr__ includes user_id and timestamp.
        
        Testing Concept: Test string representation
        Python Concept: __repr__ method for debugging
        """
        repr_str = repr(conversation_instance)
        
        assert "Conversation" in repr_str
        assert "user_id=123" in repr_str
        assert "timestamp=" in repr_str
    
    def test_repr_format_is_correct(self):
        """
        Test that __repr__ follows expected format.
        
        Testing Concept: Test output format
        """
        conversation = ConversationORM(
            user_id=999,
            content="Test",
            timestamp=datetime(2024, 2, 1, 12, 0, 0)
        )
        
        repr_str = repr(conversation)
        
        # Should match format: <Conversation(user_id=..., timestamp=...)>
        assert repr_str.startswith("<Conversation(")
        assert repr_str.endswith(")>")
        assert "user_id=999" in repr_str
    
    def test_repr_with_different_user_ids(self):
        """
        Test __repr__ with various user IDs.
        
        Testing Concept: Test representation with different data
        """
        for user_id in [1, 100, 999999]:
            conversation = ConversationORM(
                user_id=user_id,
                content="Test",
                timestamp=datetime.now()
            )
            
            repr_str = repr(conversation)
            assert f"user_id={user_id}" in repr_str


# ============================================================================
# TEST CLASS: Database Operations (Mocked)
# ============================================================================


class TestConversationORMDatabaseOperations:
    """Test database operations with mocked session."""
    
    def test_add_conversation_to_session(self, mock_session, conversation_instance):
        """
        Test adding conversation to database session.
        
        Testing Concept: Test ORM persistence workflow
        """
        mock_session.add(conversation_instance)
        mock_session.commit()
        
        # Verify add and commit were called
        mock_session.add.assert_called_once_with(conversation_instance)
        mock_session.commit.assert_called_once()
    
    def test_query_conversations_by_user_id(self, mock_session):
        """
        Test querying conversations by user_id.
        
        Testing Concept: Test query operations
        """
        # Mock query chain
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.all.return_value = [
            ConversationORM(user_id=123, content="Msg1", timestamp=datetime.now()),
            ConversationORM(user_id=123, content="Msg2", timestamp=datetime.now())
        ]
        
        mock_session.query.return_value = mock_query
        
        # Execute query
        results = mock_session.query(ConversationORM).filter_by(user_id=123).all()
        
        assert len(results) == 2
        assert all(conv.user_id == 123 for conv in results)
    
    def test_delete_conversation(self, mock_session, conversation_instance):
        """
        Test deleting a conversation.
        
        Testing Concept: Test delete operation
        """
        mock_session.delete(conversation_instance)
        mock_session.commit()
        
        mock_session.delete.assert_called_once_with(conversation_instance)
        mock_session.commit.assert_called_once()
    
    def test_update_conversation_content(
        self, mock_session, conversation_instance
    ):
        """
        Test updating conversation content.
        
        Testing Concept: Test update operation
        """
        # Modify content
        conversation_instance.content = "Updated message"
        
        mock_session.add(conversation_instance)
        mock_session.commit()
        
        assert conversation_instance.content == "Updated message"
        mock_session.commit.assert_called_once()
    
    def test_bulk_insert_conversations(self, mock_session):
        """
        Test bulk inserting multiple conversations.
        
        Testing Concept: Test bulk operations
        """
        conversations = [
            ConversationORM(user_id=i, content=f"Msg {i}", timestamp=datetime.now())
            for i in range(10)
        ]
        
        for conv in conversations:
            mock_session.add(conv)
        
        mock_session.commit()
        
        assert mock_session.add.call_count == 10
        mock_session.commit.assert_called_once()


# ============================================================================
# TEST CLASS: Timestamp Behavior
# ============================================================================


class TestConversationORMTimestamps:
    """Test timestamp default values and behavior."""
    
    def test_timestamp_defaults_to_current_time_when_not_provided(self):
        """
        Test that timestamp column has default configured.
        
        Testing Concept: Test default value configuration
        Note: Defaults apply at DB level, not Python instantiation
        """
        # Check that the column has a default configured
        mapper = inspect(ConversationORM)
        timestamp_column = mapper.columns["timestamp"]
        
        # Verify defaults exist
        assert timestamp_column.default is not None
        assert timestamp_column.server_default is not None
    
    def test_timestamp_can_be_explicitly_set(self):
        """
        Test that timestamp can be manually set.
        
        Testing Concept: Test explicit value override
        """
        explicit_time = datetime(2023, 6, 15, 14, 30, 0)
        
        conversation = ConversationORM(
            user_id=456,
            content="Test",
            timestamp=explicit_time
        )
        
        assert conversation.timestamp == explicit_time
    
    def test_timestamp_is_timezone_aware_when_set(self):
        """
        Test that timestamp can be timezone-aware.
        
        Testing Concept: Test timezone handling
        """
        tz_aware_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        conversation = ConversationORM(
            user_id=789,
            content="Test",
            timestamp=tz_aware_time
        )
        
        assert conversation.timestamp.tzinfo is not None
    
    def test_multiple_conversations_have_different_timestamps(self):
        """
        Test that explicitly set timestamps can be different.
        
        Testing Concept: Test timestamp uniqueness
        """
        import time
        
        time1 = datetime.utcnow()
        conv1 = ConversationORM(user_id=1, content="First", timestamp=time1)
        
        time.sleep(0.01)
        
        time2 = datetime.utcnow()
        conv2 = ConversationORM(user_id=2, content="Second", timestamp=time2)
        
        # Both should have timestamps
        assert conv1.timestamp is not None
        assert conv2.timestamp is not None
        assert conv1.timestamp != conv2.timestamp


# ============================================================================
# TEST CLASS: Meta Data JSON Field
# ============================================================================


class TestConversationORMMetaData:
    """Test meta_data JSON field behavior."""
    
    def test_meta_data_stores_simple_dict(self):
        """
        Test storing simple dictionary in meta_data.
        
        Testing Concept: Test JSON storage
        """
        conversation = ConversationORM(
            user_id=123,
            content="Test",
            timestamp=datetime.now(),
            meta_data={"key": "value"}
        )
        
        assert conversation.meta_data["key"] == "value"
    
    def test_meta_data_stores_nested_structures(self):
        """
        Test storing nested JSON structures.
        
        Testing Concept: Test complex JSON
        """
        nested_meta = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", "c"]
                }
            }
        }
        
        conversation = ConversationORM(
            user_id=456,
            content="Test",
            timestamp=datetime.now(),
            meta_data=nested_meta
        )
        
        assert conversation.meta_data["level1"]["level2"]["level3"] == ["a", "b", "c"]
    
    def test_meta_data_stores_lists(self):
        """
        Test storing lists in meta_data.
        
        Testing Concept: Test JSON array storage
        """
        conversation = ConversationORM(
            user_id=789,
            content="Test",
            timestamp=datetime.now(),
            meta_data={"tags": ["visa", "travel", "schengen"]}
        )
        
        assert conversation.meta_data["tags"] == ["visa", "travel", "schengen"]
    
    def test_meta_data_stores_numbers(self):
        """
        Test storing numbers in meta_data.
        
        Testing Concept: Test JSON number types
        """
        conversation = ConversationORM(
            user_id=100,
            content="Test",
            timestamp=datetime.now(),
            meta_data={
                "confidence": 0.95,
                "tokens": 150,
                "temperature": 0.7
            }
        )
        
        assert conversation.meta_data["confidence"] == 0.95
        assert conversation.meta_data["tokens"] == 150
        assert conversation.meta_data["temperature"] == 0.7
    
    def test_meta_data_can_be_updated(self):
        """
        Test updating meta_data after instantiation.
        
        Testing Concept: Test mutability of JSON field
        """
        conversation = ConversationORM(
            user_id=200,
            content="Test",
            timestamp=datetime.now(),
            meta_data={"initial": "value"}
        )
        
        # Update meta_data
        conversation.meta_data["new_key"] = "new_value"
        
        assert conversation.meta_data["new_key"] == "new_value"
        assert conversation.meta_data["initial"] == "value"


# ============================================================================
# TEST CLASS: Edge Cases and Validation
# ============================================================================


class TestConversationORMEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_content_with_very_long_text(self):
        """
        Test storing very long text in content field.
        
        Testing Concept: Test Text column capacity
        """
        long_content = "A" * 10000  # 10,000 characters
        
        conversation = ConversationORM(
            user_id=123,
            content=long_content,
            timestamp=datetime.now()
        )
        
        assert len(conversation.content) == 10000
    
    def test_content_with_special_characters(self):
        """
        Test storing special characters in content.
        
        Testing Concept: Test Unicode/special character handling
        """
        special_content = "Hello 👋 Test émoji & special chars: <>?{}[]"
        
        conversation = ConversationORM(
            user_id=456,
            content=special_content,
            timestamp=datetime.now()
        )
        
        assert conversation.content == special_content
    
    def test_content_with_newlines_and_tabs(self):
        """
        Test storing content with whitespace characters.
        
        Testing Concept: Test whitespace preservation
        """
        multiline_content = "Line 1\nLine 2\tTabbed\r\nCarriage return"
        
        conversation = ConversationORM(
            user_id=789,
            content=multiline_content,
            timestamp=datetime.now()
        )
        
        assert "\n" in conversation.content
        assert "\t" in conversation.content
    
    def test_user_id_with_large_integer(self):
        """
        Test storing large integer in user_id.
        
        Testing Concept: Test integer boundary
        """
        large_user_id = 2147483647  # Max 32-bit signed int
        
        conversation = ConversationORM(
            user_id=large_user_id,
            content="Test",
            timestamp=datetime.now()
        )
        
        assert conversation.user_id == large_user_id
    
    def test_user_id_with_zero(self):
        """
        Test storing zero as user_id.
        
        Testing Concept: Test edge value
        """
        conversation = ConversationORM(
            user_id=0,
            content="Test",
            timestamp=datetime.now()
        )
        
        assert conversation.user_id == 0
    
    def test_empty_string_content(self):
        """
        Test storing empty string in content.
        
        Testing Concept: Test minimum valid value
        """
        conversation = ConversationORM(
            user_id=123,
            content="",  # Empty but not None
            timestamp=datetime.now()
        )
        
        assert conversation.content == ""
    
    def test_meta_data_with_empty_dict(self):
        """
        Test storing empty dict in meta_data.
        
        Testing Concept: Test empty JSON object
        """
        conversation = ConversationORM(
            user_id=456,
            content="Test",
            timestamp=datetime.now(),
            meta_data={}
        )
        
        assert conversation.meta_data == {}
        assert len(conversation.meta_data) == 0


# ============================================================================
# TEST CLASS: Base Class
# ============================================================================


class TestSQLAlchemyBase:
    """Test Base declarative class."""
    
    def test_base_is_declarative_base(self):
        """
        Test that Base is SQLAlchemy declarative base.
        
        Testing Concept: Test framework setup
        """
        from sqlalchemy.orm import DeclarativeMeta
        
        assert isinstance(Base, DeclarativeMeta)
        
    def test_conversation_orm_inherits_from_base(self):
        """
        Test that ConversationORM inherits from Base.
        
        Testing Concept: Test inheritance
        Python Concept: Proper way to check SQLAlchemy declarative base inheritance
        """
        assert Base in ConversationORM.__mro__, \
            "ConversationORM should inherit from Base"
        
        # Alternative: Check if ConversationORM has Base's metaclass
        from sqlalchemy.orm import DeclarativeMeta
        assert isinstance(ConversationORM, DeclarativeMeta), \
            "ConversationORM should be an instance of DeclarativeMeta"
        
        # Alternative: Create instance and check
        conversation = ConversationORM(
            user_id=999,
            content="Test",
            timestamp=datetime.now()
        )
        # The instance should be of a type that has Base in its class hierarchy
        assert Base in type(conversation).__mro__, \
            "ConversationORM instances should have Base in class hierarchy"


# ============================================================================
# TEST CLASS: Integration-Style Tests
# ============================================================================


class TestConversationORMIntegration:
    """Test realistic usage scenarios."""
    
    def test_create_query_and_delete_workflow(self, mock_session):
        """
        Test complete CRUD workflow.
        
        Testing Concept: Integration test of multiple operations
        """
        # Create
        conversation = ConversationORM(
            user_id=12345,
            content="Integration test message",
            timestamp=datetime.now(),
            meta_data={"test": True}
        )
        
        mock_session.add(conversation)
        mock_session.commit()
        
        # Query (mock)
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = conversation
        mock_session.query.return_value = mock_query
        
        result = mock_session.query(ConversationORM).filter_by(user_id=12345).first()
        
        assert result.user_id == 12345
        assert result.content == "Integration test message"
        
        # Delete
        mock_session.delete(result)
        mock_session.commit()
        
        assert mock_session.add.called
        assert mock_session.delete.called
        assert mock_session.commit.call_count == 2
    
    def test_multiple_conversations_for_same_user(self, mock_session):
        """
        Test storing multiple conversations for one user.
        
        Testing Concept: Test one-to-many relationship simulation
        """
        conversations = [
            ConversationORM(
                user_id=555,
                content=f"Message {i}",
                timestamp=datetime.now()
            )
            for i in range(5)
        ]
        
        for conv in conversations:
            mock_session.add(conv)
        
        mock_session.commit()
        
        assert mock_session.add.call_count == 5
        assert all(conv.user_id == 555 for conv in conversations)


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("user_id", [1, 100, 999999, 0])
    def test_conversation_with_various_user_ids(self, user_id):
        """
        Test creating conversations with different user IDs.
        
        Testing Concept: Parameterized testing
        """
        conversation = ConversationORM(
            user_id=user_id,
            content="Test",
            timestamp=datetime.now()
        )
        
        assert conversation.user_id == user_id
    
    @pytest.mark.parametrize("content", [
        "Short",
        "A" * 1000,  # Long
        "",  # Empty
        "Special: émojis 👋",
        "Multiline\ntext\nhere"
    ])
    def test_conversation_with_various_content(self, content):
        """
        Test storing various content types.
        
        Testing Concept: Parameterized testing for content variations
        """
        conversation = ConversationORM(
            user_id=123,
            content=content,
            timestamp=datetime.now()
        )
        
        assert conversation.content == content
    
    @pytest.mark.parametrize("meta_data", [
        None,
        {},
        {"key": "value"},
        {"nested": {"data": [1, 2, 3]}},
        {"confidence": 0.95, "source": "test"}
    ])
    def test_conversation_with_various_meta_data(self, meta_data):
        """
        Test storing various meta_data structures.
        
        Testing Concept: Parameterized testing for JSON variations
        """
        conversation = ConversationORM(
            user_id=456,
            content="Test",
            timestamp=datetime.now(),
            meta_data=meta_data
        )
        
        assert conversation.meta_data == meta_data


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.chat.schemas",
        "--cov-report=term-missing"
    ])


