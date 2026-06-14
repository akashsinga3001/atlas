# backend/app/core/exceptions.py

from typing import Any, Dict, Optional, List
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AtlasException(Exception):
    """
    Base class for all exceptions in the application.
    """

    def __init__(self, message: str, details: Optional[List[Dict[str, Any]]] = None, error_code: Optional[str] = None):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """ Convert the exception to a dictionary representation. """
        return { "error_type": self.__class__.__name__, "message": self.message, "details": self.details, "error_code": self.error_code }


class ValidationError(AtlasException):
    """Raised when data validation fails."""

    def __init__(self, message: str = "Validation error", field_errors: Optional[Dict[str, Any]] = None, **kwargs):
        self.field_errors = field_errors or {}
        super().__init__(message, details={ "field_errors": self.field_errors }, **kwargs)


class NotFoundError(AtlasException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: Optional[str] = None, **kwargs):
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier '{identifier}'"

        details = { "resource": resource }
        if identifier:
            details["identifier"] = identifier

        super().__init__(message, details=details, **kwargs)


class AuthenticationError(AtlasException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, **kwargs)


class ExternalAPIError(AtlasException):
    """Raised when external API calls fail."""

    def __init__(self, api_name: str, message: str = "External API error", status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None, **kwargs):
        self.api_name = api_name
        self.status_code = status_code
        self.response_data = response_data

        # Merge provided details with API-specific details
        provided_details = kwargs.pop('details', {})
        details = { "api_name": api_name, "status_code": status_code, "response_data": response_data, **provided_details }

        super().__init__(message, details=details, **kwargs)


class DatabaseError(AtlasException):
    """Raised when database operations fail."""

    def __init__(self, operation: str, message: str = "Database operation failed", **kwargs):
        details = { "operation": operation }
        super().__init__(message, details=details, **kwargs)


async def atlas_exception_handler(request: Request, exc: AtlasException) -> JSONResponse:
    """
    Custom exception handler for AtlasException and its subclasses.
    """
    status_code_map = { ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY, NotFoundError: status.HTTP_404_NOT_FOUND, AuthenticationError: status.HTTP_401_UNAUTHORIZED, ExternalAPIError: status.HTTP_502_BAD_GATEWAY }
    status_code = status_code_map.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=status_code, content={ "success": False, "message": exc.message, "error_type": exc.__class__.__name__, "details": exc.details, "error_code": exc.error_code })
