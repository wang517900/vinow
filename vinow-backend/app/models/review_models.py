商家系统7评价管理
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class MerchantReview(Base):
    __tablename__ = "merchant_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_name = Column(String(100), nullable=False)
    user_avatar = Column(String(500))
    rating = Column(Integer, nullable=False)  # 1-5星
    content = Column(Text)
    images = Column(JSONB)  # 存储图片URL数组
    is_anonymous = Column(Boolean, default=False)
    status = Column(String(20), default='active')  # active/hidden/deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReviewReply(Base):
    __tablename__ = "review_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, nullable=False, index=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    reply_type = Column(String(20), default='official')  # official/thank
    created_at = Column(DateTime, default=datetime.utcnow)

class ReviewStatistics(Base):
    __tablename__ = "review_statistics"
    
    merchant_id = Column(Integer, primary_key=True, index=True)
    total_reviews = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    reply_rate = Column(Float, default=0.0)
    last_7_days_trend = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    内容系统
    from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, validator, root_validator
from enum import Enum
import uuid
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, Float, ForeignKey, DECIMAL, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database.connection import Base as SQLBase
from app.models.content_models import Content, ContentType

class ReviewStatus(str, Enum):
    """评价状态枚举"""
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"
    DELETED = "deleted"
    HIDDEN = "hidden"

class ReviewDimension(str, Enum):
    """评价维度枚举 - 支持多行业"""
    # 通用维度
    OVERALL = "overall"
    SERVICE = "service"
    QUALITY = "quality"
    VALUE = "value"
    
    # 餐饮行业
    TASTE = "taste"
    ENVIRONMENT = "environment"
    CLEANLINESS = "cleanliness"
    
    # 美业
    SKILL = "skill"
    RESULT = "result"
    PROFESSIONALISM = "professionalism"
    
    # 零售
    PACKAGING = "packaging"
    DELIVERY = "delivery"
    ACCURACY = "accuracy"

class ReviewVerificationStatus(str, Enum):
    """评价验证状态"""
    UNVERIFIED = "unverified"
    VERIFIED_PURCHASE = "verified_purchase"
    VERIFIED_VISIT = "verified_visit"
    VERIFIED_OWNER = "verified_owner"

# SQLAlchemy 数据库模型
class Review(SQLBase):
    """评价表 - 扩展自内容表"""
    __tablename__ = "reviews"
    
    # 主键和关联
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False, unique=True, index=True)
    
    # 评价特定字段
    overall_rating = Column(DECIMAL(2, 1), nullable=False)  # 总体评分 1.0-5.0
    rating_breakdown = Column(JSON, nullable=False)  # 各维度评分
    
    # 验证信息
    verification_status = Column(String(50), default=ReviewVerificationStatus.UNVERIFIED)
    order_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # 关联订单
    purchase_date = Column(DateTime, nullable=True)
    
    # 评价内容增强
    pros = Column(ARRAY(String), default=[])  # 优点
    cons = Column(ARRAY(String), default=[])  # 缺点
    review_tags = Column(ARRAY(String), default=[])  # 评价标签
    
    # 有用性投票
    helpful_votes = Column(Integer, default=0)
    unhelpful_votes = Column(Integer, default=0)
    
    # 商家回复
    business_reply = Column(Text, nullable=True)
    business_reply_at = Column(DateTime, nullable=True)
    business_replier_id = Column(UUID(as_uuid=True), nullable=True)
    
    # 追评功能
    has_followup = Column(Boolean, default=False)
    followup_review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    content = relationship("Content", backref="review", uselist=False)
    followup = relationship("Review", remote_side=[id], backref="original_review", uselist=False)
    
    # 约束
    __table_args__ = (
        CheckConstraint('overall_rating >= 1.0 AND overall_rating <= 5.0', name='check_rating_range'),
    )

class ReviewDimensionConfig(SQLBase):
    """评价维度配置表 - 支持不同行业"""
    __tablename__ = "review_dimension_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_type = Column(String(100), nullable=False, index=True)  # 行业类型
    dimension_name = Column(String(100), nullable=False)  # 维度名称
    dimension_key = Column(String(50), nullable=False)  # 维度键
    display_order = Column(Integer, default=0)  # 显示顺序
    is_required = Column(Boolean, default=False)  # 是否必填
    is_active = Column(Boolean, default=True)  # 是否激活
    
    # 多语言支持
    display_name_vi = Column(String(200), nullable=True)  # 越南语显示名
    display_name_en = Column(String(200), nullable=True)  # 英语显示名
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReviewHelpfulVote(SQLBase):
    """评价有用性投票表"""
    __tablename__ = "review_helpful_votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_helpful = Column(Boolean, nullable=False)  # True=有用, False=无用
    
    # 设备信息
    device_fingerprint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 唯一约束：一个用户对同一评价只能投票一次
    __table_args__ = (
        CheckConstraint('is_helpful IN (True, False)', name='check_helpful_value'),
    )

