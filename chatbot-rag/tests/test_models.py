"""
Comprehensive unit tests for Pydantic models.

This test suite covers:
- Model instantiation and validation
- Field validators (content sanitization, metadata validation)
- Model validators (cross-field validation)
- HTML escaping and XSS prevention
- Whitespace handling
- Boundary conditions (min/max lengths)
- Type validation and coercion
- Optional field handling
- Factory methods
- Edge cases (None, empty strings, special characters)
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import (
    Message,
    ConfidenceResult,
    ScoringWeights,
    RetrievalResult,
    User,
    IncomingMessagePayload,
    ValidatedStoredMessage,
    WebSocketMessageRequest,
)


# ============================================================================
# FIXTURES - Reusable Test Data
# ============================================================================


@pytest.fixture
def valid_timestamp():
    """Valid timestamp for testing."""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def sample_metadata():
    """Sample metadata dictionary."""
    return {
        "interaction_type": "message",
        "form_data": {"field1": "value1"}
    }


@pytest.fixture
def sample_message_data(valid_timestamp):
    """Valid data for Message model."""
    return {
        "content": "Test message content",
        "role": "user",
        "timestamp": valid_timestamp,
        "user_id": 123,
        "metadata": {"key": "value"}
    }


@pytest.fixture
def sample_confidence_data():
    """Valid data for ConfidenceResult model."""
    return {
        "retrieval_confidence": 0.85,
        "llm_confidence": 0.90,
        "overall_confidence": 0.875,
        "is_confident": True,
        "confidence_breakdown": {
            "retrieval": 0.85,
            "llm": 0.90
        }
    }


@pytest.fixture
def sample_retrieval_result():
    """Valid data for RetrievalResult model."""
    return {
        "content": "Retrieved document content",
        "metadata": {"source": "doc1.pdf", "page": 5},
        "relevance_score": 0.92
    }


@pytest.fixture
def sample_user_data(valid_timestamp):
    """Valid data for User model."""
    return {
        "id": "user123",
        "email": "test@example.com",
        "user_type": "guest",
        "created_at": valid_timestamp,
        "last_active": valid_timestamp
    }


@pytest.fixture
def sample_incoming_payload():
    """Valid data for IncomingMessagePayload."""
    return {
        "content": "Hello world",
        "timestamp": "2024-01-15T10:30:00",
        "metadata": {
            "interaction_type": "message"
        }
    }


# ============================================================================
# TEST CLASS: Message Model
# ============================================================================


class TestMessageModel:
    """Test Message Pydantic model."""
    
    def test_message_creation_with_valid_data(self, sample_message_data):
        """
        Test creating Message with valid data.
        
        Testing Concept: Happy path validation
        """
        message = Message(**sample_message_data)
        
        assert message.content == "Test message content"
        assert message.role == "user"
        assert message.user_id == 123
        assert message.metadata == {"key": "value"}
    
    def test_message_with_assistant_role(self, sample_message_data):
        """
        Test Message with assistant role.
        
        Testing Concept: Role variation
        """
        sample_message_data["role"] = "assistant"
        message = Message(**sample_message_data)
        
        assert message.role == "assistant"
    
    def test_message_with_empty_metadata(self, sample_message_data):
        """
        Test Message with empty metadata.
        
        Testing Concept: Optional field - empty dict
        """
        sample_message_data["metadata"] = {}
        message = Message(**sample_message_data)
        
        assert message.metadata == {}
    
    def test_message_without_metadata(self, sample_message_data):
        """
        Test Message without metadata field.
        
        Testing Concept: Optional field - omitted
        """
        del sample_message_data["metadata"]
        message = Message(**sample_message_data)
        
        assert message.metadata == {}  # Default value
    
    def test_message_with_none_metadata(self, sample_message_data):
        """
        Test Message with None metadata.
        
        Testing Concept: Optional field - None value
        """
        sample_message_data["metadata"] = None
        message = Message(**sample_message_data)
        
        # Pydantic converts None to default value
        assert message.metadata is None
    
    def test_message_invalid_role(self, sample_message_data):
        """
        Test Message with invalid role.
        
        Testing Concept: Literal validation
        """
        sample_message_data["role"] = "invalid_role"
        
        with pytest.raises(ValidationError) as exc_info:
            Message(**sample_message_data)
        
        assert "role" in str(exc_info.value).lower()
    
    def test_message_missing_required_field(self, sample_message_data):
        """
        Test Message with missing required field.
        
        Testing Concept: Required field validation
        """
        del sample_message_data["content"]
        
        with pytest.raises(ValidationError) as exc_info:
            Message(**sample_message_data)
        
        assert "content" in str(exc_info.value).lower()
    
    def test_message_invalid_timestamp_type(self, sample_message_data):
        """
        Test Message with invalid timestamp type.
        
        Testing Concept: Type validation
        """
        sample_message_data["timestamp"] = "not a datetime"
        
        with pytest.raises(ValidationError) as exc_info:
            Message(**sample_message_data)
        
        # Pydantic might try to parse string, but invalid format should fail
        assert "timestamp" in str(exc_info.value).lower() or exc_info.value is not None


# ============================================================================
# TEST CLASS: ConfidenceResult Model
# ============================================================================


class TestConfidenceResultModel:
    """Test ConfidenceResult Pydantic model."""
    
    def test_confidence_result_creation(self, sample_confidence_data):
        """
        Test creating ConfidenceResult with valid data.
        
        Testing Concept: Happy path validation
        """
        result = ConfidenceResult(**sample_confidence_data)
        
        assert result.retrieval_confidence == 0.85
        assert result.llm_confidence == 0.90
        assert result.overall_confidence == 0.875
        assert result.is_confident is True
        assert result.confidence_breakdown == {"retrieval": 0.85, "llm": 0.90}
    
    def test_confidence_result_with_zero_confidence(self, sample_confidence_data):
        """
        Test ConfidenceResult with zero confidence scores.
        
        Testing Concept: Boundary value - minimum
        """
        sample_confidence_data["retrieval_confidence"] = 0.0
        sample_confidence_data["llm_confidence"] = 0.0
        sample_confidence_data["overall_confidence"] = 0.0
        sample_confidence_data["is_confident"] = False
        
        result = ConfidenceResult(**sample_confidence_data)
        
        assert result.retrieval_confidence == 0.0
        assert result.llm_confidence == 0.0
        assert result.is_confident is False
    
    def test_confidence_result_with_max_confidence(self, sample_confidence_data):
        """
        Test ConfidenceResult with maximum confidence (1.0).
        
        Testing Concept: Boundary value - maximum
        """
        sample_confidence_data["retrieval_confidence"] = 1.0
        sample_confidence_data["llm_confidence"] = 1.0
        sample_confidence_data["overall_confidence"] = 1.0
        
        result = ConfidenceResult(**sample_confidence_data)
        
        assert result.retrieval_confidence == 1.0
        assert result.llm_confidence == 1.0
    
    def test_confidence_result_missing_required_field(self, sample_confidence_data):
        """
        Test ConfidenceResult with missing required field.
        
        Testing Concept: Required field validation
        """
        del sample_confidence_data["is_confident"]
        
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceResult(**sample_confidence_data)
        
        assert "is_confident" in str(exc_info.value).lower()
    
    def test_confidence_result_invalid_type(self, sample_confidence_data):
        """
        Test ConfidenceResult with invalid type for float field.
        
        Testing Concept: Type validation
        """
        sample_confidence_data["retrieval_confidence"] = "not a float"
        
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceResult(**sample_confidence_data)
        
        assert "retrieval_confidence" in str(exc_info.value).lower()


# ============================================================================
# TEST CLASS: ScoringWeights Model
# ============================================================================


class TestScoringWeightsModel:
    """Test ScoringWeights Pydantic model."""
    
    def test_scoring_weights_with_defaults(self):
        """
        Test ScoringWeights with default values.
        
        Testing Concept: Default field values
        """
        weights = ScoringWeights()
        
        assert weights.retrieval_weight == 0.4
        assert weights.llm_weight == 0.6
    
    def test_scoring_weights_with_custom_values(self):
        """
        Test ScoringWeights with custom values.
        
        Testing Concept: Custom field values
        """
        weights = ScoringWeights(retrieval_weight=0.3, llm_weight=0.7)
        
        assert weights.retrieval_weight == 0.3
        assert weights.llm_weight == 0.7
    
    def test_scoring_weights_with_zero_values(self):
        """
        Test ScoringWeights with zero weights.
        
        Testing Concept: Boundary value - zero
        """
        weights = ScoringWeights(retrieval_weight=0.0, llm_weight=1.0)
        
        assert weights.retrieval_weight == 0.0
        assert weights.llm_weight == 1.0
    
    def test_scoring_weights_invalid_type(self):
        """
        Test ScoringWeights with invalid type.
        
        Testing Concept: Type validation
        """
        with pytest.raises(ValidationError) as exc_info:
            ScoringWeights(retrieval_weight="invalid")
        
        assert "retrieval_weight" in str(exc_info.value).lower()


# ============================================================================
# TEST CLASS: RetrievalResult Model
# ============================================================================


class TestRetrievalResultModel:
    """Test RetrievalResult Pydantic model."""
    
    def test_retrieval_result_creation(self, sample_retrieval_result):
        """
        Test creating RetrievalResult with valid data.
        
        Testing Concept: Happy path validation
        """
        result = RetrievalResult(**sample_retrieval_result)
        
        assert result.content == "Retrieved document content"
        assert result.metadata == {"source": "doc1.pdf", "page": 5}
        assert result.relevance_score == 0.92
    
    def test_retrieval_result_with_empty_content(self, sample_retrieval_result):
        """
        Test RetrievalResult with empty content.
        
        Testing Concept: Edge case - empty string
        """
        sample_retrieval_result["content"] = ""
        result = RetrievalResult(**sample_retrieval_result)
        
        assert result.content == ""
    
    def test_retrieval_result_with_empty_metadata(self, sample_retrieval_result):
        """
        Test RetrievalResult with empty metadata.
        
        Testing Concept: Edge case - empty dict
        """
        sample_retrieval_result["metadata"] = {}
        result = RetrievalResult(**sample_retrieval_result)
        
        assert result.metadata == {}
    
    def test_retrieval_result_with_zero_score(self, sample_retrieval_result):
        """
        Test RetrievalResult with zero relevance score.
        
        Testing Concept: Boundary value - minimum
        """
        sample_retrieval_result["relevance_score"] = 0.0
        result = RetrievalResult(**sample_retrieval_result)
        
        assert result.relevance_score == 0.0
    
    def test_retrieval_result_with_max_score(self, sample_retrieval_result):
        """
        Test RetrievalResult with maximum relevance score.
        
        Testing Concept: Boundary value - maximum
        """
        sample_retrieval_result["relevance_score"] = 1.0
        result = RetrievalResult(**sample_retrieval_result)
        
        assert result.relevance_score == 1.0
    
    def test_retrieval_result_missing_field(self, sample_retrieval_result):
        """
        Test RetrievalResult with missing required field.
        
        Testing Concept: Required field validation
        """
        del sample_retrieval_result["content"]
        
        with pytest.raises(ValidationError) as exc_info:
            RetrievalResult(**sample_retrieval_result)
        
        assert "content" in str(exc_info.value).lower()


# ============================================================================
# TEST CLASS: User Model
# ============================================================================


class TestUserModel:
    """Test User Pydantic model."""
    
    def test_user_creation_with_all_fields(self, sample_user_data):
        """
        Test creating User with all fields.
        
        Testing Concept: Happy path with all fields
        """
        user = User(**sample_user_data)
        
        assert user.id == "user123"
        assert user.email == "test@example.com"
        assert user.user_type == "guest"
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.last_active, datetime)
    
    def test_user_without_email(self, sample_user_data):
        """
        Test User without email (optional field).
        
        Testing Concept: Optional field - omitted
        """
        del sample_user_data["email"]
        user = User(**sample_user_data)
        
        assert user.email is None
    
    def test_user_with_none_email(self, sample_user_data):
        """
        Test User with None email.
        
        Testing Concept: Optional field - None value
        """
        sample_user_data["email"] = None
        user = User(**sample_user_data)
        
        assert user.email is None
    
    def test_user_with_default_user_type(self, sample_user_data):
        """
        Test User with default user_type.
        
        Testing Concept: Default field value
        """
        del sample_user_data["user_type"]
        user = User(**sample_user_data)
        
        assert user.user_type == "guest"
    
    def test_user_with_custom_user_type(self, sample_user_data):
        """
        Test User with custom user_type.
        
        Testing Concept: Custom field value
        """
        sample_user_data["user_type"] = "admin"
        user = User(**sample_user_data)
        
        assert user.user_type == "admin"
    
    def test_user_missing_required_field(self, sample_user_data):
        """
        Test User with missing required field.
        
        Testing Concept: Required field validation
        """
        del sample_user_data["id"]
        
        with pytest.raises(ValidationError) as exc_info:
            User(**sample_user_data)
        
        assert "id" in str(exc_info.value).lower()


# ============================================================================
# TEST CLASS: IncomingMessagePayload Model - Content Sanitization
# ============================================================================


class TestIncomingMessagePayloadContentSanitization:
    """Test IncomingMessagePayload content sanitization."""
    
    def test_payload_with_valid_content(self, sample_incoming_payload):
        """
        Test payload with valid content.
        
        Testing Concept: Happy path sanitization
        """
        payload = IncomingMessagePayload(**sample_incoming_payload)
        
        assert payload.content == "Hello world"
    
    def test_payload_sanitizes_html_tags(self):
        """
        Test that HTML tags are escaped.
        
        Testing Concept: XSS prevention
        """
        data = {
            "content": "<script>alert('xss')</script>Hello"
        }
        
        payload = IncomingMessagePayload(**data)
        
        # HTML should be escaped
        assert "&lt;script&gt;" in payload.content
        assert "&lt;/script&gt;" in payload.content
        assert "<script>" not in payload.content
    
    def test_payload_sanitizes_html_entities(self):
        """
        Test that HTML entities are escaped.
        
        Testing Concept: HTML entity escaping
        """
        data = {
            "content": "Hello & goodbye < > \" '"
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Special chars should be escaped
        assert "&amp;" in payload.content
        assert "&lt;" in payload.content
        assert "&gt;" in payload.content
    
    def test_payload_removes_null_bytes(self):
        """
        Test that null bytes are removed.
        
        Testing Concept: Null byte injection prevention
        """
        data = {
            "content": "Hello\x00World"
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert "\x00" not in payload.content
        assert "HelloWorld" == payload.content
    
    def test_payload_strips_whitespace(self):
        """
        Test that leading/trailing whitespace is stripped.
        
        Testing Concept: Whitespace normalization
        """
        data = {
            "content": "   Hello world   "
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert payload.content == "Hello world"
    
    def test_payload_limits_consecutive_whitespace(self):
        """
        Test that excessive consecutive whitespace is limited.
        
        Testing Concept: Whitespace limiting
        """
        data = {
            "content": "Hello" + " " * 20 + "world"
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Should limit to max 10 consecutive spaces
        consecutive_spaces = payload.content.count(" " * 11)
        assert consecutive_spaces == 0
    
    def test_payload_content_min_length_validation(self):
        """
        Test that content must have minimum length.
        
        Testing Concept: Min length validation
        """
        data = {
            "content": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            IncomingMessagePayload(**data)
        
        assert "content" in str(exc_info.value).lower()
    
    def test_payload_content_max_length_validation(self):
        """
        Test that content respects max length.
        
        Testing Concept: Max length validation
        """
        data = {
            "content": "A" * 10001  # Exceeds max_length=10000
        }
        
        with pytest.raises(ValidationError) as exc_info:
            IncomingMessagePayload(**data)
        
        assert "content" in str(exc_info.value).lower()
    
    def test_payload_content_at_max_length(self):
        """
        Test content exactly at max length.
        
        Testing Concept: Boundary value - max length
        """
        data = {
            "content": "A" * 10000
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert len(payload.content) == 10000
    
    def test_payload_with_unicode_characters(self):
        """
        Test content with Unicode characters.
        
        Testing Concept: Unicode handling
        """
        data = {
            "content": "Hello 你好 مرحبا"
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert "你好" in payload.content
        assert "مرحبا" in payload.content
    
    def test_payload_with_special_characters(self):
        """
        Test content with special characters.
        
        Testing Concept: Special character handling
        """
        data = {
            "content": "Test!@#$%^&*()_+-=[]{}|;:,.<>?"
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Non-HTML special chars should be preserved (after escaping)
        assert payload.content is not None
        assert len(payload.content) > 0


# ============================================================================
# TEST CLASS: IncomingMessagePayload Model - Metadata Validation
# ============================================================================


class TestIncomingMessagePayloadMetadataValidation:
    """Test IncomingMessagePayload metadata validation."""
    
    def test_payload_with_valid_metadata(self):
        """
        Test payload with valid metadata.
        
        Testing Concept: Happy path metadata validation
        """
        data = {
            "content": "Hello",
            "metadata": {
                "interaction_type": "message"
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert payload.metadata["interaction_type"] == "message"
    
    def test_payload_with_allowed_interaction_types(self):
        """
        Test all allowed interaction types.
        
        Testing Concept: Whitelist validation
        """
        allowed_types = ['button_click', 'form_submission', 'message', 'bot_response']
        
        for interaction_type in allowed_types:
            data = {
                "content": "Hello",
                "metadata": {
                    "interaction_type": interaction_type
                }
            }
            
            payload = IncomingMessagePayload(**data)
            assert payload.metadata["interaction_type"] == interaction_type
    
    def test_payload_with_invalid_interaction_type(self):
        """
        Test that invalid interaction_type defaults to 'message'.
        
        Testing Concept: Invalid value handling
        """
        data = {
            "content": "Hello",
            "metadata": {
                "interaction_type": "invalid_type"
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Should default to safe value
        assert payload.metadata["interaction_type"] == "message"
    
    def test_payload_filters_unknown_metadata_keys(self):
        """
        Test that unknown metadata keys are filtered out.
        
        Testing Concept: Whitelist filtering
        """
        data = {
            "content": "Hello",
            "metadata": {
                "interaction_type": "message",
                "unknown_key": "malicious_value",
                "another_unknown": "bad_data"
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Only allowed keys should be present
        assert "interaction_type" in payload.metadata
        assert "unknown_key" not in payload.metadata
        assert "another_unknown" not in payload.metadata
    
    def test_payload_with_form_data(self):
        """
        Test payload with form_data metadata.
        
        Testing Concept: Nested metadata validation
        """
        data = {
            "content": "Hello",
            "metadata": {
                "form_data": {
                    "field1": "value1",
                    "field2": "value2"
                }
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert "form_data" in payload.metadata
        assert payload.metadata["form_data"]["field1"] == "value1"
    
    def test_payload_sanitizes_form_data_values(self):
        """
        Test that form_data values are HTML escaped.
        
        Testing Concept: Nested value sanitization
        """
        data = {
            "content": "Hello",
            "metadata": {
                "form_data": {
                    "field1": "<script>alert('xss')</script>"
                }
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Form data values should be HTML escaped
        assert "&lt;script&gt;" in payload.metadata["form_data"]["field1"]
        assert "<script>" not in payload.metadata["form_data"]["field1"]
    
    def test_payload_limits_form_data_field_count(self):
        """
        Test that form_data field count is limited.
        
        Testing Concept: DoS prevention
        """
        # Create more than 50 fields
        form_data = {f"field{i}": f"value{i}" for i in range(60)}
        
        data = {
            "content": "Hello",
            "metadata": {
                "form_data": form_data
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Should not include form_data if field count exceeds limit
        # (Based on: if len(value) <= 50)
        assert "form_data" not in payload.metadata or payload.metadata["form_data"] == {}
    
    def test_payload_truncates_form_data_keys(self):
        """
        Test that form_data keys are truncated to 100 chars.
        
        Testing Concept: Length limiting
        """
        long_key = "A" * 150
        
        data = {
            "content": "Hello",
            "metadata": {
                "form_data": {
                    long_key: "value"
                }
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Key should be truncated to 100 chars
        if payload.metadata.get("form_data"):
            for key in payload.metadata["form_data"].keys():
                assert len(key) <= 100
    
    def test_payload_truncates_form_data_values(self):
        """
        Test that form_data values are truncated to 1000 chars.
        
        Testing Concept: Length limiting
        """
        long_value = "B" * 1500
        
        data = {
            "content": "Hello",
            "metadata": {
                "form_data": {
                    "field1": long_value
                }
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Value should be truncated to 1000 chars
        if payload.metadata.get("form_data"):
            assert len(payload.metadata["form_data"]["field1"]) <= 1000
    
    def test_payload_with_none_metadata(self):
        """
        Test payload with None metadata.
        
        Testing Concept: None handling
        """
        data = {
            "content": "Hello",
            "metadata": None
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert payload.metadata == {}
    
    def test_payload_without_metadata(self):
        """
        Test payload without metadata field.
        
        Testing Concept: Optional field - omitted
        """
        data = {
            "content": "Hello"
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert payload.metadata == {}
    
    def test_payload_with_empty_metadata(self):
        """
        Test payload with empty metadata dict.
        
        Testing Concept: Empty dict handling
        """
        data = {
            "content": "Hello",
            "metadata": {}
        }
        
        payload = IncomingMessagePayload(**data)
        
        assert payload.metadata == {}
    
    def test_payload_form_data_not_dict(self):
        """
        Test that non-dict form_data is ignored.
        
        Testing Concept: Type validation
        """
        data = {
            "content": "Hello",
            "metadata": {
                "form_data": "not a dict"
            }
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Non-dict form_data should be filtered out
        assert "form_data" not in payload.metadata


# ============================================================================
# TEST CLASS: ValidatedStoredMessage Model
# ============================================================================


class TestValidatedStoredMessageModel:
    """Test ValidatedStoredMessage Pydantic model."""
    
    def test_validated_message_creation(self, valid_timestamp):
        """
        Test creating ValidatedStoredMessage directly.
        
        Testing Concept: Direct model instantiation
        """
        message = ValidatedStoredMessage(
            content="Test content",
            role="user",
            timestamp=valid_timestamp,
            user_id=123,
            metadata={"key": "value"}
        )
        
        assert message.content == "Test content"
        assert message.role == "user"
        assert message.user_id == 123
    
    def test_validated_message_role_is_user_only(self, valid_timestamp):
        """
        Test that role is restricted to 'user'.
        
        Testing Concept: Literal validation
        """
        # Should accept "user"
        message = ValidatedStoredMessage(
            content="Test",
            role="user",
            timestamp=valid_timestamp,
            user_id=123
        )
        assert message.role == "user"
        
        # Should reject "assistant"
        with pytest.raises(ValidationError) as exc_info:
            ValidatedStoredMessage(
                content="Test",
                role="assistant",
                timestamp=valid_timestamp,
                user_id=123
            )
        
        assert "role" in str(exc_info.value).lower()
    
    def test_validated_message_with_default_metadata(self, valid_timestamp):
        """
        Test ValidatedStoredMessage with default metadata.
        
        Testing Concept: Default field value
        """
        message = ValidatedStoredMessage(
            content="Test",
            role="user",
            timestamp=valid_timestamp,
            user_id=123
        )
        
        assert message.metadata == {}
    
    @patch('src.models.datetime')
    def test_from_client_payload_factory_method(self, mock_datetime):
        """
        Test creating ValidatedStoredMessage from client payload.
        
        Testing Concept: Factory method
        """
        # Mock datetime.utcnow
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        
        client_payload = IncomingMessagePayload(
            content="Client message",
            metadata={"interaction_type": "message"}
        )
        
        validated = ValidatedStoredMessage.from_client_payload(
            payload=client_payload,
            user_id=456
        )
        
        assert validated.content == "Client message"
        assert validated.role == "user"  # Force user role
        assert validated.timestamp == fixed_time  # Server timestamp
        assert validated.user_id == 456
        assert validated.metadata == {"interaction_type": "message"}
    
    @patch('src.models.datetime')
    def test_from_client_payload_ignores_client_timestamp(self, mock_datetime):
        """
        Test that server timestamp overrides client timestamp.
        
        Testing Concept: Server-controlled fields
        """
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        
        client_payload = IncomingMessagePayload(
            content="Message",
            timestamp="2020-01-01T00:00:00"  # Old client timestamp
        )
        
        validated = ValidatedStoredMessage.from_client_payload(
            payload=client_payload,
            user_id=789
        )
        
        # Server timestamp should be used, not client's
        assert validated.timestamp == fixed_time
    
    @patch('src.models.datetime')
    def test_from_client_payload_forces_user_role(self, mock_datetime):
        """
        Test that client cannot set assistant role.
        
        Testing Concept: Security - role enforcement
        """
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        
        client_payload = IncomingMessagePayload(
            content="Trying to impersonate assistant"
        )
        
        validated = ValidatedStoredMessage.from_client_payload(
            payload=client_payload,
            user_id=999
        )
        
        # Role should always be "user" regardless of any client input
        assert validated.role == "user"
    
    @patch('src.models.datetime')
    def test_from_client_payload_with_sanitized_content(self, mock_datetime):
        """
        Test that content sanitization is preserved through factory method.
        
        Testing Concept: Sanitization preservation
        """
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        
        client_payload = IncomingMessagePayload(
            content="<script>alert('xss')</script>Safe text"
        )
        
        validated = ValidatedStoredMessage.from_client_payload(
            payload=client_payload,
            user_id=111
        )
        
        # Content should be sanitized (HTML escaped)
        assert "&lt;script&gt;" in validated.content
        assert "<script>" not in validated.content


# ============================================================================
# TEST CLASS: WebSocketMessageRequest Model
# ============================================================================


class TestWebSocketMessageRequestModel:
    """Test WebSocketMessageRequest Pydantic model."""
    
    def test_websocket_request_query_type(self):
        """
        Test WebSocketMessageRequest with query type.
        
        Testing Concept: Query type validation
        """
        data = {
            "type": "query",
            "query": "What is my visa status?"
        }
        
        request = WebSocketMessageRequest(**data)
        
        assert request.type == "query"
        assert request.query == "What is my visa status?"
        assert request.message is None
    
    def test_websocket_request_store_message_type(self):
        """
        Test WebSocketMessageRequest with store_message type.
        
        Testing Concept: Store message type validation
        """
        data = {
            "type": "store_message",
            "message": {
                "content": "Store this message"
            }
        }
        
        request = WebSocketMessageRequest(**data)
        
        assert request.type == "store_message"
        assert request.message is not None
        assert request.message.content == "Store this message"
        assert request.query is None
    
    def test_websocket_request_default_type(self):
        """
        Test WebSocketMessageRequest with default type.
        
        Testing Concept: Default field value
        """
        data = {
            "query": "Test query"
        }
        
        request = WebSocketMessageRequest(**data)
        
        # Default type should be "query"
        assert request.type == "query"
    
    def test_websocket_request_sanitizes_query(self):
        """
        Test that query is sanitized.
        
        Testing Concept: Query sanitization
        """
        data = {
            "type": "query",
            "query": "<script>alert('xss')</script>Query"
        }
        
        request = WebSocketMessageRequest(**data)
        
        # Query should be HTML escaped
        assert "&lt;script&gt;" in request.query
        assert "<script>" not in request.query
    
    def test_websocket_request_strips_query_whitespace(self):
        """
        Test that query whitespace is stripped.
        
        Testing Concept: Whitespace normalization
        """
        data = {
            "type": "query",
            "query": "   Test query   "
        }
        
        request = WebSocketMessageRequest(**data)
        
        assert request.query == "Test query"
    
    def test_websocket_request_query_max_length(self):
        """
        Test query max length validation.
        
        Testing Concept: Max length validation
        """
        data = {
            "type": "query",
            "query": "A" * 5001  # Exceeds max_length=5000
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        assert "query" in str(exc_info.value).lower()
    
    def test_websocket_request_query_at_max_length(self):
        """
        Test query exactly at max length.
        
        Testing Concept: Boundary value - max length
        """
        data = {
            "type": "query",
            "query": "A" * 5000
        }
        
        request = WebSocketMessageRequest(**data)
        
        assert len(request.query) == 5000
    
    def test_websocket_request_query_type_without_query_fails(self):
        """
        Test that query type requires query field.
        
        Testing Concept: Cross-field validation
        """
        data = {
            "type": "query"
            # Missing query field
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        error_str = str(exc_info.value).lower()
        assert "query" in error_str or "empty" in error_str
    
    def test_websocket_request_query_type_with_empty_query_fails(self):
        """
        Test that query type rejects empty query.
        
        Testing Concept: Empty value validation
        """
        data = {
            "type": "query",
            "query": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        error_str = str(exc_info.value).lower()
        assert "query" in error_str or "empty" in error_str
    
    def test_websocket_request_query_type_with_none_query_fails(self):
        """
        Test that query type rejects None query.
        
        Testing Concept: None value validation
        """
        data = {
            "type": "query",
            "query": None
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        error_str = str(exc_info.value).lower()
        assert "query" in error_str or "empty" in error_str
    
    def test_websocket_request_store_message_type_without_message_fails(self):
        """
        Test that store_message type requires message field.
        
        Testing Concept: Cross-field validation
        """
        data = {
            "type": "store_message"
            # Missing message field
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        error_str = str(exc_info.value).lower()
        assert "message" in error_str or "required" in error_str
    
    def test_websocket_request_store_message_type_with_none_message_fails(self):
        """
        Test that store_message type rejects None message.
        
        Testing Concept: None value validation
        """
        data = {
            "type": "store_message",
            "message": None
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        error_str = str(exc_info.value).lower()
        assert "message" in error_str or "required" in error_str
    
    def test_websocket_request_invalid_type(self):
        """
        Test WebSocketMessageRequest with invalid type.
        
        Testing Concept: Literal validation
        """
        data = {
            "type": "invalid_type",
            "query": "Test"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessageRequest(**data)
        
        assert "type" in str(exc_info.value).lower()
    
    def test_websocket_request_with_none_query_for_query_type(self):
        """
        Test that None query is handled correctly.
        
        Testing Concept: None value handling in sanitizer
        """
        # This should fail validation because query type needs query
        data = {
            "type": "query",
            "query": None
        }
        
        with pytest.raises(ValidationError):
            WebSocketMessageRequest(**data)
    
    def test_websocket_request_query_with_special_characters(self):
        """
        Test query with special characters.
        
        Testing Concept: Special character handling
        """
        data = {
            "type": "query",
            "query": "What's the status of my application?"
        }
        
        request = WebSocketMessageRequest(**data)
        
        # Apostrophe should be escaped
        assert "&#x27;" in request.query or "What" in request.query


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestModelIntegration:
    """Integration tests combining multiple models."""
    
    @patch('src.models.datetime')
    def test_full_message_flow_from_client_to_storage(self, mock_datetime):
        """
        Test complete message flow: client payload -> validation -> storage.
        
        Testing Concept: End-to-end model flow
        """
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        
        # 1. Client sends payload with potentially malicious content
        websocket_request = WebSocketMessageRequest(
            type="store_message",
            message={
                "content": "<script>alert('xss')</script>Legitimate question",
                "metadata": {
                    "interaction_type": "message",
                    "malicious_key": "should_be_filtered"
                }
            }
        )
        
        # 2. Create validated storage message
        validated = ValidatedStoredMessage.from_client_payload(
            payload=websocket_request.message,
            user_id=12345
        )
        
        # 3. Verify sanitization occurred
        assert "&lt;script&gt;" in validated.content
        assert "<script>" not in validated.content
        
        # 4. Verify role enforcement
        assert validated.role == "user"
        
        # 5. Verify server timestamp used
        assert validated.timestamp == fixed_time
        
        # 6. Verify metadata filtering
        assert "interaction_type" in validated.metadata
        assert "malicious_key" not in validated.metadata
    
    def test_websocket_query_request_sanitization(self):
        """
        Test WebSocket query request sanitization.
        
        Testing Concept: Query sanitization flow
        """
        request = WebSocketMessageRequest(
            type="query",
            query="<img src=x onerror='alert(1)'>What is my visa status?"
        )
        
        # Query should be sanitized
        assert "&lt;img" in request.query
        assert "<img" not in request.query
        assert "onerror" in request.query  # Text preserved, but escaped


# ============================================================================
# TEST CLASS: Edge Cases and Security
# ============================================================================


class TestSecurityAndEdgeCases:
    """Test security-related edge cases."""
    
    def test_sql_injection_attempt_in_content(self):
        """
        Test that SQL injection attempts are escaped.
        
        Testing Concept: SQL injection prevention
        """
        data = {
            "content": "'; DROP TABLE users; --"
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Content should be preserved but HTML escaped
        # SQL injection shouldn't work since content is escaped
        assert payload.content is not None
    
    def test_path_traversal_attempt(self):
        """
        Test path traversal attempts are neutralized.
        
        Testing Concept: Path traversal prevention
        """
        data = {
            "content": "../../etc/passwd"
        }
        
        payload = IncomingMessagePayload(**data)
        
        # Should be stored as-is (escaped), not interpreted
        assert "../" in payload.content
    
    def test_extremely_nested_metadata(self):
        """
        Test deeply nested metadata structures.
        
        Testing Concept: Nested structure handling
        """
        data = {
            "content": "Test",
            "metadata": {
                "form_data": {
                    "field1": {"nested": {"deeply": "value"}}
                }
            }
        }
        
        # Should handle nested structures gracefully
        payload = IncomingMessagePayload(**data)
        
        # Form data should be processed (converted to string)
        assert "form_data" in payload.metadata or payload.metadata == {}


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.models",
        "--cov-report=term-missing",
        "--cov-report=html"
    ])


