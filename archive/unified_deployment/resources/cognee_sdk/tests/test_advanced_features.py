"""
Unit tests for advanced features.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.models import AddResult


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


@pytest.mark.asyncio
async def test_add_batch(client):
    """Test batch adding data."""
    data_list = ["data1", "data2", "data3"]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "message": "Data added",
        "data_id": str(uuid4()),
    }

    with patch.object(client, "add", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = AddResult(
            status="success",
            message="Data added",
            data_id=uuid4(),
        )
        results = await client.add_batch(
            data_list=data_list,
            dataset_name="test-dataset",
        )

        assert len(results) == 3
        assert all(isinstance(r, AddResult) for r in results)
        assert mock_add.call_count == 3
