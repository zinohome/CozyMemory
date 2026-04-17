"""
Integration test scenarios.

Tests complete workflows and error recovery scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient, SearchType
from cognee_sdk.exceptions import AuthenticationError, ServerError
from cognee_sdk.models import (
    AddResult,
    Dataset,
    DeleteResult,
    GraphData,
)


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000", api_token="test-token")


class TestCompleteWorkflow:
    """Tests for complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_complete_data_workflow(self, client):
        """Test complete workflow: create dataset -> add data -> cognify -> search -> get graph -> delete."""
        dataset_id = uuid4()
        owner_id = uuid4()
        data_id = uuid4()
        pipeline_run_id = uuid4()
        node_id = uuid4()

        # Mock responses for each step
        create_dataset_response = MagicMock()
        create_dataset_response.json.return_value = {
            "id": str(dataset_id),
            "name": "workflow-dataset",
            "created_at": "2025-01-01T00:00:00Z",
            "owner_id": str(owner_id),
        }

        add_response = MagicMock()
        add_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(data_id),
            "dataset_id": str(dataset_id),
        }

        cognify_response = MagicMock()
        cognify_response.json.return_value = {
            "pipeline_run_id": str(pipeline_run_id),
            "status": "completed",
            "entity_count": 10,
            "duration": 5.5,
        }

        search_response = MagicMock()
        search_response.json.return_value = [
            {
                "id": "1",
                "text": "Search result",
                "score": 0.9,
                "metadata": {"source": "workflow-dataset"},
            }
        ]

        graph_response = MagicMock()
        graph_response.json.return_value = {
            "nodes": [
                {
                    "id": str(node_id),
                    "label": "Entity",
                    "properties": {"name": "Test Entity"},
                }
            ],
            "edges": [],
        }

        delete_response = MagicMock()
        delete_response.json.return_value = {
            "status": "success",
            "message": "Data deleted",
        }

        def mock_request_side_effect(method, endpoint, **kwargs):
            if endpoint == "/api/v1/datasets" and method == "POST":
                return create_dataset_response
            elif endpoint == "/api/v1/add":
                return add_response
            elif endpoint == "/api/v1/cognify":
                return cognify_response
            elif endpoint == "/api/v1/search":
                return search_response
            elif "/api/v1/datasets" in endpoint and "/graph" in endpoint:
                return graph_response
            elif endpoint == "/api/v1/delete":
                return delete_response
            return MagicMock()

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_request_side_effect

            # Step 1: Create dataset
            dataset = await client.create_dataset("workflow-dataset")
            assert isinstance(dataset, Dataset)
            assert dataset.name == "workflow-dataset"

            # Step 2: Add data
            add_result = await client.add(
                data="Test data for workflow", dataset_name="workflow-dataset"
            )
            assert isinstance(add_result, AddResult)
            assert add_result.status == "success"

            # Step 3: Cognify
            cognify_result = await client.cognify(datasets=["workflow-dataset"])
            assert isinstance(cognify_result, dict)
            assert cognify_result["default"].status == "completed"

            # Step 4: Search
            search_results = await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION
            )
            assert isinstance(search_results, list)
            assert len(search_results) > 0

            # Step 5: Get graph
            graph = await client.get_dataset_graph(dataset_id)
            assert isinstance(graph, GraphData)
            assert len(graph.nodes) > 0

            # Step 6: Delete data
            delete_result = await client.delete(data_id=data_id, dataset_id=dataset_id)
            assert isinstance(delete_result, DeleteResult)
            assert delete_result.status == "success"

            # Verify all steps were called
            assert mock_request.call_count >= 6


class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_retry(self, client):
        """Test retry mechanism on network errors."""
        import httpx

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"status": "ok"}

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            # First two attempts fail, third succeeds
            mock_request.side_effect = [
                httpx.RequestError("Connection error"),
                httpx.RequestError("Connection error"),
                success_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.health_check()

                assert result.status == "ok"
                assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_retry(self, client):
        """Test retry mechanism on timeout errors."""
        import httpx

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"status": "ok"}

        client.max_retries = 3
        client.retry_delay = 0.1

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            # First attempt times out, second succeeds
            mock_request.side_effect = [
                httpx.TimeoutException("Request timeout"),
                success_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.health_check()

                assert result.status == "ok"
                assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_authentication_error_recovery(self, client):
        """Test handling authentication errors."""
        auth_error_response = MagicMock()
        auth_error_response.status_code = 401
        auth_error_response.json.return_value = {"error": "Unauthorized"}
        auth_error_response.text = "Unauthorized"

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = auth_error_response

            with pytest.raises(AuthenticationError) as exc_info:
                await client.list_datasets()

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_server_error_retry(self, client):
        """Test retry mechanism on server errors."""

        # Server errors (5xx) should not retry by default in _request
        # But we can test the error handling
        server_error_response = MagicMock()
        server_error_response.status_code = 500
        server_error_response.json.return_value = {"error": "Internal server error"}
        server_error_response.text = "Internal server error"

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = server_error_response

            with pytest.raises(ServerError) as exc_info:
                await client.health_check()

            assert exc_info.value.status_code == 500


class TestComplexScenarios:
    """Tests for complex usage scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_datasets_workflow(self, client):
        """Test workflow with multiple datasets."""
        dataset_id1 = uuid4()
        dataset_id2 = uuid4()
        owner_id = uuid4()

        # Mock list_datasets response
        list_response = MagicMock()
        list_response.json.return_value = [
            {
                "id": str(dataset_id1),
                "name": "dataset1",
                "created_at": "2025-01-01T00:00:00Z",
                "owner_id": str(owner_id),
            },
            {
                "id": str(dataset_id2),
                "name": "dataset2",
                "created_at": "2025-01-01T00:00:00Z",
                "owner_id": str(owner_id),
            },
        ]

        cognify_response = MagicMock()
        cognify_response.json.return_value = {
            "pipeline_run_id": str(uuid4()),
            "status": "completed",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:

            def side_effect(method, endpoint, **kwargs):
                if endpoint == "/api/v1/datasets" and method == "GET":
                    return list_response
                elif endpoint == "/api/v1/cognify":
                    return cognify_response
                return MagicMock()

            mock_request.side_effect = side_effect

            # List datasets
            datasets = await client.list_datasets()
            assert len(datasets) == 2

            # Cognify multiple datasets
            result = await client.cognify(datasets=["dataset1", "dataset2"])
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, client):
        """Test search with multiple filters applied."""
        dataset_id = uuid4()
        search_response = MagicMock()
        search_response.json.return_value = [{"id": "1", "text": "Result", "score": 0.9}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = search_response

            results = await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                datasets=["dataset1"],
                dataset_ids=[dataset_id],
                system_prompt="Custom prompt",
                node_name=["node1", "node2"],
                top_k=20,
                only_context=False,
                use_combined_context=True,
            )

            assert isinstance(results, list)
            # Verify all parameters were included
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["query"] == "test query"
            assert "datasets" in payload
            assert "dataset_ids" in payload
            assert "system_prompt" in payload
            assert "node_name" in payload
            assert payload["top_k"] == 20
