"""
Comprehensive unit tests for AuthMiddleware authentication service.

This test suite covers:
- JWT token generation (access and refresh tokens)
- Token validation and decoding
- User extraction from tokens
- Error handling for invalid tokens
- Edge cases (expired tokens, missing secrets, invalid algorithms)
- Configuration loading
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from jose import JWTError, jwt

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.auth.service import AuthMiddleware


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_env_and_config():
    """
    Mock environment variables and configuration.
    
    Returns environment setup that needs to be active during tests.
    """
    with patch.dict(
        os.environ,
        {
            "JWT_SECRET": "test-secret-key-12345",  # Mock JWT secret
        },
        clear=False,  # Don't clear other env vars
    ):
        with patch("src.auth.service.get_config") as mock_config:
            # Mock configuration values
            mock_config.side_effect = lambda key, default=None: {
                "auth.jwt_algorithm": "HS256",
                "auth.access_jwt_expiration_minutes": 30,
                "auth.refresh_jwt_expiration_days": 7,
            }.get(key, default)
            
            yield mock_config


@pytest.fixture
def auth_middleware(mock_env_and_config):
    """
    Provides an AuthMiddleware instance with mocked config.
    
    Python Concept: Fixture that depends on another fixture
    """
    return AuthMiddleware()


@pytest.fixture
def valid_access_token(auth_middleware):
    """
    Generate a valid access token for testing.
    
    Testing Concept: Fixture that generates test data
    """
    return auth_middleware.generate_jwt(user_id=123, token_usage="access")


@pytest.fixture
def valid_refresh_token(auth_middleware):
    """Generate a valid refresh token for testing."""
    return auth_middleware.generate_jwt(user_id=456, token_usage="refresh")


@pytest.fixture
def expired_token():
    """
    Generate an expired token for testing.
    
    Testing Concept: Creating edge case test data
    """
    secret = "test-secret-key-12345"
    payload = {
        "sub": "789",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
        "token_usage": "access",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestAuthMiddlewareInitialization:
    """Test AuthMiddleware initialization and configuration."""
    
    def test_initialization_success(self, auth_middleware):
        """
        Test that AuthMiddleware initializes with correct configuration.
        
        Testing Concept: Verify object initialization
        """
        assert auth_middleware is not None
        assert auth_middleware.jwt_secret == "test-secret-key-12345"
        assert auth_middleware.jwt_algorithm == "HS256"
    
    def test_initialization_loads_jwt_secret_from_env(self):
        """
        Test that JWT_SECRET is loaded from environment variables.
        
        Python Concept: Environment variable access
        Testing Concept: Test configuration loading
        """
        with patch.dict(os.environ, {"JWT_SECRET": "custom-secret"}, clear=False):
            with patch("src.auth.service.get_config") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "auth.jwt_algorithm": "HS256",
                }.get(key, default)
                
                middleware = AuthMiddleware()
                assert middleware.jwt_secret == "custom-secret"
    
    def test_initialization_loads_algorithm_from_config(self):
        """
        Test that JWT algorithm is loaded from config.
        
        Testing Concept: Verify configuration integration
        """
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}, clear=False):
            with patch("src.auth.service.get_config") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "auth.jwt_algorithm": "HS512",  # Different algorithm
                }.get(key, default)
                
                middleware = AuthMiddleware()
                assert middleware.jwt_algorithm == "HS512"


# ============================================================================
# TEST CLASS: JWT Token Generation - Happy Path
# ============================================================================


class TestJWTGenerationHappyPath:
    """Test successful JWT token generation scenarios."""
    
    def test_generate_access_token_success(self, auth_middleware):
        """
        Test generating a valid access token.
        
        Testing Concept: Happy path - normal usage
        """
        token = auth_middleware.generate_jwt(user_id=100, token_usage="access")
        
        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token payload
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == "100"
        assert decoded["token_usage"] == "access"
        assert "exp" in decoded
    
    def test_generate_refresh_token_success(self, auth_middleware):
        """
        Test generating a valid refresh token.
        
        Testing Concept: Test alternate code path (refresh vs access)
        """
        token = auth_middleware.generate_jwt(user_id=200, token_usage="refresh")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token payload
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == "200"
        assert decoded["token_usage"] == "refresh"
    
    def test_access_token_has_correct_expiration(self, auth_middleware):
        """
        Test that access token expires after configured duration.
        
        Testing Concept: Verify time-based logic
        Python Concept: datetime operations
        """
        before_generation = datetime.now(timezone.utc)
        token = auth_middleware.generate_jwt(user_id=300, token_usage="access")
        after_generation = datetime.now(timezone.utc)
        
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Should expire ~30 minutes from now (configured value)
        expected_expiry = before_generation + timedelta(minutes=30)
        time_diff = abs((exp_datetime - expected_expiry).total_seconds())
        
        # Allow 5 second margin for test execution time
        assert time_diff < 5
    
    def test_refresh_token_has_correct_expiration(self, auth_middleware):
        """
        Test that refresh token expires after configured duration (7 days).
        
        Testing Concept: Verify different expiration for different token types
        """
        before_generation = datetime.now(timezone.utc)
        token = auth_middleware.generate_jwt(user_id=400, token_usage="refresh")
        
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        exp_datetime = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_expiry = before_generation + timedelta(days=7)
        time_diff = abs((exp_datetime - expected_expiry).total_seconds())
        
        assert time_diff < 5
    
    def test_generate_token_includes_user_id_as_string(self, auth_middleware):
        """
        Test that user_id is stored as string in 'sub' claim.
        
        Testing Concept: Verify data type conversion
        Python Concept: Type checking with isinstance()
        """
        token = auth_middleware.generate_jwt(user_id=999, token_usage="access")
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        # 'sub' should be string "999", not integer 999
        assert decoded["sub"] == "999"
        assert isinstance(decoded["sub"], str)
    
    def test_generate_token_different_users_different_tokens(self, auth_middleware):
        """
        Test that different user IDs produce different tokens.
        
        Testing Concept: Verify uniqueness
        """
        token1 = auth_middleware.generate_jwt(user_id=1, token_usage="access")
        token2 = auth_middleware.generate_jwt(user_id=2, token_usage="access")
        
        assert token1 != token2


# ============================================================================
# TEST CLASS: JWT Token Generation - Error Cases
# ============================================================================


class TestJWTGenerationErrors:
    """Test error handling in JWT token generation."""
    
    def test_generate_jwt_invalid_token_usage_raises_error(self, auth_middleware):
        """
        Test that invalid token_usage raises ValueError.
        
        Testing Concept: Test error handling for invalid input
        Python Concept: pytest.raises context manager
        """
        with pytest.raises(ValueError, match="Invalid token usage"):
            auth_middleware.generate_jwt(user_id=100, token_usage="invalid")
    
    def test_generate_jwt_with_none_user_id(self, auth_middleware):
        """
        Test behavior when user_id is None.
        
        Testing Concept: Test edge case - None value
        """
        # This should work (JWT allows any value in 'sub')
        # but will result in "None" string in token
        token = auth_middleware.generate_jwt(user_id=None, token_usage="access")
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == "None"
    
    def test_generate_jwt_with_zero_user_id(self, auth_middleware):
        """
        Test behavior with user_id=0.
        
        Testing Concept: Boundary value testing
        """
        token = auth_middleware.generate_jwt(user_id=0, token_usage="access")
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == "0"
    
    def test_generate_jwt_with_negative_user_id(self, auth_middleware):
        """
        Test behavior with negative user_id.
        
        Testing Concept: Invalid input testing
        """
        token = auth_middleware.generate_jwt(user_id=-1, token_usage="access")
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == "-1"
    
    def test_generate_jwt_with_very_large_user_id(self, auth_middleware):
        """
        Test behavior with extremely large user_id.
        
        Testing Concept: Stress testing with extreme values
        """
        large_id = 999999999999999
        token = auth_middleware.generate_jwt(user_id=large_id, token_usage="access")
        decoded = jwt.decode(
            token, 
            auth_middleware.jwt_secret, 
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == str(large_id)


# ============================================================================
# TEST CLASS: Get Current User (Access Token Validation)
# ============================================================================


class TestGetCurrentUser:
    """Test validation and extraction of user from access tokens."""
    
    def test_get_current_user_with_valid_token_success(
        self, auth_middleware, valid_access_token
    ):
        """
        Test extracting user_id from valid access token.
        
        Testing Concept: Happy path for token validation
        """
        user_id = auth_middleware.get_current_user(valid_access_token)
        
        assert user_id == 123
        assert isinstance(user_id, int)
    
    def test_get_current_user_returns_integer_user_id(
        self, auth_middleware, valid_access_token
    ):
        """
        Test that user_id is converted to integer.
        
        Testing Concept: Verify type conversion
        """
        user_id = auth_middleware.get_current_user(valid_access_token)
        
        assert isinstance(user_id, int)
        assert user_id == 123
    
    def test_get_current_user_with_expired_token_raises_401(
        self, auth_middleware, expired_token
    ):
        """
        Test that expired token raises HTTPException with 401.
        
        Testing Concept: Test expiration handling
        Python Concept: Exception matching with pytest.raises
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(expired_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate user" in exc_info.value.detail
    
    def test_get_current_user_with_invalid_signature_raises_401(
        self, auth_middleware
    ):
        """
        Test that token with invalid signature raises 401.
        
        Testing Concept: Security - reject tampered tokens
        """
        # Create token with different secret
        fake_token = jwt.encode(
            {"sub": "123", "token_usage": "access"}, 
            "wrong-secret",  # Different secret
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(fake_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_with_refresh_token_raises_401(
        self, auth_middleware, valid_refresh_token
    ):
        """
        Test that using refresh token in access endpoint raises error.
        
        Testing Concept: Verify token usage validation
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(valid_refresh_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_with_malformed_token_raises_401(self, auth_middleware):
        """
        Test that malformed token string raises 401.
        
        Testing Concept: Error handling for invalid format
        """
        malformed_token = "not.a.valid.jwt.token"
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(malformed_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_with_empty_token_raises_401(self, auth_middleware):
        """
        Test that empty token raises 401.
        
        Testing Concept: Edge case - empty string
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user("")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_without_sub_claim_raises_401(self, auth_middleware):
        """
        Test that token missing 'sub' claim raises 401.
        
        Testing Concept: Test incomplete data
        """
        # Create token without 'sub' claim
        token = jwt.encode(
            {"token_usage": "access"},  # Missing 'sub'
            auth_middleware.jwt_secret,
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_without_token_usage_raises_401(self, auth_middleware):
        """
        Test that token missing 'token_usage' claim raises 401.
        
        Testing Concept: Test missing required field
        """
        token = jwt.encode(
            {"sub": "123"},  # Missing 'token_usage'
            auth_middleware.jwt_secret,
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_with_wrong_algorithm_raises_401(self, auth_middleware):
        """
        Test that token with wrong algorithm raises 401.
        
        Testing Concept: Security - algorithm mismatch
        """
        # Create token with different algorithm
        token = jwt.encode(
            {"sub": "123", "token_usage": "access"},
            auth_middleware.jwt_secret,
            algorithm="HS512"  # Different algorithm
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_includes_www_authenticate_header(
        self, auth_middleware, expired_token
    ):
        """
        Test that 401 response includes WWW-Authenticate header.
        
        Testing Concept: Verify HTTP response headers
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_user(expired_token)
        
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


# ============================================================================
# TEST CLASS: Get Current Refresh User (Refresh Token Validation)
# ============================================================================


class TestGetCurrentRefreshUser:
    """Test validation and extraction of user from refresh tokens."""
    
    def test_get_current_refresh_user_with_valid_token_success(
        self, auth_middleware, valid_refresh_token
    ):
        """
        Test extracting user_id from valid refresh token.
        
        Testing Concept: Happy path for refresh token validation
        """
        result = auth_middleware.get_current_refresh_user(valid_refresh_token)
        
        assert result == {"user_id": 456}
        assert isinstance(result, dict)
        assert isinstance(result["user_id"], int)
    
    def test_get_current_refresh_user_returns_dict_with_user_id(
        self, auth_middleware, valid_refresh_token
    ):
        """
        Test that refresh user returns dictionary format.
        
        Testing Concept: Verify return data structure
        """
        result = auth_middleware.get_current_refresh_user(valid_refresh_token)
        
        assert "user_id" in result
        assert len(result) == 1
    
    def test_get_current_refresh_user_with_access_token_raises_401(
        self, auth_middleware, valid_access_token
    ):
        """
        Test that using access token in refresh endpoint raises error.
        
        Testing Concept: Verify token type validation
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_refresh_user(valid_access_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_refresh_user_with_expired_token_raises_401(
        self, auth_middleware
    ):
        """
        Test that expired refresh token raises 401.
        
        Testing Concept: Test expiration for refresh tokens
        """
        # Create expired refresh token
        expired_refresh = jwt.encode(
            {
                "sub": "789",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "token_usage": "refresh",
            },
            auth_middleware.jwt_secret,
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_refresh_user(expired_refresh)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_refresh_user_with_invalid_signature_raises_401(
        self, auth_middleware
    ):
        """
        Test that refresh token with invalid signature raises 401.
        
        Testing Concept: Security validation
        """
        fake_token = jwt.encode(
            {"sub": "456", "token_usage": "refresh"},
            "wrong-secret",
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_refresh_user(fake_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_refresh_user_with_malformed_token_raises_401(
        self, auth_middleware
    ):
        """
        Test that malformed refresh token raises 401.
        
        Testing Concept: Error handling for invalid format
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_refresh_user("invalid.token.format")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_refresh_user_without_sub_claim_raises_401(
        self, auth_middleware
    ):
        """
        Test that refresh token missing 'sub' claim raises 401.
        
        Testing Concept: Test incomplete token data
        """
        token = jwt.encode(
            {"token_usage": "refresh"},  # Missing 'sub'
            auth_middleware.jwt_secret,
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_refresh_user(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_refresh_user_includes_www_authenticate_header(
        self, auth_middleware
    ):
        """
        Test that 401 response includes WWW-Authenticate header.
        
        Testing Concept: Verify HTTP headers in error response
        """
        with pytest.raises(HTTPException) as exc_info:
            auth_middleware.get_current_refresh_user("invalid")
        
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


# ============================================================================
# TEST CLASS: JWT Secret Configuration Tests
# ============================================================================


class TestJWTSecretConfiguration:
    """Test JWT secret handling and validation."""
    
    def test_get_current_user_with_missing_jwt_secret_raises_error(self):
        """
        Test that missing JWT_SECRET raises RuntimeError.
        
        Testing Concept: Test missing configuration
        """
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            with patch("src.auth.service.get_config") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "auth.jwt_algorithm": "HS256",
                }.get(key, default)
                
                middleware = AuthMiddleware()
                
                # Create a valid token structure
                token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.test"
                
                with pytest.raises(RuntimeError, match="JWT secret not configured"):
                    middleware.get_current_user(token)
    
    def test_get_current_refresh_user_with_missing_jwt_secret_raises_error(self):
        """
        Test that missing JWT_SECRET raises RuntimeError for refresh tokens.
        
        Testing Concept: Test missing configuration in different code path
        """
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.auth.service.get_config") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "auth.jwt_algorithm": "HS256",
                }.get(key, default)
                
                middleware = AuthMiddleware()
                token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.test"
                
                with pytest.raises(RuntimeError, match="JWT secret not configured"):
                    middleware.get_current_refresh_user(token)
    
    def test_initialization_with_empty_jwt_secret(self):
        """
        Test that empty JWT_SECRET is handled.
        
        Testing Concept: Edge case - empty string
        """
        with patch.dict(os.environ, {"JWT_SECRET": ""}, clear=False):
            with patch("src.auth.service.get_config") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "auth.jwt_algorithm": "HS256",
                }.get(key, default)
                
                middleware = AuthMiddleware()
                
                # Empty secret should fail when trying to validate
                token = "some.jwt.token"
                with pytest.raises(RuntimeError, match="JWT secret not configured"):
                    middleware.get_current_user(token)
    
    def test_jwt_secret_is_string_or_bytes(self, auth_middleware):
        """
        Test that JWT secret is proper type.
        
        Testing Concept: Type validation
        """
        assert isinstance(auth_middleware.jwt_secret, (str, bytes))


# ============================================================================
# TEST CLASS: Integration-Style Tests
# ============================================================================


class TestEndToEndTokenFlow:
    """Test complete token generation and validation flow."""
    
    def test_full_access_token_lifecycle(self, auth_middleware):
        """
        Test generating and validating access token end-to-end.
        
        Testing Concept: Integration test of multiple methods
        """
        user_id = 555
        
        # Generate token
        token = auth_middleware.generate_jwt(user_id=user_id, token_usage="access")
        
        # Validate token
        extracted_user_id = auth_middleware.get_current_user(token)
        
        # Should match original user_id
        assert extracted_user_id == user_id
    
    def test_full_refresh_token_lifecycle(self, auth_middleware):
        """
        Test generating and validating refresh token end-to-end.
        
        Testing Concept: Integration test for refresh flow
        """
        user_id = 666
        
        # Generate refresh token
        token = auth_middleware.generate_jwt(user_id=user_id, token_usage="refresh")
        
        # Validate refresh token
        result = auth_middleware.get_current_refresh_user(token)
        
        # Should match original user_id
        assert result["user_id"] == user_id
    
    def test_access_and_refresh_tokens_are_independent(self, auth_middleware):
        """
        Test that access and refresh tokens can coexist.
        
        Testing Concept: Test multiple token types simultaneously
        """
        user_id = 777
        
        access_token = auth_middleware.generate_jwt(user_id, "access")
        refresh_token = auth_middleware.generate_jwt(user_id, "refresh")
        
        # Both should be valid for their respective endpoints
        assert auth_middleware.get_current_user(access_token) == user_id
        assert auth_middleware.get_current_refresh_user(refresh_token)["user_id"] == user_id
        
        # But should fail on wrong endpoint
        with pytest.raises(HTTPException):
            auth_middleware.get_current_user(refresh_token)
        
        with pytest.raises(HTTPException):
            auth_middleware.get_current_refresh_user(access_token)
    
    def test_multiple_users_tokens_dont_interfere(self, auth_middleware):
        """
        Test that tokens for different users are independent.
        
        Testing Concept: Test isolation between users
        """
        user1_token = auth_middleware.generate_jwt(111, "access")
        user2_token = auth_middleware.generate_jwt(222, "access")
        
        user1_id = auth_middleware.get_current_user(user1_token)
        user2_id = auth_middleware.get_current_user(user2_token)
        
        assert user1_id == 111
        assert user2_id == 222
        assert user1_id != user2_id


# ============================================================================
# TEST CLASS: Logging Tests
# ============================================================================


class TestLogging:
    """Test that logging works correctly."""
    
    @patch("src.auth.service.logger")
    def test_generate_jwt_logs_token_generation(self, mock_logger, auth_middleware):
        """
        Test that token generation is logged.
        
        Testing Concept: Verify logging behavior
        Python Concept: Mock verification with assert_called_with
        """
        auth_middleware.generate_jwt(user_id=123, token_usage="access")
        
        # Should log that we're generating access token
        mock_logger.info.assert_called_with("Generating %s token..", "access")
    
    @patch("src.auth.service.logger")
    def test_get_current_user_logs_decoding(self, mock_logger, auth_middleware, valid_access_token):
        """
        Test that token decoding is logged.
        
        Testing Concept: Verify logging in validation
        """
        auth_middleware.get_current_user(valid_access_token)
        
        # Should log that we're decoding access token
        mock_logger.info.assert_called_with("Decoding access token..")
    
    @patch("src.auth.service.logger")
    def test_get_current_refresh_user_logs_decoding(
        self, mock_logger, auth_middleware, valid_refresh_token
    ):
        """
        Test that refresh token decoding is logged.
        
        Testing Concept: Verify logging in different code path
        """
        auth_middleware.get_current_refresh_user(valid_refresh_token)
        
        mock_logger.info.assert_called_with("Decoding refresh token..")
    
    @patch("src.auth.service.logger")
    def test_get_current_user_logs_exception_on_error(self, mock_logger, auth_middleware):
        """
        Test that exceptions are logged.
        
        Testing Concept: Verify error logging
        """
        invalid_token = "invalid.token"
        
        try:
            auth_middleware.get_current_user(invalid_token)
        except HTTPException:
            pass
        
        # Should log the exception
        assert mock_logger.exception.called


# ============================================================================
# PARAMETERIZED TESTS - Test Multiple Scenarios Efficiently
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios using parameterization."""
    
    @pytest.mark.parametrize(
        "user_id,token_usage",
        [
            (1, "access"),
            (999, "access"),
            (1, "refresh"),
            (999, "refresh"),
            (0, "access"),
            (-1, "refresh"),
        ],
    )
    def test_generate_jwt_various_user_ids_and_types(
        self, auth_middleware, user_id, token_usage
    ):
        """
        Test token generation with various user IDs and token types.
        
        Testing Concept: Parameterized testing for multiple inputs
        Python Concept: @pytest.mark.parametrize decorator
        """
        token = auth_middleware.generate_jwt(user_id=user_id, token_usage=token_usage)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        decoded = jwt.decode(
            token,
            auth_middleware.jwt_secret,
            algorithms=[auth_middleware.jwt_algorithm]
        )
        
        assert decoded["sub"] == str(user_id)
        assert decoded["token_usage"] == token_usage
    
    @pytest.mark.parametrize(
        "invalid_token",
        [
            "",  # Empty
            "invalid",  # Not a JWT
            "a.b",  # Too few segments
            "a.b.c.d",  # Too many segments
            None,  # None value (will cause error)
        ],
    )
    def test_get_current_user_with_various_invalid_tokens(
        self, auth_middleware, invalid_token
    ):
        """
        Test validation rejects various invalid token formats.
        
        Testing Concept: Test multiple invalid inputs efficiently
        """
        if invalid_token is None:
            # Special case: None will cause different error
            with pytest.raises((HTTPException, AttributeError)):
                auth_middleware.get_current_user(invalid_token)
        else:
            with pytest.raises(HTTPException) as exc_info:
                auth_middleware.get_current_user(invalid_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src.auth.service", "--cov-report=term-missing"])


