商家板块5数据分析测试配额
import pytest
import asyncio
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.supabase_client import SupabaseClient

@pytest.fixture(scope="session")
def test_client():
    """测试客户端"""
    return TestClient(app)

@pytest.fixture
def sample_dashboard_data():
    """示例仪表盘数据"""
    return {
        "health_score": {
            "score": 85,
            "level": "good",
            "better_than_peers": 92.0,
            "date": "2024-01-15"
        },
        "core_metrics": {
            "metrics": [
                {
                    "name": "到店客流",
                    "value": 156,
                    "change_percentage": 15.0,
                    "change_direction": "up"
                },
                {
                    "name": "营业收入",
                    "value": "12.8M VND",
                    "change_percentage": 22.0,
                    "change_direction": "up"
                },
                {
                    "name": "订单数量",
                    "value": "89单",
                    "change_percentage": 18.0,
                    "change_direction": "up"
                },
                {
                    "name": "客户评分",
                    "value": "4.7分",
                    "change_percentage": 0.0,
                    "change_direction": "same"
                }
            ],
            "comparison_date": "2024-01-14"
        },
        "alerts": {
            "critical": 1,
            "warning": 2,
            "normal": 8,
            "alerts": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "高峰时段等位流失率高",
                    "description": "17:00-19:00时段等位流失率45%",
                    "level": "critical",
                    "created_at": "2024-01-15T10:00:00",
                    "is_resolved": False
                }
            ]
        }
    }

@pytest.fixture
def mock_supabase_client(monkeypatch):
    """模拟 Supabase 客户端"""
    
    class MockSupabaseClient:
        def __init__(self):
            self.connected = True
        
        async def health_check(self):
            return True
        
        def get_business_metrics(self, date_str):
            return {
                "date": date_str,
                "customer_count": 156,
                "revenue": 12800000,
                "order_count": 89,
                "rating": 4.7,
                "health_score": 85,
                "better_than_peers": 92.0
            }
        
        def get_active_alerts(self, date_str):
            return [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "高峰时段等位流失率高",
                    "description": "17:00-19:00时段等位流失率45%",
                    "level": "critical",
                    "is_resolved": False,
                    "created_at": "2024-01-15T10:00:00Z",
                    "business_date": date_str
                }
            ]
    
    monkeypatch.setattr("app.services.supabase_client.SupabaseClient", MockSupabaseClient)
    return MockSupabaseClient()

@pytest.fixture
def auth_headers():
    """认证头"""
    return {
        "X-API-Key": "your-api-key-1",
        "Authorization": "Bearer mock-jwt-token"
    }"""商家系统 - conftest"""

# TODO: 实现商家系统相关功能
