"""
Unit tests for CogneeClient.

Tests core functionality using mocked HTTP requests.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient, SearchType
from cognee_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from cognee_sdk.models import (
    AddResult,
    Dataset,
    DeleteResult,
)


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000", api_token="test-token")


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={})
    response.text = ""
    response.content = b""
    return response


@pytest.mark.asyncio
async def test_client_initialization(client):
    """Test client initialization."""
    assert client.api_url == "http://localhost:8000"
    assert client.api_token == "test-token"
    assert client.timeout == 300.0
    assert client.max_retries == 3


@pytest.mark.asyncio
async def test_health_check(client, mock_response):
    """Test health check."""
    mock_response.json.return_value = {"status": "healthy", "version": "1.0.0"}

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.health_check()

        assert result.status == "healthy"
        assert result.version == "1.0.0"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_add_text_data(client, mock_response):
    """Test adding text data."""
    mock_response.json.return_value = {
        "status": "success",
        "message": "Data added",
        "data_id": str(uuid4()),
        "dataset_id": str(uuid4()),
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.add(
            data="Test data",
            dataset_name="test-dataset",
        )

        assert isinstance(result, AddResult)
        assert result.status == "success"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_add_validation_error(client):
    """Test add with missing dataset name."""
    with pytest.raises(ValidationError):
        await client.add(data="test", dataset_name=None, dataset_id=None)


@pytest.mark.asyncio
async def test_delete(client, mock_response):
    """Test deleting data."""
    mock_response.json.return_value = {
        "status": "success",
        "message": "Data deleted",
    }

    data_id = uuid4()
    dataset_id = uuid4()

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.delete(data_id=data_id, dataset_id=dataset_id)

        assert isinstance(result, DeleteResult)
        assert result.status == "success"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_cognify(client, mock_response):
    """Test cognify operation."""
    mock_response.json.return_value = {
        "default": {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
            "entity_count": 10,
            "duration": 5.5,
        }
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.cognify(datasets=["test-dataset"])

        assert isinstance(result, dict)
        assert "default" in result
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_cognify_validation_error(client):
    """Test cognify with missing datasets."""
    with pytest.raises(ValidationError):
        await client.cognify(datasets=None, dataset_ids=None)


@pytest.mark.asyncio
async def test_search(client, mock_response):
    """Test search operation."""
    mock_response.json.return_value = [
        {"id": "1", "text": "Result 1", "score": 0.9},
        {"id": "2", "text": "Result 2", "score": 0.8},
    ]

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        results = await client.search(
            query="test query",
            search_type=SearchType.GRAPH_COMPLETION,
        )

        assert isinstance(results, list)
        assert len(results) == 2
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_search_validation_error(client):
    """Test search with empty query."""
    with pytest.raises(ValidationError):
        await client.search(query="")


@pytest.mark.asyncio
async def test_list_datasets(client, mock_response):
    """Test listing datasets."""
    mock_response.json.return_value = [
        {
            "id": str(uuid4()),
            "name": "dataset1",
            "created_at": "2025-01-01T00:00:00Z",
            "owner_id": str(uuid4()),
        },
        {
            "id": str(uuid4()),
            "name": "dataset2",
            "created_at": "2025-01-01T00:00:00Z",
            "owner_id": str(uuid4()),
        },
    ]

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        datasets = await client.list_datasets()

        assert isinstance(datasets, list)
        assert len(datasets) == 2
        assert all(isinstance(d, Dataset) for d in datasets)
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_create_dataset(client, mock_response):
    """Test creating a dataset."""
    dataset_id = uuid4()
    owner_id = uuid4()
    mock_response.json.return_value = {
        "id": str(dataset_id),
        "name": "new-dataset",
        "created_at": "2025-01-01T00:00:00Z",
        "owner_id": str(owner_id),
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        dataset = await client.create_dataset("new-dataset")

        assert isinstance(dataset, Dataset)
        assert dataset.name == "new-dataset"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_create_dataset_validation_error(client):
    """Test creating dataset with empty name."""
    with pytest.raises(ValidationError):
        await client.create_dataset("")


@pytest.mark.asyncio
async def test_authentication_error(client):
    """Test handling authentication errors."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": "Unauthorized"}
    mock_response.text = "Unauthorized"

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError):
            await client.list_datasets()


@pytest.mark.asyncio
async def test_not_found_error(client):
    """Test handling not found errors."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": "Not found"}
    mock_response.text = "Not found"

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(NotFoundError):
            await client.list_datasets()


@pytest.mark.asyncio
async def test_server_error(client):
    """Test handling server errors."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": "Internal server error"}
    mock_response.text = "Internal server error"

    with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        with pytest.raises(ServerError):
            await client.list_datasets()


@pytest.mark.asyncio
async def test_close(client):
    """Test closing the client."""
    with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_context_manager(client):
    """Test using client as async context manager."""
    with patch.object(client.client, "aclose", new_callable=AsyncMock):
        async with client:
            assert client.api_url == "http://localhost:8000"


@pytest.mark.asyncio
async def test_client_initialization_default_params(client):
    """Test client initialization with default parameters."""
    default_client = CogneeClient(api_url="http://localhost:8000")
    assert default_client.timeout == 300.0
    assert default_client.max_retries == 3
    assert default_client.retry_delay == 1.0


@pytest.mark.asyncio
async def test_client_initialization_custom_params():
    """Test client initialization with custom parameters."""
    client = CogneeClient(
        api_url="http://localhost:8000",
        timeout=600.0,
        max_retries=5,
        retry_delay=2.0,
    )
    assert client.timeout == 600.0
    assert client.max_retries == 5
    assert client.retry_delay == 2.0


@pytest.mark.asyncio
async def test_client_initialization_url_normalization():
    """Test client initialization with URL normalization (trailing slash)."""
    client = CogneeClient(api_url="http://localhost:8000/")
    # URL should be normalized (trailing slash removed)
    assert client.api_url == "http://localhost:8000"


@pytest.mark.asyncio
async def test_close_idempotency(client):
    """Test that close() can be called multiple times safely."""
    with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        await client.close()
        await client.close()
        # Should only close once (or handle multiple calls gracefully)
        assert mock_close.call_count >= 1


@pytest.mark.asyncio
async def test_context_manager_with_exception(client):
    """Test context manager handles exceptions correctly."""
    with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
        try:
            async with client:
                raise ValueError("Test exception")
        except ValueError:
            pass
        # Client should still be closed even if exception occurs
        mock_close.assert_called_once()