# Pydantic 数据模型
class ReviewDimensionScore(BaseModel):
    """评价维度评分模型"""
    dimension: str = Field(..., description="维度键")
    score: float = Field(..., ge=1.0, le=5.0, description="评分 1-5")
    dimension_name: Optional[str] = Field(None, description="维度显示名")

class ReviewCreate(BaseModel):
    """创建评价模型"""
    model_config = ConfigDict(from_attributes=True)
    
    # 基础信息
    target_entity_type: str = Field(..., description="目标实体类型")
    target_entity_id: str = Field(..., description="目标实体ID")
    
    # 评分
    overall_rating: float = Field(..., ge=1.0, le=5.0, description="总体评分")
    dimension_scores: List[ReviewDimensionScore] = Field(..., description="维度评分")
    
    # 内容
    title: Optional[str] = Field(None, max_length=200, description="评价标题")
    description: str = Field(..., max_length=2000, description="评价内容")
    
    # 元数据
    tags: List[str] = Field(default=[], description="标签")
    pros: List[str] = Field(default=[], description="优点")
    cons: List[str] = Field(default=[], description="缺点")
    is_anonymous: bool = Field(default=False, description="是否匿名")
    
    # 验证信息
    order_id: Optional[str] = Field(None, description="订单ID")
    purchase_date: Optional[datetime] = Field(None, description="购买日期")
    
    # 媒体文件
    media_files: List[Dict[str, Any]] = Field(default=[], description="媒体文件")
    
    @validator('dimension_scores')
    def validate_dimension_scores(cls, v):
        """验证维度评分"""
        if not v:
            raise ValueError("至少需要一个维度评分")
        
        # 检查重复维度
        dimensions = [score.dimension for score in v]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("存在重复的评分维度")
        
        return v
    
    @validator('pros', 'cons')
    def validate_pros_cons_length(cls, v):
        """验证优点缺点长度"""
        for item in v:
            if len(item) > 100:
                raise ValueError("每个优点/缺点不能超过100字符")
        return v

class ReviewUpdate(BaseModel):
    """更新评价模型"""
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    is_anonymous: Optional[bool] = None

class ReviewResponse(BaseModel):
    """评价响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    # 基础信息
    id: str = Field(..., description="评价ID")
    content_id: str = Field(..., description="内容ID")
    
    # 评价特定信息
    overall_rating: float = Field(..., description="总体评分")
    rating_breakdown: Dict[str, float] = Field(..., description="各维度评分")
    
    # 内容信息
    title: Optional[str] = Field(None, description="标题")
    description: str = Field(..., description="描述")
    author_id: str = Field(..., description="作者ID")
    author_name: Optional[str] = Field(None, description="作者名称")
    author_avatar: Optional[str] = Field(None, description="作者头像")
    
    # 目标实体
    target_entity_type: str = Field(..., description="目标实体类型")
    target_entity_id: str = Field(..., description="目标实体ID")
    target_entity_name: Optional[str] = Field(None, description="目标实体名称")
    
    # 验证状态
    verification_status: ReviewVerificationStatus = Field(..., description="验证状态")
    is_verified: bool = Field(..., description="是否已验证")
    
    # 评价内容
    tags: List[str] = Field(default=[], description="标签")
    pros: List[str] = Field(default=[], description="优点")
    cons: List[str] = Field(default=[], description="缺点")
    is_anonymous: bool = Field(..., description="是否匿名")
    
    # 互动统计
    like_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    helpful_votes: int = Field(default=0, description="有用投票数")
    unhelpful_votes: int = Field(default=0, description="无用投票数")
    
    # 商家回复
    business_reply: Optional[str] = Field(None, description="商家回复")
    business_reply_at: Optional[datetime] = Field(None, description="商家回复时间")
    business_replier_name: Optional[str] = Field(None, description="商家回复人")
    
    # 媒体文件
    media_files: List[Dict[str, Any]] = Field(default=[], description="媒体文件")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 用户互动状态
    user_has_liked: bool = Field(default=False, description="用户是否点赞")
    user_has_voted_helpful: Optional[bool] = Field(None, description="用户是否投票有用")

class BusinessReplyCreate(BaseModel):
    """商家回复创建模型"""
    reply_text: str = Field(..., max_length=1000, description="回复内容")
    replier_id: str = Field(..., description="回复人ID")
    replier_name: Optional[str] = Field(None, description="回复人名称")

class ReviewHelpfulVoteCreate(BaseModel):
    """评价有用性投票创建模型"""
    is_helpful: bool = Field(..., description="是否认为有用")
    device_fingerprint: Optional[str] = Field(None, description="设备指纹")

class ReviewSummary(BaseModel):
    """评价汇总信息"""
    model_config = ConfigDict(from_attributes=True)
    
    target_entity_id: str = Field(..., description="目标实体ID")
    target_entity_type: str = Field(..., description="目标实体类型")
    
    # 评分统计
    average_rating: float = Field(..., description="平均评分")
    rating_distribution: Dict[str, int] = Field(..., description="评分分布")
    total_reviews: int = Field(..., description="总评价数")
    
    # 维度统计