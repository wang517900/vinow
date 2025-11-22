# app/models/verification.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class VerificationRecordBase(BaseModel):
    """核销记录基础模型"""
    order_id: str = Field(..., description="订单ID")
    merchant_id: str = Field(..., description="商家ID")
    store_id: str = Field(..., description="门店ID")
    staff_id: str = Field(..., description="员工ID")
    staff_name: str = Field(..., description="员工姓名")
    verification_method: str = Field(..., description="核销方式: scan_qr, manual, batch")

class VerificationRecordCreate(VerificationRecordBase):
    """创建核销记录模型"""
    pass

class VerificationRecordInDB(VerificationRecordBase):
    """数据库中的核销记录模型"""
    id: str = Field(..., description="核销记录ID")
    created_at: datetime = Field(..., description="核销时间")
    
    class Config:
        from_attributes = True

class BatchVerificationRequest(BaseModel):
    """批量核销请求模型"""
    order_ids: list[str] = Field(..., description="订单ID列表")
    staff_id: str = Field(..., description="员工ID")
    staff_name: str = Field(..., description="员工姓名")