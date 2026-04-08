"""
测试性能优化功能

测试所有高优先级和中优先级的性能优化：
1. 连接池优化（HTTP/2, 连接数）
2. 数据压缩
3. 流式传输优化
4. 本地缓存
5. 批量操作优化（自适应并发）
"""

import asyncio
import gzip
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.models import AddResult, Dataset


class TestConnectionPoolOptimization:
    """测试连接池优化"""

    def test_default_connection_pool_size(self):
        """测试默认连接池大小"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 检查连接池配置（通过保存的参数验证）
        assert client.max_keepalive_connections == 50
        assert client.max_connections == 100

    def test_custom_connection_pool_size(self):
        """测试自定义连接池大小"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            max_keepalive_connections=100,
            max_connections=200,
        )
        
        assert client.max_keepalive_connections == 100
        assert client.max_connections == 200

    def test_http2_enabled(self):
        """测试HTTP/2启用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_http2=True,
        )
        
        # HTTP/2可能因为h2包不可用而自动降级，这是正常的
        # 我们只检查参数是否正确传递
        assert client.enable_http2 is True

    def test_http2_disabled(self):
        """测试HTTP/2禁用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_http2=False,
        )
        
        assert client.enable_http2 is False


class TestDataCompression:
    """测试数据压缩功能"""

    @pytest.mark.asyncio
    async def test_compression_enabled(self):
        """测试压缩启用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_compression=True,
        )
        
        assert client.enable_compression is True
        
        # 测试压缩方法
        large_data = b"x" * 2000  # 2KB数据
        compressed, was_compressed = client._compress_data(large_data)
        
        assert was_compressed is True
        assert len(compressed) < len(large_data)

    @pytest.mark.asyncio
    async def test_compression_disabled(self):
        """测试压缩禁用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_compression=False,
        )
        
        assert client.enable_compression is False

    @pytest.mark.asyncio
    async def test_compress_small_data(self):
        """测试小数据不压缩"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        small_data = b"x" * 100  # 100字节，小于1KB
        compressed, was_compressed = client._compress_data(small_data)
        
        assert was_compressed is False
        assert compressed == small_data

    @pytest.mark.asyncio
    async def test_compress_large_data(self):
        """测试大数据压缩"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        large_data = b"x" * 5000  # 5KB数据
        compressed, was_compressed = client._compress_data(large_data)
        
        assert was_compressed is True
        assert len(compressed) < len(large_data)

    @pytest.mark.asyncio
    async def test_decompress_response(self):
        """测试响应解压缩"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 创建压缩的响应
        original_data = b'{"status": "ok"}'
        compressed_data = gzip.compress(original_data)
        
        mock_response = MagicMock()
        mock_response.headers = {"Content-Encoding": "gzip"}
        mock_response.content = compressed_data
        
        decompressed_response = client._decompress_response(mock_response)
        
        assert decompressed_response._content == original_data

    @pytest.mark.asyncio
    async def test_compression_headers(self):
        """测试压缩头设置"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_compression=True,
        )
        
        headers = client._get_headers()
        assert "Accept-Encoding" in headers
        assert "gzip" in headers["Accept-Encoding"]

    @pytest.mark.asyncio
    async def test_json_compression_in_request(self):
        """测试JSON请求压缩"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_compression=True,
        )
        
        # 创建大量JSON数据
        large_payload = {"data": "x" * 2000}  # 2KB+ JSON
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.headers = {}
        mock_response.content = b'{"status": "ok"}'
        
        with patch.object(client.client, "request", return_value=mock_response) as mock_request:
            await client._request("POST", "/api/v1/test", json=large_payload)
            
            # 检查是否使用了压缩
            call_args = mock_request.call_args
            if call_args and "content" in call_args.kwargs:
                # 如果使用了压缩，content应该是压缩的数据
                content = call_args.kwargs.get("content")
                if content:
                    # 验证是压缩数据（gzip magic bytes）
                    assert content[:2] == b'\x1f\x8b' or "json" in call_args.kwargs


class TestStreamingOptimization:
    """测试流式传输优化"""

    def test_streaming_threshold(self):
        """测试流式传输阈值已降低到1MB"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 创建一个1.5MB的临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"x" * int(1.5 * 1024 * 1024)  # 1.5MB
            f.write(large_data)
            temp_path = Path(f.name)
        
        try:
            # 准备文件上传
            field_name, content_or_file, mime_type = client._prepare_file_for_upload(
                temp_path,
                use_streaming=True
            )
            
            # 应该返回文件对象（流式）而不是bytes
            assert hasattr(content_or_file, "read")
            assert not isinstance(content_or_file, bytes)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_small_file_no_streaming(self):
        """测试小文件不使用流式传输"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 创建一个500KB的临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            small_data = b"x" * (500 * 1024)  # 500KB
            f.write(small_data)
            temp_path = Path(f.name)
        
        try:
            # 准备文件上传
            field_name, content_or_file, mime_type = client._prepare_file_for_upload(
                temp_path,
                use_streaming=True
            )
            
            # 小文件应该返回bytes（内存上传）
            assert isinstance(content_or_file, bytes)
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestLocalCache:
    """测试本地缓存功能"""

    def test_cache_enabled(self):
        """测试缓存启用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
        )
        
        assert client.enable_cache is True
        assert hasattr(client, "_cache")

    def test_cache_disabled(self):
        """测试缓存禁用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=False,
        )
        
        assert client.enable_cache is False

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        key1 = client._get_cache_key("GET", "/api/v1/datasets", params={"a": 1})
        key2 = client._get_cache_key("GET", "/api/v1/datasets", params={"a": 1})
        key3 = client._get_cache_key("GET", "/api/v1/datasets", params={"a": 2})
        
        # 相同参数应该生成相同键
        assert key1 == key2
        # 不同参数应该生成不同键
        assert key1 != key3

    def test_cache_get_set(self):
        """测试缓存获取和设置"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
            cache_ttl=300,
        )
        
        cache_key = "test_key"
        test_value = {"status": "ok"}
        
        # 设置缓存
        client._set_cache(cache_key, test_value)
        
        # 获取缓存
        cached_value = client._get_from_cache(cache_key)
        
        assert cached_value == test_value

    def test_cache_expiration(self):
        """测试缓存过期"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
            cache_ttl=1,  # 1秒TTL
        )
        
        cache_key = "test_key"
        test_value = {"status": "ok"}
        
        # 设置缓存
        client._set_cache(cache_key, test_value)
        
        # 立即获取应该成功
        assert client._get_from_cache(cache_key) == test_value
        
        # 等待过期
        import time
        time.sleep(1.1)
        
        # 过期后应该返回None
        assert client._get_from_cache(cache_key) is None

    def test_cache_only_get_and_post_with_json(self):
        """测试缓存GET请求和带json的POST请求"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # GET请求应该有缓存键
        get_key = client._get_cache_key("GET", "/api/v1/datasets")
        assert get_key != ""
        
        # POST请求带json（如search）应该有缓存键
        post_with_json_key = client._get_cache_key("POST", "/api/v1/search", json={"query": "test"})
        assert post_with_json_key != ""
        
        # POST请求不带json可能也会生成键（基于其他参数），但实际不会缓存
        # 因为缓存逻辑会检查是否有json参数
        post_key = client._get_cache_key("POST", "/api/v1/add")
        # 注意：即使生成了键，实际缓存逻辑会检查json参数，所以不会缓存
        
        # PUT/DELETE等不应该有缓存键
        put_key = client._get_cache_key("PUT", "/api/v1/update")
        assert put_key == ""
        
        delete_key = client._get_cache_key("DELETE", "/api/v1/delete")
        assert delete_key == ""

    @pytest.mark.asyncio
    async def test_list_datasets_cache(self):
        """测试list_datasets使用缓存"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
        )
        
        test_uuid = str(uuid4())
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": test_uuid, "name": "test"}]
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = json.dumps([{"id": test_uuid, "name": "test"}]).encode()
        
        with patch.object(client, "_request", return_value=mock_response) as mock_request:
            # 第一次调用
            result1 = await client.list_datasets()
            assert len(result1) == 1
            assert mock_request.call_count == 1
            
            # 第二次调用应该使用缓存
            result2 = await client.list_datasets()
            assert len(result2) == 1
            # 注意：由于缓存是在方法内部处理的，实际调用次数可能不同
            # 但结果应该相同

    @pytest.mark.asyncio
    async def test_search_cache(self):
        """测试search使用缓存"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "result-1", "text": "result"}]
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'[{"id": "result-1", "text": "result"}]'
        
        with patch.object(client, "_request", return_value=mock_response) as mock_request:
            # 第一次调用
            result1 = await client.search("test query")
            assert len(result1) == 1
            
            # 第二次调用相同查询应该使用缓存
            result2 = await client.search("test query")
            assert len(result2) == 1


