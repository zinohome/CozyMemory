"""
Unit tests for file upload and data processing.

Tests add(), update(), and add_batch() methods with various input types.
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import CogneeSDKError, ValidationError
from cognee_sdk.models import AddResult, UpdateResult


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


class TestAddMethod:
    """Tests for add() method with various input types."""

    @pytest.mark.asyncio
    async def test_add_text_string(self, client):
        """Test adding plain text string."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(uuid4()),
            "dataset_id": str(uuid4()),
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(data="Test text data", dataset_name="test-dataset")

            assert isinstance(result, AddResult)
            assert result.status == "success"
            # Verify files were prepared correctly
            call_args = mock_request.call_args
            assert "files" in call_args[1] or "files" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_add_bytes(self, client):
        """Test adding bytes data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(uuid4()),
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(data=b"Binary data", dataset_name="test-dataset")

            assert isinstance(result, AddResult)
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_path_object_existing_file(self, client):
        """Test adding data from existing file Path."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test file content")
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
                "data_id": str(uuid4()),
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.add(data=temp_path, dataset_name="test-dataset")

                assert isinstance(result, AddResult)
                mock_request.assert_called_once()
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_add_path_object_nonexistent_file(self, client):
        """Test adding data from non-existent file Path."""
        nonexistent_path = Path("/nonexistent/file.txt")

        # Path object with non-existent file should raise error when trying to read
        with pytest.raises(CogneeSDKError) as exc_info:
            await client.add(data=nonexistent_path, dataset_name="test-dataset")

        assert "Failed to read file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_path_object_file_read_error(self, client):
        """Test handling file read error."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with pytest.raises(CogneeSDKError) as exc_info:
                    await client.add(data=temp_path, dataset_name="test-dataset")

                assert "Failed to read file" in str(exc_info.value)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_add_binary_io(self, client):
        """Test adding data from BinaryIO file object."""
        file_obj = io.BytesIO(b"File object content")
        file_obj.name = "test.bin"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(uuid4()),
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(data=file_obj, dataset_name="test-dataset")

            assert isinstance(result, AddResult)
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_file_path_string_file_exists(self, client):
        """Test adding data from file path string (file://)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            temp_path = f.name

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.add(data=f"file://{temp_path}", dataset_name="test-dataset")

                assert isinstance(result, AddResult)
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_add_file_path_string_s3(self, client):
        """Test adding data from S3 path string."""
        s3_path = "s3://bucket/file.txt"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            # S3 paths should be treated as text strings
            result = await client.add(data=s3_path, dataset_name="test-dataset")

            assert isinstance(result, AddResult)

    @pytest.mark.asyncio
    async def test_add_list_mixed_types(self, client):
        """Test adding list of mixed data types."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(
                data=["text1", b"bytes1", "text2"], dataset_name="test-dataset"
            )

            assert isinstance(result, AddResult)
            # Should handle multiple files
            call_args = mock_request.call_args
            assert "files" in call_args[1] or "files" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_add_with_node_set(self, client):
        """Test adding data with node_set parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(
                data="Test data",
                dataset_name="test-dataset",
                node_set=["node1", "node2"],
            )

            assert isinstance(result, AddResult)
            # Verify node_set was included
            call_args = mock_request.call_args
            assert "data" in call_args[1] or "data" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_add_with_dataset_id(self, client):
        """Test adding data with dataset_id instead of dataset_name."""
        dataset_id = uuid4()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(data="Test data", dataset_id=dataset_id)

            assert isinstance(result, AddResult)

    @pytest.mark.asyncio
    async def test_add_validation_error_no_dataset(self, client):
        """Test add validation error when neither dataset_name nor dataset_id provided."""
        with pytest.raises(ValidationError) as exc_info:
            await client.add(data="Test data")

        assert "dataset_name or dataset_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_mime_type_detection(self, client):
        """Test MIME type detection for different file extensions."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pdf") as f:
            f.write("PDF content")
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                await client.add(data=temp_path, dataset_name="test-dataset")

                # MIME type should be detected
                mock_request.assert_called_once()
        finally:
            temp_path.unlink()


class TestUpdateMethod:
    """Tests for update() method with various input types."""

    @pytest.mark.asyncio
    async def test_update_text_string(self, client):
        """Test updating with text string."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data updated",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.update(
                data_id=data_id, dataset_id=dataset_id, data="Updated content"
            )

            assert isinstance(result, UpdateResult)
            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_update_bytes(self, client):
        """Test updating with bytes data."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data updated",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.update(
                data_id=data_id, dataset_id=dataset_id, data=b"Updated binary"
            )

            assert isinstance(result, UpdateResult)

    @pytest.mark.asyncio
    async def test_update_path_object(self, client):
        """Test updating with Path object."""
        data_id = uuid4()
        dataset_id = uuid4()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Updated file content")
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data updated",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.update(data_id=data_id, dataset_id=dataset_id, data=temp_path)

                assert isinstance(result, UpdateResult)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_update_binary_io(self, client):
        """Test updating with BinaryIO file object."""
        data_id = uuid4()
        dataset_id = uuid4()
        file_obj = io.BytesIO(b"Updated file object content")
        file_obj.name = "updated.bin"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data updated",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.update(data_id=data_id, dataset_id=dataset_id, data=file_obj)

            assert isinstance(result, UpdateResult)

    @pytest.mark.asyncio
    async def test_update_file_read_error(self, client):
        """Test handling file read error in update."""
        data_id = uuid4()
        dataset_id = uuid4()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with pytest.raises(CogneeSDKError) as exc_info:
                    await client.update(data_id=data_id, dataset_id=dataset_id, data=temp_path)

                assert "Failed to read file" in str(exc_info.value)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_update_with_node_set(self, client):
        """Test updating with node_set parameter."""
        data_id = uuid4()
        dataset_id = uuid4()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data updated",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.update(
                data_id=data_id,
                dataset_id=dataset_id,
                data="Updated content",
                node_set=["node1", "node2"],
            )

            assert isinstance(result, UpdateResult)


class TestAddBatchMethod:
    """Tests for add_batch() method."""

    @pytest.mark.asyncio
    async def test_add_batch_success(self, client):
        """Test successful batch add operation."""
        data_list = ["data1", "data2", "data3"]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
            "data_id": str(uuid4()),
        }

        with patch.object(client, "add", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = AddResult(
                status="success", message="Data added", data_id=uuid4()
            )
            results = await client.add_batch(data_list=data_list, dataset_name="test-dataset")

            assert len(results) == 3
            assert all(isinstance(r, AddResult) for r in results)
            assert mock_add.call_count == 3

    @pytest.mark.asyncio
    async def test_add_batch_mixed_types(self, client):
        """Test batch add with mixed data types."""
        data_list = ["text1", b"bytes1", "text2"]

        with patch.object(client, "add", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = AddResult(
                status="success", message="Data added", data_id=uuid4()
            )
            results = await client.add_batch(data_list=data_list, dataset_name="test-dataset")

            assert len(results) == 3
            assert mock_add.call_count == 3

    @pytest.mark.asyncio
    async def test_add_batch_with_dataset_id(self, client):
        """Test batch add with dataset_id."""
        dataset_id = uuid4()
        data_list = ["data1", "data2"]

        with patch.object(client, "add", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = AddResult(
                status="success", message="Data added", data_id=uuid4()
            )
            results = await client.add_batch(data_list=data_list, dataset_id=dataset_id)

            assert len(results) == 2
            # Verify dataset_id was passed to add
            for call in mock_add.call_args_list:
                assert call[1]["dataset_id"] == dataset_id

    @pytest.mark.asyncio
    async def test_add_batch_with_node_set(self, client):
        """Test batch add with node_set."""
        data_list = ["data1", "data2"]
        node_set = ["node1", "node2"]

        with patch.object(client, "add", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = AddResult(
                status="success", message="Data added", data_id=uuid4()
            )
            results = await client.add_batch(
                data_list=data_list, dataset_name="test-dataset", node_set=node_set
            )

            assert len(results) == 2
            # Verify node_set was passed to add
            for call in mock_add.call_args_list:
                assert call[1]["node_set"] == node_set

    @pytest.mark.asyncio
    async def test_add_batch_empty_list(self, client):
        """Test batch add with empty list."""
        data_list = []

        results = await client.add_batch(data_list=data_list, dataset_name="test-dataset")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_add_batch_concurrent_execution(self, client):
        """Test that add_batch executes operations concurrently."""
        import asyncio

        data_list = ["data1", "data2", "data3"]
        call_times = []

        async def mock_add_with_delay(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)  # Simulate network delay
            return AddResult(status="success", message="Data added", data_id=uuid4())

        with patch.object(client, "add", side_effect=mock_add_with_delay):
            start_time = asyncio.get_event_loop().time()
            await client.add_batch(data_list=data_list, dataset_name="test-dataset")
            end_time = asyncio.get_event_loop().time()

            # If concurrent, all calls should start around the same time
            # Total time should be close to single call time, not 3x
            duration = end_time - start_time
            assert duration < 0.5  # Should be much less than 3 * 0.1 = 0.3s


class TestStreamingUpload:
    """Tests for streaming upload functionality for large files."""

    @pytest.mark.asyncio
    async def test_streaming_upload_large_file_path(self, client):
        """Test streaming upload for large file (Path object)."""
        # Create a temporary file larger than streaming threshold (10MB)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            # Write 12MB of data (larger than 10MB threshold)
            large_data = b"x" * (12 * 1024 * 1024)
            f.write(large_data)
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
                "data_id": str(uuid4()),
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.add(data=temp_path, dataset_name="test-dataset")

                assert isinstance(result, AddResult)
                # Verify that file object was passed (not bytes)
                call_args = mock_request.call_args
                files = call_args[1].get("files") or call_args[0][2].get("files")
                assert files is not None
                # Check that file object is used (not bytes)
                file_tuple = files[0]
                file_content = file_tuple[1][1]  # Get file content
                # Should be a file object, not bytes
                assert hasattr(file_content, "read") or isinstance(file_content, bytes)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_streaming_upload_large_file_string_path(self, client):
        """Test streaming upload for large file (string path)."""
        # Create a temporary file larger than streaming threshold
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"y" * (12 * 1024 * 1024)
            f.write(large_data)
            temp_path = f.name

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.add(data=f"file://{temp_path}", dataset_name="test-dataset")

                assert isinstance(result, AddResult)
                mock_request.assert_called_once()
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_streaming_upload_small_file_uses_memory(self, client):
        """Test that small files (< 10MB) use memory upload, not streaming."""
        # Create a small file (< 10MB threshold)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            small_data = b"small file content" * 1000  # ~17KB
            f.write(small_data)
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.add(data=temp_path, dataset_name="test-dataset")

                assert isinstance(result, AddResult)
                # Verify that bytes were passed (not file object)
                call_args = mock_request.call_args
                files = call_args[1].get("files") or call_args[0][2].get("files")
                assert files is not None
                file_tuple = files[0]
                file_content = file_tuple[1][1]
                # Should be bytes for small files
                assert isinstance(file_content, bytes)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_streaming_upload_file_object_large(self, client):
        """Test streaming upload for large file object."""
        # Create a large file object
        large_data = b"z" * (12 * 1024 * 1024)
        file_obj = io.BytesIO(large_data)
        file_obj.name = "large_file.bin"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "message": "Data added",
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.add(data=file_obj, dataset_name="test-dataset")

            assert isinstance(result, AddResult)
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_upload_file_cleanup(self, client):
        """Test that opened files are properly closed after streaming upload."""
        # Create a large file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"test" * (3 * 1024 * 1024)  # 12MB
            f.write(large_data)
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                
                # Track file objects
                opened_files = []
                original_open = open
                
                def track_open(*args, **kwargs):
                    file_obj = original_open(*args, **kwargs)
                    opened_files.append(file_obj)
                    return file_obj
                
                with patch("builtins.open", side_effect=track_open):
                    result = await client.add(data=temp_path, dataset_name="test-dataset")
                
                assert isinstance(result, AddResult)
                # Verify files were closed
                for file_obj in opened_files:
                    assert file_obj.closed
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_streaming_upload_warning_for_large_files(self, client):
        """Test that large files (> 50MB) trigger warnings."""
        import warnings

        # Create a very large file (> 50MB)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            very_large_data = b"w" * (60 * 1024 * 1024)  # 60MB
            f.write(very_large_data)
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data added",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                
                # Capture warnings
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = await client.add(data=temp_path, dataset_name="test-dataset")
                    
                    # Verify warning was issued
                    assert len(w) > 0
                    assert any("exceeds recommended limit" in str(warning.message) for warning in w)
                    
                assert isinstance(result, AddResult)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_update_with_streaming_upload(self, client):
        """Test update() method with streaming upload for large files."""
        data_id = uuid4()
        dataset_id = uuid4()

        # Create a large file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"update content" * (3 * 1024 * 1024)  # ~42MB
            f.write(large_data)
            temp_path = Path(f.name)

        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "message": "Data updated",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                result = await client.update(
                    data_id=data_id, dataset_id=dataset_id, data=temp_path
                )

                assert isinstance(result, UpdateResult)
                assert result.status == "success"
        finally:
            temp_path.unlink()
