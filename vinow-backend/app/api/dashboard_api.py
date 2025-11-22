# app/api/dashboard.py
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.services.analytics_service import analytics_service
from app.services.refund_service import refund_service
from app.schemas.order import OrderTrendResponse, ProductRankingResponse, DailyReportResponse

router = APIRouter()

@router.get("/dashboard/order-trends")
async def get_order_trends(
    merchant_id: str = Query(..., description="商家ID"),
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """获取订单趋势"""
    trends_data = await analytics_service.get_order_trends(merchant_id, days)
    
    return {
        "message": "获取订单趋势成功",
        "data": trends_data
    }

@router.get("/dashboard/verification-hours")
async def get_verification_hours(
    merchant_id: str = Query(..., description="商家ID"),
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """获取核销时间段分布"""
    hourly_data = await analytics_service.get_verification_hourly_stats(merchant_id, days)
    
    return {
        "message": "获取核销时间段分布成功",
        "data": hourly_data
    }

@router.get("/dashboard/top-products")
async def get_top_products(
    merchant_id: str = Query(..., description="商家ID"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """获取热销商品排行"""
    products = await analytics_service.get_top_products(merchant_id, limit, days)
    
    return {
        "message": "获取热销商品成功",
        "data": products
    }

@router.get("/dashboard/daily-report")
async def get_daily_report(
    merchant_id: str = Query(..., description="商家ID"),
    report_date: Optional[datetime] = Query(None, description="报告日期")
):
    """获取日报表"""
    report = await analytics_service.get_daily_report(merchant_id, report_date)
    
    if not report:
        raise HTTPException(status_code=404, detail="生成日报表失败")
    
    return {
        "message": "获取日报表成功",
        "data": report
    }

@router.get("/dashboard/refund-stats")
async def get_refund_stats(
    merchant_id: str = Query(..., description="商家ID"),
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """获取退款统计"""
    stats = await refund_service.get_refund_stats(merchant_id, days)
    
    return {
        "message": "获取退款统计成功",
        "data": stats
    }

@router.get("/dashboard/export-orders")
async def export_orders_data(
    merchant_id: str = Query(..., description="商家ID"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    format: str = Query("excel", description="导出格式")
):
    """导出订单数据"""
    export_data = await analytics_service.export_orders_data(
        merchant_id, start_date, end_date, format
    )
    
    return {
        "message": "导出订单数据成功",
        "data": export_data
    }


    商家板块5数据分析
    from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.core.logging import logger
from app.core.exceptions import NotFoundException
from app.services.analytics import AnalyticsService
from app.schemas.analytics import DashboardResponse
from app.api.dependencies import get_analytics_service, get_authenticated_user

router = APIRouter()

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    business_date: Optional[date] = Query(None, description="业务日期，默认为今天"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取仪表盘数据"""
    try:
        if business_date is None:
            business_date = date.today()
        
        logger.info(f"Fetching dashboard data for date: {business_date}, user: {user.username}")
        
        dashboard_data = await analytics_service.get_dashboard_data(business_date)
        
        logger.info(f"Successfully fetched dashboard data for date: {business_date}")
        return dashboard_data
        
    except NotFoundException as e:
        logger.warning(f"Dashboard data not found for date: {business_date}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/dashboard/health-score")
async def get_health_score(
    business_date: Optional[date] = Query(None, description="业务日期，默认为今天"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取健康分数"""
    try:
        if business_date is None:
            business_date = date.today()
        
        health_score = await analytics_service.get_health_score(business_date)
        return health_score
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch health score: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/dashboard/core-metrics")
async def get_core_metrics(
    business_date: Optional[date] = Query(None, description="业务日期，默认为今天"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取核心指标"""
    try:
        if business_date is None:
            business_date = date.today()
        
        core_metrics = await analytics_service.get_core_metrics(business_date)
        return core_metrics
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch core metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")