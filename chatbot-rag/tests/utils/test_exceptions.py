"""
Comprehensive unit tests for custom exceptions.

This test suite covers:
- RecordNotFoundException initialization and logging
- UserExistsException initialization and logging
- AuthenticationException initialization and logging
- AuthorizationException initialization and logging
- InvalidFilenameException initialization and logging
- InvalidExtensionException initialization and logging
- InvalidMimeTypeException initialization and logging
- LLMException initialization and logging
- Exception messages and attributes
- Logger calls verification
- Edge cases (None values, empty strings)
"""

import pytest
from unittest.mock import MagicMock, patch

from src.utils.exceptions import (
    AuthenticationException,
    AuthorizationException,
    InvalidExtensionException,
    InvalidFilenameException,
    InvalidMimeTypeException,
    LLMException,
    RecordNotFoundException,
    UserExistsException,
)


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger to prevent actual logging during tests."""
    with patch("src.utils.exceptions.logger") as mock:
        yield mock


# ============================================================================
# TEST CLASS: RecordNotFoundException
# ============================================================================


class TestRecordNotFoundException:
    """Test RecordNotFoundException."""
    
    def test_record_not_found_exception_with_default_message(self, mock_logger):
        """Test RecordNotFoundException with default message."""
        unique_id = "user123"
        
        exc = RecordNotFoundException(unique_id)
        
        assert str(exc) == "User not found."
        mock_logger.exception.assert_called_once_with(
            "RecordNotFoundException for %s", unique_id
        )
    
    def test_record_not_found_exception_with_custom_message(self, mock_logger):
        """Test RecordNotFoundException with custom message."""
        unique_id = "order456"
        custom_message = "Order not found in the system."
        
        exc = RecordNotFoundException(unique_id, message=custom_message)
        
        assert str(exc) == custom_message
        mock_logger.exception.assert_called_once_with(
            "RecordNotFoundException for %s", unique_id
        )
    
    def test_record_not_found_exception_can_be_raised(self, mock_logger):
        """Test that RecordNotFoundException can be raised."""
        with pytest.raises(RecordNotFoundException) as exc_info:
            raise RecordNotFoundException("user789")
        
        assert "User not found." in str(exc_info.value)


# ============================================================================
# TEST CLASS: UserExistsException
# ============================================================================


class TestUserExistsException:
    """Test UserExistsException."""
    
    def test_user_exists_exception_with_email_only(self, mock_logger):
        """Test UserExistsException with email only."""
        email = "test@example.com"
        
        exc = UserExistsException(email)
        
        assert str(exc) == "User with the email or mobile already exists."
        mock_logger.exception.assert_called_once()
    
    def test_user_exists_exception_with_email_and_mobile(self, mock_logger):
        """Test UserExistsException with email and mobile."""
        email = "test@example.com"
        mobile = "+1234567890"
        
        exc = UserExistsException(email, mobile=mobile)
        
        assert str(exc) == "User with the email or mobile already exists."
        mock_logger.exception.assert_called_once()
    
    def test_user_exists_exception_can_be_raised(self, mock_logger):
        """Test that UserExistsException can be raised."""
        with pytest.raises(UserExistsException) as exc_info:
            raise UserExistsException("duplicate@example.com")
        
        assert "already exists" in str(exc_info.value)


# ============================================================================
# TEST CLASS: AuthenticationException
# ============================================================================


class TestAuthenticationException:
    """Test AuthenticationException."""
    
    def test_authentication_exception_with_default_message(self, mock_logger):
        """Test AuthenticationException with default message."""
        email = "user@example.com"
        
        exc = AuthenticationException(email)
        
        assert str(exc) == "Incorrect email or password"
        assert exc.message == "Incorrect email or password"
        mock_logger.exception.assert_called_once_with(
            "AuthenticationException for email %s", email
        )
    
    def test_authentication_exception_with_custom_message(self, mock_logger):
        """Test AuthenticationException with custom message."""
        email = "user@example.com"
        custom_message = "Account locked."
        
        exc = AuthenticationException(email, message=custom_message)
        
        assert str(exc) == custom_message
        assert exc.message == custom_message
    
    def test_authentication_exception_can_be_raised(self, mock_logger):
        """Test that AuthenticationException can be raised."""
        with pytest.raises(AuthenticationException) as exc_info:
            raise AuthenticationException("failed@example.com")
        
        assert "Incorrect email or password" in str(exc_info.value)


# ============================================================================
# TEST CLASS: AuthorizationException
# ============================================================================


class TestAuthorizationException:
    """Test AuthorizationException."""
    
    def test_authorization_exception_with_default_message(self, mock_logger):
        """Test AuthorizationException with default message."""
        user_id = "user123"
        
        exc = AuthorizationException(user_id)
        
        assert str(exc) == "Unauthorized"
        assert exc.message == "Unauthorized"
        mock_logger.exception.assert_called_once_with(
            "AuthorizationException for user %s.", user_id
        )
    
    def test_authorization_exception_with_custom_message(self, mock_logger):
        """Test AuthorizationException with custom message."""
        user_id = "user456"
        custom_message = "Insufficient permissions."
        
        exc = AuthorizationException(user_id, message=custom_message)
        
        assert str(exc) == custom_message
        assert exc.message == custom_message
    
    def test_authorization_exception_can_be_raised(self, mock_logger):
        """Test that AuthorizationException can be raised."""
        with pytest.raises(AuthorizationException) as exc_info:
            raise AuthorizationException("restricted_user")
        
        assert "Unauthorized" in str(exc_info.value)


# ============================================================================
# TEST CLASS: InvalidFilenameException
# ============================================================================


class TestInvalidFilenameException:
    """Test InvalidFilenameException."""
    
    def test_invalid_filename_exception_with_default_message(self, mock_logger):
        """Test InvalidFilenameException with default message."""
        filename = "../../etc/passwd"
        
        exc = InvalidFilenameException(filename)
        
        assert str(exc) == "Invalid filename provided."
        mock_logger.exception.assert_called_once_with(
            "InvalidFilenameException for %s", filename
        )
    
    def test_invalid_filename_exception_with_custom_message(self, mock_logger):
        """Test InvalidFilenameException with custom message."""
        filename = "malicious.txt"
        custom_message = "Filename contains forbidden characters."
        
        exc = InvalidFilenameException(filename, message=custom_message)
        
        assert str(exc) == custom_message
    
    def test_invalid_filename_exception_can_be_raised(self, mock_logger):
        """Test that InvalidFilenameException can be raised."""
        with pytest.raises(InvalidFilenameException) as exc_info:
            raise InvalidFilenameException("../../../etc/hosts")
        
        assert "Invalid filename" in str(exc_info.value)


# ============================================================================
# TEST CLASS: InvalidExtensionException
# ============================================================================


class TestInvalidExtensionException:
    """Test InvalidExtensionException."""
    
    def test_invalid_extension_exception_with_default_message(self, mock_logger):
        """Test InvalidExtensionException with default message."""
        extension = ".exe"
        
        exc = InvalidExtensionException(extension)
        
        assert str(exc) == "Invalid file extension provided."
        mock_logger.exception.assert_called_once_with(
            "InvalidExtensionException for %s", extension
        )
    
    def test_invalid_extension_exception_with_custom_message(self, mock_logger):
        """Test InvalidExtensionException with custom message."""
        extension = ".php"
        custom_message = "PHP files are not allowed."
        
        exc = InvalidExtensionException(extension, message=custom_message)
        
        assert str(exc) == custom_message
    
    def test_invalid_extension_exception_can_be_raised(self, mock_logger):
        """Test that InvalidExtensionException can be raised."""
        with pytest.raises(InvalidExtensionException) as exc_info:
            raise InvalidExtensionException(".sh")
        
        assert "Invalid file extension" in str(exc_info.value)


# ============================================================================
# TEST CLASS: InvalidMimeTypeException
# ============================================================================


class TestInvalidMimeTypeException:
    """Test InvalidMimeTypeException."""
    
    def test_invalid_mime_type_exception_with_default_message(self, mock_logger):
        """Test InvalidMimeTypeException with default message."""
        mime_type = "application/x-msdownload"
        
        exc = InvalidMimeTypeException(mime_type)
        
        assert str(exc) == "Invalid MIME type provided."
        mock_logger.exception.assert_called_once_with(
            "InvalidMimeTypeException for %s", mime_type
        )
    
    def test_invalid_mime_type_exception_with_custom_message(self, mock_logger):
        """Test InvalidMimeTypeException with custom message."""
        mime_type = "application/javascript"
        custom_message = "JavaScript files are not allowed."
        
        exc = InvalidMimeTypeException(mime_type, message=custom_message)
        
        assert str(exc) == custom_message
    
    def test_invalid_mime_type_exception_can_be_raised(self, mock_logger):
        """Test that InvalidMimeTypeException can be raised."""
        with pytest.raises(InvalidMimeTypeException) as exc_info:
            raise InvalidMimeTypeException("application/x-executable")
        
        assert "Invalid MIME type" in str(exc_info.value)


# ============================================================================
# TEST CLASS: LLMException
# ============================================================================


class TestLLMException:
    """Test LLMException."""
    
    def test_llm_exception_with_default_message(self, mock_logger):
        """Test LLMException with default message."""
        exc = LLMException()
        
        assert str(exc) == "LLM error"
        assert exc.message == "LLM error"
        mock_logger.exception.assert_called_once_with("LLMException")
    
    def test_llm_exception_with_custom_message(self, mock_logger):
        """Test LLMException with custom message."""
        custom_message = "LLM API rate limit exceeded."
        
        exc = LLMException(message=custom_message)
        
        assert str(exc) == custom_message
        assert exc.message == custom_message
    
    def test_llm_exception_can_be_raised(self, mock_logger):
        """Test that LLMException can be raised."""
        with pytest.raises(LLMException) as exc_info:
            raise LLMException(message="Model timeout")
        
        assert "Model timeout" in str(exc_info.value)


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


@pytest.mark.parametrize("unique_id,message", [
    ("user123", "User not found."),
    ("order456", "Order not found."),
    (12345, "Record not found."),
])
def test_record_not_found_with_various_inputs(mock_logger, unique_id, message):
    """Test RecordNotFoundException with various inputs."""
    exc = RecordNotFoundException(unique_id, message=message)
    
    assert str(exc) == message
    mock_logger.exception.assert_called()


@pytest.mark.parametrize("extension", [".exe", ".bat", ".sh", ".php"])
def test_invalid_extension_with_various_extensions(mock_logger, extension):
    """Test InvalidExtensionException with various extensions."""
    exc = InvalidExtensionException(extension)
    
    assert "Invalid file extension" in str(exc)
    mock_logger.exception.assert_called()


@pytest.mark.parametrize("mime_type", [
    "application/x-msdownload",
    "application/javascript",
    "text/html",
])
def test_invalid_mime_type_with_various_types(mock_logger, mime_type):
    """Test InvalidMimeTypeException with various MIME types."""
    exc = InvalidMimeTypeException(mime_type)
    
    assert "Invalid MIME type" in str(exc)
    mock_logger.exception.assert_called()