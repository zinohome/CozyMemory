"""Debug script to check get_dataset_data response format."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cognee_sdk import CogneeClient
from uuid import uuid4

API_URL = os.getenv("API_URL", "http://192.168.66.11")
API_TOKEN = os.getenv("API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3M2FiNzhlYi1iOWNmLTQ3MWYtOWY4Ny1kY2U2YjZiOTViOWUiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl0sImV4cCI6MTc2NTA5ODA0M30.J4AsAvLbqfvFX8KroXQE_SAd-bKZRT6RJ23UOi_iIMQ")


async def test_get_data():
    """Test getting dataset data."""
    client = CogneeClient(api_url=API_URL, api_token=API_TOKEN)
    
    try:
        # Create dataset
        dataset = await client.create_dataset(name=f"debug-get-data-{uuid4().hex[:8]}")
        print(f"Created dataset: {dataset.id}")
        
        # Add data
        add_result = await client.add(
            data="Test data for getting dataset data.",
            dataset_name=dataset.name
        )
        print(f"Added data: {add_result.data_id}")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Get dataset data - check raw response first
        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{API_URL}/api/v1/datasets/{dataset.id}/data",
                    headers={"Authorization": f"Bearer {API_TOKEN}"}
                )
                print(f"\nRaw response status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print(f"Response type: {type(result)}")
                    if isinstance(result, list) and len(result) > 0:
                        print(f"First item keys: {list(result[0].keys())}")
                        print(f"First item: {result[0]}")
        except Exception as e:
            print(f"Error getting raw data: {e}")
        
        # Try with SDK
        try:
            data_items = await client.get_dataset_data(dataset_id=dataset.id)
            print(f"\nGot {len(data_items)} data items via SDK")
        except Exception as e:
            print(f"SDK Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Clean up
        try:
            await client.delete_dataset(dataset_id=dataset.id)
            print("\n✓ Cleaned up")
        except:
            pass
            
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_get_data())

