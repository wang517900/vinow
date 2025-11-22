# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re
from decimal import Decimal

class ProductStatus(str, Enum):
    """商品状态枚举"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 上架
    INACTIVE = "inactive"     # 下架
    SOLD_OUT = "sold_out"     # 售罄
    DELETED = "deleted"       # 已删除

class ProductType(str, Enum):
    """商品类型枚举"""
    PHYSICAL = "physical"     # 实物商品
    DIGITAL = "digital"       # 数字商品
    SERVICE = "service"       # 服务类商品

class PriceType(str, Enum):
    """价格类型枚举"""
    FIXED = "fixed"           # 固定价格
    VARIABLE = "variable"     # 可变价格（如按重量、时间等）

class ProductCategory(BaseModel):
    """商品分类模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    id: str = Field(..., description="分类ID")
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    parent_id: Optional[str] = Field(None, description="父分类ID")
    level: int = Field(1, ge=1, le=5, description="分类层级")
    sort_order: int = Field(0, ge=0, description="排序序号")
    is_active: bool = Field(True, description="是否启用")

class ProductTag(BaseModel):
    """商品标签模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    id: str = Field(..., description="标签ID")
    name: str = Field(..., min_length=1, max_length=20, description="标签名称")
    color: Optional[str] = Field(None, description="标签颜色")
    is_active: bool = Field(True, description="是否启用")

class ProductVariant(BaseModel):
    """商品规格变体模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    sku: str = Field(..., min_length=1, max_length=50, description="SKU编码")
    name: str = Field(..., min_length=1, max_length=100, description="规格名称")
    price: Decimal = Field(..., gt=0, description="价格")
    original_price: Optional[Decimal] = Field(None, gt=0, description="原价")
    cost_price: Optional[Decimal] = Field(None, ge=0, description="成本价")
    stock_quantity: int = Field(0, ge=0, description="库存数量")
    stock_threshold: int = Field(0, ge=0, description="库存预警阈值")
    weight: Optional[float] = Field(None, ge=0, description="重量(kg)")
    dimensions: Optional[str] = Field(None, description="尺寸")
    barcode: Optional[str] = Field(None, description="条形码")
    is_default: bool = Field(False, description="是否默认规格")
    sort_order: int = Field(0, ge=0, description="排序序号")
    
    @field_validator('price', 'original_price', 'cost_price')
    @classmethod
    def validate_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """验证价格格式，确保价格有2位小数"""
        if v is not None:
            # 确保价格有2位小数
            return v.quantize(Decimal('0.01'))
        return v
    
    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        """
        SKU 只能包含：字母、数字、下划线、横杠
        并且必须是完整匹配
        """
        pattern = r"^[A-Za-z0-9_-]+$"
        if not re.fullmatch(pattern, v):
            raise ValueError("SKU只能包含字母、数字、下划线和连字符")
        return v
