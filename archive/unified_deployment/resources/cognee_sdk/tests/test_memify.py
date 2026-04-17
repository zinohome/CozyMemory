"""
Unit tests for memify and search history API.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import ValidationError
from cognee_sdk.models import MemifyResult, SearchHistoryItem


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


@pytest.mark.asyncio
async def test_memify(client):
    """Test memify operation."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "pipeline_run_id": str(uuid4()),
        "status": "completed",
        "message": "Memify completed",
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.memify(
            dataset_name="test-dataset",
            extraction_tasks=["task1"],
            enrichment_tasks=["task2"],
        )

        assert isinstance(result, MemifyResult)
        assert result.status == "completed"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_memify_validation_error(client):
    """Test memify with missing dataset."""
    with pytest.raises(ValidationError):
        await client.memify(dataset_name=None, dataset_id=None)


@pytest.mark.asyncio
async def test_get_search_history(client):
    """Test getting search history."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": str(uuid4()),
            "text": "test query 1",
            "user": "user@example.com",
            "created_at": "2025-01-01T00:00:00Z",
        },
        {
            "id": str(uuid4()),
            "text": "test query 2",
            "user": "user@example.com",
            "created_at": "2025-01-01T01:00:00Z",
        },
    ]

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        history = await client.get_search_history()

        assert len(history) == 2
        assert all(isinstance(item, SearchHistoryItem) for item in history)
        assert history[0].text == "test query 1"
        mock_request.assert_called_once()
