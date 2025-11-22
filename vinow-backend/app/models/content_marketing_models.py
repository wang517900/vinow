# app/content_marketing/models.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class ContentType(str, Enum):
    VIDEO = "video"
    IMAGE_TEXT = "image_text"
    LIVE = "live"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"

class CollaborationStatus(str, Enum):
    PENDING = "pending"
    RECRUITING = "recruiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

class ContentBase(BaseModel):
    """内容基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="内容标题")
    description: Optional[str] = Field(None, max_length=1000, description="内容描述")
    content_type: ContentType = Field(..., description="内容类型")
    status: ContentStatus = Field(ContentStatus.DRAFT, description="内容状态")
    
    # 媒体内容
    video_url: Optional[str] = Field(None, description="视频URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    image_urls: List[str] = Field(default_factory=list, description="图片URL列表")
    text_content: Optional[str] = Field(None, description="文本内容")
    
    # 关联信息
    product_ids: List[str] = Field(default_factory=list, description="关联商品ID列表")
    coupon_id: Optional[str] = Field(None, description="关联优惠券ID")
    
    # 时间管理
    scheduled_at: Optional[datetime] = Field(None, description="定时发布时间")
    
    # 商家信息
    merchant_id: str = Field(..., description="商家ID")
    store_id: Optional[str] = Field(None, description="门店ID")

class ContentCreate(ContentBase):
    """创建内容模型"""
    pass

class ContentUpdate(BaseModel):
    """更新内容模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ContentStatus] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_urls: Optional[List[str]] = None
    text_content: Optional[str] = None
    product_ids: Optional[List[str]] = None
    coupon_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None

class ContentInDB(ContentBase):
    """数据库中的内容模型"""
    id: str = Field(..., description="内容ID")
    tracking_code: str = Field(..., description="追踪代码")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

class ContentStats(BaseModel):
    """内容统计数据模型"""
    content_id: str = Field(..., description="内容ID")
    merchant_id: str = Field(..., description="商家ID")
    
    view_count: int = Field(0, description="播放量")
    like_count: int = Field(0, description="点赞数")
    comment_count: int = Field(0, description="评论数")
    share_count: int = Field(0, description="分享数")
    click_count: int = Field(0, description="点击量")
    order_count: int = Field(0, description="订单数")
    revenue_amount: float = Field(0.0, description="收入金额")
    
    stat_date: datetime = Field(..., description="统计日期")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

class CollaborationBase(BaseModel):
    """合作任务基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str = Field(..., min_length=1, description="任务描述")
    requirements: Optional[str] = Field(None, description="达人要求")
    budget_amount: Optional[float] = Field(None, description="预算金额")
    commission_rate: Optional[float] = Field(None, ge=0, le=100, description="佣金比例")
    commission_amount: Optional[float] = Field(None, ge=0, description="固定佣金")
    
    content_requirements: Optional[str] = Field(None, description="内容要求")
    product_ids: List[str] = Field(default_factory=list, description="推广商品ID列表")
    
    application_deadline: Optional[datetime] = Field(None, description="申请截止时间")
    completion_deadline: Optional[datetime] = Field(None, description="完成截止时间")
    
    merchant_id: str = Field(..., description="商家ID")
    store_id: Optional[str] = Field(None, description="门店ID")

class CollaborationCreate(CollaborationBase):
    """创建合作任务模型"""
    pass

class CollaborationInDB(CollaborationBase):
    """数据库中的合作任务模型"""
    id: str = Field(..., description="合作任务ID")
    status: CollaborationStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

class CollaborationApplicationBase(BaseModel):
    """合作申请基础模型"""
    collaboration_id: str = Field(..., description="合作任务ID")
    merchant_id: str = Field(..., description="商家ID")
    
    influencer_name: str = Field(..., description="达人名称")
    influencer_contact: str = Field(..., description="联系方式")
    follower_count: Optional[int] = Field(None, description="粉丝数")
    previous_performance: Optional[str] = Field(None, description="过往表现")
    
    proposal: str = Field(..., description="合作方案")
    expected_content: Optional[str] = Field(None, description="预期内容")

class CollaborationApplicationCreate(CollaborationApplicationBase):
    """创建合作申请模型"""
    pass

class CollaborationApplicationInDB(CollaborationApplicationBase):
    """数据库中的合作申请模型"""
    id: str = Field(..., description="申请ID")
    status: ApplicationStatus = Field(..., description="申请状态")
    applied_at: datetime = Field(..., description="申请时间")
    accepted_at: Optional[datetime] = Field(None, description="接受时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    final_content_id: Optional[str] = Field(None, description="最终内容ID")
    commission_paid: bool = Field(False, description="佣金是否支付")
    paid_amount: float = Field(0.0, description="支付金额")
    
    class Config:
        from_attributes = True

class ContentMarketingDashboard(BaseModel):
    """内容营销数据看板"""
    today_orders: int = Field(0, description="今日订单数")
    today_revenue: float = Field(0.0, description="今日收入")
    top_contents: List[Dict[str, Any]] = Field(default_factory=list, description="热门内容")
    roi: float = Field(0.0, description="投入产出比")
    
    pending_applications: int = Field(0, description="待处理申请")
    active_collaborations: int = Field(0, description="进行中合作")