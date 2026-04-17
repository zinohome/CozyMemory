"""
Cognee SDK Client

Main client class for interacting with Cognee API server.
"""

import asyncio
import gzip
import hashlib
import json
import logging
import mimetypes
import time
import warnings
from collections.abc import AsyncIterator
from io import BufferedReader
from pathlib import Path
from typing import Any, BinaryIO, Callable, Literal, Union
from uuid import UUID

import httpx

from cognee_sdk.exceptions import (
    AuthenticationError,
    CogneeAPIError,
    CogneeSDKError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from cognee_sdk.models import (
    AddResult,
    CognifyResult,
    CombinedSearchResult,
    DataItem,
    Dataset,
    DeleteResult,
    GraphData,
    HealthStatus,
    MemifyResult,
    PipelineRunStatus,
    SearchHistoryItem,
    SearchResult,
    SearchType,
    SyncResult,
    SyncStatus,
    UpdateResult,
    User,
)


class CogneeClient:
    """
    Cognee SDK Client.

    A lightweight, type-safe, and fully asynchronous Python client for Cognee API.

    Args:
        api_url: Base URL of the Cognee API server (e.g., "http://localhost:8000")
        api_token: Optional authentication token for Bearer token authentication
        timeout: Request timeout in seconds (default: 300.0)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial retry delay in seconds (default: 1.0)

    Example:
        >>> import asyncio
        >>> from cognee_sdk import CogneeClient
        >>>
        >>> async def main():
        >>>     client = CogneeClient(api_url="http://localhost:8000")
        >>>     try:
        >>>         datasets = await client.list_datasets()
        >>>         print(f"Found {len(datasets)} datasets")
        >>>     finally:
        >>>         await client.close()
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        api_url: str,
        api_token: str | None = None,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_logging: bool = False,
        request_interceptor: Callable[[str, str, dict[str, Any]], None] | None = None,
        response_interceptor: Callable[[httpx.Response], None] | None = None,
        max_keepalive_connections: int = 50,
        max_connections: int = 100,
        enable_compression: bool = True,
        enable_http2: bool = True,
        enable_cache: bool = True,
        cache_ttl: int = 300,
    ) -> None:
        """
        Initialize Cognee client.

        Args:
            api_url: Base URL of the Cognee API server
            api_token: Optional authentication token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay in seconds
            enable_logging: Enable request/response logging (default: False)
            request_interceptor: Optional callback function called before each request.
                               Receives (method, url, headers) as arguments
            response_interceptor: Optional callback function called after each response.
                                Receives httpx.Response as argument
            max_keepalive_connections: Maximum number of keepalive connections (default: 50)
            max_connections: Maximum number of total connections (default: 100)
            enable_compression: Enable request/response compression (default: True)
            enable_http2: Enable HTTP/2 support (default: True)
            enable_cache: Enable local caching for read operations (default: True)
            cache_ttl: Cache time-to-live in seconds (default: 300)
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_logging = enable_logging
        self.request_interceptor = request_interceptor
        self.response_interceptor = response_interceptor
        self.enable_compression = enable_compression
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.max_keepalive_connections = max_keepalive_connections
        self.max_connections = max_connections
        self.enable_http2 = enable_http2

        # Initialize cache
        if enable_cache:
            self._cache: dict[str, tuple[Any, float]] = {}
        else:
            self._cache = {}

        # Setup logger if logging is enabled
        if enable_logging:
            self.logger = logging.getLogger("cognee_sdk")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.DEBUG)
        else:
            self.logger = None

        # Check if HTTP/2 is available
        http2_enabled = enable_http2
        if enable_http2:
            try:
                import h2  # noqa: F401
            except ImportError:
                http2_enabled = False
                if self.logger:
                    self.logger.warning(
                        "HTTP/2 requested but 'h2' package not installed. "
                        "Install with: pip install httpx[http2]. Falling back to HTTP/1.1."
                    )

        # Create HTTP client with optimized connection pool and HTTP/2
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections,
                max_connections=max_connections,
            ),
            follow_redirects=True,
            http2=http2_enabled,
        )

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """
        Get request headers with authentication and compression support.

        Args:
            content_type: Content-Type header value

        Returns:
            Dictionary of headers
        """
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        # Add compression headers if enabled
        if self.enable_compression:
            headers["Accept-Encoding"] = "gzip, deflate, br"
        
        return headers
    
    def _get_cache_key(self, method: str, endpoint: str, **kwargs: Any) -> str:
        """
        Generate cache key for a request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Request parameters
            
        Returns:
            Cache key string (empty string if not cacheable)
        """
        # Cache GET requests and POST requests with json payload (like search)
        # For POST with json, we include the json in the cache key
        if method.upper() not in ("GET", "POST"):
            return ""
        
        # Create a hash of the request parameters
        cache_data = {
            "method": method,
            "endpoint": endpoint,
            "params": kwargs.get("params", {}),
            "headers": {k: v for k, v in kwargs.get("headers", {}).items() 
                       if k.lower() not in ["authorization", "user-agent"]},
        }
        # Also include json payload for POST requests that should be cached (like search)
        if "json" in kwargs:
            cache_data["json"] = kwargs["json"]
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Any | None:
        """
        Get value from cache if valid.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enable_cache or not cache_key:
            return None
        
        if cache_key in self._cache:
            value, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return value
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        
        return None
    
    def _set_cache(self, cache_key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            cache_key: Cache key
            value: Value to cache
        """
        if self.enable_cache and cache_key:
            self._cache[cache_key] = (value, time.time())
    
    def _compress_data(self, data: bytes) -> tuple[bytes, bool]:
        """
        Compress data if it's large enough to benefit from compression.
        
        Args:
            data: Data to compress
            
        Returns:
            Tuple of (compressed_data, was_compressed)
        """
        if not self.enable_compression or len(data) < 1024:  # Don't compress small data
            return data, False
        
        try:
            compressed = gzip.compress(data, compresslevel=6)  # Balance between speed and size
            # Only use compressed version if it's actually smaller
            if len(compressed) < len(data) * 0.9:  # At least 10% reduction
                return compressed, True
        except Exception:
            # If compression fails, return original
            if self.logger:
                self.logger.warning("Failed to compress data, using uncompressed")
        
        return data, False
    
    def _decompress_response(self, response: httpx.Response) -> httpx.Response:
        """
        Decompress response if needed.
        
        Args:
            response: HTTP response
            
        Returns:
            Response (possibly modified)
        """
        if not self.enable_compression:
            return response
        
        content_encoding = response.headers.get("Content-Encoding", "").lower()
        if content_encoding == "gzip" and response.content:
            try:
                decompressed = gzip.decompress(response.content)
                # Create a new response with decompressed content
                response._content = decompressed
            except Exception:
                if self.logger:
                    self.logger.warning("Failed to decompress response")
        
        return response

    def _parse_json_response(self, response: httpx.Response) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Parse JSON response with error handling.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            CogneeAPIError: If JSON parsing fails
        """
        try:
            return response.json()
        except json.JSONDecodeError as e:
            # Provide more detailed error information
            error_preview = response.text[:200] if response.text else "(empty response)"
            raise CogneeAPIError(
                f"Invalid JSON response: {str(e)}. Response preview: {error_preview}",
                response.status_code,
                None,
            ) from e

    async def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Handle error responses and raise appropriate exceptions.

        Args:
            response: HTTP response object

        Raises:
            AuthenticationError: For 401 status codes
            NotFoundError: For 404 status codes
            ValidationError: For 400 status codes
            ServerError: For 5xx status codes
            CogneeAPIError: For other error status codes
        """
        error_data: dict | None = None
        try:
            error_data = response.json()
            error_message = (
                error_data.get("error")
                or error_data.get("detail")
                or error_data.get("message")
                or str(error_data)  # Show full error data if available
                or response.text
            )
        except Exception:
            error_message = response.text or f"HTTP {response.status_code}"

        # Add request information to error message for better debugging
        request_info = f"Request: {response.request.method} {response.request.url}"
        if error_message and request_info:
            error_message = f"{error_message} ({request_info})"

        status_code = response.status_code

        if status_code == 401 or status_code == 403:
            raise AuthenticationError(error_message, status_code, error_data)
        elif status_code == 404:
            raise NotFoundError(error_message, status_code, error_data)
        elif status_code == 400:
            raise ValidationError(error_message, status_code, error_data)
        elif status_code >= 500:
            raise ServerError(error_message, status_code, error_data)
        else:
            raise CogneeAPIError(error_message, status_code, error_data)

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Send HTTP request with intelligent retry mechanism.

        Implements smart retry logic:
        - 4xx errors (except 429): No retry, immediately raise
        - 429 errors (rate limit): Retry with exponential backoff
        - 5xx errors: Retry with exponential backoff
        - Network errors: Retry with exponential backoff

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/api/v1/datasets")
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            HTTP response object

        Raises:
            TimeoutError: If request times out after all retries
            CogneeSDKError: If request fails after all retries
        """
        url = f"{self.api_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        
        # Cache is handled in individual methods (list_datasets, search, etc.)
        # to properly handle response parsing
        cache_key = ""  # Initialize cache_key for potential use in response caching
        
        # For multipart/form-data requests, don't set Content-Type header
        # Let httpx set it automatically with boundary
        if "files" in kwargs:
            # Only set Authorization header for multipart requests
            base_headers = {}
            if self.api_token:
                base_headers["Authorization"] = f"Bearer {self.api_token}"
            # Don't compress multipart data
        else:
            base_headers = self._get_headers()
            
            # Compress JSON data if enabled
            if self.enable_compression and "json" in kwargs:
                json_data = kwargs["json"]
                json_bytes = json.dumps(json_data).encode("utf-8")
                compressed_data, was_compressed = self._compress_data(json_bytes)
                if was_compressed:
                    kwargs["content"] = compressed_data
                    kwargs.pop("json")
                    base_headers["Content-Encoding"] = "gzip"
                    base_headers["Content-Type"] = "application/json"

        # Merge headers, custom headers take precedence
        merged_headers = {**base_headers, **headers}

        # Call request interceptor if provided
        if self.request_interceptor:
            try:
                self.request_interceptor(method, url, merged_headers)
            except Exception as e:
                # Don't fail the request if interceptor fails
                if self.logger:
                    self.logger.warning(f"Request interceptor failed: {e}")

        # Log request if logging is enabled
        if self.logger:
            self.logger.debug(f"Request: {method} {url}")

        # Status codes that should not be retried (client errors)
        NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 422}

        last_exception: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(
                    method,
                    url,
                    headers=merged_headers,
                    **kwargs,
                )

                # Log response if logging is enabled
                if self.logger:
                    self.logger.debug(
                        f"Response: {method} {url} - {response.status_code} "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )

                # Call response interceptor if provided
                if self.response_interceptor:
                    try:
                        self.response_interceptor(response)
                    except Exception as e:
                        # Don't fail the request if interceptor fails
                        if self.logger:
                            self.logger.warning(f"Response interceptor failed: {e}")

                # Handle error responses with smart retry logic
                if response.status_code >= 400:
                    status_code = response.status_code
                    
                    # Client errors (4xx) - don't retry except for 429 (rate limit)
                    if 400 <= status_code < 500:
                        if status_code == 429:
                            # Rate limit - retry with exponential backoff
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay * (2**attempt))
                                continue
                            else:
                                await self._handle_error_response(response)
                        elif status_code in NON_RETRYABLE_STATUS_CODES:
                            # Non-retryable client errors - immediately raise
                            await self._handle_error_response(response)
                        else:
                            # Other 4xx errors - don't retry
                            await self._handle_error_response(response)
                    
                    # Server errors (5xx) - retry with exponential backoff
                    elif status_code >= 500:
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (2**attempt))
                            continue
                        else:
                            await self._handle_error_response(response)
                    
                    # Should not reach here, but handle just in case
                    await self._handle_error_response(response)

                # Decompress response if needed
                response = self._decompress_response(response)
                
                # Cache successful GET responses
                if cache_key and response.status_code == 200:
                    try:
                        # Try to get JSON response for caching
                        content_type = response.headers.get("Content-Type", "").lower()
                        if "application/json" in content_type:
                            # Clone response content before caching (response.json() consumes the stream)
                            response_content = response.content
                            if response_content:
                                cached_data = json.loads(response_content)
                                self._set_cache(cache_key, cached_data)
                    except Exception:
                        # If we can't parse JSON, don't cache
                        pass

                return response

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))  # Exponential backoff
                else:
                    raise TimeoutError(f"Request timeout after {self.max_retries} attempts") from e

            except httpx.HTTPStatusError as e:
                # HTTP status error - check if should retry
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                raise

            except httpx.RequestError as e:
                # Network errors - retry with exponential backoff
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                else:
                    raise CogneeSDKError(f"Request failed: {str(e)}") from e

        if last_exception:
            raise last_exception
        raise CogneeSDKError("Request failed for unknown reason")

    async def health_check(self) -> HealthStatus:
        """
        Check API server health.

        Returns:
            Health status information

        Raises:
            CogneeAPIError: If health check fails
        """
        response = await self._request("GET", "/health")
        data = self._parse_json_response(response)
        if isinstance(data, dict):
            return HealthStatus(**data)
        raise CogneeAPIError("Invalid health check response format", response.status_code, data)

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        await self.client.aclose()

    async def __aenter__(self) -> "CogneeClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # ==================== Helper Methods ====================

    def _get_file_name_for_upload(
        self,
        data: str | bytes | Path | BinaryIO,
    ) -> str:
        """
        Determine file name for multipart upload based on data type.

        Args:
            data: Data item (string, bytes, Path, or BinaryIO)

        Returns:
            File name string for multipart upload
        """
        if isinstance(data, Path):
            return data.name
        elif isinstance(data, str) and data.startswith(("/", "file://")):
            file_path = Path(data.replace("file://", ""))
            return file_path.name if file_path.exists() else "data.txt"
        elif hasattr(data, "name"):
            return getattr(data, "name", "data.bin")
        elif isinstance(data, bytes):
            return "data.bin"
        else:
            return "data.txt"

    def _prepare_file_for_upload(
        self,
        data: str | bytes | Path | BinaryIO,
        use_streaming: bool = True,
    ) -> tuple[str, Union[bytes, BinaryIO], str]:
        """
        Prepare a single file for upload.

        Handles different input types: strings, bytes, file paths, and file objects.
        For large files, uses streaming upload to avoid loading entire file into memory.

        Args:
            data: Data to prepare. Can be:
                - Text string
                - Bytes data
                - File path (Path object or string starting with "/", "file://", or "s3://")
                - File object (BinaryIO)
            use_streaming: If True, use streaming for large files (default: True)

        Returns:
            Tuple of (field_name, content_or_file_obj, mime_type) for multipart/form-data upload.
            For small files or when use_streaming=False, content is bytes.
            For large files when use_streaming=True, content is a file object for streaming.

        Raises:
            CogneeSDKError: If file cannot be read or processed
        """
        # Maximum recommended file size (50MB) - files larger than this will use streaming
        MAX_RECOMMENDED_FILE_SIZE = 50 * 1024 * 1024
        # Threshold for streaming upload (1MB) - files larger than this will stream (optimized from 10MB)
        STREAMING_THRESHOLD = 1 * 1024 * 1024

        if isinstance(data, str):
            # Check if it's a file path
            if data.startswith(("/", "file://", "s3://")):
                file_path = Path(data.replace("file://", ""))
                if file_path.exists() and file_path.is_file():
                    # Check file size
                    file_size = file_path.stat().st_size
                    if file_size > MAX_RECOMMENDED_FILE_SIZE:
                        warnings.warn(
                            f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
                            f"recommended limit ({MAX_RECOMMENDED_FILE_SIZE / 1024 / 1024}MB). "
                            "Large files may cause memory issues.",
                            UserWarning,
                            stacklevel=2
                        )
                    
                    mime_type, _ = mimetypes.guess_type(str(file_path))
                    
                    # Use streaming for large files
                    if use_streaming and file_size > STREAMING_THRESHOLD:
                        try:
                            # Return file object for streaming upload
                            file_obj = open(file_path, "rb")
                            return (
                                "data",
                                file_obj,  # File object for streaming
                                mime_type or "application/octet-stream",
                            )
                        except OSError as e:
                            raise CogneeSDKError(
                                f"Failed to open file {file_path} for streaming: {str(e)}"
                            ) from e
                    else:
                        # Read entire file for small files
                        try:
                            with open(file_path, "rb") as f:
                                file_content = f.read()
                            return (
                                "data",
                                file_content,
                                mime_type or "application/octet-stream",
                            )
                        except OSError as e:
                            raise CogneeSDKError(
                                f"Failed to read file {file_path}: {str(e)}"
                            ) from e
                else:
                    # Treat as text string if file doesn't exist
                    return ("data", data.encode("utf-8"), "text/plain")
            else:
                # Plain text string
                return ("data", data.encode("utf-8"), "text/plain")
        
        elif isinstance(data, bytes):
            # Bytes data - always return as-is (already in memory)
            return ("data", data, "application/octet-stream")
        
        elif isinstance(data, Path):
            # Check file size
            file_size = 0
            if data.exists() and data.is_file():
                file_size = data.stat().st_size
                if file_size > MAX_RECOMMENDED_FILE_SIZE:
                    warnings.warn(
                        f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
                        f"recommended limit ({MAX_RECOMMENDED_FILE_SIZE / 1024 / 1024}MB). "
                        "Large files may cause memory issues.",
                        UserWarning,
                        stacklevel=2
                    )
            
            mime_type, _ = mimetypes.guess_type(str(data))
            
            # Use streaming for large files
            if use_streaming and file_size > STREAMING_THRESHOLD:
                try:
                    # Return file object for streaming upload
                    file_obj = open(data, "rb")
                    return (
                        "data",
                        file_obj,  # File object for streaming
                        mime_type or "application/octet-stream",
                    )
                except OSError as e:
                    raise CogneeSDKError(f"Failed to open file {data} for streaming: {str(e)}") from e
            else:
                # Read entire file for small files
                try:
                    with open(data, "rb") as f:
                        file_content = f.read()
                    return (
                        "data",
                        file_content,
                        mime_type or "application/octet-stream",
                    )
                except OSError as e:
                    raise CogneeSDKError(f"Failed to read file {data}: {str(e)}") from e
        
        elif hasattr(data, "read"):
            # File-like object (BinaryIO)
            file_name = getattr(data, "name", "data.bin")
            
            # For file objects, check if we can determine size
            file_size = 0
            if hasattr(data, "seek") and hasattr(data, "tell"):
                try:
                    current_pos = data.tell()
                    data.seek(0, 2)  # Seek to end
                    file_size = data.tell()
                    data.seek(current_pos)  # Restore position
                except (OSError, AttributeError):
                    pass
            
            # Save original position if supported
            original_position = None
            if hasattr(data, "tell"):
                try:
                    original_position = data.tell()
                except (OSError, AttributeError):
                    pass
            
            # Use streaming for large file objects if size is known and exceeds threshold
            if use_streaming and file_size > STREAMING_THRESHOLD and hasattr(data, "seek"):
                # Reset position to start for streaming
                try:
                    data.seek(0)
                except (OSError, AttributeError):
                    pass
                
                mime_type, _ = mimetypes.guess_type(file_name)
                # Return file object as-is for streaming (httpx will handle it)
                return (
                    "data",
                    data,  # File object for streaming
                    mime_type or "application/octet-stream",
                )
            else:
                # Read entire content for small files or when streaming is disabled
                try:
                    content = data.read() if hasattr(data, "read") else data
                    
                    # Restore position if supported and was saved
                    if original_position is not None and hasattr(data, "seek"):
                        try:
                            data.seek(original_position)
                        except (OSError, AttributeError):
                            pass  # Ignore if seek fails
                    
                    mime_type, _ = mimetypes.guess_type(file_name)
                    return (
                        "data",
                        content,
                        mime_type or "application/octet-stream",
                    )
                except Exception as e:
                    raise CogneeSDKError(
                        f"Failed to read file object {file_name}: {str(e)}"
                    ) from e
        
        else:
            # Fallback: convert to string
            return ("data", str(data).encode("utf-8"), "text/plain")

    # ==================== Core API Methods (P0) ====================

    async def add(
        self,
        data: str | bytes | Path | BinaryIO | list[str | bytes | Path | BinaryIO],
        dataset_name: str | None = None,
        dataset_id: UUID | None = None,
        node_set: list[str] | None = None,
    ) -> AddResult:
        """
        Add data to Cognee for processing.

        Supports multiple input types: strings, bytes, file paths, file objects, or lists of these.

        Args:
            data: Data to add. Can be:
                - Single text string
                - Bytes data
                - File path (Path object or string)
                - File object (BinaryIO)
                - List of any of the above
            dataset_name: Name of the dataset to add data to
            dataset_id: UUID of an existing dataset (alternative to dataset_name)
            node_set: Optional list of node identifiers for graph organization

        Returns:
            AddResult with operation status and created data ID

        Raises:
            ValidationError: If neither dataset_name nor dataset_id is provided
            AuthenticationError: If authentication fails
            ServerError: If server error occurs

        Example:
            >>> # Add text data
            >>> result = await client.add(
            ...     data="Cognee turns documents into AI memory.",
            ...     dataset_name="my-dataset"
            ... )
            >>>
            >>> # Add file
            >>> result = await client.add(
            ...     data=Path("document.pdf"),
            ...     dataset_name="my-dataset"
            ... )
        """
        if not dataset_name and not dataset_id:
            raise ValidationError(
                "Either dataset_name or dataset_id must be provided",
                400,
            )

        # Handle single item or list
        if not isinstance(data, list):
            data_list = [data]
        else:
            data_list = data

        # Prepare form data
        form_data: dict[str, Any] = {}
        if dataset_name:
            form_data["datasetName"] = dataset_name
        if dataset_id:
            form_data["datasetId"] = str(dataset_id)
        if node_set:
            form_data["node_set"] = json.dumps(node_set)

        # Prepare files for multipart/form-data using unified method
        files: list[tuple] = []
        opened_files: list[BufferedReader] = []  # Track opened files for cleanup
        
        try:
            for item in data_list:
                field_name, content_or_file, mime_type = self._prepare_file_for_upload(item)
                # Determine file name for multipart upload
                file_name = self._get_file_name_for_upload(item)
                
                # Check if content is a file object (for streaming) or bytes
                if isinstance(content_or_file, (BufferedReader, BinaryIO)) and hasattr(content_or_file, "read"):
                    # File object for streaming - httpx will handle it
                    files.append((field_name, (file_name, content_or_file, mime_type)))
                    # Track opened files (only for files we opened, not user-provided file objects)
                    if isinstance(content_or_file, BufferedReader):
                        opened_files.append(content_or_file)
                else:
                    # Bytes content - normal upload
                    files.append((field_name, (file_name, content_or_file, mime_type)))
            
            # Send request (don't set Content-Type for multipart/form-data)
            response = await self._request(
                "POST",
                "/api/v1/add",
                files=files,
                data=form_data,
                headers={},  # Let httpx set Content-Type for multipart
            )
            
            result_data = response.json()
            return AddResult(**result_data)
        finally:
            # Close any files we opened for streaming
            for file_obj in opened_files:
                try:
                    file_obj.close()
                except Exception:
                    pass  # Ignore errors when closing

    async def delete(
        self,
        data_id: UUID,
        dataset_id: UUID,
        mode: str = "soft",
    ) -> DeleteResult:
        """
        Delete data from a dataset.

        Args:
            data_id: UUID of the data to delete
            dataset_id: UUID of the dataset containing the data
            mode: Deletion mode - "soft" (default) or "hard"

        Returns:
            DeleteResult with operation status

        Raises:
            NotFoundError: If data or dataset not found
            ValidationError: If invalid parameters provided
        """
        params = {
            "data_id": str(data_id),
            "dataset_id": str(dataset_id),
            "mode": mode,
        }

        response = await self._request("DELETE", "/api/v1/delete", params=params)
        result_data = response.json()
        return DeleteResult(**result_data)

    async def cognify(
        self,
        datasets: list[str] | None = None,
        dataset_ids: list[UUID] | None = None,
        run_in_background: bool = False,
        custom_prompt: str | None = None,
    ) -> dict[str, CognifyResult]:
        """
        Transform datasets into structured knowledge graphs.

        Args:
            datasets: List of dataset names to process
            dataset_ids: List of dataset UUIDs to process
            run_in_background: Whether to run processing in background
            custom_prompt: Custom prompt for entity extraction

        Returns:
            Dictionary mapping dataset IDs to CognifyResult objects

        Raises:
            ValidationError: If neither datasets nor dataset_ids provided
            ServerError: If processing fails

        Example:
            >>> result = await client.cognify(
            ...     datasets=["my-dataset"],
            ...     run_in_background=False
            ... )
        """
        if (not datasets) and (not dataset_ids):
            raise ValidationError(
                "Either datasets or dataset_ids must be provided",
                400,
            )

        payload: dict[str, Any] = {
            "run_in_background": run_in_background,
        }
        if datasets:
            payload["datasets"] = datasets
        if dataset_ids:
            payload["dataset_ids"] = [str(did) for did in dataset_ids]
        if custom_prompt:
            payload["custom_prompt"] = custom_prompt

        response = await self._request("POST", "/api/v1/cognify", json=payload)

        result_data = response.json()
        # Handle dictionary of results (one per dataset)
        if isinstance(result_data, dict):
            # Check if it's already a dict with dataset keys or a single result
            if "pipeline_run_id" in result_data or "status" in result_data:
                # Single result, wrap in "default" key
                return {"default": CognifyResult(**result_data)}
            else:
                # Dictionary of results (one per dataset)
                return {
                    key: CognifyResult(**value) if isinstance(value, dict) else value
                    for key, value in result_data.items()
                }
        return {"default": CognifyResult(**result_data)}

    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.GRAPH_COMPLETION,
        datasets: list[str] | None = None,
        dataset_ids: list[UUID] | None = None,
        system_prompt: str | None = None,
        node_name: list[str] | None = None,
        top_k: int = 10,
        only_context: bool = False,
        use_combined_context: bool = False,
        return_type: Literal["parsed", "raw"] = "parsed",
    ) -> Union[list[SearchResult], CombinedSearchResult, list[dict[str, Any]]]:
        """
        Search the knowledge graph.

        Args:
            query: Search query string
            search_type: Type of search to perform
            datasets: List of dataset names to search within
            dataset_ids: List of dataset UUIDs to search within
            system_prompt: System prompt for completion searches
            node_name: Filter results to specific node names
            top_k: Maximum number of results to return
            only_context: Return only context without LLM completion
            use_combined_context: Use combined context for search
            return_type: Type of return value - "parsed" (default) returns typed objects,
                        "raw" returns raw dictionaries

        Returns:
            Search results - type depends on return_type and search_type:
            - If return_type="parsed": List[SearchResult] or CombinedSearchResult
            - If return_type="raw": List[dict[str, Any]]

        Raises:
            ValidationError: If query is empty
            ServerError: If search fails

        Example:
            >>> results = await client.search(
            ...     query="What is Cognee?",
            ...     search_type=SearchType.GRAPH_COMPLETION,
            ...     datasets=["my-dataset"]
            ... )
        """
        if not query:
            raise ValidationError("Query cannot be empty", 400)

        payload: dict[str, Any] = {
            "query": query,
            "search_type": search_type.value,
            "top_k": top_k,
            "only_context": only_context,
            "use_combined_context": use_combined_context,
        }
        if datasets:
            payload["datasets"] = datasets
        if dataset_ids:
            payload["dataset_ids"] = [str(did) for did in dataset_ids]
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if node_name:
            payload["node_name"] = node_name

        # Check cache for search queries
        cache_key = self._get_cache_key("POST", "/api/v1/search", json=payload) if self.enable_cache else ""
        if cache_key:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                result_data = cached_data
            else:
                response = await self._request("POST", "/api/v1/search", json=payload)
                result_data = self._parse_json_response(response)
                # Cache the result
                if cache_key:
                    self._set_cache(cache_key, result_data)
        else:
            response = await self._request("POST", "/api/v1/search", json=payload)
            result_data = self._parse_json_response(response)

        # Handle raw return type
        if return_type == "raw":
            if isinstance(result_data, list):
                return result_data
            elif isinstance(result_data, dict):
                return [result_data]
            else:
                return [result_data] if result_data else []

        # Handle parsed return type (default)
        if isinstance(result_data, dict) and "result" in result_data:
            result: CombinedSearchResult = CombinedSearchResult(**result_data)
            return result
        elif isinstance(result_data, list):
            # Try to parse as SearchResult objects
            try:
                parsed_results: list[SearchResult] = [
                    SearchResult(**item) if isinstance(item, dict) else item for item in result_data
                ]
                return parsed_results
            except Exception:
                # Return raw data if parsing fails (fallback)
                raw_results: list[dict[str, Any]] = result_data
                return raw_results
        else:
            # Fallback to raw dict list
            fallback_results: list[dict[str, Any]] = [result_data] if isinstance(result_data, dict) else result_data
            return fallback_results

    async def list_datasets(self) -> list[Dataset]:
        """
        Get all datasets accessible to the authenticated user.

        Returns:
            List of Dataset objects

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If request fails
        """
        # Check cache
        cache_key = self._get_cache_key("GET", "/api/v1/datasets") if self.enable_cache else ""
        if cache_key:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                result_data = cached_data
            else:
                response = await self._request("GET", "/api/v1/datasets")
                result_data = self._parse_json_response(response)
                # Cache the result
                if cache_key:
                    self._set_cache(cache_key, result_data)
        else:
            response = await self._request("GET", "/api/v1/datasets")
            result_data = self._parse_json_response(response)
        return [Dataset(**item) for item in result_data]

    async def create_dataset(self, name: str) -> Dataset:
        """
        Create a new dataset or return existing dataset with the same name.

        Args:
            name: Name of the dataset to create

        Returns:
            Dataset object (created or existing)

        Raises:
            ValidationError: If name is empty
            ServerError: If creation fails

        Example:
            >>> dataset = await client.create_dataset("my-dataset")
            >>> print(f"Dataset ID: {dataset.id}")
        """
        if not name:
            raise ValidationError("Dataset name cannot be empty", 400)

        payload = {"name": name}
        response = await self._request("POST", "/api/v1/datasets", json=payload)
        result_data = response.json()
        return Dataset(**result_data)

    # ==================== Dataset Management API (P1) ====================

    async def update(
        self,
        data_id: UUID,
        dataset_id: UUID,
        data: str | bytes | Path | BinaryIO,
        node_set: list[str] | None = None,
    ) -> UpdateResult:
        """
        Update existing data in a dataset.

        Args:
            data_id: UUID of the data to update
            dataset_id: UUID of the dataset containing the data
            data: New data content (string, bytes, file path, or file object)
            node_set: Optional list of node identifiers

        Returns:
            UpdateResult with operation status

        Raises:
            NotFoundError: If data or dataset not found
            ValidationError: If invalid parameters provided
        """
        # Prepare file for upload using unified method
        field_name, content_or_file, mime_type = self._prepare_file_for_upload(data)
        # Determine file name for multipart upload
        file_name = self._get_file_name_for_upload(data)
        
        # Check if content is a file object (for streaming) or bytes
        opened_file: BufferedReader | None = None
        try:
            if isinstance(content_or_file, (BufferedReader, BinaryIO)) and hasattr(content_or_file, "read"):
                # File object for streaming - httpx will handle it
                files: list[tuple] = [(field_name, (file_name, content_or_file, mime_type))]
                # Track opened file (only for files we opened, not user-provided file objects)
                if isinstance(content_or_file, BufferedReader):
                    opened_file = content_or_file
            else:
                # Bytes content - normal upload
                files = [(field_name, (file_name, content_or_file, mime_type))]

            form_data: dict[str, Any] = {}
            if node_set:
                form_data["node_set"] = json.dumps(node_set)

            params = {
                "data_id": str(data_id),
                "dataset_id": str(dataset_id),
            }

            response = await self._request(
                "PATCH",
                "/api/v1/update",
                files=files,
                data=form_data,
                params=params,
                headers={},
            )

            result_data = response.json()
            # Handle dictionary of results (one per dataset)
            if isinstance(result_data, dict):
                return UpdateResult(**result_data)
            return UpdateResult(status="success", message="Update completed", data_id=None)
        finally:
            # Close file if we opened it for streaming
            if opened_file is not None:
                try:
                    opened_file.close()
                except Exception:
                    pass  # Ignore errors when closing

    async def delete_dataset(self, dataset_id: UUID) -> None:
        """
        Delete a dataset by its ID.

        Args:
            dataset_id: UUID of the dataset to delete

        Raises:
            NotFoundError: If dataset not found
            AuthenticationError: If user doesn't have permission
        """
        await self._request("DELETE", f"/api/v1/datasets/{dataset_id}")

    async def get_dataset_data(self, dataset_id: UUID) -> list[DataItem]:
        """
        Get all data items in a dataset.

        Args:
            dataset_id: UUID of the dataset

        Returns:
            List of DataItem objects

        Raises:
            NotFoundError: If dataset not found
        """
        from cognee_sdk.models import DataItem

        response = await self._request("GET", f"/api/v1/datasets/{dataset_id}/data")
        result_data = response.json()
        return [DataItem(**item) for item in result_data]

    async def get_dataset_graph(self, dataset_id: UUID) -> GraphData:
        """
        Get the knowledge graph data for a dataset.

        Args:
            dataset_id: UUID of the dataset

        Returns:
            GraphData with nodes and edges

        Raises:
            NotFoundError: If dataset not found
        """
        response = await self._request("GET", f"/api/v1/datasets/{dataset_id}/graph")
        result_data = response.json()
        return GraphData(**result_data)

    async def get_dataset_status(self, dataset_ids: list[UUID]) -> dict[UUID, PipelineRunStatus]:
        """
        Get the processing status of datasets.

        Args:
            dataset_ids: List of dataset UUIDs to check

        Returns:
            Dictionary mapping dataset IDs to their processing status

        Raises:
            ValidationError: If dataset_ids is empty
        """
        if not dataset_ids:
            raise ValidationError("dataset_ids cannot be empty", 400)

        params = {"dataset": [str(did) for did in dataset_ids]}
        response = await self._request("GET", "/api/v1/datasets/status", params=params)
        result_data = response.json()

        # Convert string keys to UUID and status strings to enum
        return {
            UUID(key): PipelineRunStatus(value) if isinstance(value, str) else value
            for key, value in result_data.items()
        }

    async def download_raw_data(self, dataset_id: UUID, data_id: UUID) -> bytes:
        """
        Download the raw data file for a specific data item.

        Args:
            dataset_id: UUID of the dataset
            data_id: UUID of the data item

        Returns:
            Raw data as bytes

        Raises:
            NotFoundError: If data or dataset not found
        """
        response = await self._request("GET", f"/api/v1/datasets/{dataset_id}/data/{data_id}/raw")
        return response.content

    # ==================== Authentication API (P1) ====================

    async def login(self, email: str, password: str) -> str:
        """
        Login and get authentication token.

        Args:
            email: User email address
            password: User password

        Returns:
            Authentication token

        Raises:
            AuthenticationError: If credentials are invalid
            ValidationError: If email or password is empty
        """
        if not email or not password:
            raise ValidationError("Email and password are required", 400)

        payload = {"username": email, "password": password}
        response = await self._request("POST", "/api/v1/auth/login", json=payload)

        # Extract token from response (format may vary)
        result_data = response.json()
        token: str | None = result_data.get("access_token") or result_data.get("token")
        if token:
            self.api_token = token
            return str(token)  # Ensure return type is str
        raise AuthenticationError("Token not found in response", response.status_code)

    async def register(self, email: str, password: str) -> "User":
        """
        Register a new user.

        Args:
            email: User email address
            password: User password

        Returns:
            User object

        Raises:
            ValidationError: If email or password is invalid
            ServerError: If registration fails
        """
        if not email or not password:
            raise ValidationError("Email and password are required", 400)

        payload = {"email": email, "password": password}
        response = await self._request("POST", "/api/v1/auth/register", json=payload)
        result_data = response.json()
        return User(**result_data)

    async def get_current_user(self) -> User:
        """
        Get current authenticated user information.

        Returns:
            User object

        Raises:
            AuthenticationError: If not authenticated
        """
        response = await self._request("GET", "/api/v1/auth/me")
        result_data = response.json()
        return User(**result_data)

    # ==================== Memify API (P1) ====================

    async def memify(
        self,
        dataset_name: str | None = None,
        dataset_id: UUID | None = None,
        extraction_tasks: list[str] | None = None,
        enrichment_tasks: list[str] | None = None,
        data: str | None = None,
        node_name: list[str] | None = None,
        run_in_background: bool = False,
    ) -> MemifyResult:
        """
        Enrich knowledge graph with memory algorithms.

        Args:
            dataset_name: Name of the dataset to memify
            dataset_id: UUID of the dataset to memify
            extraction_tasks: List of extraction tasks to execute
            enrichment_tasks: List of enrichment tasks to execute
            data: Custom data to process (optional)
            node_name: Filter graph to specific named entities
            run_in_background: Whether to run in background

        Returns:
            MemifyResult with operation status

        Raises:
            ValidationError: If neither dataset_name nor dataset_id provided
        """
        if not dataset_name and not dataset_id:
            raise ValidationError(
                "Either dataset_name or dataset_id must be provided",
                400,
            )

        payload: dict[str, Any] = {
            "run_in_background": run_in_background,
        }
        if dataset_name:
            payload["dataset_name"] = dataset_name
        if dataset_id:
            payload["dataset_id"] = str(dataset_id)
        if extraction_tasks:
            payload["extraction_tasks"] = extraction_tasks
        if enrichment_tasks:
            payload["enrichment_tasks"] = enrichment_tasks
        if data:
            payload["data"] = data
        if node_name:
            payload["node_name"] = node_name

        response = await self._request("POST", "/api/v1/memify", json=payload)
        result_data = response.json()
        return MemifyResult(**result_data)

    async def get_search_history(self) -> list[SearchHistoryItem]:
        """
        Get search history for the authenticated user.

        Returns:
            List of SearchHistoryItem objects

        Raises:
            AuthenticationError: If not authenticated
        """
        response = await self._request("GET", "/api/v1/search")
        result_data = response.json()
        return [SearchHistoryItem(**item) for item in result_data]

    # ==================== Visualization API (P2) ====================

    async def visualize(self, dataset_id: UUID) -> str:
        """
        Generate HTML visualization of the dataset's knowledge graph.

        Args:
            dataset_id: UUID of the dataset to visualize

        Returns:
            HTML content as string

        Raises:
            NotFoundError: If dataset not found
        """
        response = await self._request(
            "GET", "/api/v1/visualize", params={"dataset_id": str(dataset_id)}
        )
        return response.text

    # ==================== Sync API (P2) ====================

    async def sync_to_cloud(self, dataset_ids: list[UUID] | None = None) -> SyncResult:
        """
        Sync local data to Cognee Cloud.

        Args:
            dataset_ids: List of dataset UUIDs to sync (None = all datasets)

        Returns:
            SyncResult with operation status

        Raises:
            ServerError: If sync fails
        """
        payload: dict[str, Any] = {}
        if dataset_ids:
            payload["dataset_ids"] = [str(did) for did in dataset_ids]

        response = await self._request("POST", "/api/v1/sync", json=payload)
        result_data = response.json()

        # Handle dictionary of results
        if isinstance(result_data, dict) and "run_id" in result_data:
            return SyncResult(**result_data)
        # If multiple results, return the first one
        elif isinstance(result_data, dict):
            first_key = next(iter(result_data))
            return SyncResult(**result_data[first_key])
        return SyncResult(**result_data)

    async def get_sync_status(self) -> SyncStatus:
        """
        Get status of running sync operations.

        Returns:
            SyncStatus with information about running syncs
        """
        response = await self._request("GET", "/api/v1/sync/status")
        result_data = response.json()
        return SyncStatus(**result_data)

    # ==================== WebSocket Support (P2) ====================

    async def subscribe_cognify_progress(
        self, pipeline_run_id: UUID
    ) -> "AsyncIterator[dict[str, Any]]":
        """
        Subscribe to Cognify processing progress via WebSocket.

        Args:
            pipeline_run_id: UUID of the pipeline run to monitor

        Yields:
            Progress updates as dictionaries with status and payload

        Raises:
            ImportError: If websockets package is not installed
            AuthenticationError: If authentication fails
            ServerError: If WebSocket connection fails

        Example:
            >>> async for update in client.subscribe_cognify_progress(pipeline_run_id):
            ...     print(f"Status: {update['status']}")
            ...     if update['status'] == 'completed':
            ...         break
        """
        try:
            import websockets
        except ImportError as err:
            raise ImportError(
                "websockets package is required for WebSocket support. "
                "Install it with: pip install cognee-sdk[websocket]"
            ) from err

        # Convert HTTP URL to WebSocket URL
        ws_url = self.api_url.replace("http://", "ws://").replace("https://", "wss://")
        endpoint = f"/api/v1/cognify/subscribe/{pipeline_run_id}"

        # Prepare headers
        headers: dict[str, str] = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        # Connect to WebSocket
        async with websockets.connect(
            f"{ws_url}{endpoint}",
            extra_headers=headers,
        ) as websocket:
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    yield data

                    # Exit when processing is completed
                    if data.get("status") in ("completed", "PipelineRunCompleted"):
                        break
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    raise ServerError(f"WebSocket error: {str(e)}", 500) from e

    # ==================== Advanced Features (P2) ====================

    async def add_batch(
        self,
        data_list: list[str | bytes | Path | BinaryIO],
        dataset_name: str | None = None,
        dataset_id: UUID | None = None,
        node_set: list[str] | None = None,
        max_concurrent: int | None = None,
        continue_on_error: bool = False,
        return_errors: bool = False,
        adaptive_concurrency: bool = True,
    ) -> list[AddResult] | tuple[list[AddResult], list[Exception]]:
        """
        Add multiple data items in batch with concurrent control and error handling.

        Args:
            data_list: List of data items to add
            dataset_name: Name of the dataset
            dataset_id: UUID of the dataset
            node_set: Optional list of node identifiers
            max_concurrent: Maximum number of concurrent operations. If None and adaptive_concurrency=True,
                          will be automatically determined based on data size (default: None)
            continue_on_error: If True, continue processing even if some items fail (default: False)
            return_errors: If True, return tuple of (results, errors) instead of just results (default: False)
            adaptive_concurrency: If True, automatically adjust concurrency based on data size (default: True)

        Returns:
            If return_errors=False: List of AddResult objects
            If return_errors=True: Tuple of (list of AddResult objects, list of Exception objects)
            
            When continue_on_error=True, failed items will have None in results list and error in errors list.

        Raises:
            ValidationError: If data_list is empty
            ServerError: If any operation fails and continue_on_error=False (first error encountered)

        Example:
            >>> # Basic usage - stop on first error
            >>> results = await client.add_batch(
            ...     data_list=["text1", "text2", "text3"],
            ...     dataset_name="my-dataset",
            ...     max_concurrent=5
            ... )
            >>>
            >>> # Continue on error and collect all errors
            >>> results, errors = await client.add_batch(
            ...     data_list=["text1", "text2", "text3"],
            ...     dataset_name="my-dataset",
            ...     continue_on_error=True,
            ...     return_errors=True
            ... )
        """
        if not data_list:
            if return_errors:
                return [], []
            return []

        # Adaptive concurrency: adjust based on data size
        if adaptive_concurrency and max_concurrent is None:
            # Estimate average data size
            total_size = 0
            sample_count = min(10, len(data_list))  # Sample first 10 items
            for item in data_list[:sample_count]:
                if isinstance(item, (str, bytes)):
                    total_size += len(item) if isinstance(item, bytes) else len(item.encode())
                elif isinstance(item, Path) and item.exists():
                    total_size += item.stat().st_size
            
            avg_size = total_size / sample_count if sample_count > 0 else 0
            
            # Adjust concurrency based on data size
            if avg_size > 10 * 1024 * 1024:  # > 10MB
                max_concurrent = 5  # Large files: lower concurrency
            elif avg_size > 1 * 1024 * 1024:  # > 1MB
                max_concurrent = 10  # Medium files: moderate concurrency
            else:
                max_concurrent = 20  # Small files: higher concurrency
        
        # Default concurrency if not set
        if max_concurrent is None:
            max_concurrent = 10

        # Use semaphore to control concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)

        async def add_with_semaphore(
            item: str | bytes | Path | BinaryIO,
        ) -> tuple[int, AddResult | None, Exception | None]:
            """Add a single item with semaphore control and error handling."""
            async with semaphore:
                try:
                    result = await self.add(
                        data=item,
                        dataset_name=dataset_name,
                        dataset_id=dataset_id,
                        node_set=node_set,
                    )
                    return (0, result, None)  # (index_offset, result, error)
                except Exception as e:
                    return (0, None, e)

        # Create tasks with index tracking
        tasks = [add_with_semaphore(item) for item in data_list]
        
        if continue_on_error:
            # Continue processing even if some fail
            results_list: list[AddResult | None] = []
            errors_list: list[Exception] = []
            
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for task_result in task_results:
                if isinstance(task_result, Exception):
                    # Task itself failed (shouldn't happen, but handle it)
                    results_list.append(None)
                    errors_list.append(task_result)
                else:
                    _, result, error = task_result
                    results_list.append(result)
                    if error is not None:
                        errors_list.append(error)
            
            # Filter out None results if return_errors is False
            if return_errors:
                return results_list, errors_list
            else:
                # Return only successful results
                return [r for r in results_list if r is not None]
        else:
            # Stop on first error (default behavior)
            task_results = await asyncio.gather(*tasks)
            
            # Check for errors and raise the first one encountered
            for _, result, error in task_results:
                if error is not None:
                    raise error
            
            # All succeeded, collect results
            results = [result for _, result, _ in task_results if result is not None]
            
            if return_errors:
                errors = [err for _, _, err in task_results if err is not None]
                return results, errors
            else:
                return results
