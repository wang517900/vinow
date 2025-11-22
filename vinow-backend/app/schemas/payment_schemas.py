交易系统

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator

class PaymentMethod(str, Enum):
    """
    支付方式枚举类
    定义系统支持的所有支付方式
    """
    MOMO = "momo"
    ZALOPAY = "zalopay"
    VNPAY = "vnpay"
    CREDIT_CARD = "credit_card"
    BALANCE = "balance"

class PaymentStatus(str, Enum):
    """
    支付状态枚举类
    定义支付流程中可能出现的所有状态
    """
    PENDING = "pending"           # 待支付
    PROCESSING = "processing"     # 处理中
    SUCCESS = "success"           # 支付成功
    FAILED = "failed"             # 支付失败
    CANCELLED = "cancelled"       # 已取消
    REFUNDED = "refunded"         # 已退款

class PaymentCreate(BaseModel):
    """
    创建支付请求数据模型
    用于客户端发起支付请求时的数据验证
    """
    order_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="订单ID",
        example="ORD202312010001"
    )
    method: PaymentMethod = Field(
        ..., 
        description="支付方式",
        example=PaymentMethod.MOMO
    )
    amount: float = Field(
        ..., 
        gt=0, 
        le=100000000,  # 限制最大金额为1亿
        description="支付金额(单位: 分)",
        example=150000
    )
    currency: str = Field(
        default="VND", 
        min_length=3,
        max_length=3,
        description="货币代码",
        example="VND"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="支付元数据，可用于存储额外信息"
    )
    
    @validator('currency')
    def validate_currency(cls, v: str) -> str:
        """验证货币代码必须为大写"""
        if v != v.upper():
            raise ValueError('Currency code must be uppercase')
        return v

class PaymentResponse(BaseModel):
    """
    支付响应数据模型
    用于向客户端返回支付相关信息
    """
    id: str = Field(
        ...,
        description="支付记录唯一标识符",
        example="pay_123e4567-e89b-12d3-a456-426614174000"
    )
    order_id: str = Field(
        ...,
        description="关联的订单ID",
        example="ORD202312010001"
    )
    payment_number: str = Field(
        ...,
        description="支付流水号，用于与第三方支付平台对账",
        example="PMT2023120100001"
    )
    method: PaymentMethod = Field(
        ...,
        description="使用的支付方式",
        example=PaymentMethod.ZALOPAY
    )
    amount: float = Field(
        ...,
        description="支付金额(单位: 分)",
        example=150000
    )
    currency: str = Field(
        ...,
        description="货币代码",
        example="VND"
    )
    status: PaymentStatus = Field(
        ...,
        description="当前支付状态",
        example=PaymentStatus.PENDING
    )
    gateway_transaction_id: Optional[str] = Field(
        None,
        description="第三方支付网关的交易ID",
        example="GTX2023120100001"
    )
    gateway_response: Optional[Dict[str, Any]] = Field(
        None,
        description="来自第三方支付网关的原始响应数据"
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="支付完成时间"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="支付过期时间，超过此时间支付将被拒绝"
    )
    created_at: datetime = Field(
        ...,
        description="支付记录创建时间"
    )
    updated_at: datetime = Field(
        ...,
        description="支付记录最后更新时间"
    )
    
    class Config:
        """Pydantic模型配置"""
        from_attributes = True  # 允许从ORM模型转换
        
        # 示例数据用于API文档
        json_schema_extra = {
            "example": {
                "id": "pay_123e4567-e89b-12d3-a456-426614174000",
                "order_id": "ORD202312010001",
                "payment_number": "PMT2023120100001",
                "method": "momo",
                "amount": 150000,
                "currency": "VND",
                "status": "pending",
                "gateway_transaction_id": "GTX2023120100001",
                "gateway_response": {"result_code": 0},
                "paid_at": "2023-12-01T10:30:00Z",
                "expires_at": "2023-12-01T11:00:00Z",
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T10:00:00Z"
            }
        }

class PaymentCallback(BaseModel):
    """
    支付回调数据模型
    用于接收第三方支付平台的回调通知
    """
    payment_id: str = Field(
        ...,
        description="本地支付ID",
        example="pay_123e4567-e89b-12d3-a456-426614174000"
    )
    transaction_id: str = Field(
        ...,
        description="第三方支付网关交易ID",
        example="TXN2023120100001"
    )
    status: PaymentStatus = Field(
        ...,
        description="支付结果状态",
        example=PaymentStatus.SUCCESS
    )
    amount: float = Field(
        ...,
        gt=0,
        description="实际支付金额(单位: 分)",
        example=150000
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="货币代码",
        example="VND"
    )
    signature: str = Field(
        ...,
        description="回调签名，用于验证回调的真实性",
        example="a1b2c3d4e5f6..."
    )
    timestamp: datetime = Field(
        ...,
        description="回调时间戳",
        example="2023-12-01T10:30:00Z"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="回调附加数据"
    )
    
    @validator('currency')
    def validate_currency(cls, v: str) -> str:
        """验证货币代码必须为大写"""
        if v != v.upper():
            raise ValueError('Currency code must be uppercase')
        return v
    
    class Config:
        """Pydantic模型配置"""
        # 示例数据用于API文档
        json_schema_extra = {
            "example": {
                "payment_id": "pay_123e4567-e89b-12d3-a456-426614174000",
                "transaction_id": "TXN2023120100001",
                "status": "success",
                "amount": 150000,
                "currency": "VND",
                "signature": "a1b2c3d4e5f67890...",
                "timestamp": "2023-12-01T10:30:00Z",
                "metadata": {"bank_code": "VCB"}
            }
        }