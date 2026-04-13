"""用户画像模型测试"""

import pytest
from cozymemory.models.profile import (
    ProfileInsertRequest,
    ProfileFlushRequest,
    ProfileContextRequest,
    ProfileTopic,
    UserProfile,
    ProfileContext,
    ProfileInsertResponse,
)
from cozymemory.models.common import Message


def test_profile_insert_request():
    req = ProfileInsertRequest(
        user_id="user_123",
        messages=[Message(role="user", content="我叫小明")],
    )
    assert req.sync is False


def test_profile_flush_request():
    req = ProfileFlushRequest(user_id="user_123", sync=True)
    assert req.sync is True


def test_profile_context_request():
    req = ProfileContextRequest(user_id="user_123", max_token_size=500)
    assert req.max_token_size == 500
    assert req.chats is None


def test_profile_context_request_token_range():
    with pytest.raises(Exception):
        ProfileContextRequest(user_id="user_123", max_token_size=50)
    with pytest.raises(Exception):
        ProfileContextRequest(user_id="user_123", max_token_size=5001)


def test_profile_topic():
    topic = ProfileTopic(id="prof_123", topic="basic_info", sub_topic="name", content="小明")
    assert topic.topic == "basic_info"
    assert topic.sub_topic == "name"


def test_user_profile():
    profile = UserProfile(
        user_id="user_123",
        topics=[ProfileTopic(id="p1", topic="basic_info", sub_topic="name", content="小明")],
    )
    assert len(profile.topics) == 1


def test_profile_context():
    ctx = ProfileContext(user_id="user_123", context="# Memory\n用户背景...")
    assert "用户背景" in ctx.context


def test_profile_insert_response():
    resp = ProfileInsertResponse(user_id="user_123", blob_id="blob_123")
    assert resp.success is True
    assert resp.blob_id == "blob_123"