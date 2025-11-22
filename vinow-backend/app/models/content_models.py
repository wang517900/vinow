内容系统
"""
内容管理模块的数据模型定义

本模块定义了内容管理系统中的核心数据模型，包括：
1. SQLAlchemy数据库模型（Content, ContentMedia, ContentInteraction）
2. Pydantic数据传输对象（ContentBase, ContentCreate, ContentUpdate, ContentResponse等）

支持多种内容类型（评价、短视频、图文、直播、问答等）和丰富的互动功能。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database.connection import Base as SQLBase

__all__ = [
    'ContentType',
    'ContentStatus',
    'MediaType',
    'InteractionType',
    'Content',
    'ContentMedia',
    'ContentInteraction',
    'ContentBase',
    'ContentCreate',
    'ContentUpdate',
    'ContentResponse',
    'ContentMediaCreate',
    'ContentInteractionCreate'
]


class ContentType(str, Enum):
    """内容类型枚举 - 完整定义"""
    REVIEW = "review"           # 评价
    VIDEO = "video"             # 短视频
    ARTICLE = "article"         # 图文
    LIVE = "live"               # 直播
    QNA = "qna"                 # 问答
    SHORT_VIDEO = "short_video" # 短视频（兼容）
    POST = "post"               # 动态


class ContentStatus(str, Enum):
    """内容状态枚举 - 完整定义"""
    DRAFT = "draft"                  # 草稿
    PENDING_REVIEW = "pending_review"  # 待审核
    APPROVED = "approved"            # 审核通过
    PUBLISHED = "published"          # 已发布
    REJECTED = "rejected"            # 已拒绝
    DELETED = "deleted"              # 已删除
    ARCHIVED = "archived"            # 已归档
    FLAGGED = "flagged"              # 被标记


class MediaType(str, Enum):
    """媒体类型枚举 - 完整定义"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"


class InteractionType(str, Enum):
    """互动类型枚举"""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    VIEW = "view"
    BOOKMARK = "bookmark"
    REPORT = "report"


# SQLAlchemy 数据库模型
class Content(SQLBase):
    """内容表 - 生产级别数据库模型"""
    __tablename__ = "contents"
    
    # 主键和基础字段
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    content_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    
    # 作者信息
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    author_name = Column(String(200), nullable=True)
    author_avatar = Column(String(500), nullable=True)
    
    # 目标实体信息
    target_entity_type = Column(String(100), nullable=True, index=True)
    target_entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    target_entity_name = Column(String(200), nullable=True)
    
    # 状态和可见性
    status = Column(String(50), default=ContentStatus.DRAFT.value, index=True)
    visibility = Column(String(50), default="public")
    is_anonymous = Column(Boolean, default=False)
    
    # 元数据
    tags = Column(ARRAY(String), default=[])
    categories = Column(ARRAY(String), default=[])
    location_data = Column(JSON, nullable=True)
    language = Column(String(10), default="vi")  # 越南语默认
    
    # 互动统计（缓存）
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    bookmark_count = Column(Integer, default=0)
    report_count = Column(Integer, default=0)
    
    # 质量评分
    quality_score = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # 审核信息
    moderated_at = Column(DateTime, nullable=True)
    moderator_id = Column(UUID(as_uuid=True), nullable=True)
    moderation_notes = Column(Text, nullable=True)
    
    # 关系
    media_files = relationship("ContentMedia", back_populates="content", cascade="all, delete-orphan")
    interactions = relationship("ContentInteraction", back_populates="content", cascade="all, delete-orphan")


