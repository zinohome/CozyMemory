"""BackupService 测试

覆盖：export_user 组装 bundle、import_bundle 的三类数据回写、
失败单条不中断整体、dataset dump 从 graph 抽 DocumentChunk.text。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cozymemory.clients.base import EngineError
from cozymemory.models.backup import DatasetDump, MemoryBundle
from cozymemory.models.conversation import (
    ConversationMemory,
    ConversationMemoryListResponse,
)
from cozymemory.models.knowledge import (
    DatasetGraphResponse,
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeDataset,
    KnowledgeDatasetListResponse,
)
from cozymemory.models.profile import (
    ProfileGetResponse,
    ProfileTopic,
    UserProfile,
)
from cozymemory.services.backup import BackupService

# ───────────────────────── 测试用 fixtures ─────────────────────────


def _make_profile_resp(topics: list[ProfileTopic]) -> ProfileGetResponse:
    return ProfileGetResponse(
        success=True,
        data=UserProfile(user_id="u1", topics=topics),
    )


@pytest.fixture
def services():
    """三个互相独立的 service mock，每个都 AsyncMock；按需在测试里改返回值。"""
    conv = MagicMock()
    conv.get_all = AsyncMock(
        return_value=ConversationMemoryListResponse(
            success=True,
            data=[ConversationMemory(id="m1", user_id="u1", content="用户爱科幻")],
            total=1,
        )
    )
    conv.add = AsyncMock(return_value=None)

    prof = MagicMock()
    prof.get_profile = AsyncMock(
        return_value=_make_profile_resp(
            [ProfileTopic(id="t1", topic="interest", sub_topic="hobby", content="sci-fi")]
        )
    )
    prof.add_profile_item = AsyncMock(return_value=None)

    know = MagicMock()
    know.list_datasets = AsyncMock(
        return_value=KnowledgeDatasetListResponse(
            success=True, data=[KnowledgeDataset(id="ds1", name="my-ds")]
        )
    )
    know.get_dataset_graph = AsyncMock(
        return_value=DatasetGraphResponse(
            dataset_id="ds1",
            data={
                "nodes": [
                    {
                        "type": "DocumentChunk",
                        "properties": {"text": "chunk-one"},
                    },
                    {
                        "type": "DocumentChunk",
                        "properties": {"text": "chunk-two"},
                    },
                    {
                        # 其它类型节点应被忽略
                        "type": "Entity",
                        "properties": {"text": "should-skip"},
                    },
                    {
                        # 空 text 忽略
                        "type": "DocumentChunk",
                        "properties": {"text": "  "},
                    },
                ]
            },
        )
    )
    know.create_dataset = AsyncMock(return_value=None)
    know.add = AsyncMock(
        return_value=KnowledgeAddResponse(success=True, data_id="d1")
    )
    know.cognify = AsyncMock(
        return_value=KnowledgeCognifyResponse(
            success=True, pipeline_run_id="run-1"
        )
    )
    return conv, prof, know


@pytest.fixture
def backup_service(services):
    conv, prof, know = services
    return BackupService(conv, prof, know)


# ───────────────────────── export_user ─────────────────────────


@pytest.mark.asyncio
async def test_export_user_basic_without_datasets(backup_service, services):
    bundle = await backup_service.export_user("u1")
    assert bundle.user_id == "u1"
    assert len(bundle.conversations) == 1
    assert bundle.conversations[0].content == "用户爱科幻"
    assert len(bundle.profile_topics) == 1
    assert bundle.profile_topics[0].sub_topic == "hobby"
    assert bundle.datasets == []
    conv, prof, know = services
    conv.get_all.assert_awaited_once_with(user_id="u1", limit=1000)
    prof.get_profile.assert_awaited_once_with(user_id="u1")
    know.get_dataset_graph.assert_not_called()


@pytest.mark.asyncio
async def test_export_user_with_dataset_dump(backup_service, services):
    bundle = await backup_service.export_user("u1", dataset_ids=["ds1"])
    assert len(bundle.datasets) == 1
    dump = bundle.datasets[0]
    assert dump.name == "my-ds"
    # 只含 DocumentChunk 且 text 非空
    assert dump.documents == ["chunk-one", "chunk-two"]


@pytest.mark.asyncio
async def test_export_user_skips_dataset_when_name_missing(backup_service, services):
    _, _, know = services
    # list_datasets 返回空 → 找不到 name → dump 应返回 None
    know.list_datasets.return_value = KnowledgeDatasetListResponse(success=True, data=[])
    bundle = await backup_service.export_user("u1", dataset_ids=["ds1"])
    assert bundle.datasets == []


@pytest.mark.asyncio
async def test_export_user_dataset_graph_engine_error_ignored(
    backup_service, services
):
    _, _, know = services
    know.get_dataset_graph.side_effect = EngineError(
        engine="Cognee", message="down", status_code=502
    )
    bundle = await backup_service.export_user("u1", dataset_ids=["ds1"])
    assert bundle.datasets == []


@pytest.mark.asyncio
async def test_export_user_dataset_with_malformed_graph(
    backup_service, services
):
    _, _, know = services
    # data 不是 dict → 早退，datasets 空
    know.get_dataset_graph.return_value = DatasetGraphResponse(
        dataset_id="ds1", data="not-a-dict"
    )
    bundle = await backup_service.export_user("u1", dataset_ids=["ds1"])
    assert bundle.datasets == []


@pytest.mark.asyncio
async def test_export_user_no_profile_data(backup_service, services):
    _, prof, _ = services
    prof.get_profile.return_value = ProfileGetResponse(success=True, data=None)
    bundle = await backup_service.export_user("u1")
    assert bundle.profile_topics == []


# ───────────────────────── import_bundle ─────────────────────────


def _make_bundle(
    conversations=None,
    topics=None,
    datasets=None,
    user_id="u1",
) -> MemoryBundle:
    return MemoryBundle(
        exported_at=datetime.now(UTC),
        user_id=user_id,
        conversations=conversations or [],
        profile_topics=topics or [],
        datasets=datasets or [],
    )


@pytest.mark.asyncio
async def test_import_bundle_target_user_id_override(backup_service, services):
    conv, prof, _ = services
    bundle = _make_bundle(
        conversations=[ConversationMemory(id="m1", user_id="u1", content="fact1")],
    )
    resp = await backup_service.import_bundle(bundle, target_user_id="other")
    assert resp.user_id == "other"
    # add 调用的 user_id 应该是 "other" 而不是 bundle.user_id
    conv.add.assert_awaited_once()
    kwargs = conv.add.await_args.kwargs
    assert kwargs["user_id"] == "other"


@pytest.mark.asyncio
async def test_import_bundle_uses_bundle_user_id_when_no_override(
    backup_service, services
):
    conv, _, _ = services
    bundle = _make_bundle(conversations=[ConversationMemory(id="m1", user_id="u1", content="x")])
    resp = await backup_service.import_bundle(bundle)
    assert resp.user_id == "u1"


@pytest.mark.asyncio
async def test_import_bundle_skips_empty_conversation(backup_service, services):
    conv, _, _ = services
    bundle = _make_bundle(
        conversations=[
            ConversationMemory(id="m-empty", user_id="u1", content="   "),
            ConversationMemory(id="m-ok", user_id="u1", content="real"),
        ]
    )
    resp = await backup_service.import_bundle(bundle)
    assert resp.conversations_imported == 1
    assert resp.conversations_skipped == 1
    conv.add.assert_awaited_once()  # 只调了一次


@pytest.mark.asyncio
async def test_import_bundle_conversation_engine_error_records(
    backup_service, services
):
    conv, _, _ = services
    conv.add.side_effect = EngineError(engine="Mem0", message="boom", status_code=502)
    bundle = _make_bundle(conversations=[ConversationMemory(id="m1", user_id="u1", content="x")])
    resp = await backup_service.import_bundle(bundle)
    assert resp.conversations_imported == 0
    assert resp.conversations_skipped == 1
    assert resp.errors[0]["kind"] == "conversation"
    assert resp.errors[0]["id"] == "m1"


@pytest.mark.asyncio
async def test_import_bundle_profile_engine_error_records(
    backup_service, services
):
    _, prof, _ = services
    prof.add_profile_item.side_effect = EngineError(
        engine="Memobase", message="nope", status_code=400
    )
    bundle = _make_bundle(
        topics=[
            ProfileTopic(id="t1", topic="a", sub_topic="b", content="c"),
        ]
    )
    resp = await backup_service.import_bundle(bundle)
    assert resp.profiles_imported == 0
    assert resp.profiles_skipped == 1
    assert resp.errors[0]["kind"] == "profile"


@pytest.mark.asyncio
async def test_import_bundle_dataset_full_flow(backup_service, services):
    _, _, know = services
    bundle = _make_bundle(
        datasets=[
            DatasetDump(name="my-ds", documents=["doc1", "doc2", "   "]),
        ]
    )
    resp = await backup_service.import_bundle(bundle)
    # 两个非空 doc + 一个空白 skip
    assert resp.documents_imported == 2
    assert resp.datasets_imported == 1
    # create_dataset + 2x add + cognify
    know.create_dataset.assert_awaited_once_with(name="my-ds")
    assert know.add.await_count == 2
    know.cognify.assert_awaited_once_with(
        datasets=["my-ds"], run_in_background=True
    )


@pytest.mark.asyncio
async def test_import_bundle_dataset_empty_docs_skipped(backup_service, services):
    _, _, know = services
    bundle = _make_bundle(
        datasets=[DatasetDump(name="empty-ds", documents=["   "])],
    )
    resp = await backup_service.import_bundle(bundle)
    assert resp.datasets_imported == 0
    assert resp.datasets_skipped == 1
    know.cognify.assert_not_called()


@pytest.mark.asyncio
async def test_import_bundle_dataset_create_failure_ignored(
    backup_service, services
):
    """create_dataset 失败（例如已存在）时仍继续 add"""
    _, _, know = services
    know.create_dataset.side_effect = EngineError(
        engine="Cognee", message="already exists", status_code=409
    )
    bundle = _make_bundle(
        datasets=[DatasetDump(name="exists", documents=["d1"])],
    )
    resp = await backup_service.import_bundle(bundle)
    assert resp.datasets_imported == 1  # 仍算成功
    assert resp.documents_imported == 1


@pytest.mark.asyncio
async def test_import_bundle_dataset_add_failure_records_error(
    backup_service, services
):
    _, _, know = services
    know.add.side_effect = EngineError(
        engine="Cognee", message="add-fail", status_code=502
    )
    bundle = _make_bundle(
        datasets=[DatasetDump(name="ds1", documents=["x"])],
    )
    resp = await backup_service.import_bundle(bundle)
    assert resp.datasets_imported == 0
    assert resp.datasets_skipped == 1
    assert any(e["kind"] == "dataset_doc" for e in resp.errors)


@pytest.mark.asyncio
async def test_import_bundle_cognify_failure_records_error(
    backup_service, services
):
    _, _, know = services
    know.cognify.side_effect = EngineError(
        engine="Cognee", message="cog-fail", status_code=502
    )
    bundle = _make_bundle(
        datasets=[DatasetDump(name="ds1", documents=["x"])],
    )
    resp = await backup_service.import_bundle(bundle)
    # 文档仍成功 import，但 cognify 失败进 errors
    assert resp.documents_imported == 1
    assert any(e["kind"] == "cognify" for e in resp.errors)
