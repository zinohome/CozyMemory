"""
Comprehensive unit tests for search functionality.

Tests all search types, return types, and parameter combinations.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient, SearchType
from cognee_sdk.exceptions import ValidationError
from cognee_sdk.models import CombinedSearchResult, SearchResult


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


class TestSearchTypes:
    """Tests for all 19 search types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "search_type",
        [
            SearchType.SUMMARIES,
            SearchType.CHUNKS,
            SearchType.RAG_COMPLETION,
            SearchType.GRAPH_COMPLETION,
            SearchType.GRAPH_SUMMARY_COMPLETION,
            SearchType.CODE,
            SearchType.CYPHER,
            SearchType.NATURAL_LANGUAGE,
            SearchType.GRAPH_COMPLETION_COT,
            SearchType.GRAPH_COMPLETION_CONTEXT_EXTENSION,
            SearchType.FEELING_LUCKY,
            SearchType.FEEDBACK,
            SearchType.TEMPORAL,
            SearchType.CODING_RULES,
            SearchType.CHUNKS_LEXICAL,
        ],
    )
    async def test_all_search_types(self, client, search_type):
        """Test all search types return results."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "text": "Result 1", "score": 0.9},
            {"id": "2", "text": "Result 2", "score": 0.8},
        ]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search(query="test query", search_type=search_type)

            assert isinstance(results, list)
            mock_request.assert_called_once()
            # Verify search_type was included in payload
            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["search_type"] == search_type.value


class TestSearchReturnTypes:
    """Tests for different return types."""

    @pytest.mark.asyncio
    async def test_search_list_of_search_results(self, client):
        """Test search returning List[SearchResult]."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "1",
                "text": "Result 1",
                "score": 0.9,
                "metadata": {"source": "dataset1"},
            },
            {
                "id": "2",
                "text": "Result 2",
                "score": 0.8,
                "metadata": {"source": "dataset2"},
            },
        ]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION
            )

            assert isinstance(results, list)
            assert len(results) == 2
            assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_combined_result(self, client):
        """Test search returning CombinedSearchResult."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": "Combined search result text",
            "context": ["Context 1", "Context 2"],
            "metadata": {"model": "gpt-4"},
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION
            )

            assert isinstance(result, CombinedSearchResult)
            assert result.result == "Combined search result text"

    @pytest.mark.asyncio
    async def test_search_raw_dict_list(self, client):
        """Test search returning raw List[Dict] when parsing fails."""
        mock_response = MagicMock()
        # Invalid format - SearchResult can accept extra fields, so it will parse
        # but we can check that extra fields are preserved
        mock_response.json.return_value = [
            {"invalid": "format", "text": "some text"},
            {"another": "invalid", "text": "more text"},
        ]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION
            )

            # SearchResult allows extra fields, so it will parse successfully
            assert isinstance(results, list)
            assert isinstance(results[0], SearchResult)
            # Extra fields should be preserved
            assert hasattr(results[0], "invalid") or hasattr(results[0], "another")

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Test search with empty results."""
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION
            )

            assert isinstance(results, list)
            assert len(results) == 0


class TestSearchParameters:
    """Tests for various parameter combinations."""

    @pytest.mark.asyncio
    async def test_search_with_datasets(self, client):
        """Test search with datasets parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                datasets=["dataset1", "dataset2"],
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "datasets" in payload
            assert payload["datasets"] == ["dataset1", "dataset2"]

    @pytest.mark.asyncio
    async def test_search_with_dataset_ids(self, client):
        """Test search with dataset_ids parameter."""
        dataset_id1 = uuid4()
        dataset_id2 = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                dataset_ids=[dataset_id1, dataset_id2],
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "dataset_ids" in payload
            assert len(payload["dataset_ids"]) == 2

    @pytest.mark.asyncio
    async def test_search_with_system_prompt(self, client):
        """Test search with system_prompt parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                system_prompt="You are a helpful assistant.",
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "system_prompt" in payload
            assert payload["system_prompt"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_search_with_node_name(self, client):
        """Test search with node_name parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                node_name=["node1", "node2"],
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert "node_name" in payload
            assert payload["node_name"] == ["node1", "node2"]

    @pytest.mark.asyncio
    async def test_search_with_top_k(self, client):
        """Test search with top_k parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION, top_k=5
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["top_k"] == 5

    @pytest.mark.asyncio
    async def test_search_with_top_k_zero(self, client):
        """Test search with top_k=0."""
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION, top_k=0
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["top_k"] == 0

    @pytest.mark.asyncio
    async def test_search_with_top_k_large(self, client):
        """Test search with large top_k value."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query", search_type=SearchType.GRAPH_COMPLETION, top_k=100
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["top_k"] == 100

    @pytest.mark.asyncio
    async def test_search_with_only_context(self, client):
        """Test search with only_context=True."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                only_context=True,
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["only_context"] is True

    @pytest.mark.asyncio
    async def test_search_with_use_combined_context(self, client):
        """Test search with use_combined_context=True."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                use_combined_context=True,
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["use_combined_context"] is True

    @pytest.mark.asyncio
    async def test_search_all_parameters(self, client):
        """Test search with all parameters combined."""
        dataset_id = uuid4()
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1", "text": "Result"}]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.search(
                query="test query",
                search_type=SearchType.GRAPH_COMPLETION,
                datasets=["dataset1"],
                dataset_ids=[dataset_id],
                system_prompt="System prompt",
                node_name=["node1"],
                top_k=20,
                only_context=False,
                use_combined_context=True,
            )

            call_args = mock_request.call_args
            payload = call_args[1]["json"]
            assert payload["query"] == "test query"
            assert payload["search_type"] == SearchType.GRAPH_COMPLETION.value
            assert "datasets" in payload
            assert "dataset_ids" in payload
            assert "system_prompt" in payload
            assert "node_name" in payload
            assert payload["top_k"] == 20
            assert payload["only_context"] is False
            assert payload["use_combined_context"] is True


class TestSearchValidation:
    """Tests for search validation and error cases."""

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client):
        """Test search with empty query raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await client.search(query="", search_type=SearchType.GRAPH_COMPLETION)

        assert "cannot be empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_whitespace_only_query(self, client):
        """Test search with whitespace-only query."""
        # Whitespace-only strings are truthy in Python, so this should pass validation
        # but may be handled by the API
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            results = await client.search(query="   ", search_type=SearchType.GRAPH_COMPLETION)

            assert isinstance(results, list)
