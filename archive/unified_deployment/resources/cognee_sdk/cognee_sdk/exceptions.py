"""
Exception classes for Cognee SDK.

All exceptions inherit from CogneeSDKError and provide detailed error information.
"""



class CogneeSDKError(Exception):
    """Base exception for all Cognee SDK errors."""

    pass


class CogneeAPIError(CogneeSDKError):
    """Exception raised for API call errors."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response: dict | None = None,
    ) -> None:
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: Optional response data from the API
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(f"[{status_code}] {message}")


class AuthenticationError(CogneeAPIError):
    """Exception raised for authentication errors (401)."""

    pass


class NotFoundError(CogneeAPIError):
    """Exception raised when a resource is not found (404)."""

    pass


class ValidationError(CogneeAPIError):
    """Exception raised for request validation errors (400)."""

    pass


class ServerError(CogneeAPIError):
    """Exception raised for server errors (5xx)."""

    pass


class TimeoutError(CogneeSDKError):
    """Exception raised when a request times out."""

    def __init__(self, message: str, attempts: int = 0) -> None:
        """
        Initialize timeout error.

        Args:
            message: Error message
            attempts: Number of retry attempts made
        """
        self.attempts = attempts
        super().__init__(message)
