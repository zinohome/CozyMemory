"""通用数据模型测试"""

import pytest

from cozymemory.models.common import EngineStatus, ErrorResponse, HealthResponse, Message


def test_message_creation():
    msg = Message(role="user", content="你好")
    assert msg.role == "user"
    assert msg.content == "你好"
    assert msg.created_at is None


def test_message_with_timestamp():
    msg = Message(role="assistant", content="你好！", created_at="2026-04-13T10:00:00Z")
    assert msg.created_at == "2026-04-13T10:00:00Z"


def test_message_validation_error():
    with pytest.raises(Exception):
        Message(role="user")


def test_engine_status_healthy():
    status = EngineStatus(name="Mem0", status="healthy", latency_ms=12.5)
    assert status.name == "Mem0"
    assert status.status == "healthy"
    assert status.error is None


def test_engine_status_unhealthy():
    status = EngineStatus(name="Cognee", status="unhealthy", error="连接超时")
    assert status.status == "unhealthy"
    assert status.error == "连接超时"


def test_health_response():
    resp = HealthResponse(
        status="healthy",
        engines={"mem0": EngineStatus(name="Mem0", status="healthy", latency_ms=10.0)},
    )
    assert resp.status == "healthy"
    assert "mem0" in resp.engines
    assert resp.timestamp is not None


def test_health_response_degraded():
    resp = HealthResponse(
        status="degraded",
        engines={
            "mem0": EngineStatus(name="Mem0", status="healthy"),
            "cognee": EngineStatus(name="Cognee", status="unhealthy", error="超时"),
        },
    )
    assert resp.status == "degraded"


def test_error_response():
    err = ErrorResponse(error="EngineError", detail="Mem0 不可用", engine="mem0")
    assert err.success is False
    assert err.error == "EngineError"
    assert err.engine == "mem0"
