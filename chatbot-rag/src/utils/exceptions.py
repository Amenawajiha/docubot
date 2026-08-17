"""Common exceptions module."""

from src.utils.log_helper import logger


class RecordNotFoundException(Exception):
    """Exception raised when a record is not found."""

    def __init__(self, unique_identifier, message="User not found."):
        logger.exception("RecordNotFoundException for %s", unique_identifier)
        super().__init__(message)


class UserExistsException(Exception):
    """Exception raised when a user already exists."""

    def __init__(
        self,
        email,
        mobile=None,
        message="User with the email or mobile already exists.",
    ):
        text = "UserExistsException for email: %s", email
        if mobile:
            text = f"{text}, mobile: {mobile}"
        logger.exception(text)
        super().__init__(message)


class AuthenticationException(Exception):
    """Exception raised for authentication errors."""

    def __init__(self, email, message="Incorrect email or password"):
        logger.exception("AuthenticationException for email %s", email)
        self.message = message
        super().__init__(self.message)


class AuthorizationException(Exception):
    """Exception raised for authorization errors."""

    def __init__(self, user_id, message="Unauthorized"):
        logger.exception("AuthorizationException for user %s.", user_id)
        self.message = message
        super().__init__(self.message)


class InvalidFilenameException(Exception):
    """Exception raised when an invalid filename is provided."""

    def __init__(self, filename, message="Invalid filename provided."):
        logger.exception("InvalidFilenameException for %s", filename)
        super().__init__(message)


class InvalidExtensionException(Exception):
    """Exception raised when an invalid file extension is provided."""

    def __init__(self, extension, message="Invalid file extension provided."):
        logger.exception("InvalidExtensionException for %s", extension)
        super().__init__(message)


class InvalidMimeTypeException(Exception):
    """Exception raised when an invalid MIME type is provided."""

    def __init__(self, mime_type, message="Invalid MIME type provided."):
        logger.exception("InvalidMimeTypeException for %s", mime_type)
        super().__init__(message)


class LLMException(Exception):
    """Exception raised for LLM errors."""

    def __init__(self, message="LLM error"):
        logger.exception("LLMException")
        self.message = message
        super().__init__(self.message)