class ContentMedia(SQLBase):
    """内容媒体文件表"""
    __tablename__ = "content_media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False, index=True)
    
    # 文件信息
    file_url = Column(String(1000), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # 字节
    mime_type = Column(String(100), nullable=False)
    
    # 媒体元数据
    duration = Column(Integer, nullable=True)  # 视频/音频时长（秒）
    width = Column(Integer, nullable=True)     # 图片/视频宽度
    height = Column(Integer, nullable=True)    # 图片/视频高度
    thumbnail_url = Column(String(1000), nullable=True)
    
    # 处理状态
    processing_status = Column(String(50), default="pending")
    processing_metadata = Column(JSON, nullable=True)
    
    # 排序和显示
    display_order = Column(Integer, default=0)
    caption = Column(Text, nullable=True)
    alt_text = Column(String(500), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    content = relationship("Content", back_populates="media_files")


class ContentInteraction(SQLBase):
    """内容互动表"""
    __tablename__ = "content_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # 互动信息
    interaction_type = Column(String(50), nullable=False, index=True)
    interaction_data = Column(JSON, nullable=True)  # 额外数据（如分享平台、评论内容等）
    
    # 设备信息（用于反作弊）
    device_fingerprint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    content = relationship("Content", back_populates="interactions")


# Pydantic 数据模型
class ContentBase(BaseModel):
    """内容基础模型 - 生产级别"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    # 基础信息
    title: Optional[str] = Field(None, max_length=500, description="内容标题")
    description: Optional[str] = Field(None, max_length=5000, description="内容描述")
    content_type: ContentType = Field(..., description="内容类型")
    
    # 作者信息
    author_id: str = Field(..., description="作者用户ID")
    author_name: Optional[str] = Field(None, description="作者名称")
    author_avatar: Optional[str] = Field(None, description="作者头像URL")
    
    # 目标实体
    target_entity_type: Optional[str] = Field(None, description="目标实体类型(shop/product/service)")
    target_entity_id: Optional[str] = Field(None, description="目标实体ID")
    target_entity_name: Optional[str] = Field(None, description="目标实体名称")
    
    # 状态和可见性
    status: ContentStatus = Field(default=ContentStatus.DRAFT, description="内容状态")
    visibility: str = Field(default="public", description="可见性设置")
    is_anonymous: bool = Field(default=False, description="是否匿名")
    
    # 元数据
    tags: List[str] = Field(default_factory=list, description="内容标签")
    categories: List[str] = Field(default_factory=list, description="内容分类")
    location_data: Optional[Dict[str, Any]] = Field(None, description="地理位置信息")
    language: str = Field(default="vi", description="内容语言")
    
    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v: Optional[str]) -> Optional[str]:
        """验证标题长度"""
        if v and len(v) > 500:
            raise ValueError("标题长度不能超过500字符")
        return v
    
    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: Optional[str]) -> Optional[str]:
        """验证描述长度"""
        if v and len(v) > 5000:
            raise ValueError("描述长度不能超过5000字符")
        return v
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """验证标签"""
        if v and len(v) > 20:
            raise ValueError("标签数量不能超过20个")
        for tag in v:
            if len(tag) > 50:
                raise ValueError("单个标签长度不能超过50字符")
        return v


class ContentCreate(ContentBase):
    """创建内容模型"""
    media_files: List[Dict[str, Any]] = Field(default_factory=list, description="媒体文件信息")
    
    @model_validator(mode='after')
    def validate_content_creation(self) -> 'ContentCreate':
        """内容创建整体验证"""
        # 验证媒体文件数量
        if self.content_type == ContentType.VIDEO and len(self.media_files) == 0:
            raise ValueError("视频内容必须包含媒体文件")
        
        # 验证标题和描述
        if not self.title and not self.description:
            raise ValueError("标题和描述不能同时为空")
        
        return self


class ContentUpdate(BaseModel):
    """更新内容模型"""
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    status: Optional[ContentStatus] = None
    visibility: Optional[str] = None
    is_anonymous: Optional[bool] = None


class ContentResponse(ContentBase):
    """内容响应模型 - 完整字段"""
    id: str = Field(..., description="内容ID")
    
    # 互动统计
    like_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    share_count: int = Field(default=0, description="分享数")
    view_count: int = Field(default=0, description="浏览数")
    bookmark_count: int = Field(default=0, description="收藏数")
    report_count: int = Field(default=0, description="举报数")
    
    # 质量指标
    quality_score: float = Field(default=0.0, description="质量评分")
    engagement_rate: float = Field(default=0.0, description="互动率")
    
    # 媒体文件
    media_files: List[Dict[str, Any]] = Field(default_factory=list, description="媒体文件列表")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    
    # 审核信息
    moderated_at: Optional[datetime] = Field(None, description="审核时间")
    moderator_id: Optional[str] = Field(None, description="审核员ID")
    moderation_notes: Optional[str] = Field(None, description="审核备注")
    
    # 用户互动状态（当前用户）
    user_has_liked: bool = Field(default=False, description="用户是否点赞")
    user_has_bookmarked: bool = Field(default=False, description="用户是否收藏")
    user_has_reported: bool = Field(default=False, description="用户是否举报")


class ContentMediaCreate(BaseModel):
    """创建媒体文件模型"""
    file_url: str = Field(..., description="文件URL")
    file_type: MediaType = Field(..., description="文件类型")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    mime_type: str = Field(..., description="MIME类型")
    duration: Optional[int] = Field(None, description="时长（秒）")
    width: Optional[int] = Field(None, description="宽度")
    height: Optional[int] = Field(None, description="高度")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    display_order: int = Field(default=0, description="显示顺序")
    caption: Optional[str] = Field(None, description="标题")
    alt_text: Optional[str] = Field(None, description="替代文本")


class ContentInteractionCreate(BaseModel):
    """创建互动模型"""
    interaction_type: InteractionType = Field(..., description="互动类型")
    interaction_data: Optional[Dict[str, Any]] = Field(None, description="互动数据")
    device_fingerprint: Optional[str] = Field(None, description="设备指纹")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")


    内容板块

    from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4

class ContentType(str, Enum):
    VIDEO = "video"
    REVIEW = "review"
    ARTICLE = "article"
    LIVE = "live"
    PRODUCT = "product"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELETED = "deleted"

class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"

class ContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    content_type: ContentType
    media_urls: List[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('media_urls')
    def validate_media_urls(cls, v):
        if not v:
            raise ValueError('At least one media URL is required')
        return v

class ContentCreate(ContentBase):
    creator_id: UUID

class ContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    location: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ContentInDB(ContentBase):
    id: UUID = Field(default_factory=uuid4)
    creator_id: UUID
    status: ContentStatus = ContentStatus.DRAFT
    moderation_status: ModerationStatus = ModerationStatus.PENDING
    view_count: int = Field(0, ge=0)
    like_count: int = Field(0, ge=0)
    share_count: int = Field(0, ge=0)
    comment_count: int = Field(0, ge=0)
    duration: Optional[int] = None  # 视频时长（秒）
    file_size: Optional[int] = None  # 文件大小（字节）
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ContentResponse(ContentInDB):
    creator_info: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    user_interaction: Optional[Dict[str, Any]] = None

class ContentListResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    page: int
    size: int
    pages: int

class ContentInteractionType(str, Enum):
    VIEW = "view"
    LIKE = "like"
    SHARE = "share"
    COMMENT = "comment"
    CLICK = "click"
    FAVORITE = "favorite"

class ContentInteraction(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    content_id: UUID
    interaction_type: ContentInteractionType
    duration: Optional[float] = None  # 观看时长（秒）
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ContentInteractionCreate(BaseModel):
    content_id: UUID
    interaction_type: ContentInteractionType
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ContentQualityScore(BaseModel):
    content_id: UUID
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    engagement_score: float = Field(0.0, ge=0.0, le=1.0)
    creator_score: float = Field(0.0, ge=0.0, le=1.0)
    freshness_score: float = Field(0.0, ge=0.0, le=1.0)
    media_quality_score: float = Field(0.0, ge=0.0, le=1.0)
    overall_score: float = Field(0.0, ge=0.0, le=1.0)
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('overall_score', always=True)
    def calculate_overall_score(cls, v, values):
        """计算总体质量分数"""
        weights = {
            'completeness_score': 0.2,
            'engagement_score': 0.3,
            'creator_score': 0.2,
            'freshness_score': 0.15,
            'media_quality_score': 0.15
        }
        
        total = 0.0
        for key, weight in weights.items():
            if key in values:
                total += values[key] * weight
        
        return round(total, 4)

class ContentSearchQuery(BaseModel):
    query: Optional[str] = None
    content_type: Optional[ContentType] = None
    tags: Optional[List[str]] = None
    location: Optional[Dict[str, Any]] = None
    creator_id: Optional[UUID] = None
    min_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    sort_by: str = Field("created_at", regex="^(created_at|updated_at|view_count|like_count|quality_score)$")
    sort_order: str = Field("desc", regex="^(asc|desc)$")