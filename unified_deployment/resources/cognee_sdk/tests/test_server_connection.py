"""
Quick connection test to verify server accessibility.

Run this first to verify the server is accessible before running full integration tests.
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cognee_sdk import CogneeClient

# Note: API_URL should be the base URL without /api
# If your server is at http://192.168.66.11/api, use http://192.168.66.11
API_URL = os.getenv("API_URL", "http://192.168.66.11")
API_TOKEN = os.getenv("API_TOKEN", None)


async def test_connection():
    """Quick test to verify server connection."""
    print(f"Testing connection to: {API_URL}")
    print(f"API Token: {'Set' if API_TOKEN else 'Not set'}")
    print("-" * 50)
    
    client = CogneeClient(api_url=API_URL, api_token=API_TOKEN)
    
    try:
        # Test 1: List datasets
        print("Test 1: Listing datasets...")
        try:
            datasets = await client.list_datasets()
            print(f"✓ Success! Found {len(datasets)} datasets")
            if datasets:
                print(f"  First dataset: {datasets[0].name} (ID: {datasets[0].id})")
        except Exception as e:
            print(f"✗ Failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        # Test 2: Health check (if available)
        print("\nTest 2: Health check...")
        try:
            health = await client.health_check()
            print(f"✓ Success! Status: {health.status}")
            if hasattr(health, "version"):
                print(f"  Version: {health.version}")
        except Exception as e:
            print(f"⚠ Health check not available: {type(e).__name__}")
            print(f"  (This is okay, health check endpoint may not exist)")
        
        # Test 3: Create a test dataset
        print("\nTest 3: Creating test dataset...")
        try:
            test_name = f"connection-test-{int(asyncio.get_event_loop().time())}"
            dataset = await client.create_dataset(name=test_name)
            print(f"✓ Success! Created dataset: {dataset.name} (ID: {dataset.id})")
            
            # Clean up
            try:
                await client.delete_dataset(dataset_id=dataset.id)
                print(f"✓ Cleaned up test dataset")
            except Exception as e:
                print(f"⚠ Could not delete test dataset: {e}")
        except Exception as e:
            print(f"✗ Failed: {e}")
            print(f"  Error type: {type(e).__name__}")
        
        print("\n" + "=" * 50)
        print("Connection test completed!")
        
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False
    finally:
        await client.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)

