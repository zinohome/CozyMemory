"""
File upload example for Cognee SDK.

This example demonstrates how to upload different types of files to Cognee.
"""

import asyncio
from pathlib import Path

from cognee_sdk import CogneeClient


async def main():
    """Main example function."""
    client = CogneeClient(api_url="http://localhost:8000")

    try:
        # Example 1: Upload text string
        print("Uploading text string...")
        result1 = await client.add(
            data="This is a text document about AI and machine learning.",
            dataset_name="documents",
        )
        print(f"Text uploaded: {result1.status}")

        # Example 2: Upload bytes
        print("\nUploading bytes...")
        text_bytes = b"This is binary data content."
        result2 = await client.add(
            data=text_bytes,
            dataset_name="documents",
        )
        print(f"Bytes uploaded: {result2.status}")

        # Example 3: Upload file from path
        print("\nUploading file from path...")
        # Create a temporary file for demonstration
        temp_file = Path("temp_example.txt")
        temp_file.write_text("This is a temporary file for demonstration.")

        try:
            result3 = await client.add(
                data=temp_file,
                dataset_name="documents",
            )
            print(f"File uploaded: {result3.status}")
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()

        # Example 4: Upload multiple files
        print("\nUploading multiple files...")
        results = await client.add_batch(
            data_list=[
                "First document",
                "Second document",
                "Third document",
            ],
            dataset_name="documents",
        )
        print(f"Uploaded {len(results)} files")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.status}")

        # Example 5: Upload with node_set
        print("\nUploading with node_set...")
        result5 = await client.add(
            data="Document with specific node set",
            dataset_name="documents",
            node_set=["category1", "tag1"],
        )
        print(f"Uploaded with node_set: {result5.status}")

        # Example 6: Streaming upload for large files
        print("\nDemonstrating streaming upload for large files...")
        print("Note: Files > 10MB automatically use streaming upload")
        print("Files > 50MB will trigger warnings but still work")
        
        # Create a large file for demonstration (12MB - triggers streaming)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            large_data = b"Large file content " * (600 * 1024)  # ~12MB
            f.write(large_data)
            large_file = Path(f.name)

        try:
            result6 = await client.add(
                data=large_file,
                dataset_name="documents",
            )
            print(f"Large file uploaded (streaming): {result6.status}")
        finally:
            # Clean up
            if large_file.exists():
                large_file.unlink()

        # Example 7: Batch upload with concurrent control
        print("\nBatch upload with concurrent control...")
        batch_results = await client.add_batch(
            data_list=[
                "Document 1",
                "Document 2",
                "Document 3",
                "Document 4",
                "Document 5",
            ],
            dataset_name="documents",
            max_concurrent=3,  # Limit to 3 concurrent uploads
        )
        print(f"Batch uploaded {len(batch_results)} files with max_concurrent=3")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
