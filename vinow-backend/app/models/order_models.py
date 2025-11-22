# app/models/order.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"           # 待核销
    VERIFIED = "verified"         # 已核销
    REFUNDING = "refunding"       # 退款中
    REFUNDED = "refunded"         # 已退款
    COMPLETED = "completed"       # 已完成
    CANCELLED = "cancelled"       # 已取消

class PaymentMethod(str, Enum):
    """支付方式枚举"""
    MOMO = "momo"
    ZALO_PAY = "zalo_pay"
    CASH = "cash"
    BANK_CARD = "bank_card"
    CREDIT_CARD = "credit_card"

class OrderBase(BaseModel):
    """订单基础模型"""
    order_number: str = Field(..., description="订单号")
    user_id: str = Field(..., description="用户ID")
    user_phone: str = Field(..., description="用户手机号")
    user_name: str = Field(..., description="用户姓名")
    
    product_name: str = Field(..., description="商品名称")
    product_id: str = Field(..., description="商品ID")
    quantity: int = Field(1, description="购买数量")
    unit_price: float = Field(..., description="商品单价")
    total_amount: float = Field(..., description="订单总金额")
    discount_amount: float = Field(0.0, description="优惠金额")
    paid_amount: float = Field(..., description="实付金额")
    
    payment_method: PaymentMethod = Field(..., description="支付方式")
    status: OrderStatus = Field(OrderStatus.PENDING, description="订单状态")
    
    verification_code: str = Field(..., description="核销码")
    merchant_id: str = Field(..., description="商家ID")
    store_id: str = Field(..., description="门店ID")

class OrderCreate(OrderBase):
    """创建订单模型"""
    pass

class OrderUpdate(BaseModel):
    """更新订单模型"""
    status: Optional[OrderStatus] = None
    verification_code: Optional[str] = None
    refund_reason: Optional[str] = None

class OrderInDB(OrderBase):
    """数据库中的订单模型"""
    id: str = Field(..., description="订单ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    verified_at: Optional[datetime] = Field(None, description="核销时间")
    refunded_at: Optional[datetime] = Field(None, description="退款时间")
    
    class Config:
        from_attributes = True

class OrderListItem(BaseModel):
    """订单列表项模型"""
    id: str
    order_number: str
    user_name: str
    user_phone: str
    product_name: str
    quantity: int
    total_amount: float
    paid_amount: float
    status: OrderStatus
    payment_method: PaymentMethod
    created_at: datetime
    verified_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True"""商家系统 - order_models"""

# TODO: 实现商家系统相关功能


交易系统

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import Field, validator
from .base import BaseModelMixin

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class OrderItem(BaseModelMixin):
    order_id: str = Field(..., description="订单ID")
    product_id: str = Field(..., description="商品ID")
    product_name: str = Field(..., description="商品名称")
    product_image: Optional[str] = Field(None, description="商品图片")
    unit_price: float = Field(..., ge=0, description="单价")
    quantity: int = Field(..., ge=1, description="数量")
    total_price: float = Field(..., ge=0, description="总价")
    
    @validator('total_price')
    def validate_total_price(cls, v, values):
        if 'unit_price' in values and 'quantity' in values:
            expected = values['unit_price'] * values['quantity']
            if abs(v - expected) > 0.01:  # 允许浮点数误差
                raise ValueError(f"Total price {v} doesn't match unit_price * quantity")
        return v

class Order(BaseModelMixin):
    order_number: str = Field(..., description="订单号")
    user_id: str = Field(..., description="用户ID")
    merchant_id: str = Field(..., description="商家ID")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="订单状态")
    total_amount: float = Field(..., ge=0, description="订单总金额")
    discount_amount: float = Field(default=0, ge=0, description="折扣金额")
    final_amount: float = Field(..., ge=0, description="实付金额")
    currency: str = Field(default="VND", description="货币")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="收货地址")
    contact_info: Optional[Dict[str, Any]] = Field(None, description="联系信息")
    expires_at: Optional[datetime] = Field(None, description="订单过期时间")
    paid_at: Optional[datetime] = Field(None, description="支付时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    cancelled_at: Optional[datetime] = Field(None, description="取消时间")
    cancellation_reason: Optional[str] = Field(None, description="取消原因")
    items: List[OrderItem] = Field(default_factory=list, description="订单项")
    
    @validator('final_amount')
    def validate_final_amount(cls, v, values):
        if 'total_amount' in values and 'discount_amount' in values:
            expected = values['total_amount'] - values['discount_amount']
            if v < 0:
                raise ValueError("Final amount cannot be negative")
            if abs(v - expected) > 0.01:
                raise ValueError(f"Final amount {v} doesn't match total_amount - discount_amount")
        return v

class OrderStatistics(BaseModel):
    total_orders: int = Field(..., description="总订单数")
    total_amount: float = Field(..., description="总金额")
    pending_orders: int = Field(..., description="待处理订单")
    completed_orders: int = Field(..., description="已完成订单")
    cancelled_orders: int = Field(..., description="已取消订单")
    average_order_value: float = Field(..., description="平均订单价值")
