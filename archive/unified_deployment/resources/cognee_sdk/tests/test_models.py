"""
Unit tests for data models.

Tests all Pydantic models and enumerations.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from cognee_sdk.models import (
    AddResult,
    CognifyResult,
    CombinedSearchResult,
    DataItem,
    Dataset,
    DeleteResult,
    GraphData,
    GraphEdge,
    GraphNode,
    HealthStatus,
    MemifyResult,
    PipelineRunStatus,
    SearchHistoryItem,
    SearchResult,
    SearchType,
    SyncResult,
    SyncStatus,
    UpdateResult,
    User,
)


class TestEnumerations:
    """Tests for enumeration types."""

    def test_search_type_values(self):
        """Test all SearchType enum values."""
        assert SearchType.SUMMARIES == "SUMMARIES"
        assert SearchType.CHUNKS == "CHUNKS"
        assert SearchType.RAG_COMPLETION == "RAG_COMPLETION"
        assert SearchType.GRAPH_COMPLETION == "GRAPH_COMPLETION"
        assert SearchType.GRAPH_SUMMARY_COMPLETION == "GRAPH_SUMMARY_COMPLETION"
        assert SearchType.CODE == "CODE"
        assert SearchType.CYPHER == "CYPHER"
        assert SearchType.NATURAL_LANGUAGE == "NATURAL_LANGUAGE"
        assert SearchType.GRAPH_COMPLETION_COT == "GRAPH_COMPLETION_COT"
        assert SearchType.GRAPH_COMPLETION_CONTEXT_EXTENSION == "GRAPH_COMPLETION_CONTEXT_EXTENSION"
        assert SearchType.FEELING_LUCKY == "FEELING_LUCKY"
        assert SearchType.FEEDBACK == "FEEDBACK"
        assert SearchType.TEMPORAL == "TEMPORAL"
        assert SearchType.CODING_RULES == "CODING_RULES"
        assert SearchType.CHUNKS_LEXICAL == "CHUNKS_LEXICAL"

    def test_pipeline_run_status_values(self):
        """Test all PipelineRunStatus enum values."""
        assert PipelineRunStatus.PENDING == "pending"
        assert PipelineRunStatus.RUNNING == "running"
        assert PipelineRunStatus.COMPLETED == "completed"
        assert PipelineRunStatus.FAILED == "failed"


class TestUser:
    """Tests for User model."""

    def test_user_creation(self):
        """Test creating User with all fields."""
        user_id = uuid4()
        created_at = datetime.now()
        user = User(id=user_id, email="user@example.com", created_at=created_at)

        assert user.id == user_id
        assert user.email == "user@example.com"
        assert user.created_at == created_at

    def test_user_creation_without_created_at(self):
        """Test creating User without optional created_at."""
        user_id = uuid4()
        user = User(id=user_id, email="user@example.com")

        assert user.id == user_id
        assert user.email == "user@example.com"
        assert user.created_at is None

    def test_user_validation_missing_id(self):
        """Test User validation with missing id."""
        with pytest.raises(PydanticValidationError):
            User(email="user@example.com")

    def test_user_validation_missing_email(self):
        """Test User validation with missing email."""
        with pytest.raises(PydanticValidationError):
            User(id=uuid4())


class TestDataset:
    """Tests for Dataset model."""

    def test_dataset_creation(self):
        """Test creating Dataset with all fields."""
        dataset_id = uuid4()
        owner_id = uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()

        dataset = Dataset(
            id=dataset_id,
            name="test-dataset",
            created_at=created_at,
            updated_at=updated_at,
            owner_id=owner_id,
        )

        assert dataset.id == dataset_id
        assert dataset.name == "test-dataset"
        assert dataset.created_at == created_at
        assert dataset.updated_at == updated_at
        assert dataset.owner_id == owner_id

    def test_dataset_creation_without_updated_at(self):
        """Test creating Dataset without optional updated_at."""
        dataset_id = uuid4()
        owner_id = uuid4()
        created_at = datetime.now()

        dataset = Dataset(
            id=dataset_id, name="test-dataset", created_at=created_at, owner_id=owner_id
        )

        assert dataset.updated_at is None


class TestDataItem:
    """Tests for DataItem model."""

    def test_data_item_creation(self):
        """Test creating DataItem with all fields."""
        data_id = uuid4()
        dataset_id = uuid4()
        created_at = datetime.now()
        updated_at = datetime.now()

        data_item = DataItem(
            id=data_id,
            name="test-data.txt",
            created_at=created_at,
            updated_at=updated_at,
            extension=".txt",
            mime_type="text/plain",
            raw_data_location="/path/to/data",
            dataset_id=dataset_id,
        )

        assert data_item.id == data_id
        assert data_item.name == "test-data.txt"
        assert data_item.extension == ".txt"
        assert data_item.mime_type == "text/plain"


class TestAddResult:
    """Tests for AddResult model."""

    def test_add_result_creation(self):
        """Test creating AddResult with all fields."""
        data_id = uuid4()
        dataset_id = uuid4()

        result = AddResult(
            status="success",
            message="Data added",
            data_id=data_id,
            dataset_id=dataset_id,
        )

        assert result.status == "success"
        assert result.message == "Data added"
        assert result.data_id == data_id
        assert result.dataset_id == dataset_id

    def test_add_result_without_optional_fields(self):
        """Test creating AddResult without optional fields."""
        result = AddResult(status="success", message="Data added")

        assert result.data_id is None
        assert result.dataset_id is None


class TestDeleteResult:
    """Tests for DeleteResult model."""

    def test_delete_result_creation(self):
        """Test creating DeleteResult."""
        result = DeleteResult(status="success", message="Data deleted")

        assert result.status == "success"
        assert result.message == "Data deleted"


class TestCognifyResult:
    """Tests for CognifyResult model."""

    def test_cognify_result_creation(self):
        """Test creating CognifyResult with all fields."""
        pipeline_run_id = uuid4()

        result = CognifyResult(
            pipeline_run_id=pipeline_run_id,
            status="completed",
            entity_count=25,
            duration=10.5,
            message="Processing completed",
        )

        assert result.pipeline_run_id == pipeline_run_id
        assert result.status == "completed"
        assert result.entity_count == 25
        assert result.duration == 10.5
        assert result.message == "Processing completed"

    def test_cognify_result_without_optional_fields(self):
        """Test creating CognifyResult without optional fields."""
        pipeline_run_id = uuid4()

        result = CognifyResult(pipeline_run_id=pipeline_run_id, status="pending")

        assert result.entity_count is None
        assert result.duration is None
        assert result.message is None


class TestMemifyResult:
    """Tests for MemifyResult model."""

    def test_memify_result_creation(self):
        """Test creating MemifyResult."""
        pipeline_run_id = uuid4()

        result = MemifyResult(
            pipeline_run_id=pipeline_run_id, status="completed", message="Memify done"
        )

        assert result.pipeline_run_id == pipeline_run_id
        assert result.status == "completed"
        assert result.message == "Memify done"

    def test_memify_result_without_message(self):
        """Test creating MemifyResult without optional message."""
        pipeline_run_id = uuid4()

        result = MemifyResult(pipeline_run_id=pipeline_run_id, status="pending")

        assert result.message is None


class TestUpdateResult:
    """Tests for UpdateResult model."""

    def test_update_result_creation(self):
        """Test creating UpdateResult."""
        data_id = uuid4()

        result = UpdateResult(status="success", message="Data updated", data_id=data_id)

        assert result.status == "success"
        assert result.message == "Data updated"
        assert result.data_id == data_id

    def test_update_result_without_data_id(self):
        """Test creating UpdateResult without optional data_id."""
        result = UpdateResult(status="success", message="Data updated")

        assert result.data_id is None


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_search_result_creation(self):
        """Test creating SearchResult with all fields."""
        result = SearchResult(
            id="1",
            text="Result text",
            score=0.9,
            metadata={"source": "dataset1"},
        )

        assert result.id == "1"
        assert result.text == "Result text"
        assert result.score == 0.9
        assert result.metadata == {"source": "dataset1"}

    def test_search_result_with_extra_fields(self):
        """Test SearchResult allows extra fields."""
        result = SearchResult(id="1", text="Result", extra_field="extra_value")

        assert hasattr(result, "extra_field")
        assert result.extra_field == "extra_value"

    def test_search_result_minimal(self):
        """Test creating SearchResult with minimal fields."""
        result = SearchResult()

        assert result.id is None
        assert result.text is None
        assert result.score is None
        assert result.metadata is None


class TestCombinedSearchResult:
    """Tests for CombinedSearchResult model."""

    def test_combined_search_result_creation(self):
        """Test creating CombinedSearchResult."""
        result = CombinedSearchResult(
            result="Combined result text",
            context=["Context 1", "Context 2"],
            metadata={"model": "gpt-4"},
        )

        assert result.result == "Combined result text"
        assert result.context == ["Context 1", "Context 2"]
        assert result.metadata == {"model": "gpt-4"}

    def test_combined_search_result_without_optional_fields(self):
        """Test creating CombinedSearchResult without optional fields."""
        result = CombinedSearchResult(result="Result text")

        assert result.context is None
        assert result.metadata is None


class TestSearchHistoryItem:
    """Tests for SearchHistoryItem model."""

    def test_search_history_item_creation(self):
        """Test creating SearchHistoryItem."""
        history_id = uuid4()
        created_at = datetime.now()

        item = SearchHistoryItem(
            id=history_id,
            text="search query",
            user="user@example.com",
            created_at=created_at,
        )

        assert item.id == history_id
        assert item.text == "search query"
        assert item.user == "user@example.com"
        assert item.created_at == created_at


class TestGraphNode:
    """Tests for GraphNode model."""

    def test_graph_node_creation(self):
        """Test creating GraphNode."""
        node_id = uuid4()

        node = GraphNode(id=node_id, label="Person", properties={"name": "John", "age": 30})

        assert node.id == node_id
        assert node.label == "Person"
        assert node.properties == {"name": "John", "age": 30}

    def test_graph_node_without_properties(self):
        """Test creating GraphNode without properties."""
        node_id = uuid4()

        node = GraphNode(id=node_id, label="Person")

        assert node.properties == {}


class TestGraphEdge:
    """Tests for GraphEdge model."""

    def test_graph_edge_creation(self):
        """Test creating GraphEdge."""
        source_id = uuid4()
        target_id = uuid4()

        edge = GraphEdge(source=source_id, target=target_id, label="KNOWS")

        assert edge.source == source_id
        assert edge.target == target_id
        assert edge.label == "KNOWS"


class TestGraphData:
    """Tests for GraphData model."""

    def test_graph_data_creation(self):
        """Test creating GraphData."""
        node1_id = uuid4()
        node2_id = uuid4()

        node1 = GraphNode(id=node1_id, label="Node1")
        node2 = GraphNode(id=node2_id, label="Node2")
        edge = GraphEdge(source=node1_id, target=node2_id, label="RELATED_TO")

        graph = GraphData(nodes=[node1, node2], edges=[edge])

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.nodes[0].id == node1_id
        assert graph.edges[0].source == node1_id

    def test_graph_data_empty(self):
        """Test creating GraphData with empty lists."""
        graph = GraphData(nodes=[], edges=[])

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0


class TestSyncResult:
    """Tests for SyncResult model."""

    def test_sync_result_creation(self):
        """Test creating SyncResult with all fields."""
        dataset_id1 = uuid4()
        dataset_id2 = uuid4()
        user_id = uuid4()
        timestamp = datetime.now()

        result = SyncResult(
            run_id="sync-123",
            status="started",
            dataset_ids=[dataset_id1, dataset_id2],
            dataset_names=["dataset1", "dataset2"],
            message="Sync started",
            timestamp=timestamp,
            user_id=user_id,
        )

        assert result.run_id == "sync-123"
        assert result.status == "started"
        assert len(result.dataset_ids) == 2
        assert len(result.dataset_names) == 2
        assert result.timestamp == timestamp
        assert result.user_id == user_id

    def test_sync_result_without_optional_fields(self):
        """Test creating SyncResult without optional fields."""
        result = SyncResult(
            run_id="sync-123",
            status="started",
            dataset_ids=[],
            dataset_names=[],
            message="Sync started",
        )

        assert result.timestamp is None
        assert result.user_id is None


class TestSyncStatus:
    """Tests for SyncStatus model."""

    def test_sync_status_creation(self):
        """Test creating SyncStatus with all fields."""
        status = SyncStatus(
            has_running_sync=True,
            running_sync_count=2,
            latest_running_sync={"run_id": "sync-123", "progress": 50},
        )

        assert status.has_running_sync is True
        assert status.running_sync_count == 2
        assert status.latest_running_sync == {"run_id": "sync-123", "progress": 50}

    def test_sync_status_no_running_sync(self):
        """Test creating SyncStatus with no running syncs."""
        status = SyncStatus(has_running_sync=False, running_sync_count=0, latest_running_sync=None)

        assert status.has_running_sync is False
        assert status.running_sync_count == 0
        assert status.latest_running_sync is None


class TestHealthStatus:
    """Tests for HealthStatus model."""

    def test_health_status_creation(self):
        """Test creating HealthStatus with all fields."""
        status = HealthStatus(status="healthy", version="1.0.0")

        assert status.status == "healthy"
        assert status.version == "1.0.0"

    def test_health_status_without_version(self):
        """Test creating HealthStatus without optional version."""
        status = HealthStatus(status="healthy")

        assert status.version is None


class TestModelValidation:
    """Tests for model validation and error cases."""

    def test_invalid_uuid_format(self):
        """Test model validation with invalid UUID format."""
        with pytest.raises(PydanticValidationError):
            User(id="invalid-uuid", email="user@example.com")

    def test_invalid_datetime_format(self):
        """Test model validation with invalid datetime format."""
        with pytest.raises(PydanticValidationError):
            Dataset(
                id=uuid4(),
                name="test",
                created_at="invalid-datetime",
                owner_id=uuid4(),
            )

    def test_missing_required_fields(self):
        """Test model validation with missing required fields."""
        with pytest.raises(PydanticValidationError):
            Dataset(name="test")  # Missing id, created_at, owner_id

    def test_model_serialization(self):
        """Test model serialization to dict."""
        user_id = uuid4()
        user = User(id=user_id, email="user@example.com")

        user_dict = user.model_dump()
        # UUID can be serialized as UUID object or string depending on mode
        assert user_dict["id"] == user_id or str(user_dict["id"]) == str(user_id)
        assert user_dict["email"] == "user@example.com"

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        user_id = uuid4()
        user = User(id=user_id, email="user@example.com")

        user_json = user.model_dump_json()
        assert str(user_id) in user_json
        assert "user@example.com" in user_json
