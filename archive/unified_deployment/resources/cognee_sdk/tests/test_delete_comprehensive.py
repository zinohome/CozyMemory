"""
Comprehensive unit tests for delete functionality.

Tests soft/hard delete modes and error cases.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import NotFoundError
from cognee_sdk.models import DeleteResult


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


class TestDeleteModes:
    """Tests for different delete modes."""

    @pytest.mark.asyncio
    async def test_delete_soft_mode(self, client):
        """Test soft delete mode (default)."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data deleted (soft)",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.delete(data_id=data_id, dataset_id=dataset_id, mode="soft")

            assert isinstance(result, DeleteResult)
            assert result.status == "success"
            # Verify mode parameter was included
            call_args = mock_request.call_args
            params = call_args[1]["params"]
            assert params["mode"] == "soft"

    @pytest.mark.asyncio
    async def test_delete_hard_mode(self, client):
        """Test hard delete mode."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data deleted (hard)",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.delete(data_id=data_id, dataset_id=dataset_id, mode="hard")

            assert isinstance(result, DeleteResult)
            assert result.status == "success"
            # Verify mode parameter was included
            call_args = mock_request.call_args
            params = call_args[1]["params"]
            assert params["mode"] == "hard"

    @pytest.mark.asyncio
    async def test_delete_default_mode(self, client):
        """Test delete with default mode (soft)."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data deleted",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.delete(data_id=data_id, dataset_id=dataset_id)

            assert isinstance(result, DeleteResult)
            # Default mode should be soft
            call_args = mock_request.call_args
            params = call_args[1]["params"]
            assert params["mode"] == "soft"


class TestDeleteErrorCases:
    """Tests for delete error cases."""

    @pytest.mark.asyncio
    async def test_delete_not_found_data_id(self, client):
        """Test delete with non-existent data_id."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Data not found"}
        mock_response.text = "Data not found"

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(NotFoundError) as exc_info:
                await client.delete(data_id=data_id, dataset_id=dataset_id)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found_dataset_id(self, client):
        """Test delete with non-existent dataset_id."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Dataset not found"}
        mock_response.text = "Dataset not found"

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(NotFoundError) as exc_info:
                await client.delete(data_id=data_id, dataset_id=dataset_id)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_invalid_mode(self, client):
        """Test delete with invalid mode parameter."""
        data_id = uuid4()
        dataset_id = uuid4()

        # Invalid mode should still be sent to API, which will handle validation
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data deleted",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            # SDK doesn't validate mode, API will handle it
            result = await client.delete(
                data_id=data_id, dataset_id=dataset_id, mode="invalid_mode"
            )

            assert isinstance(result, DeleteResult)
            call_args = mock_request.call_args
            params = call_args[1]["params"]
            assert params["mode"] == "invalid_mode"


class TestDeleteParameters:
    """Tests for delete parameter handling."""

    @pytest.mark.asyncio
    async def test_delete_parameters_included(self, client):
        """Test that all parameters are correctly included in request."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data deleted",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.delete(data_id=data_id, dataset_id=dataset_id, mode="hard")

            call_args = mock_request.call_args
            params = call_args[1]["params"]
            assert params["data_id"] == str(data_id)
            assert params["dataset_id"] == str(dataset_id)
            assert params["mode"] == "hard"
            # Verify DELETE method was used
            assert call_args[0][0] == "DELETE"
            assert call_args[0][1] == "/api/v1/delete"
