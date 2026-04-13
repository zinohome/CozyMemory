"""知识库模型测试"""

import pytest
from cozymemory.models.knowledge import (
    KnowledgeAddRequest,
    KnowledgeCognifyRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeDataset,
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeSearchResponse,
    KnowledgeDatasetListResponse,
)


def test_knowledge_add_request():
    req = KnowledgeAddRequest(data="文本内容", dataset="my-dataset")
    assert req.node_set is None


def test_knowledge_add_request_validation():
    with pytest.raises(Exception):
        KnowledgeAddRequest(data="", dataset="my-dataset")


def test_knowledge_cognify_request():
    req = KnowledgeCognifyRequest()
    assert req.datasets is None
    assert req.run_in_background is True


def test_knowledge_search_request():
    req = KnowledgeSearchRequest(query="Cognee 是什么？")
    assert req.search_type == "GRAPH_COMPLETION"
    assert req.top_k == 10


def test_knowledge_search_result():
    result = KnowledgeSearchResult(id="node_1", text="内容", score=0.95, extra_field="value")
    assert result.id == "node_1"


def test_knowledge_dataset():
    ds = KnowledgeDataset(id="uuid-123", name="my-dataset")
    assert ds.name == "my-dataset"


def test_knowledge_add_response():
    resp = KnowledgeAddResponse(data_id="data_123", dataset_name="my-dataset")
    assert resp.success is True


def test_knowledge_cognify_response():
    resp = KnowledgeCognifyResponse(pipeline_run_id="pipe_123", status="pending")
    assert resp.status == "pending"


def test_knowledge_search_response():
    resp = KnowledgeSearchResponse(
        data=[KnowledgeSearchResult(id="1", text="结果")],
        total=1,
    )
    assert resp.total == 1


def test_knowledge_dataset_list_response():
    resp = KnowledgeDatasetListResponse(
        data=[KnowledgeDataset(id="1", name="ds1")],
    )
    assert resp.success is True