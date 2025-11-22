内容板块-视频api路由
"""
视频内容路由模块

本模块提供了视频内容管理系统的RESTful API接口，包括：
1. 视频内容的创建、查询、更新、删除
2. 视频文件上传（普通上传和分片上传）
3. 视频状态管理和发布
4. 视频互动记录（观看、点赞、分享等）
5. 视频统计信息查询
6. 视频转码进度跟踪
7. 热门视频推荐

所有接口都包含完善的认证、授权和异常处理机制。
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database.session import get_db
from app.middleware.auth import get_current_user
from app.schemas.video_schemas import (
    VideoCreate, VideoUpdate, VideoResponse, VideoUploadResponse,
    VideoUploadComplete, VideoInteractionCreate, VideoStatsResponse,
    VideoStatus, VideoVisibility, TranscodingStatus
)
from app.schemas.response_schemas import StandardResponse, PaginatedResponse
from app.schemas.pagination_schemas import PaginationParams
from app.services.video_service import VideoService
from app.services.transcoding_service import VideoTranscodingService
from app.services.cdn_service import cdn_service
from app.services.storage_service import StorageService
from app.core.exceptions import NotFoundException, ValidationException, BusinessException
from app.utils.pagination import Pagination
from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ['router']

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("", response_model=StandardResponse[VideoResponse], status_code=status.HTTP_201_CREATED)
async def create_video(
    video_data: VideoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    创建视频记录
    
    Args:
        video_data: 视频创建数据
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        创建的视频信息
        
    Raises:
        HTTPException: 创建失败时抛出相应错误
    """
    try:
        video = VideoService.create_video(db, video_data, current_user["user_id"])
        return StandardResponse(
            success=True,
            message="视频创建成功",
            data=video
        )
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Create video error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/{video_id}", response_model=StandardResponse[VideoResponse])
async def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    获取视频详情
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户信息（可选）
        
    Returns:
        视频详细信息
        
    Raises:
        HTTPException: 视频不存在或无权限时抛出相应错误
    """
    try:
        video = VideoService.get_video_by_id(db, video_id)
        
        # 检查权限
        if (video.visibility == VideoVisibility.PRIVATE and 
            (not current_user or video.user_id != current_user["user_id"])):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此视频")
            
        return StandardResponse(
            success=True,
            message="获取视频成功",
            data=video
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get video error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.put("/{video_id}", response_model=StandardResponse[VideoResponse])
async def update_video(
    video_id: str,
    update_data: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    更新视频信息
    
    Args:
        video_id: 视频ID
        update_data: 视频更新数据
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        更新后的视频信息
        
    Raises:
        HTTPException: 视频不存在、无权限或更新失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此视频")
            
        video = VideoService.update_video(db, video_id, update_data)
        return StandardResponse(
            success=True,
            message="视频更新成功",
            data=video
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update video error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.delete("/{video_id}", response_model=StandardResponse[bool])
async def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    删除视频（软删除）
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        删除操作结果
        
    Raises:
        HTTPException: 视频不存在、无权限或删除失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除此视频")
            
        result = VideoService.delete_video(db, video_id)
        return StandardResponse(
            success=True,
            message="视频删除成功",
            data=result
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete video error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("", response_model=PaginatedResponse[VideoResponse])
async def list_videos(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    merchant_id: Optional[str] = Query(None, description="商家ID过滤"),
    status: Optional[VideoStatus] = Query(None, description="状态过滤"),
    visibility: Optional[VideoVisibility] = Query(None, description="可见性过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    分页列出视频
    
    Args:
        user_id: 用户ID过滤
        merchant_id: 商家ID过滤
        status: 状态过滤
        visibility: 可见性过滤
        page: 页码
        page_size: 每页数量
        db: 数据库会话
        current_user: 当前用户信息（可选）
        
    Returns:
        分页视频列表
        
    Raises:
        HTTPException: 查询失败时抛出相应错误
    """
    try:
        # 如果是普通用户，只能看到公开视频或自己的视频
        if current_user and current_user.get("role") != "admin":
            if user_id and user_id != current_user["user_id"]:
                visibility = VideoVisibility.PUBLIC
            elif not user_id:
                user_id = current_user["user_id"]
                
        page_result = VideoService.list_videos(
            db, user_id, merchant_id, status, visibility, page, page_size
        )
        
        return PaginatedResponse(
            success=True,
            message="获取视频列表成功",
            data=page_result.items,
            pagination={
                "page": page_result.page,
                "page_size": page_result.page_size,
                "total": page_result.total,
                "pages": page_result.pages
            }
        )
    except Exception as e:
        logger.error(f"List videos error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.post("/{video_id}/upload", response_model=StandardResponse[VideoUploadResponse])
async def initiate_video_upload(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    初始化视频上传
    
    Args:
        video_id: 视频ID
        background_tasks: 后台任务
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        上传初始化信息
        
    Raises:
        HTTPException: 视频不存在、无权限或初始化失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权上传此视频")
            
        # 生成文件路径
        file_extension = video.original_filename.split('.')[-1] if '.' in video.original_filename else 'mp4'
        file_key = f"videos/{video_id}/original.{file_extension}"
        
        # 生成预签名上传URL
        upload_url = cdn_service.generate_presigned_url(file_key, 'put_object', 3600)
        
        # 更新视频文件信息
        video.file_key = file_key
        db.commit()
        
        response_data = VideoUploadResponse(
            video_id=video_id,
            upload_url=upload_url,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        return StandardResponse(
            success=True,
            message="上传初始化成功",
            data=response_data
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Initiate upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.post("/{video_id}/upload-multipart", response_model=StandardResponse[Dict[str, Any]])
async def initiate_multipart_upload(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    初始化分片上传
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        分片上传初始化信息
        
    Raises:
        HTTPException: 视频不存在、无权限或初始化失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权上传此视频")
            
        # 生成文件路径
        file_extension = video.original_filename.split('.')[-1] if '.' in video.original_filename else 'mp4'
        file_key = f"videos/{video_id}/original.{file_extension}"
        
        # 初始化分片上传
        upload_info = cdn_service.initiate_multipart_upload(file_key)
        
        # 更新视频文件信息
        video.file_key = file_key
        db.commit()
        
        return StandardResponse(
            success=True,
            message="分片上传初始化成功",
            data=upload_info
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Initiate multipart upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.post("/{video_id}/upload-complete", response_model=StandardResponse[bool])
async def complete_multipart_upload(
    video_id: str,
    complete_data: VideoUploadComplete,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    完成分片上传
    
    Args:
        video_id: 视频ID
        complete_data: 完成上传数据
        background_tasks: 后台任务
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        上传完成结果
        
    Raises:
        HTTPException: 视频不存在、无权限或完成失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权上传此视频")
            
        # 完成分片上传
        cdn_service.complete_multipart_upload(
            video.file_key, complete_data.upload_id, complete_data.parts
        )
        
        # 获取文件信息
        file_info = cdn_service.get_file_info(video.file_key)
        if file_info:
            video.file_size = file_info["file_size"]
            video.status = VideoStatus.PROCESSING
            db.commit()
            
            # 启动转码任务
            if settings.ENABLE_VIDEO_TRANSCODING:
                profiles = VideoTranscodingService.create_transcoding_profiles(
                    db, video_id, video.file_key
                )
                background_tasks.add_task(
                    VideoTranscodingService.start_transcoding_task,
                    video_id, video.file_key, profiles
                )
        
        return StandardResponse(
            success=True,
            message="分片上传完成",
            data=True
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete multipart upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.post("/{video_id}/interactions", response_model=StandardResponse[bool])
async def record_interaction(
    video_id: str,
    interaction_data: VideoInteractionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    记录用户互动
    
    Args:
        video_id: 视频ID
        interaction_data: 互动数据
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        互动记录结果
        
    Raises:
        HTTPException: 视频不存在、无权限或记录失败时抛出相应错误
    """
    try:
        # 增加观看次数（如果是观看互动）
        if interaction_data.interaction_type == 'view':
            VideoService.increment_view_count(db, video_id)
            
        # 记录互动
        VideoService.record_video_interaction(
            db, video_id, current_user["user_id"], interaction_data.model_dump()
        )
        
        return StandardResponse(
            success=True,
            message="互动记录成功",
            data=True
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Record interaction error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/{video_id}/stats", response_model=StandardResponse[VideoStatsResponse])
async def get_video_stats(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    获取视频统计信息
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户信息（可选）
        
    Returns:
        视频统计信息
        
    Raises:
        HTTPException: 视频不存在、无权限或获取失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if (video.visibility == VideoVisibility.PRIVATE and 
            current_user and video.user_id != current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此视频统计")
            
        stats = VideoService.get_video_stats(db, video_id)
        return StandardResponse(
            success=True,
            message="获取视频统计成功",
            data=stats
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get video stats error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/{video_id}/transcoding-progress", response_model=StandardResponse[Dict[str, Any]])
async def get_transcoding_progress(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取转码进度
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        转码进度信息
        
    Raises:
        HTTPException: 视频不存在、无权限或获取失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看转码进度")
            
        progress = VideoTranscodingService.get_transcoding_progress(db, video_id)
        return StandardResponse(
            success=True,
            message="获取转码进度成功",
            data=progress
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get transcoding progress error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.post("/{video_id}/publish", response_model=StandardResponse[VideoResponse])
async def publish_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    发布视频
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户信息
        
    Returns:
        发布后的视频信息
        
    Raises:
        HTTPException: 视频不存在、无权限、状态不正确或发布失败时抛出相应错误
    """
    try:
        # 检查权限
        video = VideoService.get_video_by_id(db, video_id)
        if video.user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权发布此视频")
            
        # 检查视频状态
        if video.transcoding_status != TranscodingStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="视频转码未完成")
            
        video = VideoService.update_video_status(
            db, video_id, VideoStatus.PUBLISHED, current_user["user_id"]
        )
        
        return StandardResponse(
            success=True,
            message="视频发布成功",
            data=video
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Publish video error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/popular/latest", response_model=StandardResponse[List[VideoResponse]])
async def get_popular_videos(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    days: int = Query(7, ge=1, le=30, description="时间范围(天)"),
    db: Session = Depends(get_db)
):
    """
    获取热门视频
    
    Args:
        limit: 返回视频数量
        days: 时间范围（天）
        db: 数据库会话
        
    Returns:
        热门视频列表
        
    Raises:
        HTTPException: 查询失败时抛出相应错误
    """
    try:
        videos = VideoService.get_popular_videos(db, limit, days)
        return StandardResponse(
            success=True,
            message="获取热门视频成功",
            data=videos
        )
    except Exception as e:
        logger.error(f"Get popular videos error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")