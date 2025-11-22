商家系统板块5商家数据分析
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID
from ..models.business import HealthScoreLevel, AlertLevel, PeriodType

# 请求 Schemas
class DateRangeRequest(BaseModel):
    start_date: date
    end_date: date

class BusinessDateRequest(BaseModel):
    business_date: date

# 响应 Schemas
class HealthScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    level: HealthScoreLevel
    better_than_peers: float = Field(..., ge=0, le=100)
    date: date

class CoreMetric(BaseModel):
    name: str
    value: Any
    change_percentage: Optional[float] = None
    change_direction: Optional[str] = None  # up, down, same

class CoreMetricsResponse(BaseModel):
    metrics: List[CoreMetric]
    comparison_date: date

class AlertResponse(BaseModel):
    id: UUID
    title: str
    description: str
    level: AlertLevel
    created_at: datetime
    is_resolved: bool

class AlertSummaryResponse(BaseModel):
    critical: int
    warning: int
    normal: int
    alerts: List[AlertResponse]

class BusinessSnapshotResponse(BaseModel):
    business_date: date
    positive_points: List[str]
    improvement_points: List[str]
    generated_at: datetime

class CompetitorAnalysisResponse(BaseModel):
    business_date: date
    total_competitors: int
    rating_rank: int
    price_level: str
    customer_flow_rank: int
    promotion_intensity: str

class MarketingROIResponse(BaseModel):
    campaigns: List[Dict[str, Any]]
    total_investment: float
    total_revenue_generated: float
    overall_roi: float

class RevenueTrendResponse(BaseModel):
    date: date
    revenue: float
    period: Optional[PeriodType] = None

class RevenueAnalysisResponse(BaseModel):
    trends: List[RevenueTrendResponse]
    period_totals: Dict[str, float]

class ReviewSummaryResponse(BaseModel):
    total_reviews: int
    average_rating: float
    pending_responses: int
    critical_reviews: int
    keyword_frequency: Dict[str, int]

class DashboardResponse(BaseModel):
    health_score: HealthScoreResponse
    core_metrics: CoreMetricsResponse
    alerts: AlertSummaryResponse
    snapshot: BusinessSnapshotResponse
    competitor_analysis: CompetitorAnalysisResponse
    revenue_trends: RevenueAnalysisResponse
    review_summary: ReviewSummaryResponse"""商家系统 - analytics_schemas"""

# TODO: 实现商家系统相关功能
