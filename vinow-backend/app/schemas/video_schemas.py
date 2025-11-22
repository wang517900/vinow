内容模块-视频pydantic模式
"""
视频内容数据模式模块

本模块定义了视频内容管理系统的Pydantic数据模型，包括：
1. 视频创建和更新模型（VideoCreate, VideoUpdate）
2. 视频响应模型（VideoResponse）
3. 视频转码配置模型（TranscodingProfileResponse）
4. 视频缩略图模型（ThumbnailResponse）
5. 视频上传相关模型（VideoUploadResponse, VideoUploadComplete）
6. 视频分析模型（VideoAnalyticsResponse）
7. 视频互动模型（VideoInteractionCreate）
8. 视频统计模型（VideoStatsResponse）

所有模型都使用Pydantic V2语法，并支持从ORM对象创建。
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

__all__ = [
    'VideoStatus',
    'TranscodingStatus',
    'VideoVisibility',
    'VideoCreate',
    'VideoUpdate',
    'VideoResponse',
    'TranscodingProfileResponse',
    'ThumbnailResponse',
    'VideoUploadResponse',
    'VideoUploadComplete',
    'VideoAnalyticsResponse',
    'VideoInteractionCreate',
    'VideoStatsResponse'
]


class VideoStatus(str, Enum):
    """视频状态枚举"""
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    PUBLISHED = "published"
    REJECTED = "rejected"


class TranscodingStatus(str, Enum):
    """转码状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoVisibility(str, Enum):
    """视频可见性枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"


class VideoCreate(BaseModel):
    """创建视频请求模型"""
    model_config = ConfigDict(from_attributes=True)
    
    title: str = Field(..., min_length=1, max_length=500, description="视频标题")
    description: Optional[str] = Field(None, max_length=5000, description="视频描述")
    tags: List[str] = Field(default_factory=list, description="视频标签")
    merchant_id: Optional[str] = Field(None, description="商家ID")
    visibility: VideoVisibility = Field(default=VideoVisibility.PUBLIC, description="视频可见性")


class VideoUpdate(BaseModel):
    """更新视频请求模型"""
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="视频标题")
    description: Optional[str] = Field(None, max_length=5000, description="视频描述")
    tags: Optional[List[str]] = Field(None, description="视频标签")
    visibility: Optional[VideoVisibility] = Field(None, description="视频可见性")


class VideoResponse(BaseModel):
    """视频响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    merchant_id: Optional[str]
    title: str
    description: Optional[str]
    tags: Optional[List[str]]
    status: VideoStatus
    visibility: VideoVisibility
    original_filename: str
    file_size: int
    duration: Optional[float]
    resolution: Optional[str]
    format: Optional[str]
    transcoding_status: TranscodingStatus
    transcoding_progress: float
    view_count: int
    like_count: int
    share_count: int
    comment_count: int
    is_approved: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]


class TranscodingProfileResponse(BaseModel):
    """转码配置响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    video_id: str
    profile_name: str
    width: int
    height: int
    video_bitrate: int
    audio_bitrate: int
    file_key: str
    file_size: Optional[int]
    format: str
    status: TranscodingStatus
    cdn_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class ThumbnailResponse(BaseModel):
    """缩略图响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    video_id: str
    thumbnail_type: str
    time_offset: Optional[float]
    width: int
    height: int
    file_key: str
    file_size: Optional[int]
    format: str
    cdn_url: Optional[str]
    created_at: datetime


class VideoUploadResponse(BaseModel):
    """视频上传响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    video_id: str
    upload_url: str
    upload_id: Optional[str] = None
    parts: Optional[List[Dict]] = None
    expires_at: datetime


class VideoUploadComplete(BaseModel):
    """视频上传完成请求"""
    model_config = ConfigDict(from_attributes=True)
    
    upload_id: str
    parts: List[Dict[str, Any]]


class VideoAnalyticsResponse(BaseModel):
    """视频分析响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    video_id: str
    date: datetime
    views: int
    unique_viewers: int
    watch_time: float
    likes: int
    shares: int
    comments: int
    completion_25: int
    completion_50: int
    completion_75: int
    completion_100: int


class VideoInteractionCreate(BaseModel):
    """视频互动创建模型"""
    model_config = ConfigDict(from_attributes=True)
    
    interaction_type: str = Field(..., description="互动类型: view, like, share")
    watch_duration: Optional[float] = Field(0.0, description="观看时长(秒)")
    watch_percentage: Optional[float] = Field(0.0, description="观看百分比")


class VideoStatsResponse(BaseModel):
    """视频统计响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    video_id: str
    total_views: int
    total_likes: int
    total_shares: int
    total_comments: int
    average_watch_time: float
    completion_rate: float
    engagement_rate: float
    last_updated: datetime