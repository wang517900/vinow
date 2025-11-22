# app/schemas/order.py
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.order import OrderStatus, PaymentMethod

class OrderResponse(BaseModel):
    """订单响应模型"""
    message: str = "成功"
    data: Optional[Any] = None

class OrderListResponse(BaseModel):
    """订单列表响应模型"""
    orders: List[Any]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class OrderStatsResponse(BaseModel):
    """订单统计响应模型"""
    total_orders: int
    pending_orders: int
    completed_amount: float
    verification_rate: float

class RefundRequest(BaseModel):
    """退款请求模型"""
    order_id: str = Field(..., description="订单ID")
    reason: str = Field(..., description="退款原因")
    explanation: Optional[str] = Field(None, description="详细说明")
    evidence_images: Optional[List[str]] = Field(None, description="证据图片")

class RefundApprovalRequest(BaseModel):
    """退款审批请求模型"""
    processed_by: str = Field(..., description="处理人员")
    reject_reason: Optional[str] = Field(None, description="拒绝原因")

class OrderTrendResponse(BaseModel):
    """订单趋势响应模型"""
    period: str
    trends: List[dict]

class ProductRankingResponse(BaseModel):
    """商品排行响应模型"""
    products: List[dict]

class DailyReportResponse(BaseModel):
    """日报表响应模型"""
    report_date: str
    total_orders: int
    verified_orders: int
    pending_orders: int
    refunded_orders: int
    total_amount: float
    verified_amount: float
    verification_rate: float
    payment_method_distribution: dict
    average_order_value: float


    交易系统

    from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.models.order import OrderStatus

class OrderItemCreate(BaseModel):
    product_id: str = Field(..., min_length=1, description="商品ID")
    product_name: str = Field(..., min_length=1, max_length=255, description="商品名称")
    product_image: Optional[str] = Field(None, description="商品图片")
    unit_price: float = Field(..., gt=0, description="单价")
    quantity: int = Field(..., gt=0, description="数量")

class OrderCreate(BaseModel):
    merchant_id: str = Field(..., min_length=1, description="商家ID")
    items: List[OrderItemCreate] = Field(..., min_items=1, description="订单项列表")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="收货地址")
    contact_info: Optional[Dict[str, Any]] = Field(None, description="联系信息")
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = Field(None, description="订单状态")
    cancellation_reason: Optional[str] = Field(None, max_length=500, description="取消原因")

class OrderResponse(BaseModel):
    id: str = Field(..., description="订单ID")
    order_number: str = Field(..., description="订单号")
    user_id: str = Field(..., description="用户ID")
    merchant_id: str = Field(..., description="商家ID")
    status: OrderStatus = Field(..., description="订单状态")
    total_amount: float = Field(..., description="订单总金额")
    discount_amount: float = Field(..., description="折扣金额")
    final_amount: float = Field(..., description="实付金额")
    currency: str = Field(..., description="货币")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="收货地址")
    contact_info: Optional[Dict[str, Any]] = Field(None, description="联系信息")
    expires_at: Optional[datetime] = Field(None, description="订单过期时间")
    paid_at: Optional[datetime] = Field(None, description="支付时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    cancelled_at: Optional[datetime] = Field(None, description="取消时间")
    cancellation_reason: Optional[str] = Field(None, description="取消原因")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    items: List[OrderResponse] = Field(..., description="订单列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    has_next: bool = Field(..., description="是否有下一页")

class OrderQueryParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    status: Optional[OrderStatus] = Field(None, description="订单状态")
    merchant_id: Optional[str] = Field(None, description="商家ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    search: Optional[str] = Field(None, description="搜索关键词")
