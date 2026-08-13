from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception with a default status code."""


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found.",
        )


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource already exists.") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Not authenticated.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Permission denied.") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestError(AppException):
    def __init__(self, detail: str = "Bad request.") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnprocessableError(AppException):
    def __init__(self, detail: str = "Unprocessable entity.") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class BotOfflineError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "BOT_OFFLINE", "message": "Bot is offline"}
        )


class RateLimitError(AppException):
    def __init__(self, detail: str = "Rate limit exceeded.") -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail
        )


class TokenExpiredError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__(detail="Token has expired.")


class InvalidTokenError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__(detail="Invalid token.")


class EmailNotVerifiedError(ForbiddenError):
    def __init__(self) -> None:
        super().__init__(detail="Email address is not verified.")


class InactiveAccountError(ForbiddenError):
    def __init__(self) -> None:
        super().__init__(detail="Account is inactive.")