"""
Basic usage example for Cognee SDK.

This example demonstrates the core functionality of the Cognee SDK:
1. Adding data
2. Processing data (cognify)
3. Searching the knowledge graph
"""

import asyncio

from cognee_sdk import CogneeClient, SearchType


async def main():
    """Main example function."""
    # Initialize client
    client = CogneeClient(
        api_url="http://localhost:8000",
        api_token="your-token-here",  # Optional, if authentication is enabled
    )

    try:
        # 1. Create or get a dataset
        print("Creating dataset...")
        dataset = await client.create_dataset("example-dataset")
        print(f"Dataset created: {dataset.name} (ID: {dataset.id})")

        # 2. Add data to the dataset
        print("\nAdding data...")
        add_result = await client.add(
            data="Cognee turns documents into AI memory. It combines vector search with graph databases.",
            dataset_name="example-dataset",
        )
        print(f"Data added: {add_result.message}")
        if add_result.data_id:
            print(f"Data ID: {add_result.data_id}")

        # 3. Process the data to generate knowledge graph
        print("\nProcessing data (cognify)...")
        cognify_result = await client.cognify(
            datasets=["example-dataset"],
            run_in_background=False,
        )
        print(f"Cognify status: {cognify_result.get('default', {}).status}")
        if cognify_result.get("default"):
            result = cognify_result["default"]
            if result.entity_count:
                print(f"Entities extracted: {result.entity_count}")
            if result.duration:
                print(f"Processing duration: {result.duration:.2f}s")

        # 4. Search the knowledge graph
        print("\nSearching knowledge graph...")
        search_results = await client.search(
            query="What does Cognee do?",
            search_type=SearchType.GRAPH_COMPLETION,
            datasets=["example-dataset"],
            top_k=5,
            return_type="parsed",  # Use "raw" for raw dictionary results
        )

        print(f"\nFound {len(search_results)} results:")
        for i, result in enumerate(search_results, 1):
            if isinstance(result, dict):
                print(f"{i}. {result.get('text', result)}")
            else:
                print(f"{i}. {result}")

        # 5. List all datasets
        print("\nListing all datasets...")
        datasets = await client.list_datasets()
        print(f"Total datasets: {len(datasets)}")
        for ds in datasets:
            print(f"  - {ds.name} (ID: {ds.id})")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Always close the client
        await client.close()
        print("\nClient closed.")


if __name__ == "__main__":
    asyncio.run(main())
