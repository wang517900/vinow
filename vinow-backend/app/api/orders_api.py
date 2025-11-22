# app/api/orders.py
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from app.services.order_service import order_service
from app.models.order import OrderInDB, OrderListItem, OrderStatus
from app.schemas.order import OrderResponse, OrderListResponse, OrderStatsResponse

router = APIRouter()

@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    merchant_id: str = Query(..., description="商家ID"),
    status: Optional[OrderStatus] = Query(None, description="订单状态"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取订单列表"""
    try:
        orders, total_count = await order_service.list_orders(
            merchant_id=merchant_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
            search=search
        )
        
        return OrderListResponse(
            orders=orders,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单列表失败: {str(e)}")

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """获取订单详情"""
    order = await order_service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    return OrderResponse(data=order)

@router.get("/orders/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(order_number: str):
    """根据订单号获取订单"""
    order = await order_service.get_order_by_number(order_number)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    return OrderResponse(data=order)

@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    status: OrderStatus,
    refund_reason: Optional[str] = None
):
    """更新订单状态"""
    kwargs = {}
    if refund_reason:
        kwargs["refund_reason"] = refund_reason
    
    order = await order_service.update_order_status(order_id, status, **kwargs)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在或更新失败")
    
    return {"message": "订单状态更新成功", "data": order}

@router.get("/merchants/{merchant_id}/stats/today")
async def get_today_stats(merchant_id: str):
    """获取今日统计"""
    stats = await order_service.get_today_stats(merchant_id)
    return {"message": "获取统计成功", "data": stats}

@router.get("/merchants/{merchant_id}/orders/recent")
async def get_recent_orders(
    merchant_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """获取最近订单"""
    orders = await order_service.get_recent_orders(merchant_id, limit)
    return {"message": "获取最近订单成功", "data": orders}


    交易系统

    from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse, OrderUpdate, OrderQueryParams
from app.services.order_service import OrderService
from app.middleware.auth import JWTBearer
from app.utils.logger import logger

router = APIRouter(prefix="/orders", tags=["orders"])
order_service = OrderService()

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    user_info: dict = Depends(JWTBearer())
):
    """创建订单"""
    try:
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        order = await order_service.create_order(order_data, user_id)
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create order error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    user_info: dict = Depends(JWTBearer())
):
    """获取订单详情"""
    try:
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        order = await order_service.get_order_by_id(order_id, user_id)
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderUpdate,
    user_info: dict = Depends(JWTBearer())
):
    """更新订单状态"""
    try:
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        if not status_update.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required"
            )
        
        order = await order_service.update_order_status(
            order_id, 
            status_update.status, 
            user_id,
            status_update.cancellation_reason
        )
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update order status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(default=1, ge=1, description="页码"),
    size: int = Query(default=20, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="订单状态"),
    merchant_id: Optional[str] = Query(None, description="商家ID"),
    start_date: Optional[str] = Query(None, description="开始时间"),
    end_date: Optional[str] = Query(None, description="结束时间"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    user_info: dict = Depends(JWTBearer())
):
    """查询订单列表"""
    try:
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        # 构建查询参数
        query_params = OrderQueryParams(
            page=page,
            size=size,
            status=status,
            merchant_id=merchant_id,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
        
        result = await order_service.list_orders(query_params, user_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List orders error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{order_id}/statistics")
async def get_order_statistics(
    days: int = Query(default=30, ge=1, le=365, description="统计天数"),
    user_info: dict = Depends(JWTBearer())
):
    """获取订单统计"""
    try:
        user_id = user_info.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        statistics = await order_service.get_order_statistics(user_id, days)
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order statistics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )