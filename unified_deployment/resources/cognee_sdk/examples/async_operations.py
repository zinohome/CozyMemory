"""
Async operations example for Cognee SDK.

This example demonstrates concurrent operations and async patterns.
"""

import asyncio

from cognee_sdk import CogneeClient, SearchType


async def main():
    """Main example function."""
    client = CogneeClient(api_url="http://localhost:8000")

    try:
        # Example 1: Concurrent dataset creation
        print("Creating multiple datasets concurrently...")
        dataset_names = ["dataset1", "dataset2", "dataset3"]
        tasks = [client.create_dataset(name) for name in dataset_names]
        datasets = await asyncio.gather(*tasks)
        print(f"Created {len(datasets)} datasets")

        # Example 2: Concurrent data addition
        print("\nAdding data to multiple datasets concurrently...")
        add_tasks = [
            client.add(
                data=f"Data for {ds.name}",
                dataset_name=ds.name,
            )
            for ds in datasets
        ]
        add_results = await asyncio.gather(*add_tasks)
        print(f"Added data to {len(add_results)} datasets")

        # Example 3: Concurrent searches
        print("\nPerforming concurrent searches...")
        search_queries = [
            "What is dataset1 about?",
            "What is dataset2 about?",
            "What is dataset3 about?",
        ]
        search_tasks = [
            client.search(
                query=query,
                search_type=SearchType.GRAPH_COMPLETION,
                datasets=[datasets[i].name],
            )
            for i, query in enumerate(search_queries)
        ]
        search_results = await asyncio.gather(*search_tasks)
        print(f"Completed {len(search_results)} searches")

        # Example 4: Batch operations with concurrent control
        print("\nUsing batch operations with concurrent control...")
        data_list = [f"Batch data item {i}" for i in range(10)]
        batch_results = await client.add_batch(
            data_list=data_list,
            dataset_name="example-dataset",
            max_concurrent=5,  # Limit concurrent operations
        )
        print(f"Batch added {len(batch_results)} items")

        # Example 5: Batch operations with error handling
        print("\nUsing batch operations with error handling...")
        mixed_data = ["valid1", "valid2", "valid3"]
        try:
            results, errors = await client.add_batch(
                data_list=mixed_data,
                dataset_name="example-dataset",
                continue_on_error=True,  # Continue on error
                return_errors=True,      # Return errors
            )
            print(f"Successfully added: {len([r for r in results if r])} items")
            if errors:
                print(f"Errors encountered: {len(errors)}")
        except Exception as e:
            print(f"Batch operation error: {e}")

        # Example 6: Using async context manager
        print("\nUsing async context manager...")
        async with CogneeClient(api_url="http://localhost:8000") as ctx_client:
            datasets = await ctx_client.list_datasets()
            print(f"Listed {len(datasets)} datasets")
        # Client automatically closed

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
