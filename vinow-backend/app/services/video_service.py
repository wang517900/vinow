内容模块-视频核心服务
"""
视频内容服务模块

本模块提供了视频内容管理的核心业务逻辑，包括：
1. 视频内容的创建、查询、更新、删除
2. 视频状态管理和转码进度跟踪
3. 视频互动记录（观看、点赞、分享等）
4. 视频分析数据统计
5. 热门视频推荐
6. 缓存优化和分页查询

所有服务方法都包含完善的异常处理和日志记录。
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import uuid
from datetime import datetime, timedelta

from app.models.video_models import (
    VideoContent, VideoTranscodingProfile, VideoThumbnail, 
    VideoAnalytics, VideoInteraction
)
from app.schemas.video_schemas import (
    VideoCreate, VideoUpdate, VideoStatus, TranscodingStatus,
    VideoVisibility, VideoInteractionCreate
)
from app.core.exceptions import NotFoundException, ValidationException, BusinessException
from app.utils.pagination import paginate, Page
from app.utils.cache_utils import cache_manager
from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ['VideoService']


class VideoService:
    """视频内容服务"""
    
    @staticmethod
    def create_video(db: Session, video_data: VideoCreate, user_id: str) -> VideoContent:
        """
        创建视频记录
        
        Args:
            db: 数据库会话
            video_data: 视频创建数据
            user_id: 用户ID
            
        Returns:
            创建的视频内容对象
            
        Raises:
            BusinessException: 创建失败时抛出
        """
        try:
            video = VideoContent(
                user_id=user_id,
                merchant_id=video_data.merchant_id,
                title=video_data.title,
                description=video_data.description,
                tags=video_data.tags or [],
                visibility=video_data.visibility,
                status=VideoStatus.DRAFT
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            
            logger.info(f"Video record created: {video.id} by user: {user_id}")
            return video
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create video record: {str(e)}", exc_info=True)
            raise BusinessException("创建视频记录失败")
    
    @staticmethod
    def get_video_by_id(db: Session, video_id: str) -> VideoContent:
        """
        根据ID获取视频
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            视频内容对象
            
        Raises:
            NotFoundException: 视频不存在时抛出
        """
        video = db.query(VideoContent).filter(
            VideoContent.id == video_id
        ).first()
        
        if not video:
            raise NotFoundException(f"视频不存在: {video_id}")
            
        return video
    
    @staticmethod
    def update_video(db: Session, video_id: str, update_data: VideoUpdate) -> VideoContent:
        """
        更新视频信息
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            update_data: 视频更新数据
            
        Returns:
            更新后的视频内容对象
            
        Raises:
            NotFoundException: 视频不存在时抛出
            BusinessException: 更新失败时抛出
        """
        video = VideoService.get_video_by_id(db, video_id)
        
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                setattr(video, key, value)
                
            video.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(video)
            
            # 清除缓存
            cache_key_pattern = f"video:{video_id}:*"
            cache_manager.delete_pattern(cache_key_pattern)
            
            logger.info(f"Video updated: {video_id}")
            return video
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update video {video_id}: {str(e)}", exc_info=True)
            raise BusinessException("更新视频失败")
    
    @staticmethod
    def delete_video(db: Session, video_id: str) -> bool:
        """
        删除视频（软删除）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            删除是否成功
            
        Raises:
            NotFoundException: 视频不存在时抛出
            BusinessException: 删除失败时抛出
        """
        video = VideoService.get_video_by_id(db, video_id)
        
        try:
            video.status = VideoStatus.REJECTED
            video.updated_at = datetime.utcnow()
            db.commit()
            
            # 清除缓存
            cache_key_pattern = f"video:{video_id}:*"
            cache_manager.delete_pattern(cache_key_pattern)
            
            logger.info(f"Video deleted: {video_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete video {video_id}: {str(e)}", exc_info=True)
            raise BusinessException("删除视频失败")
    
    @staticmethod
    def list_videos(
        db: Session,
        user_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        status: Optional[VideoStatus] = None,
        visibility: Optional[VideoVisibility] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Page[VideoContent]:
        """
        分页列出视频
        
        Args:
            db: 数据库会话
            user_id: 用户ID过滤
            merchant_id: 商家ID过滤
            status: 视频状态过滤
            visibility: 可见性过滤
            page: 页码
            page_size: 每页大小
            
        Returns:
            分页视频内容列表
        """
        query = db.query(VideoContent)
        
        # 过滤条件
        if user_id:
            query = query.filter(VideoContent.user_id == user_id)
        if merchant_id:
            query = query.filter(VideoContent.merchant_id == merchant_id)
        if status:
            query = query.filter(VideoContent.status == status)
        if visibility:
            query = query.filter(VideoContent.visibility == visibility)
            
        # 排序
        query = query.order_by(desc(VideoContent.created_at))
        
        return paginate(query, page, page_size)
    
    @staticmethod
    def update_video_status(
        db: Session,
        video_id: str,
        status: VideoStatus,
        approved_by: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> VideoContent:
        """
        更新视频状态
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            status: 新状态
            approved_by: 审核人ID
            rejection_reason: 拒绝原因
            
        Returns:
            更新后的视频内容对象
            
        Raises:
            NotFoundException: 视频不存在时抛出
            BusinessException: 更新失败时抛出
        """
        video = VideoService.get_video_by_id(db, video_id)
        
        try:
            video.status = status
            
            if status == VideoStatus.PUBLISHED:
                video.is_approved = True
                video.approved_by = approved_by
                video.approved_at = datetime.utcnow()
                video.published_at = datetime.utcnow()
            elif status == VideoStatus.REJECTED:
                video.is_approved = False
                video.rejection_reason = rejection_reason
                
            video.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(video)
            
            # 清除缓存
            cache_key_pattern = f"video:{video_id}:*"
            cache_manager.delete_pattern(cache_key_pattern)
            
            logger.info(f"Video status updated: {video_id} -> {status}")
            return video
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update video status {video_id}: {str(e)}", exc_info=True)
            raise BusinessException("更新视频状态失败")
    
    @staticmethod
    def update_transcoding_progress(
        db: Session,
        video_id: str,
        progress: float,
        status: TranscodingStatus
    ) -> VideoContent:
        """
        更新转码进度和状态
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            progress: 转码进度
            status: 转码状态
            
        Returns:
            更新后的视频内容对象
            
        Raises:
            NotFoundException: 视频不存在时抛出
            BusinessException: 更新失败时抛出
        """
        video = VideoService.get_video_by_id(db, video_id)
        
        try:
            video.transcoding_progress = progress
            video.transcoding_status = status
            
            if status == TranscodingStatus.COMPLETED:
                video.status = VideoStatus.READY
                
            video.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(video)
            
            return video
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update transcoding progress for {video_id}: {str(e)}", exc_info=True)
            raise BusinessException("更新转码进度失败")
    
    @staticmethod
    def increment_view_count(db: Session, video_id: str) -> VideoContent:
        """
        增加视频观看次数
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            更新后的视频内容对象
            
        Raises:
            NotFoundException: 视频不存在时抛出
            BusinessException: 更新失败时抛出
        """
        video = VideoService.get_video_by_id(db, video_id)
        
        try:
            video.view_count += 1
            db.commit()
            db.refresh(video)
            
            # 更新缓存中的观看次数
            cache_key = f"video:{video_id}:views"
            cache_manager.set(cache_key, video.view_count, expire=3600)
            
            return video
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to increment view count for {video_id}: {str(e)}", exc_info=True)
            raise BusinessException("更新观看次数失败")
    
    @staticmethod
    def record_video_interaction(
        db: Session,
        video_id: str,
        user_id: str,
        interaction_data: Dict[str, Any]
    ) -> VideoInteraction:
        """
        记录用户互动
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID
            interaction_data: 互动数据
            
        Returns:
            创建的互动记录对象
            
        Raises:
            BusinessException: 记录失败时抛出
        """
        try:
            interaction = VideoInteraction(
                video_id=video_id,
                user_id=user_id,
                interaction_type=interaction_data.get('interaction_type'),
                watch_duration=interaction_data.get('watch_duration', 0.0),
                watch_percentage=interaction_data.get('watch_percentage', 0.0)
            )
            
            db.add(interaction)
            db.commit()
            db.refresh(interaction)
            
            # 更新视频的互动计数
            video = VideoService.get_video_by_id(db, video_id)
            if interaction_data.get('interaction_type') == 'like':
                video.like_count += 1
            elif interaction_data.get('interaction_type') == 'share':
                video.share_count += 1
                
            db.commit()
            
            return interaction
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record interaction for video {video_id}: {str(e)}", exc_info=True)
            raise BusinessException("记录用户互动失败")
    
    @staticmethod
    def get_video_analytics(
        db: Session,
        video_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[VideoAnalytics]:
        """
        获取视频分析数据
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            视频分析数据列表
        """
        return db.query(VideoAnalytics).filter(
            VideoAnalytics.video_id == video_id,
            VideoAnalytics.date >= start_date,
            VideoAnalytics.date <= end_date
        ).order_by(VideoAnalytics.date).all()
    
    @staticmethod
    def get_video_stats(db: Session, video_id: str) -> Dict[str, Any]:
        """
        获取视频统计信息
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            视频统计信息字典
        """
        # 尝试从缓存获取
        cache_key = f"video:{video_id}:stats"
        cached_stats = cache_manager.get(cache_key)
        
        if cached_stats:
            return cached_stats
        
        video = VideoService.get_video_by_id(db, video_id)
        
        # 计算平均观看时长
        avg_watch_time = db.query(func.avg(VideoInteraction.watch_duration)).filter(
            VideoInteraction.video_id == video_id,
            VideoInteraction.interaction_type == 'view'
        ).scalar() or 0.0
        
        # 计算完成率
        total_views = db.query(func.count(VideoInteraction.id)).filter(
            VideoInteraction.video_id == video_id,
            VideoInteraction.interaction_type == 'view'
        ).scalar() or 0
        
        completed_views = db.query(func.count(VideoInteraction.id)).filter(
            VideoInteraction.video_id == video_id,
            VideoInteraction.interaction_type == 'view',
            VideoInteraction.watch_percentage >= 0.9
        ).scalar() or 0
        
        completion_rate = (completed_views / total_views * 100) if total_views > 0 else 0
        
        stats = {
            "video_id": video_id,
            "total_views": video.view_count,
            "total_likes": video.like_count,
            "total_shares": video.share_count,
            "total_comments": video.comment_count,
            "average_watch_time": round(avg_watch_time, 2),
            "completion_rate": round(completion_rate, 2),
            "engagement_rate": round((video.like_count + video.share_count) / max(video.view_count, 1) * 100, 2),
            "last_updated": datetime.utcnow()
        }
        
        # 缓存统计信息
        cache_manager.set(cache_key, stats, expire=300)  # 5分钟缓存
        
        return stats
    
    @staticmethod
    def get_popular_videos(
        db: Session,
        limit: int = 10,
        days: int = 7
    ) -> List[VideoContent]:
        """
        获取热门视频
        
        Args:
            db: 数据库会话
            limit: 返回视频数量限制
            days: 天数范围
            
        Returns:
            热门视频列表
        """
        cache_key = f"popular_videos:{days}d:{limit}"
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        videos = db.query(VideoContent).filter(
            VideoContent.status == VideoStatus.PUBLISHED,
            VideoContent.created_at >= since_date
        ).order_by(
            desc(VideoContent.view_count),
            desc(VideoContent.like_count)
        ).limit(limit).all()
        
        # 缓存结果
        cache_manager.set(cache_key, videos, expire=900)  # 15分钟缓存
        
        return videos