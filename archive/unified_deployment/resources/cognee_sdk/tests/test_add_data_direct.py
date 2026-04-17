"""
Direct test of add data functionality to debug the issue.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cognee_sdk import CogneeClient

API_URL = os.getenv("API_URL", "http://192.168.66.11")
API_TOKEN = os.getenv("API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3M2FiNzhlYi1iOWNmLTQ3MWYtOWY4Ny1kY2U2YjZiOTViOWUiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl0sImV4cCI6MTc2NTA5ODA0M30.J4AsAvLbqfvFX8KroXQE_SAd-bKZRT6RJ23UOi_iIMQ")


async def test_add():
    """Test adding data directly."""
    client = CogneeClient(api_url=API_URL, api_token=API_TOKEN)
    
    try:
        # Create dataset
        dataset = await client.create_dataset(name="test-add-direct")
        print(f"Created dataset: {dataset.id}")
        
        # Try to add data
        try:
            result = await client.add(
                data="This is test data for debugging.",
                dataset_name="test-add-direct"
            )
            print(f"✓ Success! Added data: {result.data_id}")
        except Exception as e:
            print(f"✗ Failed: {e}")
            print(f"  Error type: {type(e).__name__}")
            # Print error details if available
            if hasattr(e, 'response') and e.response:
                print(f"  Response: {e.response}")
            if hasattr(e, 'status_code'):
                print(f"  Status code: {e.status_code}")
            import traceback
            traceback.print_exc()
            
        # Wait a bit before trying again
        await asyncio.sleep(1)
        
        # Try with dataset_id instead
        try:
            print("\nTrying with dataset_id...")
            result = await client.add(
                data="This is test data using dataset_id.",
                dataset_id=dataset.id
            )
            print(f"✓ Success! Added data: {result.data_id}")
        except Exception as e:
            print(f"✗ Failed with dataset_id: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        # Clean up
        try:
            await client.delete_dataset(dataset_id=dataset.id)
            print("✓ Cleaned up dataset")
        except:
            pass
            
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_add())

