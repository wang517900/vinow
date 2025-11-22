商家板块5数据分析
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.core.logging import logger
from app.core.exceptions import NotFoundException
from app.services.analytics import AnalyticsService
from app.schemas.analytics import (
    AlertSummaryResponse, BusinessSnapshotResponse, CompetitorAnalysisResponse,
    MarketingROIResponse, RevenueAnalysisResponse, ReviewSummaryResponse
)
from app.api.dependencies import get_analytics_service, get_authenticated_user

router = APIRouter()

@router.get("/alerts", response_model=AlertSummaryResponse)
async def get_alerts(
    business_date: Optional[date] = Query(None, description="业务日期，默认为今天"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取预警信息"""
    try:
        if business_date is None:
            business_date = date.today()
        
        alerts = await analytics_service.get_alerts_summary(business_date)
        return alerts
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/snapshot", response_model=BusinessSnapshotResponse)
async def get_business_snapshot(
    business_date: Optional[date] = Query(None, description="业务日期，默认为今天"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取经营快照"""
    try:
        if business_date is None:
            business_date = date.today()
        
        snapshot = await analytics_service.get_business_snapshot(business_date)
        return snapshot
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch business snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/competitors", response_model=CompetitorAnalysisResponse)
async def get_competitor_analysis(
    business_date: Optional[date] = Query(None, description="业务日期，默认为今天"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取竞对分析"""
    try:
        if business_date is None:
            business_date = date.today()
        
        analysis = await analytics_service.get_competitor_analysis(business_date)
        return analysis
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch competitor analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/marketing/roi", response_model=MarketingROIResponse)
async def get_marketing_roi(
    days: int = Query(30, description="分析天数", ge=1, le=365),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取营销 ROI"""
    try:
        roi_data = await analytics_service.get_marketing_roi(days)
        return roi_data
        
    except Exception as e:
        logger.error(f"Failed to fetch marketing ROI: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/revenue/trends", response_model=RevenueAnalysisResponse)
async def get_revenue_trends(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取收入趋势"""
    try:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
        
        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail "分析期间不能超过365天")
        
        trends = await analytics_service.get_revenue_analysis(start_date, end_date)
        return trends
        
    except Exception as e:
        logger.error(f"Failed to fetch revenue trends: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reviews/summary", response_model=ReviewSummaryResponse)
async def get_review_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user: dict = Depends(get_authenticated_user)
):
    """获取评价摘要"""
    try:
        if start_date is None:
            start_date = date.today() - timedelta(days=6)
        if end_date is None:
            end_date = date.today()
        
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
        
        summary = await analytics_service.get_review_summary(start_date, end_date)
        return summary
        
    except Exception as e:
        logger.error(f"Failed to fetch review summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")