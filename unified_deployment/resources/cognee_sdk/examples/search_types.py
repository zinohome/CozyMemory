"""
Search types example for Cognee SDK.

This example demonstrates different search types available in Cognee.
"""

import asyncio

from cognee_sdk import CogneeClient, SearchType


async def main():
    """Main example function."""
    client = CogneeClient(api_url="http://localhost:8000")

    try:
        # Ensure we have some data
        print("Setting up data...")
        await client.add(
            data="Python is a high-level programming language. It supports multiple programming paradigms.",
            dataset_name="programming",
        )
        await client.cognify(datasets=["programming"])

        query = "What is Python?"

        # Example 1: Graph Completion (default)
        print("\n1. Graph Completion Search:")
        results = await client.search(
            query=query,
            search_type=SearchType.GRAPH_COMPLETION,
            datasets=["programming"],
        )
        print(f"   Results: {len(results)}")

        # Example 2: RAG Completion
        print("\n2. RAG Completion Search:")
        results = await client.search(
            query=query,
            search_type=SearchType.RAG_COMPLETION,
            datasets=["programming"],
        )
        print(f"   Results: {len(results)}")

        # Example 3: Chunks
        print("\n3. Chunks Search:")
        results = await client.search(
            query=query,
            search_type=SearchType.CHUNKS,
            datasets=["programming"],
            top_k=5,
        )
        print(f"   Results: {len(results)}")

        # Example 4: Summaries
        print("\n4. Summaries Search:")
        results = await client.search(
            query=query,
            search_type=SearchType.SUMMARIES,
            datasets=["programming"],
        )
        print(f"   Results: {len(results)}")

        # Example 5: Code Search
        print("\n5. Code Search:")
        results = await client.search(
            query=query,
            search_type=SearchType.CODE,
            datasets=["programming"],
        )
        print(f"   Results: {len(results)}")

        # Example 6: Cypher Query
        print("\n6. Cypher Query Search:")
        results = await client.search(
            query="MATCH (n) RETURN n LIMIT 10",
            search_type=SearchType.CYPHER,
            datasets=["programming"],
        )
        print(f"   Results: {len(results)}")

        # Example 7: Search with system prompt
        print("\n7. Search with System Prompt:")
        results = await client.search(
            query=query,
            search_type=SearchType.GRAPH_COMPLETION,
            datasets=["programming"],
            system_prompt="Answer in a concise and technical manner.",
        )
        print(f"   Results: {len(results)}")

        # Example 8: Search with node filtering
        print("\n8. Search with Node Filtering:")
        results = await client.search(
            query=query,
            search_type=SearchType.GRAPH_COMPLETION,
            datasets=["programming"],
            node_name=["Python", "programming"],
        )
        print(f"   Results: {len(results)}")

        # Example 9: Get search history
        print("\n9. Search History:")
        history = await client.get_search_history()
        print(f"   History items: {len(history)}")
        for item in history[:5]:  # Show first 5
            print(f"   - {item.text} ({item.created_at})")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
