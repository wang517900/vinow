# -*- coding: utf-8 -*-
"""商品服务测试模块"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime
from main import app
from app.models.product_models import (
    ProductCreate, ProductUpdate, ProductResponse, ProductStatus,
    ProductType, PriceType, ProductVariant, BulkUpdateStatus,
    BulkStockUpdate, StockUpdate
)
from app.services.product_service import ProductService

client = TestClient(app)

class TestProductModels:
    """商品模型测试"""
    
    def test_product_create_valid(self):
        """测试有效的商品创建数据"""
        variant = ProductVariant(
            sku="TEST-SKU-001",
            name="默认规格",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            stock_quantity=100,
            stock_threshold=10,
            is_default=True
        )
        
        product_data = {
            "name": "测试商品",
            "description": "这是一个测试商品",
            "product_type": ProductType.PHYSICAL,
            "price_type": PriceType.FIXED,
            "merchant_id": "merchant-123",
            "variants": [variant]
        }
        
        product = ProductCreate(**product_data)
        assert product.name == "测试商品"
        assert product.product_type == ProductType.PHYSICAL
        assert len(product.variants) == 1
        assert product.variants[0].sku == "TEST-SKU-001"
    
    def test_product_create_invalid_sku(self):
        """测试无效的SKU格式"""
        variant = ProductVariant(
            sku="invalid sku!",  # 包含空格和特殊字符
            name="默认规格",
            price=Decimal("99.99"),
            is_default=True
        )
        
        product_data = {
            "name": "测试商品",
            "product_type": ProductType.PHYSICAL,
            "merchant_id": "merchant-123",
            "variants": [variant]
        }
        
        with pytest.raises(ValueError, match="SKU只能包含字母、数字、下划线和连字符"):
            ProductCreate(**product_data)
    
    def test_product_create_duplicate_sku(self):
        """测试重复的SKU"""
        variant1 = ProductVariant(
            sku="TEST-SKU-001",
            name="规格1",
            price=Decimal("99.99"),
            is_default=True
        )
        variant2 = ProductVariant(
            sku="TEST-SKU-001",  # 重复的SKU
            name="规格2",
            price=Decimal("129.99"),
            is_default=False
        )
        
        product_data = {
            "name": "测试商品",
            "product_type": ProductType.PHYSICAL,
            "merchant_id": "merchant-123",
            "variants": [variant1, variant2]
        }
        
        with pytest.raises(ValueError, match="SKU编码不能重复"):
            ProductCreate(**product_data)
    
    def test_product_create_no_default_variant(self):
        """测试没有默认规格"""
        variant = ProductVariant(
            sku="TEST-SKU-001",
            name="规格1",
            price=Decimal("99.99"),
            is_default=False  # 不是默认规格
        )
        
        product_data = {
            "name": "测试商品",
            "product_type": ProductType.PHYSICAL,
            "merchant_id": "merchant-123",
            "variants": [variant]
        }
        
        with pytest.raises(ValueError, match="必须有且仅有一个默认规格"):
            ProductCreate(**product_data)
    
    def test_product_create_multiple_default_variants(self):
        """测试多个默认规格"""
        variant1 = ProductVariant(
            sku="TEST-SKU-001",
            name="规格1",
            price=Decimal("99.99"),
            is_default=True
        )
        variant2 = ProductVariant(
            sku="TEST-SKU-002",
            name="规格2",
            price=Decimal("129.99"),
            is_default=True  # 也是默认规格
        )
        
        product_data = {
            "name": "测试商品",
            "product_type": ProductType.PHYSICAL,
            "merchant_id": "merchant-123",
            "variants": [variant1, variant2]
        }
        
        with pytest.raises(ValueError, match="必须有且仅有一个默认规格"):
            ProductCreate(**product_data)
    
    def test_product_variant_price_validation(self):
        """测试商品规格价格验证"""
        variant = ProductVariant(
            sku="TEST-SKU-001",
            name="默认规格",
            price=Decimal("99.999"),  # 3位小数
            is_default=True
        )
        
        # 价格应该被量化为2位小数
        assert variant.price == Decimal("100.00")  # 修正：应该是四舍五入到100.00

class TestProductService:
    """商品服务测试"""
    
    @pytest.fixture
    def sample_product_data(self):
        """示例商品数据"""
        variant = ProductVariant(
            sku="TEST-SKU-001",
            name="默认规格",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            stock_quantity=100,
            stock_threshold=10,
            is_default=True
        )
        
        return ProductCreate(
            name="测试商品",
            description="这是一个测试商品",
            product_type=ProductType.PHYSICAL,
            price_type=PriceType.FIXED,
            merchant_id="merchant-123",
            variants=[variant]
        )
    
    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase客户端"""
        mock_client = Mock()
        # 重置mock状态以确保每次调用都返回新的mock对象
        mock_client.reset_mock()
        
        # 默认的链式调用行为
        mock_client.table.return_value = mock_client
        mock_client.select.return_value = mock_client
        mock_client.eq.return_value = mock_client
        mock_client.neq.return_value = mock_client
        mock_client.in_.return_value = mock_client
        mock_client.or_.return_value = mock_client
        mock_client.order.return_value = mock_client
        mock_client.range.return_value = mock_client
        mock_client.insert.return_value = mock_client
        mock_client.update.return_value = mock_client
        mock_client.delete.return_value = mock_client
        
        # 默认返回空数据
        mock_client.execute.return_value = Mock(data=[])
        return mock_client
    
    @pytest.mark.asyncio
    async def test_create_product_success(self, sample_product_data, mock_supabase):
        """测试成功创建商品"""
        # 设置商品创建的mock返回值
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "product-123",
            "name": sample_product_data.name,
            "description": sample_product_data.description,
            "product_type": sample_product_data.product_type.value,
            "price_type": sample_product_data.price_type.value,
            "merchant_id": sample_product_data.merchant_id,
            "status": ProductStatus.DRAFT.value,
            "is_featured": False,
            "is_available_online": True,
            "requires_shipping": True,
            "is_taxable": True,
            "seo_title": None,
            "seo_description": None,
            "slug": None,
            "view_count": 0,
            "sale_count": 0,
            "average_rating": None,
            "review_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "published_at": None
        }]
        
        # 设置规格创建的mock返回值
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "variant-123",
            "product_id": "product-123",
            "sku": "TEST-SKU-001",
            "name": "默认规格",
            "price": 99.99,
            "original_price": 129.99,
            "stock_quantity": 100,
            "stock_threshold": 10,
            "is_default": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }]
        
        # Mock商家验证 - 商家存在且属于当前用户
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "merchant-123",
            "owner_id": "user-123"
        }]
        
        # Mock名称重复检查 - 没有重复
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock分类和标签验证 - 假设都存在
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        
        # Mock获取完整商品详情
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "product-123",
            "name": sample_product_data.name,
            "description": sample_product_data.description,
            "product_type": sample_product_data.product_type.value,
            "price_type": sample_product_data.price_type.value,
            "merchant_id": sample_product_data.merchant_id,
            "status": ProductStatus.DRAFT.value,
            "is_featured": False,
            "is_available_online": True,
            "requires_shipping": True,
            "is_taxable": True,
            "seo_title": None,
            "seo_description": None,
            "slug": None,
            "view_count": 0,
            "sale_count": 0,
            "average_rating": None,
            "review_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "published_at": None
        }]
        
        service = ProductService(mock_supabase)
        result = await service.create_product(sample_product_data, "user-123")
        
        assert result.name == sample_product_data.name
        assert result.status == ProductStatus.DRAFT
        assert result.merchant_id == sample_product_data.merchant_id
    
    @pytest.mark.asyncio
    async def test_create_product_duplicate_name(self, sample_product_data, mock_supabase):
        """测试创建重复名称的商品"""
        # Mock商家验证 - 商家存在且属于当前用户
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "merchant-123",
            "owner_id": "user-123"
        }]
        
        # Mock重复名称检查 - 发现重复商品
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{
            "id": "existing-product"
        }]
        
        service = ProductService(mock_supabase)
        
        with pytest.raises(ValueError, match="该商家下已存在相同名称的商品"):
            await service.create_product(sample_product_data, "user-123")
    
    @pytest.mark.asyncio
    async def test_create_product_merchant_not_found(self, sample_product_data, mock_supabase):
        """测试为不存在的商家创建商品"""
        # Mock商家验证 - 商家不存在
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        service = ProductService(mock_supabase)
        
        with pytest.raises(ValueError, match="商家不存在"):
            await service.create_product(sample_product_data, "user-123")
    
    @pytest.mark.asyncio
    async def test_create_product_permission_denied(self, sample_product_data, mock_supabase):
        """测试无权限创建商品"""
        # Mock商家验证 - 商家存在但所有者不是当前用户
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "merchant-123",
            "owner_id": "other-user"  # 其他用户
        }]
        
        service = ProductService(mock_supabase)
        
        with pytest.raises(PermissionError, match="无权为该商家创建商品"):
            await service.create_product(sample_product_data, "user-123")
    
    @pytest.mark.asyncio
    async def test_get_product_success(self, mock_supabase):
        """测试成功获取商品"""
        mock_product_data = {
            "id": "product-123",
            "name": "测试商品",
            "description": "测试描述",
            "product_type": "physical",
            "price_type": "fixed",
            "merchant_id": "merchant-123",
            "status": "active",
            "is_featured": False,
            "is_available_online": True,
            "requires_shipping": True,
            "is_taxable": True,
            "view_count": 0,
            "sale_count": 0,
            "average_rating": None,
            "review_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "published_at": None
        }
        
        # Mock商品数据查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_product_data]
        
        # Mock规格数据查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [{
            "id": "variant-123",
            "product_id": "product-123",
            "sku": "TEST-SKU-001",
            "name": "默认规格",
            "price": 99.99,
            "original_price": 129.99,
            "cost_price": None,
            "stock_quantity": 100,
            "stock_threshold": 10,
            "weight": None,
            "dimensions": None,
            "barcode": None,
            "is_default": True,
            "sort_order": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }]
        
        # Mock分类关联查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock标签关联查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock分类详细信息查询
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        
        # Mock标签详细信息查询
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        
        # Mock评价查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        service = ProductService(mock_supabase)
        result = await service._get_product_with_details("product-123")
        
        assert result is not None
        assert result.id == "product-123"
        assert result.name == "测试商品"
    
    @pytest.mark.asyncio
    async def test_bulk_update_status_success(self, mock_supabase):
        """测试批量更新商品状态"""
        # Mock商品查询
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "product-1", "merchant_id": "merchant-123"},
            {"id": "product-2", "merchant_id": "merchant-123"}
        ]
        
        # Mock商家查询
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "merchant-123", "owner_id": "user-123"}
        ]
        
        # Mock更新操作
        mock_supabase.table.return_value.update.return_value.in_.return_value.execute.return_value.data = [{}]
        
        # Mock上架时间更新检查
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "published_at": None
        }]
        
        service = ProductService(mock_supabase)
        update_data = BulkUpdateStatus(
            product_ids=["product-1", "product-2"],
            status=ProductStatus.ACTIVE
        )
        
        result = await service.bulk_update_status(update_data, "user-123")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_stock_success(self, mock_supabase):
        """测试更新商品库存"""
        # Mock商品查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "product-123",
            "merchant_id": "merchant-123"
        }]
        
        # Mock商家查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": "merchant-123",
            "owner_id": "user-123"
        }]
        
        # Mock规格查询
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"sku": "TEST-SKU-001", "stock_quantity": 50},
            {"sku": "TEST-SKU-002", "stock_quantity": 30}
        ]
        
        # Mock更新操作
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
        
        service = ProductService(mock_supabase)
        stock_updates = BulkStockUpdate(
            updates=[
                StockUpdate(
                    variant_sku="TEST-SKU-001",
                    quantity=20,
                    operation="increment"
                )
            ]
        )
        
        result = await service.update_stock("product-123", stock_updates, "user-123")
        assert result is True

