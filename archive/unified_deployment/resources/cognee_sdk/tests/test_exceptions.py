"""
Unit tests for exception classes.

Tests all exception types and their properties.
"""


from cognee_sdk.exceptions import (
    AuthenticationError,
    CogneeAPIError,
    CogneeSDKError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


class TestCogneeSDKError:
    """Tests for CogneeSDKError base exception."""

    def test_cognee_sdk_error_creation(self):
        """Test creating CogneeSDKError."""
        error = CogneeSDKError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_cognee_sdk_error_inheritance(self):
        """Test CogneeSDKError inheritance."""
        error = CogneeSDKError("Test")
        assert isinstance(error, Exception)


class TestCogneeAPIError:
    """Tests for CogneeAPIError."""

    def test_cognee_api_error_creation(self):
        """Test creating CogneeAPIError with all parameters."""
        response_data = {"error": "API error", "code": "ERR001"}
        error = CogneeAPIError("API error occurred", 500, response_data)

        assert error.message == "API error occurred"
        assert error.status_code == 500
        assert error.response == response_data
        assert "[500] API error occurred" in str(error)

    def test_cognee_api_error_without_response(self):
        """Test creating CogneeAPIError without response data."""
        error = CogneeAPIError("API error", 400)

        assert error.message == "API error"
        assert error.status_code == 400
        assert error.response is None
        assert "[400] API error" in str(error)

    def test_cognee_api_error_inheritance(self):
        """Test CogneeAPIError inheritance."""
        error = CogneeAPIError("Test", 500)
        assert isinstance(error, CogneeSDKError)
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError."""
        error = AuthenticationError("Unauthorized", 401)

        assert error.message == "Unauthorized"
        assert error.status_code == 401
        assert isinstance(error, CogneeAPIError)
        assert isinstance(error, CogneeSDKError)

    def test_authentication_error_with_response(self):
        """Test AuthenticationError with response data."""
        response_data = {"error": "Invalid token"}
        error = AuthenticationError("Unauthorized", 401, response_data)

        assert error.response == response_data


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_not_found_error_creation(self):
        """Test creating NotFoundError."""
        error = NotFoundError("Resource not found", 404)

        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert isinstance(error, CogneeAPIError)
        assert isinstance(error, CogneeSDKError)

    def test_not_found_error_with_response(self):
        """Test NotFoundError with response data."""
        response_data = {"error": "Dataset not found"}
        error = NotFoundError("Not found", 404, response_data)

        assert error.response == response_data


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        error = ValidationError("Invalid input", 400)

        assert error.message == "Invalid input"
        assert error.status_code == 400
        assert isinstance(error, CogneeAPIError)
        assert isinstance(error, CogneeSDKError)

    def test_validation_error_with_response(self):
        """Test ValidationError with response data."""
        response_data = {"error": "Validation failed", "fields": ["email"]}
        error = ValidationError("Invalid input", 400, response_data)

        assert error.response == response_data


class TestServerError:
    """Tests for ServerError."""

    def test_server_error_500(self):
        """Test creating ServerError for 500 status."""
        error = ServerError("Internal server error", 500)

        assert error.message == "Internal server error"
        assert error.status_code == 500
        assert isinstance(error, CogneeAPIError)
        assert isinstance(error, CogneeSDKError)

    def test_server_error_502(self):
        """Test creating ServerError for 502 status."""
        error = ServerError("Bad gateway", 502)

        assert error.status_code == 502

    def test_server_error_503(self):
        """Test creating ServerError for 503 status."""
        error = ServerError("Service unavailable", 503)

        assert error.status_code == 503

    def test_server_error_with_response(self):
        """Test ServerError with response data."""
        response_data = {"error": "Database connection failed"}
        error = ServerError("Server error", 500, response_data)

        assert error.response == response_data


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_timeout_error_creation(self):
        """Test creating TimeoutError."""
        error = TimeoutError("Request timeout", attempts=3)

        assert error.attempts == 3
        assert str(error) == "Request timeout"
        assert isinstance(error, CogneeSDKError)
        assert isinstance(error, Exception)

    def test_timeout_error_without_attempts(self):
        """Test creating TimeoutError without attempts."""
        error = TimeoutError("Request timeout")

        assert error.attempts == 0
        assert str(error) == "Request timeout"

    def test_timeout_error_inheritance(self):
        """Test TimeoutError inheritance."""
        error = TimeoutError("Test")
        assert isinstance(error, CogneeSDKError)
        assert isinstance(error, Exception)


class TestExceptionHierarchy:
    """Tests for exception hierarchy and relationships."""

    def test_exception_hierarchy(self):
        """Test that all exceptions follow the correct hierarchy."""
        auth_error = AuthenticationError("Test", 401)
        not_found_error = NotFoundError("Test", 404)
        validation_error = ValidationError("Test", 400)
        server_error = ServerError("Test", 500)
        timeout_error = TimeoutError("Test")

        # All API errors should inherit from CogneeAPIError
        assert isinstance(auth_error, CogneeAPIError)
        assert isinstance(not_found_error, CogneeAPIError)
        assert isinstance(validation_error, CogneeAPIError)
        assert isinstance(server_error, CogneeAPIError)

        # All errors should inherit from CogneeSDKError
        assert isinstance(auth_error, CogneeSDKError)
        assert isinstance(not_found_error, CogneeSDKError)
        assert isinstance(validation_error, CogneeSDKError)
        assert isinstance(server_error, CogneeSDKError)
        assert isinstance(timeout_error, CogneeSDKError)

        # All should be Exception instances
        assert isinstance(auth_error, Exception)
        assert isinstance(not_found_error, Exception)
        assert isinstance(validation_error, Exception)
        assert isinstance(server_error, Exception)
        assert isinstance(timeout_error, Exception)
