# app/api/verification.py
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from app.services.verification_service import verification_service
from app.models.verification import BatchVerificationRequest
from app.schemas.order import OrderResponse

router = APIRouter()

@router.post("/verification/code", response_model=OrderResponse)
async def verify_by_code(
    verification_code: str,
    staff_id: str,
    staff_name: str
):
    """通过核销码核销订单"""
    order = await verification_service.verify_order_by_code(
        verification_code, staff_id, staff_name
    )
    
    if not order:
        raise HTTPException(status_code=400, detail="核销失败，订单不存在或状态不正确")
    
    return OrderResponse(message="核销成功", data=order)

@router.post("/verification/qr", response_model=OrderResponse)
async def verify_by_qr(
    qr_data: str,
    staff_id: str,
    staff_name: str
):
    """通过二维码核销订单"""
    order = await verification_service.verify_order_by_qr(qr_data, staff_id, staff_name)
    
    if not order:
        raise HTTPException(status_code=400, detail="核销失败，订单不存在或状态不正确")
    
    return OrderResponse(message="核销成功", data=order)

@router.post("/verification/batch")
async def batch_verify_orders(batch_request: BatchVerificationRequest):
    """批量核销订单"""
    result = await verification_service.batch_verify_orders(batch_request)
    
    return {
        "message": "批量核销完成",
        "data": result
    }

@router.get("/verification/records")
async def get_verification_records(
    merchant_id: str = Query(..., description="商家ID"),
    staff_id: Optional[str] = Query(None, description="员工ID"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取核销记录"""
    records, total_count = await verification_service.get_verification_records(
        merchant_id=merchant_id,
        staff_id=staff_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    return {
        "message": "获取核销记录成功",
        "data": {
            "records": records,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    }

@router.get("/verification/staff-stats")
async def get_staff_verification_stats(
    merchant_id: str = Query(..., description="商家ID"),
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """获取员工核销统计"""
    stats = await verification_service.get_staff_verification_stats(merchant_id, days)
    
    return {
        "message": "获取员工统计成功",
        "data": stats
    }