"""
向量存储单元测试

业务说明：
测试向量存储服务的核心功能，包括搜索和文档数量统计。
"""

import pytest
import tempfile
import shutil
from app.services.vector_store import VectorStore


class TestVectorStore:
    """向量存储测试"""

    def setup_method(self):
        """测试前准备：创建临时向量库"""
        self.temp_dir = tempfile.mkdtemp()
        self.vector_store = VectorStore()
        self.vector_store._chroma_client = None
        self.vector_store._collection = None

    def teardown_method(self):
        """测试后清理：删除临时向量库"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_search_with_results(self):
        """测试搜索有结果"""
        # 先添加测试数据
        test_docs = [
            {"content": "母乳喂养对宝宝有很多好处", "metadata": {"category": "喂养知识"}},
            {"content": "宝宝腹泻时要注意补充水分", "metadata": {"category": "健康护理"}},
        ]
        self.vector_store.add_documents(test_docs)

        # 执行搜索
        results = self.vector_store.search("母乳喂养")
        assert len(results) > 0
        assert "母乳喂养" in results[0]["content"]

    def test_search_no_results(self):
        """测试搜索无结果"""
        results = self.vector_store.search("无关内容")
        assert len(results) == 0

    def test_get_document_count(self):
        """测试获取文档数量"""
        count = self.vector_store.get_document_count()
        assert isinstance(count, int)
        assert count >= 0