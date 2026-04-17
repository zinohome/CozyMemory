"""
Debug script to test add request format.
"""

import asyncio
import httpx
import os

API_URL = os.getenv("API_URL", "http://192.168.66.11")
API_TOKEN = os.getenv("API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3M2FiNzhlYi1iOWNmLTQ3MWYtOWY4Ny1kY2U2YjZiOTViOWUiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl0sImV4cCI6MTc2NTA5ODA0M30.J4AsAvLbqfvFX8KroXQE_SAd-bKZRT6RJ23UOi_iIMQ")


async def test_add_direct():
    """Test add request directly with httpx."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create dataset first
        dataset_response = await client.post(
            f"{API_URL}/api/v1/datasets",
            json={"name": "debug-test-dataset"},
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        print(f"Create dataset status: {dataset_response.status_code}")
        if dataset_response.status_code == 200:
            dataset = dataset_response.json()
            dataset_id = dataset.get("id")
            dataset_name = dataset.get("name")
            print(f"Created dataset: {dataset_id} - {dataset_name}")
        else:
            print(f"Failed to create dataset: {dataset_response.text}")
            return
        
        # Try different formats for add
        print("\n=== Testing add with multipart/form-data ===")
        
        # Format 1: Simple text file
        files = {
            "data": ("test.txt", "This is test data content.", "text/plain")
        }
        data = {
            "datasetName": dataset_name
        }
        
        try:
            response = await client.post(
                f"{API_URL}/api/v1/add",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {API_TOKEN}"}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Response keys: {list(result.keys())}")
                print(f"Full response: {result}")
                print("✓ Success!")
            else:
                print(f"✗ Failed: {response.text}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        
        # Clean up
        if dataset_id:
            try:
                await client.delete(
                    f"{API_URL}/api/v1/datasets/{dataset_id}",
                    headers={"Authorization": f"Bearer {API_TOKEN}"}
                )
                print(f"\n✓ Cleaned up dataset")
            except:
                pass


if __name__ == "__main__":
    asyncio.run(test_add_direct())