class TestProductAPI:
    """商品API测试"""
    
    def setup_method(self):
        """测试方法设置"""
        self.valid_product_data = {
            "name": "测试商品",
            "description": "这是一个测试商品",
            "product_type": "physical",
            "price_type": "fixed",
            "merchant_id": "merchant-123",
            "variants": [
                {
                    "sku": "TEST-SKU-001",
                    "name": "默认规格",
                    "price": 99.99,
                    "original_price": 129.99,
                    "stock_quantity": 100,
                    "stock_threshold": 10,
                    "is_default": True
                }
            ]
        }
    
    @patch('app.routers.product_router.ProductService')
    @patch('app.routers.product_router.get_current_user')
    def test_create_product_success(self, mock_get_user, mock_product_service):
        """测试API成功创建商品"""
        # Mock依赖
        mock_instance = mock_product_service.return_value
        mock_instance.create_product = AsyncMock(return_value=ProductResponse(
            id="product-123",
            name="测试商品",
            description="这是一个测试商品",
            product_type=ProductType.PHYSICAL,
            price_type=PriceType.FIXED,
            status=ProductStatus.DRAFT,
            merchant_id="merchant-123",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            total_stock=100,
            low_stock_alert=False,
            categories=[],
            tags=[],
            is_featured=False,
            is_available_online=True,
            requires_shipping=True,
            is_taxable=True,
            seo_title=None,
            seo_description=None,
            slug=None,
            view_count=0,
            sale_count=0,
            average_rating=None,
            review_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            published_at=None
        ))
        
        mock_get_user.return_value = {"id": "user-123"}
        
        response = client.post("/api/products/", json=self.valid_product_data)
        
        assert response.status_code == 201
        assert response.json()["name"] == "测试商品"
        assert response.json()["status"] == "draft"
    
    @patch('app.routers.product_router.ProductService')
    @patch('app.routers.product_router.get_current_user')
    def test_create_product_invalid_data(self, mock_get_user, mock_product_service):
        """测试API创建商品时数据验证失败"""
        mock_get_user.return_value = {"id": "user-123"}
        
        invalid_data = {
            "name": "",  # 空名称
            "product_type": "physical",
            "merchant_id": "merchant-123",
            "variants": []  # 空规格列表
        }
        
        response = client.post("/api/products/", json=invalid_data)
        
        assert response.status_code == 422  # 验证错误
    
    @patch('app.routers.product_router.ProductService')
    def test_get_product_success(self, mock_product_service):
        """测试API成功获取商品详情"""
        mock_instance = mock_product_service.return_value
        mock_instance.get_product = AsyncMock(return_value=ProductResponse(
            id="product-123",
            name="测试商品",
            description="这是一个测试商品",
            product_type=ProductType.PHYSICAL,
            price_type=PriceType.FIXED,
            status=ProductStatus.ACTIVE,
            merchant_id="merchant-123",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            total_stock=100,
            low_stock_alert=False,
            categories=[],
            tags=[],
            is_featured=False,
            is_available_online=True,
            requires_shipping=True,
            is_taxable=True,
            seo_title=None,
            seo_description=None,
            slug=None,
            view_count=0,
            sale_count=0,
            average_rating=None,
            review_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            published_at=None
        ))
        
        response = client.get("/api/products/product-123")
        
        assert response.status_code == 200
        assert response.json()["id"] == "product-123"
    
    @patch('app.routers.product_router.ProductService')
    def test_get_product_not_found(self, mock_product_service):
        """测试API获取不存在的商品"""
        mock_instance = mock_product_service.return_value
        mock_instance.get_product = AsyncMock(return_value=None)
        
        response = client.get("/api/products/non-existent-product")
        
        assert response.status_code == 404
    
    @patch('app.routers.product_router.ProductService')
    @patch('app.routers.product_router.get_current_user')
    def test_bulk_update_status_success(self, mock_get_user, mock_product_service):
        """测试API批量更新商品状态"""
        mock_instance = mock_product_service.return_value
        mock_instance.bulk_update_status = AsyncMock(return_value=True)
        
        mock_get_user.return_value = {"id": "user-123"}
        
        update_data = {
            "product_ids": ["product-1", "product-2"],
            "status": "active"
        }
        
        response = client.post("/api/products/bulk/status", json=update_data)
        
        assert response.status_code == 200
        assert "成功上架 2 个商品" in response.json()["message"]
    
    @patch('app.routers.product_router.ProductService')
    @patch('app.routers.product_router.get_current_user')
    def test_publish_product_success(self, mock_get_user, mock_product_service):
        """测试API上架商品"""
        mock_instance = mock_product_service.return_value
        mock_instance.bulk_update_status = AsyncMock(return_value=True)
        mock_instance.get_product = AsyncMock(return_value=ProductResponse(
            id="product-123",
            name="测试商品",
            description="这是一个测试商品",
            product_type=ProductType.PHYSICAL,
            price_type=PriceType.FIXED,
            status=ProductStatus.ACTIVE,
            merchant_id="merchant-123",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            total_stock=100,
            low_stock_alert=False,
            categories=[],
            tags=[],
            is_featured=False,
            is_available_online=True,
            requires_shipping=True,
            is_taxable=True,
            seo_title=None,
            seo_description=None,
            slug=None,
            view_count=0,
            sale_count=0,
            average_rating=None,
            review_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            published_at=datetime.utcnow()
        ))
        
        mock_get_user.return_value = {"id": "user-123"}
        
        response = client.post("/api/products/product-123/publish")
        
        assert response.status_code == 200
        assert response.json()["status"] == "active"

# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])