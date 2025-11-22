商家系统板块5商家数据分析
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from .base import BaseDBModel, TimeStampedModel

class HealthScoreLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertLevel(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    NORMAL = "normal"

class PeriodType(str, Enum):
    MORNING = "morning"  # 6-10
    LUNCH = "lunch"      # 11-14
    AFTERNOON = "afternoon" # 15-17
    EVENING = "evening"  # 18-21

class BusinessMetrics(TimeStampedModel):
    """业务指标模型"""
    date: date
    customer_count: int
    revenue: float  # VND
    order_count: int
    rating: float
    health_score: int
    competitor_count: int
    rating_rank: int
    
    # 时段数据
    morning_revenue: Optional[float] = None
    lunch_revenue: Optional[float] = None
    afternoon_revenue: Optional[float] = None
    evening_revenue: Optional[float] = None
    
    # 比较数据
    customer_count_yesterday: Optional[int] = None
    revenue_yesterday: Optional[float] = None
    order_count_yesterday: Optional[int] = None
    rating_yesterday: Optional[float] = None

class Alert(TimeStampedModel):
    """预警模型"""
    title: str
    description: str
    level: AlertLevel
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    business_date: date

class BusinessSnapshot(TimeStampedModel):
    """经营快照模型"""
    business_date: date
    positive_points: List[str]
    improvement_points: List[str]
    recommendations: List[str]

class CompetitorAnalysis(TimeStampedModel):
    """竞对分析模型"""
    business_date: date
    total_competitors: int
    rating_rank: int
    price_level: str  # low, medium, high
    customer_flow_rank: int
    promotion_intensity: str  # low, medium, high

class MarketingCampaign(TimeStampedModel):
    """营销活动模型"""
    name: str
    start_date: date
    end_date: date
    investment: float
    revenue_generated: float
    new_customers: int
    roi: float

class Review(TimeStampedModel):
    """评价模型"""
    business_date: date
    rating: int
    comment: Optional[str] = None
    keywords: List[str] = []
    is_responded: bool = False
    response: Optional[str] = None
    responded_at: Optional[datetime] = None

class RevenueTrend(TimeStampedModel):
    """收入趋势模型"""
    business_date: date
    revenue: float
    period: Optional[PeriodType] = None