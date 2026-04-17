# Cognee Python SDK

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Lightweight, type-safe, and fully asynchronous Python SDK for [Cognee](https://github.com/topoteretes/cognee) - an AI memory platform that transforms documents into persistent and dynamic knowledge graphs.

## Features

- 🚀 **Lightweight**: Only ~5-10MB (vs 500MB-2GB for full cognee library)
- 🔒 **Type Safe**: Full type hints with Pydantic validation
- ⚡ **Async First**: Fully asynchronous API with `httpx`
- 🛡️ **Error Handling**: Comprehensive error handling with intelligent retry mechanism
- 📁 **File Upload**: Support for multiple file formats and input types
- 💾 **Streaming Upload**: Automatic streaming for large files (>10MB) to reduce memory usage
- 🔌 **WebSocket**: Optional WebSocket support for real-time progress updates
- 🔄 **Smart Retry**: Intelligent retry logic that distinguishes retryable and non-retryable errors
- 📊 **Batch Operations**: Support for batch data operations with concurrent control
- 📝 **Request Logging**: Optional request/response logging and interceptors for debugging

## Installation

```bash
pip install cognee-sdk
```

### Optional Dependencies

For WebSocket support:

```bash
pip install cognee-sdk[websocket]
```

## Quick Start

```python
import asyncio
from cognee_sdk import CogneeClient, SearchType

async def main():
    # Initialize client
    client = CogneeClient(
        api_url="http://localhost:8000",
        api_token="your-token-here"  # Optional
    )
    
    try:
        # Add data
        result = await client.add(
            data="Cognee turns documents into AI memory.",
            dataset_name="my-dataset"
        )
        print(f"Added data: {result.data_id}")
        
        # Process data
        cognify_result = await client.cognify(datasets=["my-dataset"])
        print(f"Cognify status: {cognify_result.status}")
        
        # Search
        results = await client.search(
            query="What does Cognee do?",
            search_type=SearchType.GRAPH_COMPLETION
        )
        for result in results:
            print(result)
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Overview

### Core Operations

- **Data Management**: `add()`, `update()`, `delete()`
- **Processing**: `cognify()`, `memify()`
- **Search**: `search()` with 19 different search types
- **Datasets**: `list_datasets()`, `create_dataset()`, `delete_dataset()`
- **Authentication**: `login()`, `register()`, `get_current_user()`

### Advanced Features

- **WebSocket**: `subscribe_cognify_progress()` for real-time updates
- **Batch Operations**: `add_batch()` for bulk data operations with concurrent control
- **Streaming Upload**: Automatic streaming for large files (>10MB) to reduce memory usage
- **Visualization**: `visualize()` for graph visualization
- **Sync**: `sync_to_cloud()`, `get_sync_status()` for cloud synchronization
- **Request Logging**: Optional logging and interceptors for debugging

## Streaming Upload for Large Files

The SDK automatically uses streaming upload for files larger than 10MB to reduce memory usage:

```python
# Small file (< 10MB) - uses memory upload
await client.add(data=Path("small_file.txt"), dataset_name="my-dataset")

# Large file (> 10MB) - automatically uses streaming upload
await client.add(data=Path("large_file.pdf"), dataset_name="my-dataset")

# Files > 50MB will trigger a warning but still work
```

**Benefits:**
- Reduced memory usage (50-90% reduction for large files)
- Support for very large files (limited only by system resources)
- Automatic optimization based on file size

## Examples

See the [examples/](examples/) directory for more examples:

- [Basic Usage](examples/basic_usage.py) - Core functionality
- [File Upload](examples/file_upload.py) - Different file upload methods including streaming
- [Async Operations](examples/async_operations.py) - Concurrent operations and batch processing
- [Search Types](examples/search_types.py) - All search types
- [Advanced Features](examples/advanced_features.py) - Streaming upload, error handling, logging, and more

## API Reference

### CogneeClient

Main client class for interacting with Cognee API.

```python
client = CogneeClient(
    api_url="http://localhost:8000",
    api_token="your-token",           # Optional
    timeout=300.0,                    # Request timeout
    max_retries=3,                    # Retry attempts
    retry_delay=1.0,                  # Initial retry delay
    enable_logging=False,              # Enable request/response logging
    request_interceptor=None,          # Optional request interceptor
    response_interceptor=None          # Optional response interceptor
)
```

### Search Types

Available search types:

- `SearchType.GRAPH_COMPLETION` - Graph-based completion (default)
- `SearchType.RAG_COMPLETION` - RAG-based completion
- `SearchType.CHUNKS` - Chunk search
- `SearchType.SUMMARIES` - Summary search
- `SearchType.CODE` - Code search
- `SearchType.CYPHER` - Cypher query
- And 13 more types...

See [models.py](cognee_sdk/models.py) for the complete list.

## Error Handling

The SDK provides specific exception types and intelligent retry logic:

```python
from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    ValidationError,
    ServerError,
)

try:
    await client.search("query")
except AuthenticationError:
    print("Authentication failed")
except NotFoundError:
    print("Resource not found")
except ValidationError:
    print("Invalid request")
except ServerError:
    print("Server error")
```

### Smart Retry Mechanism

The SDK implements intelligent retry logic:
- **4xx errors** (except 429): No retry, immediately raise
- **429 errors** (rate limit): Retry with exponential backoff
- **5xx errors**: Retry with exponential backoff
- **Network errors**: Retry with exponential backoff

This reduces unnecessary retries and improves response time for client errors.

## Batch Operations with Concurrent Control

Batch operations support concurrent control to prevent resource exhaustion:

```python
# Add multiple items with concurrent control
results = await client.add_batch(
    data_list=["item1", "item2", "item3"],
    dataset_name="my-dataset",
    max_concurrent=10  # Limit concurrent operations (default: 10)
)
```

## Request Logging and Interceptors

Enable logging and use interceptors for debugging:

```python
import logging

# Enable logging
client = CogneeClient(
    api_url="http://localhost:8000",
    enable_logging=True
)

# Use interceptors
def log_request(method, url, headers):
    print(f"Request: {method} {url}")

def log_response(response):
    print(f"Response: {response.status_code}")

client = CogneeClient(
    api_url="http://localhost:8000",
    request_interceptor=log_request,
    response_interceptor=log_response
)
```

## Requirements

- Python 3.10+
- Cognee API server running (see [Cognee documentation](https://docs.cognee.ai))

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/cognee-sdk.git
cd cognee-sdk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cognee_sdk --cov-report=html

# Run specific test file
pytest tests/test_client.py
```

### Code Quality

```bash
# Format code
ruff format .

# Check code
ruff check .

# Type checking
mypy cognee_sdk/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## Support

- [GitHub Issues](https://github.com/your-org/cognee-sdk/issues)
- [Documentation](https://github.com/your-org/cognee-sdk#readme)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