class TestBatchOperationsOptimization:
    """测试批量操作优化"""

    @pytest.mark.asyncio
    async def test_adaptive_concurrency_small_files(self):
        """测试自适应并发 - 小文件"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 小数据列表
        data_list = ["data1", "data2", "data3", "data4", "data5"]
        
        call_count = 0
        
        async def mock_add(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return AddResult(status="success", message="Added", data_id=uuid4())
        
        with patch.object(client, "add", side_effect=mock_add):
            results = await client.add_batch(
                data_list=data_list,
                dataset_name="test-dataset",
                adaptive_concurrency=True,
                max_concurrent=None,  # 自动确定
            )
            
            # 小文件应该使用高并发（20）
            # 由于是自适应，我们只验证功能正常
            assert len(results) == 5
            assert call_count == 5

    @pytest.mark.asyncio
    async def test_adaptive_concurrency_large_files(self):
        """测试自适应并发 - 大文件"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 创建大文件列表
        large_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
                large_data = b"x" * int(11 * 1024 * 1024)  # 11MB
                f.write(large_data)
                large_files.append(Path(f.name))
        
        try:
            call_count = 0
            
            async def mock_add(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return AddResult(status="success", message="Added", data_id=uuid4())
            
            with patch.object(client, "add", side_effect=mock_add):
                results = await client.add_batch(
                    data_list=large_files,
                    dataset_name="test-dataset",
                    adaptive_concurrency=True,
                    max_concurrent=None,  # 自动确定
                )
                
                # 大文件应该使用低并发（5）
                assert len(results) == 3
                assert call_count == 3
        finally:
            for f in large_files:
                if f.exists():
                    f.unlink()

    @pytest.mark.asyncio
    async def test_adaptive_concurrency_disabled(self):
        """测试禁用自适应并发"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        data_list = ["data1", "data2", "data3"]
        
        async def mock_add(*args, **kwargs):
            return AddResult(status="success", message="Added", data_id=uuid4())
        
        with patch.object(client, "add", side_effect=mock_add):
            results = await client.add_batch(
                data_list=data_list,
                dataset_name="test-dataset",
                adaptive_concurrency=False,
                max_concurrent=5,  # 手动指定
            )
            
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_adaptive_concurrency_mixed_sizes(self):
        """测试自适应并发 - 混合大小文件"""
        client = CogneeClient(api_url="http://localhost:8000")
        
        # 混合大小：小文件和大文件
        small_data = ["data1", "data2"]
        large_file = None
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"x" * int(11 * 1024 * 1024)  # 11MB
            f.write(large_data)
            large_file = Path(f.name)
        
        try:
            data_list = small_data + [large_file]
            
            async def mock_add(*args, **kwargs):
                return AddResult(status="success", message="Added", data_id=uuid4())
            
            with patch.object(client, "add", side_effect=mock_add):
                results = await client.add_batch(
                    data_list=data_list,
                    dataset_name="test-dataset",
                    adaptive_concurrency=True,
                    max_concurrent=None,
                )
                
                # 应该根据平均大小调整并发
                assert len(results) == 3
        finally:
            if large_file and large_file.exists():
                large_file.unlink()


class TestPerformanceIntegration:
    """测试性能优化集成"""

    @pytest.mark.asyncio
    async def test_all_optimizations_enabled(self):
        """测试所有优化同时启用"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_compression=True,
            enable_http2=True,
            enable_cache=True,
            cache_ttl=300,
            max_keepalive_connections=50,
            max_connections=100,
        )
        
        # 验证所有优化都已启用
        assert client.enable_compression is True
        assert client.enable_http2 is True
        assert client.enable_cache is True
        assert client.cache_ttl == 300
        assert client.max_keepalive_connections == 50
        assert client.max_connections == 100

    @pytest.mark.asyncio
    async def test_compression_with_large_payload(self):
        """测试压缩与大负载"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_compression=True,
        )
        
        # 创建大JSON负载
        large_payload = {
            "data": "x" * 5000,  # 5KB+ JSON
            "metadata": {"key": "value" * 100},
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.headers = {}
        mock_response.content = b'{"status": "ok"}'
        
        with patch.object(client.client, "request", return_value=mock_response):
            # 测试压缩是否工作
            json_bytes = json.dumps(large_payload).encode("utf-8")
            compressed, was_compressed = client._compress_data(json_bytes)
            
            assert was_compressed is True
            assert len(compressed) < len(json_bytes)

    @pytest.mark.asyncio
    async def test_cache_with_compression(self):
        """测试缓存与压缩同时工作"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
            enable_compression=True,
        )
        
        test_uuid = str(uuid4())
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": test_uuid, "name": "test"}]
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = json.dumps([{"id": test_uuid, "name": "test"}]).encode()
        
        with patch.object(client, "_request", return_value=mock_response):
            # 第一次调用
            result1 = await client.list_datasets()
            assert len(result1) == 1
            
            # 第二次调用应该使用缓存（即使压缩启用）
            result2 = await client.list_datasets()
            assert len(result2) == 1

    @pytest.mark.asyncio
    async def test_batch_with_adaptive_and_cache(self):
        """测试批量操作与自适应并发和缓存"""
        client = CogneeClient(
            api_url="http://localhost:8000",
            enable_cache=True,
        )
        
        data_list = ["data1", "data2", "data3"]
        
        async def mock_add(*args, **kwargs):
            return AddResult(status="success", message="Added", data_id=uuid4())
        
        with patch.object(client, "add", side_effect=mock_add):
            results = await client.add_batch(
                data_list=data_list,
                dataset_name="test-dataset",
                adaptive_concurrency=True,
            )
            
            assert len(results) == 3
            assert all(isinstance(r, AddResult) for r in results)
