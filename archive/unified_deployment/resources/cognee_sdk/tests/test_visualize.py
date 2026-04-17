"""
Unit tests for visualization API.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


@pytest.mark.asyncio
async def test_visualize(client):
    """Test visualization generation."""
    dataset_id = uuid4()

    mock_response = MagicMock()
    mock_response.text = "<html><body>Graph Visualization</body></html>"

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        html = await client.visualize(dataset_id)

        assert isinstance(html, str)
        assert "Graph Visualization" in html
        mock_request.assert_called_once()
