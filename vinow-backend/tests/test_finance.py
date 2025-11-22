import pytest
from app.services.finance_service import FinanceService
from app.schemas.finance import IncomeFlowParams


class TestFinanceService:
    """财务服务测试"""
    
    @pytest.fixture
    def finance_service(self):
        return FinanceService()
    
    @pytest.mark.asyncio
    async def test_get_daily_income(self, finance_service, mock_merchant_id):
        """测试获取日收入数据"""
        # 这里添加具体的测试逻辑
        pass
    
    @pytest.mark.asyncio 
    async def test_get_income_flow(self, finance_service, mock_merchant_id):
        """测试获取收入流水"""
        # 这里添加具体的测试逻辑
        pass