# app/api/refunds.py
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.refund_service import refund_service
from app.schemas.order import RefundRequest, RefundApprovalRequest, OrderResponse

router = APIRouter()

@router.post("/refunds/request", response_model=OrderResponse)
async def request_refund(refund_request: RefundRequest):
    """申请退款"""
    order = await refund_service.create_refund_request(
        order_id=refund_request.order_id,
        reason=refund_request.reason,
        explanation=refund_request.explanation,
        evidence_images=refund_request.evidence_images
    )
    
    if not order:
        raise HTTPException(status_code=400, detail="退款申请失败")
    
    return OrderResponse(message="退款申请提交成功", data=order)

@router.post("/refunds/{order_id}/approve", response_model=OrderResponse)
async def approve_refund(order_id: str, approval_request: RefundApprovalRequest):
    """批准退款"""
    order = await refund_service.approve_refund(
        order_id, approval_request.processed_by
    )
    
    if not order:
        raise HTTPException(status_code=400, detail="批准退款失败")
    
    return OrderResponse(message="退款批准成功", data=order)

@router.post("/refunds/{order_id}/reject", response_model=OrderResponse)
async def reject_refund(order_id: str, approval_request: RefundApprovalRequest):
    """拒绝退款"""
    if not approval_request.reject_reason:
        raise HTTPException(status_code=400, detail="拒绝退款必须提供原因")
    
    order = await refund_service.reject_refund(
        order_id, 
        approval_request.reject_reason, 
        approval_request.processed_by
    )
    
    if not order:
        raise HTTPException(status_code=400, detail="拒绝退款失败")
    
    return OrderResponse(message="退款拒绝成功", data=order)

@router.get("/refunds/pending")
async def get_pending_refunds(
    merchant_id: str = Query(..., description="商家ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取待处理退款申请"""
    orders, total_count = await refund_service.get_pending_refunds(
        merchant_id, page, page_size
    )
    
    return {
        "message": "获取退款申请成功",
        "data": {
            "orders": orders,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    }