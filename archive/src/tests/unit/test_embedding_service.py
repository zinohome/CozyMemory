"""
嵌入服务单元测试
"""

import pytest
from src.embeddings.embedding_service import EmbeddingService


class TestEmbeddingService:
    """嵌入服务测试"""
    
    @pytest.fixture
    def embedding_service(self):
        """创建嵌入服务"""
        return EmbeddingService(model_name="test-model", dimension=384)
    
    def test_get_embedding(self, embedding_service):
        """获取嵌入"""
        text = "测试文本"
        embedding = embedding_service.get_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    def test_get_embeddings_batch(self, embedding_service):
        """批量获取嵌入"""
        texts = ["文本 1", "文本 2", "文本 3"]
        embeddings = embedding_service.get_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
    
    def test_compute_similarity(self, embedding_service):
        """计算相似度"""
        emb1 = embedding_service.get_embedding("相同文本")
        emb2 = embedding_service.get_embedding("相同文本")
        emb3 = embedding_service.get_embedding("不同文本")
        
        # 相同文本应该相似度很高
        sim1 = embedding_service.compute_similarity(emb1, emb2)
        assert sim1 > 0.9
        
        # 不同文本相似度较低
        sim2 = embedding_service.compute_similarity(emb1, emb3)
        assert sim2 < 0.9
    
    def test_cache(self, embedding_service):
        """缓存测试"""
        text = "缓存测试"
        
        # 第一次调用
        emb1 = embedding_service.get_embedding(text)
        
        # 第二次调用 (应该命中缓存)
        emb2 = embedding_service.get_embedding(text)
        
        assert emb1 == emb2
        assert len(embedding_service._cache) == 1
    
    def test_get_model_info(self, embedding_service):
        """获取模型信息"""
        info = embedding_service.get_model_info()
        
        assert info["model_name"] == "test-model"
        assert info["dimension"] == 384
        assert "cache_size" in info
    
    def test_clear_cache(self, embedding_service):
        """清空缓存"""
        # 添加缓存
        embedding_service.get_embedding("测试 1")
        embedding_service.get_embedding("测试 2")
        
        # 清空
        embedding_service.clear_cache()
        
        assert len(embedding_service._cache) == 0
    
    def test_deterministic_embedding(self, embedding_service):
        """确定性嵌入"""
        text = "确定性测试"
        
        # 多次生成应该相同
        emb1 = embedding_service.get_embedding(text)
        emb2 = embedding_service.get_embedding(text)
        emb3 = embedding_service.get_embedding(text)
        
        assert emb1 == emb2 == emb3
    
    def test_different_texts_different_embeddings(self, embedding_service):
        """不同文本不同嵌入"""
        emb1 = embedding_service.get_embedding("文本 A")
        emb2 = embedding_service.get_embedding("文本 B")
        
        # 应该不同
        assert emb1 != emb2
        
        # 但相似度应该在 0-1 之间
        sim = embedding_service.compute_similarity(emb1, emb2)
        assert 0 <= sim <= 1
