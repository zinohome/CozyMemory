"""
Unit tests for sync API.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.models import SyncResult, SyncStatus


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


@pytest.mark.asyncio
async def test_sync_to_cloud(client):
    """Test syncing to cloud."""
    dataset_id1 = uuid4()
    dataset_id2 = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "run_id": str(uuid4()),
        "status": "started",
        "dataset_ids": [str(dataset_id1), str(dataset_id2)],
        "dataset_names": ["dataset1", "dataset2"],
        "message": "Sync started",
        "user_id": str(uuid4()),
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.sync_to_cloud([dataset_id1, dataset_id2])

        assert isinstance(result, SyncResult)
        assert result.status == "started"
        assert len(result.dataset_ids) == 2
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_sync_to_cloud_all_datasets(client):
    """Test syncing all datasets to cloud."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "run_id": str(uuid4()),
        "status": "started",
        "dataset_ids": [],
        "dataset_names": [],
        "message": "Sync started",
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.sync_to_cloud()

        assert isinstance(result, SyncResult)
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_get_sync_status(client):
    """Test getting sync status."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "has_running_sync": True,
        "running_sync_count": 1,
        "latest_running_sync": {
            "run_id": str(uuid4()),
            "dataset_ids": [str(uuid4())],
            "dataset_names": ["dataset1"],
            "progress_percentage": 50,
            "created_at": "2025-01-01T00:00:00Z",
        },
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        status = await client.get_sync_status()

        assert isinstance(status, SyncStatus)
        assert status.has_running_sync is True
        assert status.running_sync_count == 1
        assert status.latest_running_sync is not None
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_get_sync_status_no_running(client):
    """Test getting sync status when no syncs are running."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "has_running_sync": False,
        "running_sync_count": 0,
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        status = await client.get_sync_status()

        assert isinstance(status, SyncStatus)
        assert status.has_running_sync is False
        assert status.running_sync_count == 0
        assert status.latest_running_sync is None
