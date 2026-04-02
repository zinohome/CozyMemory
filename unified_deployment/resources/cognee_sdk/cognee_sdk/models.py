"""
Data models for Cognee SDK.

All models use Pydantic BaseModel for type validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchType(str, Enum):
    """Search type enumeration."""

    SUMMARIES = "SUMMARIES"
    CHUNKS = "CHUNKS"
    RAG_COMPLETION = "RAG_COMPLETION"
    GRAPH_COMPLETION = "GRAPH_COMPLETION"
    GRAPH_SUMMARY_COMPLETION = "GRAPH_SUMMARY_COMPLETION"
    CODE = "CODE"
    CYPHER = "CYPHER"
    NATURAL_LANGUAGE = "NATURAL_LANGUAGE"
    GRAPH_COMPLETION_COT = "GRAPH_COMPLETION_COT"
    GRAPH_COMPLETION_CONTEXT_EXTENSION = "GRAPH_COMPLETION_CONTEXT_EXTENSION"
    FEELING_LUCKY = "FEELING_LUCKY"
    FEEDBACK = "FEEDBACK"
    TEMPORAL = "TEMPORAL"
    CODING_RULES = "CODING_RULES"
    CHUNKS_LEXICAL = "CHUNKS_LEXICAL"


class PipelineRunStatus(str, Enum):
    """Pipeline run status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(BaseModel):
    """User model."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    created_at: datetime | None = Field(None, description="Account creation timestamp")


class Dataset(BaseModel):
    """Dataset model."""

    id: UUID = Field(..., description="Dataset ID")
    name: str = Field(..., description="Dataset name")
    created_at: datetime | None = Field(None, alias="createdAt", description="Dataset creation timestamp")
    updated_at: datetime | None = Field(None, alias="updatedAt", description="Last update timestamp")
    owner_id: UUID | None = Field(None, alias="ownerId", description="Dataset owner ID")
    
    model_config = ConfigDict(populate_by_name=True)  # Allow both snake_case and camelCase


class DataItem(BaseModel):
    """Data item model."""

    id: UUID = Field(..., description="Data item ID")
    name: str = Field(..., description="Data item name")
    created_at: datetime | None = Field(None, alias="createdAt", description="Creation timestamp")
    updated_at: datetime | None = Field(None, alias="updatedAt", description="Last update timestamp")
    extension: str | None = Field(None, description="File extension")
    mime_type: str | None = Field(None, alias="mimeType", description="MIME type")
    raw_data_location: str | None = Field(None, alias="rawDataLocation", description="Raw data storage location")
    dataset_id: UUID | None = Field(None, alias="datasetId", description="Dataset ID")
    
    model_config = ConfigDict(populate_by_name=True)


class AddResult(BaseModel):
    """Result model for add operation."""

    status: str = Field(..., description="Operation status")
    message: str | None = Field(None, description="Status message")
    data_id: UUID | None = Field(None, description="Created data ID")
    dataset_id: UUID | None = Field(None, description="Dataset ID")
    pipeline_run_id: UUID | None = Field(None, alias="pipeline_run_id", description="Pipeline run ID")
    dataset_name: str | None = Field(None, alias="dataset_name", description="Dataset name")
    data_ingestion_info: list[dict[str, Any]] | None = Field(None, alias="data_ingestion_info", description="Data ingestion information")
    
    model_config = ConfigDict(populate_by_name=True)
    
    def __init__(self, **data: Any) -> None:
        """Initialize AddResult, extracting data_id from data_ingestion_info if needed."""
        # Extract data_id from data_ingestion_info if present
        if "data_ingestion_info" in data and data["data_ingestion_info"]:
            ingestion_info = data["data_ingestion_info"]
            if isinstance(ingestion_info, list) and len(ingestion_info) > 0:
                first_info = ingestion_info[0]
                if isinstance(first_info, dict) and "data_id" in first_info:
                    if "data_id" not in data or data["data_id"] is None:
                        data["data_id"] = first_info["data_id"]
        
        # Set default message if not provided
        if "message" not in data or data["message"] is None:
            data["message"] = f"Data added successfully. Status: {data.get('status', 'unknown')}"
        
        super().__init__(**data)


class DeleteResult(BaseModel):
    """Result model for delete operation."""

    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")


class CognifyResult(BaseModel):
    """Result model for cognify operation."""

    pipeline_run_id: UUID = Field(..., description="Pipeline run ID")
    status: str = Field(..., description="Pipeline status")
    entity_count: int | None = Field(None, description="Number of entities extracted")
    duration: float | None = Field(None, description="Processing duration in seconds")
    message: str | None = Field(None, description="Status message")


class MemifyResult(BaseModel):
    """Result model for memify operation."""

    pipeline_run_id: UUID = Field(..., description="Pipeline run ID")
    status: str = Field(..., description="Pipeline status")
    message: str | None = Field(None, description="Status message")


class UpdateResult(BaseModel):
    """Result model for update operation."""

    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    data_id: UUID | None = Field(None, description="Updated data ID")


class SearchResult(BaseModel):
    """Search result model.

    Note: The actual structure may vary based on search_type.
    This is a base model that can be extended.
    """

    # Common fields that appear in most search results
    id: str | None = Field(None, description="Result ID")
    text: str | None = Field(None, description="Result text content")
    score: float | None = Field(None, description="Relevance score")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    # Allow additional fields
    model_config = ConfigDict(extra="allow")


class CombinedSearchResult(BaseModel):
    """Combined search result model."""

    result: str = Field(..., description="Combined result text")
    context: list[str] | None = Field(None, description="Context chunks")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class SearchHistoryItem(BaseModel):
    """Search history item model."""

    id: UUID = Field(..., description="Search history ID")
    text: str = Field(..., description="Search query text")
    user: str = Field(..., description="User who performed the search")
    created_at: datetime = Field(..., description="Search timestamp")


class GraphNode(BaseModel):
    """Graph node model."""

    id: UUID = Field(..., description="Node ID")
    label: str = Field(..., description="Node label")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphEdge(BaseModel):
    """Graph edge model."""

    source: UUID = Field(..., description="Source node ID")
    target: UUID = Field(..., description="Target node ID")
    label: str = Field(..., description="Edge label")


class GraphData(BaseModel):
    """Graph data model."""

    nodes: list[GraphNode] = Field(..., description="List of graph nodes")
    edges: list[GraphEdge] = Field(..., description="List of graph edges")


class SyncResult(BaseModel):
    """Result model for sync operation."""

    run_id: str = Field(..., description="Sync operation run ID")
    status: str = Field(..., description="Sync status")
    dataset_ids: list[UUID] = Field(..., description="Dataset IDs being synced")
    dataset_names: list[str] = Field(..., description="Dataset names being synced")
    message: str = Field(..., description="Status message")
    timestamp: datetime | None = Field(None, description="Sync initiation timestamp")
    user_id: UUID | None = Field(None, description="User ID who initiated sync")


class SyncStatus(BaseModel):
    """Sync status model."""

    has_running_sync: bool = Field(..., description="Whether there are running syncs")
    running_sync_count: int = Field(..., description="Number of running sync operations")
    latest_running_sync: dict[str, Any] | None = Field(
        None, description="Information about the latest running sync"
    )


class HealthStatus(BaseModel):
    """Health check status model."""

    status: str = Field(..., description="Health status")
    version: str | None = Field(None, description="API version")