class ProductCreate(BaseModel):
    """商品创建模型"""
    model_config = ConfigDict(str_strip_whitespace=True)  # 自动去除字符串首尾空格
    
    name: str = Field(..., min_length=1, max_length=200, description="商品名称")
    description: Optional[str] = Field(None, max_length=2000, description="商品描述")
    short_description: Optional[str] = Field(None, max_length=500, description="商品短描述")
    product_type: ProductType = Field(..., description="商品类型")
    price_type: PriceType = Field(PriceType.FIXED, description="价格类型")
    category_ids: List[str] = Field(default_factory=list, description="分类ID列表")
    tag_ids: List[str] = Field(default_factory=list, description="标签ID列表")
    merchant_id: str = Field(..., description="商家ID")
    variants: List[ProductVariant] = Field(..., min_length=1, description="商品规格列表")  # 修正：min_items -> min_length
    
    # 商品属性
    is_featured: bool = Field(False, description="是否推荐商品")
    is_available_online: bool = Field(True, description="是否在线销售")
    requires_shipping: bool = Field(True, description="是否需要配送")
    is_taxable: bool = Field(True, description="是否可征税")
    
    # SEO 相关
    seo_title: Optional[str] = Field(None, max_length=70, description="SEO标题")
    seo_description: Optional[str] = Field(None, max_length=160, description="SEO描述")
    slug: Optional[str] = Field(None, description="商品链接别名")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证商品名称，确保不为空"""
        v = v.strip()
        if len(v) < 1:
            raise ValueError('商品名称不能为空')
        return v
    
    @field_validator('variants')
    @classmethod
    def validate_variants(cls, v: List[ProductVariant]) -> List[ProductVariant]:
        """验证商品规格，确保至少有一个规格且SKU不重复，有且仅有一个默认规格"""
        if not v:
            raise ValueError('至少需要一个商品规格')
        
        # 检查SKU是否重复
        skus = [variant.sku for variant in v]
        if len(skus) != len(set(skus)):
            raise ValueError('SKU编码不能重复')
        
        # 确保有且仅有一个默认规格
        default_variants = [variant for variant in v if variant.is_default]
        if len(default_variants) != 1:
            raise ValueError('必须有且仅有一个默认规格')
        
        return v
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """验证slug格式，只能包含小写字母、数字和连字符"""
        if v is not None:
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Slug只能包含小写字母、数字和连字符')
        return v

class ProductUpdate(BaseModel):
    """商品更新模型"""
    model_config = ConfigDict(str_strip_whitespace=True)  # 自动去除字符串首尾空格
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="商品名称")
    description: Optional[str] = Field(None, max_length=2000, description="商品描述")
    short_description: Optional[str] = Field(None, max_length=500, description="商品短描述")
    product_type: Optional[ProductType] = None
    price_type: Optional[PriceType] = None
    category_ids: Optional[List[str]] = None
    tag_ids: Optional[List[str]] = None
    status: Optional[ProductStatus] = None
    
    # 商品属性
    is_featured: Optional[bool] = None
    is_available_online: Optional[bool] = None
    requires_shipping: Optional[bool] = None
    is_taxable: Optional[bool] = None
    
    # SEO 相关
    seo_title: Optional[str] = Field(None, max_length=70, description="SEO标题")
    seo_description: Optional[str] = Field(None, max_length=160, description="SEO描述")
    slug: Optional[str] = Field(None, description="商品链接别名")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """验证商品名称，确保不为空"""
        if v is not None:
            v = v.strip()
            if len(v) < 1:
                raise ValueError('商品名称不能为空')
        return v
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """验证slug格式，只能包含小写字母、数字和连字符"""
        if v is not None:
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Slug只能包含小写字母、数字和连字符')
        return v

class ProductResponse(BaseModel):
    """商品响应模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    id: str = Field(..., description="商品ID")
    name: str = Field(..., description="商品名称")
    description: Optional[str] = Field(None, description="商品描述")
    short_description: Optional[str] = Field(None, description="商品短描述")
    product_type: ProductType = Field(..., description="商品类型")
    price_type: PriceType = Field(..., description="价格类型")
    status: ProductStatus = Field(..., description="商品状态")
    merchant_id: str = Field(..., description="商家ID")
    
    # 价格信息（从默认规格获取）
    price: Decimal = Field(..., description="价格")
    original_price: Optional[Decimal] = Field(None, description="原价")
    
    # 库存信息
    total_stock: int = Field(..., description="总库存")
    low_stock_alert: bool = Field(..., description="库存预警")
    
    # 分类和标签
    categories: List[ProductCategory] = Field(default_factory=list, description="分类列表")
    tags: List[ProductTag] = Field(default_factory=list, description="标签列表")
    
    # 商品属性
    is_featured: bool = Field(..., description="是否推荐商品")
    is_available_online: bool = Field(..., description="是否在线销售")
    requires_shipping: bool = Field(..., description="是否需要配送")
    is_taxable: bool = Field(..., description="是否可征税")
    
    # SEO 相关
    seo_title: Optional[str] = Field(None, description="SEO标题")
    seo_description: Optional[str] = Field(None, description="SEO描述")
    slug: Optional[str] = Field(None, description="商品链接别名")
    
    # 统计信息
    view_count: int = Field(0, description="浏览量")
    sale_count: int = Field(0, description="销量")
    average_rating: Optional[float] = Field(None, ge=0, le=5, description="平均评分")
    review_count: int = Field(0, description="评价数量")
    
    # 时间信息
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    published_at: Optional[datetime] = Field(None, description="上架时间")

class ProductListResponse(BaseModel):
    """商品列表响应模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    products: List[ProductResponse] = Field(..., description="商品列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")

class ProductSearchParams(BaseModel):
    """商品搜索参数"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    query: Optional[str] = Field(None, description="搜索关键词")
    merchant_id: Optional[str] = Field(None, description="商家ID")
    category_id: Optional[str] = Field(None, description="分类ID")
    tag_id: Optional[str] = Field(None, description="标签ID")
    product_type: Optional[ProductType] = Field(None, description="商品类型")
    status: Optional[ProductStatus] = Field(None, description="商品状态")
    min_price: Optional[Decimal] = Field(None, ge=0, description="最低价格")
    max_price: Optional[Decimal] = Field(None, ge=0, description="最高价格")
    in_stock_only: bool = Field(False, description="仅显示有库存")
    is_featured: Optional[bool] = Field(None, description="是否推荐商品")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")

class BulkUpdateStatus(BaseModel):
    """批量更新状态模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    product_ids: List[str] = Field(..., min_length=1, description="商品ID列表")  # 修正：min_items -> min_length
    status: ProductStatus = Field(..., description="目标状态")

class StockUpdate(BaseModel):
    """库存更新模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    variant_sku: str = Field(..., description="规格SKU")
    quantity: int = Field(..., description="库存数量")
    operation: str = Field(..., description="操作类型: set, increment, decrement")
    
    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """验证操作类型，必须是 set, increment 或 decrement"""
        if v not in ['set', 'increment', 'decrement']:
            raise ValueError('操作类型必须是 set, increment 或 decrement')
        return v

class BulkStockUpdate(BaseModel):
    """批量库存更新模型"""
    model_config = ConfigDict(from_attributes=True)  # 启用 ORM 模式支持
    
    updates: List[StockUpdate] = Field(..., min_length=1, description="库存更新列表")  # 修正：min_items -> min_length