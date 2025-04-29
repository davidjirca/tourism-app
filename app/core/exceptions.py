from fastapi import HTTPException, status


class BaseAppError(HTTPException):
    """Base class for all application exceptions."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "An unexpected error occurred"

    def __init__(self, detail: str = None):
        super().__init__(status_code=self.status_code, detail=detail or self.detail)


class NotFoundError(BaseAppError):
    """Resource not found error."""

    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class ForbiddenError(BaseAppError):
    """Permission denied error."""

    status_code = status.HTTP_403_FORBIDDEN
    detail = "Not authorized to perform this action"


class BadRequestError(BaseAppError):
    """Invalid request error."""

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Invalid request"


class UnauthorizedError(BaseAppError):
    """Authentication error."""

    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication failed"

    def __init__(self, detail: str = None):
        super().__init__(detail=detail or self.detail)
        self.headers = {"WWW-Authenticate": "Bearer"}


class DuplicateError(BaseAppError):
    """Duplicate resource error."""

    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists"
