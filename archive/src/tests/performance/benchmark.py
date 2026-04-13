"""
CozyMemory 性能基准测试

测试缓存层 + 路由层 + 融合层的性能表现。

测试场景:
1. 缓存命中率测试
2. 路由延迟测试
3. 多引擎并发查询测试
4. 融合算法性能测试
5. 端到端性能测试
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime

from src.models.memory import MemoryCreate, MemoryQuery, MemoryType
from src.adapters.memobase_mock_adapter import MemobaseMockAdapter, _mock_memories
from src.services.enhanced_memory_service import EnhancedMemoryService, close_enhanced_memory_service
from src.services.cache_service import close_cache_service
from src.services.router_service import close_router_service
from src.services.fusion_service import close_fusion_service


class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self):
        self.service = None
        self.results = {}
    
    async def setup(self):
        """设置测试环境"""
        _mock_memories.clear()
        
        # 创建共享适配器
        shared_adapter = MemobaseMockAdapter(api_url="http://localhost:8000")
        
        adapters = {
            "memobase": shared_adapter,
            "local": shared_adapter,
            "vector": shared_adapter,
        }
        
        self.service = EnhancedMemoryService(
            adapters=adapters,
            enable_cache=True,
            enable_routing=True,
            enable_fusion=True,
        )
        
        # 预热
        await self.service._ensure_services()
    
    async def teardown(self):
        """清理测试环境"""
        if self.service:
            await self.service.close()
        
        await close_cache_service()
        await close_router_service()
        await close_fusion_service()
        _mock_memories.clear()
    
    async def benchmark_cache_hit_rate(self, iterations: int = 100) -> Dict[str, Any]:
        """测试缓存命中率"""
        print(f"\n📊 测试缓存命中率 (n={iterations})...")
        
        # 创建测试数据
        memory = MemoryCreate(
            user_id="benchmark_user",
            content="缓存测试数据",
            memory_type=MemoryType.FACT,
        )
        created = await self.service.create_memory(memory)
        
        # 第一次查询 (缓存未命中)
        await self.service.get_memory(created.id)
        
        # 后续查询 (应该缓存命中)
        cache_hits = 0
        latencies = []
        
        for i in range(iterations):
            start = time.perf_counter()
            result = await self.service.get_memory(created.id)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            
            if result:
                cache_hits += 1
        
        hit_rate = (cache_hits / iterations) * 100
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0]
        
        result = {
            "test": "cache_hit_rate",
            "iterations": iterations,
            "cache_hits": cache_hits,
            "hit_rate_percent": round(hit_rate, 2),
            "avg_latency_ms": round(avg_latency, 3),
            "p95_latency_ms": round(p95_latency, 3),
            "min_latency_ms": round(min(latencies), 3),
            "max_latency_ms": round(max(latencies), 3),
        }
        
        self.results["cache_hit_rate"] = result
        print(f"✅ 缓存命中率：{hit_rate:.2f}%")
        print(f"   平均延迟：{avg_latency:.3f}ms")
        print(f"   P95 延迟：{p95_latency:.3f}ms")
        
        return result
    
    async def benchmark_routing_latency(self, iterations: int = 50) -> Dict[str, Any]:
        """测试路由延迟"""
        print(f"\n📊 测试路由延迟 (n={iterations})...")
        
        latencies = []
        
        for i in range(iterations):
            query = MemoryQuery(
                user_id="benchmark_user",
                query=f"测试查询{i}",
                memory_type=MemoryType.FACT,
                limit=10,
            )
            
            start = time.perf_counter()
            await self.service.query_memories(query)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0]
        
        result = {
            "test": "routing_latency",
            "iterations": iterations,
            "avg_latency_ms": round(avg_latency, 3),
            "p95_latency_ms": round(p95_latency, 3),
            "min_latency_ms": round(min(latencies), 3),
            "max_latency_ms": round(max(latencies), 3),
            "std_dev_ms": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0,
        }
        
        self.results["routing_latency"] = result
        print(f"✅ 平均路由延迟：{avg_latency:.3f}ms")
        print(f"   P95 延迟：{p95_latency:.3f}ms")
        print(f"   标准差：{result['std_dev_ms']:.3f}ms")
        
        return result
    
    async def benchmark_concurrent_queries(self, concurrency: int = 10) -> Dict[str, Any]:
        """测试并发查询性能"""
        print(f"\n📊 测试并发查询 (concurrency={concurrency})...")
        
        # 创建测试数据
        memories = [
            MemoryCreate(
                user_id="benchmark_user",
                content=f"并发测试{i}",
                memory_type=MemoryType.FACT,
            )
            for i in range(20)
        ]
        await self.service.batch_create(memories)
        
        # 并发查询
        async def query(i):
            q = MemoryQuery(
                user_id="benchmark_user",
                query=f"并发{i}",
                limit=10,
            )
            start = time.perf_counter()
            result = await self.service.query_memories(q)
            latency = (time.perf_counter() - start) * 1000
            return latency, len(result)
        
        # 测试不同并发级别
        all_latencies = []
        
        for batch in range(5):
            tasks = [query(i + batch * concurrency) for i in range(concurrency)]
            results = await asyncio.gather(*tasks)
            
            for latency, count in results:
                all_latencies.append(latency)
        
        avg_latency = statistics.mean(all_latencies)
        p95_latency = statistics.quantiles(all_latencies, n=100)[94] if len(all_latencies) > 1 else all_latencies[0]
        
        result = {
            "test": "concurrent_queries",
            "concurrency": concurrency,
            "total_queries": len(all_latencies),
            "avg_latency_ms": round(avg_latency, 3),
            "p95_latency_ms": round(p95_latency, 3),
            "throughput_qps": round(len(all_latencies) / (sum(all_latencies) / 1000), 2),
        }
        
        self.results["concurrent_queries"] = result
        print(f"✅ 平均延迟：{avg_latency:.3f}ms")
        print(f"   吞吐量：{result['throughput_qps']:.2f} QPS")
        
        return result
    
    async def benchmark_fusion_performance(self, iterations: int = 20) -> Dict[str, Any]:
        """测试融合算法性能"""
        print(f"\n📊 测试融合性能 (n={iterations})...")
        
        latencies = []
        fusion_counts = []
        
        for i in range(iterations):
            query = MemoryQuery(
                user_id="benchmark_user",
                query="AI",
                memory_type=None,
                limit=10,
            )
            
            start = time.perf_counter()
            results = await self.service.query_memories(query)
            latency = (time.perf_counter() - start) * 1000
            
            latencies.append(latency)
            fusion_counts.append(len(results))
        
        avg_latency = statistics.mean(latencies)
        avg_results = statistics.mean(fusion_counts)
        
        result = {
            "test": "fusion_performance",
            "iterations": iterations,
            "avg_latency_ms": round(avg_latency, 3),
            "avg_results": round(avg_results, 1),
            "total_results": sum(fusion_counts),
        }
        
        self.results["fusion_performance"] = result
        print(f"✅ 平均融合延迟：{avg_latency:.3f}ms")
        print(f"   平均结果数：{avg_results:.1f}")
        
        return result
    
    async def benchmark_end_to_end(self, iterations: int = 30) -> Dict[str, Any]:
        """端到端性能测试"""
        print(f"\n📊 端到端性能测试 (n={iterations})...")
        
        latencies = []
        
        for i in range(iterations):
            # 创建
            memory = MemoryCreate(
                user_id="benchmark_user",
                content=f"E2E 测试{i}",
                memory_type=MemoryType.EVENT,
            )
            
            start = time.perf_counter()
            created = await self.service.create_memory(memory)
            
            # 查询
            query = MemoryQuery(
                user_id="benchmark_user",
                query=f"E2E 测试{i}",
                limit=10,
            )
            results = await self.service.query_memories(query)
            
            # 获取
            retrieved = await self.service.get_memory(created.id)
            
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0]
        
        result = {
            "test": "end_to_end",
            "iterations": iterations,
            "operations_per_iteration": 3,  # create + query + get
            "total_operations": iterations * 3,
            "avg_latency_ms": round(avg_latency, 3),
            "p95_latency_ms": round(p95_latency, 3),
        }
        
        self.results["end_to_end"] = result
        print(f"✅ 平均操作延迟：{avg_latency:.3f}ms")
        print(f"   总操作数：{result['total_operations']}")
        
        return result
    
    async def run_all_benchmarks(self):
        """运行所有基准测试"""
        print("\n" + "="*60)
        print("🚀 CozyMemory Phase 2 性能基准测试")
        print("="*60)
        print(f"开始时间：{datetime.now().isoformat()}")
        
        await self.setup()
        
        try:
            # 运行测试
            await self.benchmark_cache_hit_rate()
            await self.benchmark_routing_latency()
            await self.benchmark_concurrent_queries()
            await self.benchmark_fusion_performance()
            await self.benchmark_end_to_end()
            
            # 打印总结
            self._print_summary()
            
        finally:
            await self.teardown()
    
    def _print_summary(self):
        """打印测试总结"""
        print("\n" + "="*60)
        print("📊 性能基准测试总结")
        print("="*60)
        
        for test_name, result in self.results.items():
            print(f"\n{test_name.upper()}:")
            for key, value in result.items():
                if key != "test":
                    print(f"  {key}: {value}")
        
        print("\n" + "="*60)
        print(f"测试完成时间：{datetime.now().isoformat()}")
        print("="*60)


async def main():
    """主函数"""
    benchmark = PerformanceBenchmark()
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())
