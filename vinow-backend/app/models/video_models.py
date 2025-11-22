内容板块-视频数据模型
"""
视频内容数据模型模块

本模块定义了视频内容管理系统的数据库模型，包括：
1. 视频内容主表（VideoContent）
2. 视频转码配置表（VideoTranscodingProfile）
3. 视频缩略图表（VideoThumbnail）
4. 视频分析数据表（VideoAnalytics）
5. 视频用户互动表（VideoInteraction）

所有模型都基于SQLAlchemy ORM，并包含了适当的索引和关系定义。
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base
from datetime import datetime
import uuid
from typing import Dict, Any

__all__ = [
    'VideoContent',
    'VideoTranscodingProfile',
    'VideoThumbnail',
    'VideoAnalytics',
    'VideoInteraction'
]


def generate_uuid() -> str:
    """
    生成UUID字符串
    
    Returns:
        UUID字符串
    """
    return str(uuid.uuid4())


class VideoContent(Base):
    """视频内容主表"""
    __tablename__ = "video_contents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    merchant_id = Column(String(36), nullable=True, index=True)
    
    # 基础信息
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # 标签数组
    
    # 视频状态
    status = Column(String(50), default="draft", index=True)  # draft, processing, ready, published, rejected
    visibility = Column(String(20), default="public")  # public, private, unlisted
    
    # 媒体信息
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # 文件大小(bytes)
    duration = Column(Float, nullable=True)  # 视频时长(秒)
    resolution = Column(String(20), nullable=True)  # 分辨率 1920x1080
    format = Column(String(10), nullable=True)  # 视频格式
    
    # 转码信息
    transcoding_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    transcoding_progress = Column(Float, default=0.0)  # 转码进度 0-1
    
    # 统计信息
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    # 审核信息
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    published_at = Column(DateTime, nullable=True)
    
    # 关系
    transcoding_profiles = relationship("VideoTranscodingProfile", back_populates="video", cascade="all, delete-orphan")
    thumbnails = relationship("VideoThumbnail", back_populates="video", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将模型转换为字典
        
        Returns:
            包含模型数据的字典
        """
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "view_count": self.view_count,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class VideoTranscodingProfile(Base):
    """视频转码配置表"""
    __tablename__ = "video_transcoding_profiles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("video_contents.id"), nullable=False, index=True)
    
    # 转码配置
    profile_name = Column(String(50), nullable=False)  # 1080p, 720p, 480p, 360p
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    video_bitrate = Column(Integer, nullable=False)  # 视频码率(bps)
    audio_bitrate = Column(Integer, nullable=False)  # 音频码率(bps)
    
    # 文件信息
    file_key = Column(String(500), nullable=False)  # 存储路径
    file_size = Column(Integer, nullable=True)
    format = Column(String(10), default="mp4")
    
    # 状态信息
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    cdn_url = Column(String(1000), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    video = relationship("VideoContent", back_populates="transcoding_profiles")


class VideoThumbnail(Base):
    """视频缩略图表"""
    __tablename__ = "video_thumbnails"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("video_contents.id"), nullable=False, index=True)
    
    # 缩略图信息
    thumbnail_type = Column(String(20), nullable=False)  # default, custom, generated
    time_offset = Column(Float, nullable=True)  # 从视频中提取的时间点(秒)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    
    # 文件信息
    file_key = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    format = Column(String(10), default="jpg")
    cdn_url = Column(String(1000), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    video = relationship("VideoContent", back_populates="thumbnails")


class VideoAnalytics(Base):
    """视频分析数据表"""
    __tablename__ = "video_analytics"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("video_contents.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)  # 统计日期
    
    # 观看数据
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    watch_time = Column(Float, default=0.0)  # 总观看时长(秒)
    
    # 互动数据
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    
    # 完成率数据
    completion_25 = Column(Integer, default=0)  # 完成25%的观看次数
    completion_50 = Column(Integer, default=0)
    completion_75 = Column(Integer, default=0)
    completion_100 = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VideoInteraction(Base):
    """视频用户互动表"""
    __tablename__ = "video_interactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("video_contents.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    
    # 互动类型
    interaction_type = Column(String(20), nullable=False, index=True)  # view, like, share, comment
    watch_duration = Column(Float, default=0.0)  # 观看时长(秒)
    watch_percentage = Column(Float, default=0.0)  # 观看百分比
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 复合索引
    __table_args__ = (
        Index('idx_video_user_interaction', 'video_id', 'user_id', 'interaction_type'),
    )