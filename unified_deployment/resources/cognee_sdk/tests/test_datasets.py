"""
Unit tests for dataset management API.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import ValidationError
from cognee_sdk.models import DataItem, GraphData, PipelineRunStatus


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


@pytest.mark.asyncio
async def test_update_data(client):
    """Test updating data."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "message": "Data updated",
        "data_id": str(uuid4()),
    }

    data_id = uuid4()
    dataset_id = uuid4()

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        result = await client.update(
            data_id=data_id,
            dataset_id=dataset_id,
            data="Updated content",
        )

        assert result.status == "success"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_delete_dataset(client):
    """Test deleting a dataset."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    dataset_id = uuid4()

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        await client.delete_dataset(dataset_id)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "DELETE"
        assert str(dataset_id) in call_args[0][1]


@pytest.mark.asyncio
async def test_get_dataset_data(client):
    """Test getting dataset data."""
    dataset_id = uuid4()
    data_id = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": str(data_id),
            "name": "test-data",
            "created_at": "2025-01-01T00:00:00Z",
            "extension": ".txt",
            "mime_type": "text/plain",
            "raw_data_location": "/path/to/data",
            "dataset_id": str(dataset_id),
        }
    ]

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        data_items = await client.get_dataset_data(dataset_id)

        assert len(data_items) == 1
        assert isinstance(data_items[0], DataItem)
        assert data_items[0].name == "test-data"


@pytest.mark.asyncio
async def test_get_dataset_graph(client):
    """Test getting dataset graph."""
    dataset_id = uuid4()
    node_id = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "nodes": [
            {
                "id": str(node_id),
                "label": "Node1",
                "properties": {"key": "value"},
            }
        ],
        "edges": [
            {
                "source": str(node_id),
                "target": str(uuid4()),
                "label": "RELATED_TO",
            }
        ],
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        graph = await client.get_dataset_graph(dataset_id)

        assert isinstance(graph, GraphData)
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1


@pytest.mark.asyncio
async def test_get_dataset_status(client):
    """Test getting dataset status."""
    dataset_id1 = uuid4()
    dataset_id2 = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        str(dataset_id1): "completed",
        str(dataset_id2): "running",
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        statuses = await client.get_dataset_status([dataset_id1, dataset_id2])

        assert len(statuses) == 2
        assert statuses[dataset_id1] == PipelineRunStatus.COMPLETED
        assert statuses[dataset_id2] == PipelineRunStatus.RUNNING


@pytest.mark.asyncio
async def test_download_raw_data(client):
    """Test downloading raw data."""
    dataset_id = uuid4()
    data_id = uuid4()

    mock_response = MagicMock()
    mock_response.content = b"Raw file content"

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        content = await client.download_raw_data(dataset_id, data_id)

        assert content == b"Raw file content"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_get_dataset_status_empty_list(client):
    """Test getting dataset status with empty list."""
    # Empty list should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        await client.get_dataset_status([])

    assert "cannot be empty" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_dataset_status_single_dataset(client):
    """Test getting dataset status for single dataset."""
    dataset_id = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {str(dataset_id): "completed"}

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        statuses = await client.get_dataset_status([dataset_id])

        assert len(statuses) == 1
        assert statuses[dataset_id] == PipelineRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_dataset_status_all_statuses(client):
    """Test getting dataset status with all possible status values."""
    dataset_id1 = uuid4()
    dataset_id2 = uuid4()
    dataset_id3 = uuid4()
    dataset_id4 = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        str(dataset_id1): "pending",
        str(dataset_id2): "running",
        str(dataset_id3): "completed",
        str(dataset_id4): "failed",
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        statuses = await client.get_dataset_status(
            [dataset_id1, dataset_id2, dataset_id3, dataset_id4]
        )

        assert len(statuses) == 4
        assert statuses[dataset_id1] == PipelineRunStatus.PENDING
        assert statuses[dataset_id2] == PipelineRunStatus.RUNNING
        assert statuses[dataset_id3] == PipelineRunStatus.COMPLETED
        assert statuses[dataset_id4] == PipelineRunStatus.FAILED


@pytest.mark.asyncio
async def test_get_dataset_data_empty(client):
    """Test getting dataset data from empty dataset."""
    dataset_id = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = []

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        data_items = await client.get_dataset_data(dataset_id)

        assert len(data_items) == 0
        assert isinstance(data_items, list)


@pytest.mark.asyncio
async def test_get_dataset_data_multiple_items(client):
    """Test getting dataset data with multiple items."""
    dataset_id = uuid4()
    data_id1 = uuid4()
    data_id2 = uuid4()
    data_id3 = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": str(data_id1),
            "name": "data1.txt",
            "created_at": "2025-01-01T00:00:00Z",
            "extension": ".txt",
            "mime_type": "text/plain",
            "raw_data_location": "/path/to/data1",
            "dataset_id": str(dataset_id),
        },
        {
            "id": str(data_id2),
            "name": "data2.pdf",
            "created_at": "2025-01-01T01:00:00Z",
            "extension": ".pdf",
            "mime_type": "application/pdf",
            "raw_data_location": "/path/to/data2",
            "dataset_id": str(dataset_id),
        },
        {
            "id": str(data_id3),
            "name": "data3.json",
            "created_at": "2025-01-01T02:00:00Z",
            "extension": ".json",
            "mime_type": "application/json",
            "raw_data_location": "/path/to/data3",
            "dataset_id": str(dataset_id),
        },
    ]

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        data_items = await client.get_dataset_data(dataset_id)

        assert len(data_items) == 3
        assert all(isinstance(item, DataItem) for item in data_items)
        assert data_items[0].name == "data1.txt"
        assert data_items[1].name == "data2.pdf"
        assert data_items[2].name == "data3.json"


@pytest.mark.asyncio
async def test_get_dataset_graph_empty(client):
    """Test getting dataset graph with empty graph."""
    dataset_id = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {"nodes": [], "edges": []}

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        graph = await client.get_dataset_graph(dataset_id)

        assert isinstance(graph, GraphData)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0


@pytest.mark.asyncio
async def test_get_dataset_graph_complex(client):
    """Test getting dataset graph with complex structure."""
    dataset_id = uuid4()
    node1_id = uuid4()
    node2_id = uuid4()
    node3_id = uuid4()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "nodes": [
            {"id": str(node1_id), "label": "Node1", "properties": {"name": "Node 1"}},
            {"id": str(node2_id), "label": "Node2", "properties": {"name": "Node 2"}},
            {"id": str(node3_id), "label": "Node3", "properties": {"name": "Node 3"}},
        ],
        "edges": [
            {
                "source": str(node1_id),
                "target": str(node2_id),
                "label": "RELATED_TO",
            },
            {
                "source": str(node2_id),
                "target": str(node3_id),
                "label": "CONNECTED_TO",
            },
            {
                "source": str(node1_id),
                "target": str(node3_id),
                "label": "LINKS_TO",
            },
        ],
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        graph = await client.get_dataset_graph(dataset_id)

        assert isinstance(graph, GraphData)
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 3
        assert graph.nodes[0].id == node1_id
        assert graph.edges[0].source == node1_id
        assert graph.edges[0].target == node2_id
