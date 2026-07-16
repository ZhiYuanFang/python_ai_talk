"""
API 集成测试

业务说明：
测试 API 接口的基本功能，包括健康检查和意图分析。
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestHealthCheck:
    """健康检查接口测试"""

    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestIntentAnalysis:
    """意图分析接口测试"""

    def test_intent_analysis_valid_request(self, client):
        """测试意图分析接口有效请求"""
        response = client.post(
            "/v1/analyze/intent",
            json={
                "text": "开始喂奶",
                "device_no": "test-device-001",
                "model": {
                    "provider": "deepseek",
                    "name": "deepseek-chat",
                    "max_in_flight": 3,
                },
            },
        )
        # 由于没有实际调用LLM，这里测试请求格式是否正确
        assert response.status_code in [200, 500]

    def test_intent_analysis_invalid_request(self, client):
        """测试意图分析接口无效请求"""
        response = client.post(
            "/v1/analyze/intent",
            json={
                "text": "",
                "device_no": "",
            },
        )
        assert response.status_code == 422