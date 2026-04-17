"""
Advanced features example for Cognee SDK.

This example demonstrates advanced features:
1. Streaming upload for large files
2. Smart retry mechanism
3. Batch operations with error handling
4. Request logging and interceptors
5. Custom connection pool configuration
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from cognee_sdk import CogneeClient, SearchType


async def main():
    """Main example function."""
    # Example 1: Client with logging enabled
    print("=== Example 1: Request Logging ===")
    client_with_logging = CogneeClient(
        api_url="http://localhost:8000",
        enable_logging=True,  # Enable request/response logging
    )

    try:
        datasets = await client_with_logging.list_datasets()
        print(f"Found {len(datasets)} datasets (check logs above)")
    finally:
        await client_with_logging.close()

    # Example 2: Client with interceptors
    print("\n=== Example 2: Request/Response Interceptors ===")

    def request_interceptor(method: str, url: str, headers: dict):
        """Custom request interceptor."""
        print(f"  → Request: {method} {url}")

    def response_interceptor(response):
        """Custom response interceptor."""
        print(f"  ← Response: {response.status_code}")

    client_with_interceptors = CogneeClient(
        api_url="http://localhost:8000",
        request_interceptor=request_interceptor,
        response_interceptor=response_interceptor,
    )

    try:
        await client_with_interceptors.health_check()
    finally:
        await client_with_interceptors.close()

    # Example 3: Custom connection pool configuration
    print("\n=== Example 3: Custom Connection Pool ===")
    client_custom_pool = CogneeClient(
        api_url="http://localhost:8000",
        max_keepalive_connections=20,  # More keepalive connections
        max_connections=50,            # More total connections
    )

    try:
        # This is useful for high-concurrency scenarios
        print("Client configured with custom connection pool")
        await client_custom_pool.health_check()
    finally:
        await client_custom_pool.close()

    # Example 4: Streaming upload for large files
    print("\n=== Example 4: Streaming Upload ===")
    client = CogneeClient(api_url="http://localhost:8000")

    try:
        # Create a large file (> 10MB - triggers streaming)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"Streaming upload test " * (500 * 1024)  # ~12MB
            f.write(large_data)
            large_file = Path(f.name)

        try:
            print(f"Uploading large file ({large_file.stat().st_size / 1024 / 1024:.1f}MB)...")
            result = await client.add(
                data=large_file,
                dataset_name="test-dataset",
            )
            print(f"Upload successful: {result.status}")
            print("Note: Large files automatically use streaming upload")
        finally:
            if large_file.exists():
                large_file.unlink()

        # Example 5: Batch operations with error handling
        print("\n=== Example 5: Batch Operations with Error Handling ===")
        
        # Basic batch operation
        print("Basic batch operation:")
        results = await client.add_batch(
            data_list=["Item 1", "Item 2", "Item 3"],
            dataset_name="test-dataset",
            max_concurrent=2,  # Limit concurrent operations
        )
        print(f"  Successfully added {len(results)} items")

        # Batch operation with error handling
        print("\nBatch operation with error handling:")
        try:
            results, errors = await client.add_batch(
                data_list=["Valid 1", "Valid 2", "Valid 3"],
                dataset_name="test-dataset",
                continue_on_error=True,  # Continue on error
                return_errors=True,      # Return errors
                max_concurrent=2,
            )
            successful = [r for r in results if r is not None]
            print(f"  Successfully added: {len(successful)} items")
            if errors:
                print(f"  Errors: {len(errors)}")
        except Exception as e:
            print(f"  Batch error: {e}")

        # Example 6: Search with return_type
        print("\n=== Example 6: Search with Return Type ===")
        
        # Parsed results (default)
        print("Search with parsed results:")
        parsed_results = await client.search(
            query="test query",
            return_type="parsed",  # Returns SearchResult objects
        )
        print(f"  Found {len(parsed_results)} parsed results")

        # Raw results
        print("\nSearch with raw results:")
        raw_results = await client.search(
            query="test query",
            return_type="raw",  # Returns raw dictionaries
        )
        print(f"  Found {len(raw_results)} raw results")

        # Example 7: Smart retry mechanism demonstration
        print("\n=== Example 7: Smart Retry Mechanism ===")
        print("The SDK automatically:")
        print("  - Retries 5xx errors (server errors)")
        print("  - Retries 429 errors (rate limiting)")
        print("  - Retries network errors")
        print("  - Does NOT retry 4xx errors (client errors)")
        print("  - Uses exponential backoff for retries")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
