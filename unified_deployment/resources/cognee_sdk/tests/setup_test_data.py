"""
Setup script to clean up and create test data for frontend verification.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cognee_sdk import CogneeClient, SearchType

API_URL = os.getenv("API_URL", "http://192.168.66.11")
API_TOKEN = os.getenv("API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3M2FiNzhlYi1iOWNmLTQ3MWYtOWY4Ny1kY2U2YjZiOTViOWUiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl0sImV4cCI6MTc2NTA5ODA0M30.J4AsAvLbqfvFX8KroXQE_SAd-bKZRT6RJ23UOi_iIMQ")


async def setup_test_data():
    """Delete all datasets and create a new test dataset with data."""
    client = CogneeClient(api_url=API_URL, api_token=API_TOKEN)
    
    try:
        print("=" * 60)
        print("开始设置测试数据")
        print("=" * 60)
        
        # 1. 列出所有数据集
        print("\n1. 列出所有数据集...")
        datasets = await client.list_datasets()
        print(f"   找到 {len(datasets)} 个数据集")
        
        # 2. 删除所有数据集
        if datasets:
            print(f"\n2. 删除所有数据集...")
            deleted_count = 0
            for dataset in datasets:
                try:
                    await client.delete_dataset(dataset_id=dataset.id)
                    print(f"   ✓ 已删除: {dataset.name} (ID: {dataset.id})")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ✗ 删除失败 {dataset.name}: {type(e).__name__}")
            
            print(f"\n   共删除 {deleted_count} 个数据集")
        else:
            print("\n2. 没有数据集需要删除")
        
        # 等待一下确保删除完成
        await asyncio.sleep(1)
        
        # 3. 创建新的测试数据集
        print("\n3. 创建测试数据集...")
        test_dataset = await client.create_dataset(name="前端测试数据集")
        print(f"   ✓ 已创建数据集: {test_dataset.name}")
        print(f"   数据集 ID: {test_dataset.id}")
        
        # 4. 添加测试数据
        print("\n4. 添加测试数据...")
        test_data = [
            "Cognee 是一个 AI 记忆平台，可以将文档转换为知识图谱。",
            "知识图谱是一种结构化的知识表示方法，用节点和边来表示实体和关系。",
            "RAG (Retrieval-Augmented Generation) 是一种结合检索和生成的 AI 技术。",
            "向量数据库可以高效地存储和检索高维向量数据。",
            "自然语言处理 (NLP) 是人工智能的一个重要分支，专注于理解和生成人类语言。",
            "机器学习算法可以从数据中学习模式，无需显式编程。",
            "深度学习使用多层神经网络来学习数据的复杂表示。",
            "Transformer 架构是当前最先进的 NLP 模型的基础。",
        ]
        
        added_count = 0
        for i, data in enumerate(test_data, 1):
            try:
                result = await client.add(
                    data=data,
                    dataset_name=test_dataset.name
                )
                print(f"   ✓ [{i}/{len(test_data)}] 已添加: {data[:30]}...")
                added_count += 1
                # 稍微延迟避免过快
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"   ✗ [{i}/{len(test_data)}] 添加失败: {type(e).__name__}")
        
        print(f"\n   共添加 {added_count} 条数据")
        
        # 5. 等待数据处理
        print("\n5. 等待数据初步处理...")
        await asyncio.sleep(2)
        
        # 6. 启动 Cognify 处理
        print("\n6. 启动 Cognify 处理...")
        try:
            cognify_result = await client.cognify(
                datasets=[test_dataset.name],
                run_in_background=True
            )
            print(f"   ✓ Cognify 已启动（后台处理）")
            if isinstance(cognify_result, dict):
                for name, result in cognify_result.items():
                    print(f"   数据集 {name}: {result.status}")
        except Exception as e:
            print(f"   ⚠ Cognify 启动可能有问题: {type(e).__name__}")
        
        # 7. 验证数据
        print("\n7. 验证数据集...")
        try:
            data_items = await client.get_dataset_data(dataset_id=test_dataset.id)
            print(f"   ✓ 数据集包含 {len(data_items)} 个数据项")
            
            status = await client.get_dataset_status(dataset_ids=[test_dataset.id])
            if test_dataset.id in status:
                print(f"   ✓ 数据集状态: {status[test_dataset.id]}")
        except Exception as e:
            print(f"   ⚠ 验证时出现问题: {type(e).__name__}")
        
        # 8. 测试搜索
        print("\n8. 测试搜索功能...")
        try:
            await asyncio.sleep(3)  # 等待处理
            search_results = await client.search(
                query="什么是知识图谱？",
                search_type=SearchType.GRAPH_COMPLETION,
                datasets=[test_dataset.name],
                top_k=3
            )
            if isinstance(search_results, list):
                print(f"   ✓ 搜索返回 {len(search_results)} 个结果")
            else:
                print(f"   ✓ 搜索完成（结果类型: {type(search_results).__name__}）")
        except Exception as e:
            print(f"   ⚠ 搜索可能还在处理中: {type(e).__name__}")
        
        print("\n" + "=" * 60)
        print("测试数据设置完成！")
        print("=" * 60)
        print(f"\n数据集名称: {test_dataset.name}")
        print(f"数据集 ID: {test_dataset.id}")
        print(f"数据条数: {added_count}")
        print("\n现在可以在前端验证了！")
        print(f"前端地址: http://192.168.66.11/")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(setup_test_data())

