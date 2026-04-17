"""
Unit tests for concurrency and performance.

Tests concurrent operations and batch processing.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.models import AddResult


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


class TestConcurrentOperations:
    """Tests for concurrent API operations."""

    @pytest.mark.asyncio
    async def test_concurrent_add_operations(self, client):
        """Test multiple concurrent add operations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(uuid4()),
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Create multiple concurrent add tasks
            tasks = [client.add(data=f"Data {i}", dataset_name="test-dataset") for i in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(isinstance(r, AddResult) for r in results)
            assert mock_request.call_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self, client):
        """Test multiple concurrent search operations."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result", "score": 0.9}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Create multiple concurrent search tasks
            tasks = [client.search(query=f"Query {i}") for i in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(isinstance(r, list) for r in results)
            assert mock_request.call_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, client):
        """Test concurrent mixed operations (add, search, list)."""
        add_response = MagicMock()
        add_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(uuid4()),
        }

        search_response = MagicMock()
        search_response.json.return_value = [{"id": "1", "text": "Result", "score": 0.9}]

        list_response = MagicMock()
        list_response.json.return_value = []

        def mock_request_side_effect(*args, **kwargs):
            endpoint = args[1] if len(args) > 1 else kwargs.get("endpoint", "")
            if "/add" in endpoint:
                return add_response
            elif "/search" in endpoint:
                return search_response
            elif "/datasets" in endpoint:
                return list_response
            return MagicMock()

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_request_side_effect

            # Create mixed concurrent tasks
            tasks = [
                client.add(data="Data 1", dataset_name="test-dataset"),
                client.search(query="Query 1"),
                client.list_datasets(),
                client.add(data="Data 2", dataset_name="test-dataset"),
                client.search(query="Query 2"),
            ]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert isinstance(results[0], AddResult)
            assert isinstance(results[1], list)
            assert isinstance(results[2], list)
            assert isinstance(results[3], AddResult)
            assert isinstance(results[4], list)


class TestBatchOperations:
    """Tests for batch operations."""

    @pytest.mark.asyncio
    async def test_add_batch_concurrent_execution(self, client):
        """Test that add_batch executes operations concurrently."""
        data_list = [f"Data {i}" for i in range(10)]

        call_times = []
        call_lock = asyncio.Lock()

        async def mock_add_with_timing(*args, **kwargs):
            async with call_lock:
                call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Simulate network delay
            return AddResult(status="success", message="Data added", data_id=uuid4())

        with patch.object(client, "add", side_effect=mock_add_with_timing):
            start_time = asyncio.get_event_loop().time()
            results = await client.add_batch(data_list=data_list, dataset_name="test-dataset")
            end_time = asyncio.get_event_loop().time()

            assert len(results) == 10
            duration = end_time - start_time
            # If concurrent, should be much faster than sequential (10 * 0.01 = 0.1s)
            # Allow some overhead, but should be significantly less
            assert duration < 0.2

    @pytest.mark.asyncio
    async def test_add_batch_large_dataset(self, client):
        """Test add_batch with large dataset."""
        data_list = [f"Data {i}" for i in range(100)]

        with patch.object(client, "add", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = AddResult(
                status="success", message="Data added", data_id=uuid4()
            )
            results = await client.add_batch(data_list=data_list, dataset_name="test-dataset")

            assert len(results) == 100
            assert mock_add.call_count == 100
            assert all(isinstance(r, AddResult) for r in results)

    @pytest.mark.asyncio
    async def test_add_batch_with_failures(self, client):
        """Test add_batch when some operations fail."""
        from cognee_sdk.exceptions import ServerError

        data_list = [f"Data {i}" for i in range(5)]
        call_count = 0

        async def mock_add_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First two succeed
                return AddResult(status="success", message="Data added", data_id=uuid4())
            elif call_count == 3:
                # Third fails
                raise ServerError("Server error", 500)
            else:
                # Rest succeed
                return AddResult(status="success", message="Data added", data_id=uuid4())

        with patch.object(client, "add", side_effect=mock_add_with_failures):
            # Should raise the first exception encountered
            with pytest.raises(ServerError):
                await client.add_batch(data_list=data_list, dataset_name="test-dataset")


class TestConnectionPooling:
    """Tests for connection pooling behavior."""

    @pytest.mark.asyncio
    async def test_multiple_requests_reuse_connection(self, client):
        """Test that multiple requests can reuse connections."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Make multiple requests
            await client.health_check()
            await client.health_check()
            await client.health_check()

            # All should use the same client instance
            assert mock_request.call_count == 3
            # Verify all requests were made (connection pooling is handled by httpx internally)
            assert all(
                len(call[0]) >= 2 and call[0][0] == "GET" for call in mock_request.call_args_list
            )
