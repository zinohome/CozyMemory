"""
Unit tests for core infrastructure methods.

Tests _get_headers(), _handle_error_response(), and _request() methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import (
    AuthenticationError,
    CogneeAPIError,
    CogneeSDKError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000", api_token="test-token")


@pytest.fixture
def client_no_token():
    """Create a test client instance without token."""
    return CogneeClient(api_url="http://localhost:8000")


class TestGetHeaders:
    """Tests for _get_headers() method."""

    def test_get_headers_with_token(self, client):
        """Test headers generation with token."""
        headers = client._get_headers()
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"

    def test_get_headers_without_token(self, client_no_token):
        """Test headers generation without token."""
        headers = client_no_token._get_headers()
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_get_headers_custom_content_type(self, client):
        """Test headers generation with custom content type."""
        headers = client._get_headers(content_type="text/plain")
        assert headers["Content-Type"] == "text/plain"
        assert headers["Authorization"] == "Bearer test-token"


class TestHandleErrorResponse:
    """Tests for _handle_error_response() method."""

    @pytest.mark.asyncio
    async def test_handle_401_error(self, client):
        """Test handling 401 Unauthorized error."""
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {"error": "Unauthorized"}
        response.text = "Unauthorized"

        with pytest.raises(AuthenticationError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 401
        assert "Unauthorized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_403_error(self, client):
        """Test handling 403 Forbidden error."""
        response = MagicMock()
        response.status_code = 403
        response.json.return_value = {"error": "Forbidden"}
        response.text = "Forbidden"

        with pytest.raises(AuthenticationError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_handle_404_error(self, client):
        """Test handling 404 Not Found error."""
        response = MagicMock()
        response.status_code = 404
        response.json.return_value = {"error": "Not found"}
        response.text = "Not found"

        with pytest.raises(NotFoundError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_handle_400_error(self, client):
        """Test handling 400 Bad Request error."""
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {"error": "Bad request"}
        response.text = "Bad request"

        with pytest.raises(ValidationError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_handle_500_error(self, client):
        """Test handling 500 Internal Server Error."""
        response = MagicMock()
        response.status_code = 500
        response.json.return_value = {"error": "Internal server error"}
        response.text = "Internal server error"

        with pytest.raises(ServerError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_handle_502_error(self, client):
        """Test handling 502 Bad Gateway error."""
        response = MagicMock()
        response.status_code = 502
        response.json.return_value = {"error": "Bad gateway"}
        response.text = "Bad gateway"

        with pytest.raises(ServerError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_handle_503_error(self, client):
        """Test handling 503 Service Unavailable error."""
        response = MagicMock()
        response.status_code = 503
        response.json.return_value = {"error": "Service unavailable"}
        response.text = "Service unavailable"

        with pytest.raises(ServerError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_handle_other_error(self, client):
        """Test handling other error status codes."""
        response = MagicMock()
        response.status_code = 418
        response.json.return_value = {"error": "I'm a teapot"}
        response.text = "I'm a teapot"

        with pytest.raises(CogneeAPIError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 418

    @pytest.mark.asyncio
    async def test_handle_error_with_detail_field(self, client):
        """Test handling error with 'detail' field."""
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {"detail": "Validation failed"}
        response.text = "Validation failed"

        with pytest.raises(ValidationError) as exc_info:
            await client._handle_error_response(response)

        assert "Validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_with_message_field(self, client):
        """Test handling error with 'message' field."""
        response = MagicMock()
        response.status_code = 500
        response.json.return_value = {"message": "Server error occurred"}
        response.text = "Server error occurred"

        with pytest.raises(ServerError) as exc_info:
            await client._handle_error_response(response)

        assert "Server error occurred" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_json_parse_failure(self, client):
        """Test handling error when JSON parsing fails."""
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "Internal server error"

        with pytest.raises(ServerError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_error_empty_response(self, client):
        """Test handling error with empty response body."""
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = ""

        with pytest.raises(ServerError) as exc_info:
            await client._handle_error_response(response)

        assert exc_info.value.status_code == 500
        assert "HTTP 500" in str(exc_info.value)


class TestRequest:
    """Tests for _request() method."""

    @pytest.mark.asyncio
    async def test_request_success(self, client):
        """Test successful request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            response = await client._request("GET", "/api/v1/datasets")

            assert response.status_code == 200
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_custom_headers(self, client):
        """Test request with custom headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client._request(
                "GET", "/api/v1/datasets", headers={"X-Custom-Header": "custom-value"}
            )

            call_args = mock_request.call_args
            headers = call_args[1]["headers"]
            assert headers["X-Custom-Header"] == "custom-value"
            # Custom headers should take precedence
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_request_retry_on_timeout(self, client):
        """Test request retry on timeout."""
        client.max_retries = 3
        client.retry_delay = 0.1

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            # First two attempts timeout, third succeeds
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                mock_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client._request("GET", "/api/v1/datasets")

                assert response.status_code == 200
                assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_request_retry_exhausted_timeout(self, client):
        """Test request fails after all retries exhausted for timeout."""
        client.max_retries = 2
        client.retry_delay = 0.1

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Timeout")

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(TimeoutError) as exc_info:
                    await client._request("GET", "/api/v1/datasets")

                assert "timeout" in str(exc_info.value).lower()
                assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_retry_on_request_error(self, client):
        """Test request retry on RequestError."""
        client.max_retries = 3
        client.retry_delay = 0.1

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            # First attempt fails, second succeeds
            mock_request.side_effect = [
                httpx.RequestError("Connection error"),
                mock_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client._request("GET", "/api/v1/datasets")

                assert response.status_code == 200
                assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_retry_exhausted_request_error(self, client):
        """Test request fails after all retries exhausted for RequestError."""
        client.max_retries = 2
        client.retry_delay = 0.1

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.RequestError("Connection error")

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(CogneeSDKError) as exc_info:
                    await client._request("GET", "/api/v1/datasets")

                assert "Request failed" in str(exc_info.value)
                assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_exponential_backoff(self, client):
        """Test exponential backoff in retry mechanism."""
        client.max_retries = 3
        client.retry_delay = 0.1

        mock_response = MagicMock()
        mock_response.status_code = 200

        sleep_times = []

        async def mock_sleep(delay):
            sleep_times.append(delay)

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                mock_response,
            ]

            with patch("asyncio.sleep", side_effect=mock_sleep):
                await client._request("GET", "/api/v1/datasets")

                # Check exponential backoff: delay * (2 ** attempt)
                assert len(sleep_times) == 2
                assert sleep_times[0] == pytest.approx(0.1 * (2**0), rel=0.1)
                assert sleep_times[1] == pytest.approx(0.1 * (2**1), rel=0.1)

    @pytest.mark.asyncio
    async def test_request_error_response_handling(self, client):
        """Test error response handling in _request."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_response.text = "Not found"

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(NotFoundError):
                await client._request("GET", "/api/v1/datasets")

    @pytest.mark.asyncio
    async def test_request_url_construction(self, client):
        """Test URL construction in _request."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client._request("GET", "/api/v1/datasets")

            call_args = mock_request.call_args
            assert call_args[0][1] == "http://localhost:8000/api/v1/datasets"

    @pytest.mark.asyncio
    async def test_request_url_with_trailing_slash(self, client):
        """Test URL construction with trailing slash in api_url."""
        client_with_slash = CogneeClient(api_url="http://localhost:8000/", api_token="test-token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(
            client_with_slash.client, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response
            await client_with_slash._request("GET", "/api/v1/datasets")

            call_args = mock_request.call_args
            # Should handle trailing slash correctly
            url = call_args[0][1]
            assert url == "http://localhost:8000/api/v1/datasets"
