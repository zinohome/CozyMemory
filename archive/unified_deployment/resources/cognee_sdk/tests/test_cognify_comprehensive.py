"""
Comprehensive unit tests for cognify functionality.

Tests various parameter combinations and edge cases.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import ValidationError
from cognee_sdk.models import CognifyResult


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


class TestCognifyParameters:
    """Tests for various parameter combinations."""

    @pytest.mark.asyncio
    async def test_cognify_with_datasets(self, client):
        """Test cognify with datasets parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
            "entity_count": 10,
            "duration": 5.5,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1", "dataset2"])

            assert isinstance(result, dict)
            assert "default" in result
            assert isinstance(result["default"], CognifyResult)
            # Verify datasets were included in payload
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "datasets" in payload
            assert payload["datasets"] == ["dataset1", "dataset2"]

    @pytest.mark.asyncio
    async def test_cognify_with_dataset_ids(self, client):
        """Test cognify with dataset_ids parameter."""
        dataset_id1 = uuid4()
        dataset_id2 = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(dataset_ids=[dataset_id1, dataset_id2])

            assert isinstance(result, dict)
            # Verify dataset_ids were included in payload
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "dataset_ids" in payload
            assert len(payload["dataset_ids"]) == 2

    @pytest.mark.asyncio
    async def test_cognify_with_both_datasets_and_ids(self, client):
        """Test cognify with both datasets and dataset_ids."""
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1"], dataset_ids=[dataset_id])

            assert isinstance(result, dict)
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "datasets" in payload
            assert "dataset_ids" in payload

    @pytest.mark.asyncio
    async def test_cognify_run_in_background_false(self, client):
        """Test cognify with run_in_background=False."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.cognify(datasets=["dataset1"], run_in_background=False)

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload.get("run_in_background") is False

    @pytest.mark.asyncio
    async def test_cognify_run_in_background_true(self, client):
        """Test cognify with run_in_background=True."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "pending",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.cognify(datasets=["dataset1"], run_in_background=True)

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload.get("run_in_background") is True

    @pytest.mark.asyncio
    async def test_cognify_with_custom_prompt(self, client):
        """Test cognify with custom_prompt parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        custom_prompt = "Extract entities focusing on technical terms."

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.cognify(datasets=["dataset1"], custom_prompt=custom_prompt)

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "custom_prompt" in payload
            assert payload["custom_prompt"] == custom_prompt


class TestCognifyResults:
    """Tests for cognify result handling."""

    @pytest.mark.asyncio
    async def test_cognify_result_pending(self, client):
        """Test cognify result with pending status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "pending",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1"])

            assert isinstance(result, dict)
            assert result["default"].status == "pending"

    @pytest.mark.asyncio
    async def test_cognify_result_running(self, client):
        """Test cognify result with running status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "running",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1"])

            assert isinstance(result, dict)
            assert result["default"].status == "running"

    @pytest.mark.asyncio
    async def test_cognify_result_completed(self, client):
        """Test cognify result with completed status."""
        pipeline_run_id = uuid4()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(pipeline_run_id),
            "status": "completed",
            "entity_count": 25,
            "duration": 10.5,
            "message": "Processing completed successfully",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1"])

            assert isinstance(result, dict)
            cognify_result = result["default"]
            assert cognify_result.status == "completed"
            assert cognify_result.pipeline_run_id == pipeline_run_id
            assert cognify_result.entity_count == 25
            assert cognify_result.duration == 10.5
            assert cognify_result.message == "Processing completed successfully"

    @pytest.mark.asyncio
    async def test_cognify_result_failed(self, client):
        """Test cognify result with failed status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "failed",
            "message": "Processing failed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1"])

            assert isinstance(result, dict)
            assert result["default"].status == "failed"
            assert result["default"].message == "Processing failed"

    @pytest.mark.asyncio
    async def test_cognify_result_without_optional_fields(self, client):
        """Test cognify result without optional fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1"])

            assert isinstance(result, dict)
            cognify_result = result["default"]
            assert cognify_result.status == "completed"
            # Optional fields should be None
            assert cognify_result.entity_count is None
            assert cognify_result.duration is None
            assert cognify_result.message is None


class TestCognifyValidation:
    """Tests for cognify validation and error cases."""

    @pytest.mark.asyncio
    async def test_cognify_validation_error_no_datasets(self, client):
        """Test cognify validation error when neither datasets nor dataset_ids provided."""
        with pytest.raises(ValidationError) as exc_info:
            await client.cognify(datasets=None, dataset_ids=None)

        assert "datasets or dataset_ids" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cognify_validation_error_empty_datasets(self, client):
        """Test cognify with empty datasets list."""
        # Empty list should trigger validation error
        with pytest.raises(ValidationError) as exc_info:
            await client.cognify(datasets=[])

        assert "datasets or dataset_ids" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cognify_validation_error_empty_dataset_ids(self, client):
        """Test cognify with empty dataset_ids list."""
        # Empty list should trigger validation error
        with pytest.raises(ValidationError) as exc_info:
            await client.cognify(dataset_ids=[])

        assert "datasets or dataset_ids" in str(exc_info.value).lower()


class TestCognifyMultipleDatasets:
    """Tests for cognify with multiple datasets."""

    @pytest.mark.asyncio
    async def test_cognify_multiple_datasets(self, client):
        """Test cognify with multiple datasets."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
            "entity_count": 50,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(datasets=["dataset1", "dataset2", "dataset3"])

            assert isinstance(result, dict)
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert len(payload["datasets"]) == 3

    @pytest.mark.asyncio
    async def test_cognify_multiple_dataset_ids(self, client):
        """Test cognify with multiple dataset IDs."""
        dataset_ids = [uuid4(), uuid4(), uuid4()]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.cognify(dataset_ids=dataset_ids)

            assert isinstance(result, dict)
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert len(payload["dataset_ids"]) == 3
