内容板块-视频转码服务
"""
视频转码服务模块

本模块提供了视频转码处理的核心功能，包括：
1. 转码配置文件的创建和管理
2. 多分辨率视频转码处理
3. 视频缩略图生成
4. 转码进度跟踪和状态更新
5. 转码任务的异步处理

使用FFmpeg作为转码引擎，支持多种视频格式和分辨率的转码。
"""

import os
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json
from sqlalchemy.orm import Session

from app.config import settings
from app.utils.cache_utils import cache_manager
from app.models.video_models import VideoTranscodingProfile, VideoThumbnail
from app.schemas.video_schemas import TranscodingStatus
from app.core.exceptions import BusinessException

logger = logging.getLogger(__name__)

__all__ = ['VideoTranscodingService']


class VideoTranscodingService:
    """视频转码服务"""
    
    # 转码配置预设
    TRANSCODING_PROFILES = {
        "1080p": {
            "width": 1920,
            "height": 1080,
            "video_bitrate": "5000k",
            "audio_bitrate": "192k",
            "profile": "high",
            "level": "4.0"
        },
        "720p": {
            "width": 1280,
            "height": 720,
            "video_bitrate": "2500k",
            "audio_bitrate": "128k",
            "profile": "main", 
            "level": "3.1"
        },
        "480p": {
            "width": 854,
            "height": 480,
            "video_bitrate": "1000k",
            "audio_bitrate": "96k",
            "profile": "main",
            "level": "3.0"
        },
        "360p": {
            "width": 640,
            "height": 360,
            "video_bitrate": "600k",
            "audio_bitrate": "64k",
            "profile": "baseline",
            "level": "3.0"
        }
    }
    
    @staticmethod
    def create_transcoding_profiles(db: Session, video_id: str, original_file_key: str) -> List[VideoTranscodingProfile]:
        """
        创建转码配置记录
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            original_file_key: 原始文件键
            
        Returns:
            创建的转码配置列表
        """
        profiles = []
        
        for profile_name, config in VideoTranscodingService.TRANSCODING_PROFILES.items():
            profile = VideoTranscodingProfile(
                video_id=video_id,
                profile_name=profile_name,
                width=config["width"],
                height=config["height"],
                video_bitrate=int(config["video_bitrate"].replace('k', '000')),
                audio_bitrate=int(config["audio_bitrate"].replace('k', '000')),
                file_key=f"transcoded/{video_id}/{profile_name}.mp4",
                status=TranscodingStatus.PENDING
            )
            db.add(profile)
            profiles.append(profile)
        
        db.commit()
        for profile in profiles:
            db.refresh(profile)
            
        logger.info(f"Created transcoding profiles for video: {video_id}")
        return profiles
    
    @staticmethod
    async def start_transcoding_task(video_id: str, original_file_path: str, profiles: List[VideoTranscodingProfile]) -> None:
        """
        启动转码任务（异步）
        
        Args:
            video_id: 视频ID
            original_file_path: 原始文件路径
            profiles: 转码配置列表
        """
        # 这里实际应该使用消息队列（如Celery）来异步处理转码
        # 为简化，我们使用 asyncio.create_task 来模拟异步处理
        asyncio.create_task(
            VideoTranscodingService.process_transcoding(video_id, original_file_path, profiles)
        )
    
    @staticmethod
    async def process_transcoding(video_id: str, original_file_path: str, profiles: List[VideoTranscodingProfile]) -> None:
        """
        处理视频转码
        
        Args:
            video_id: 视频ID
            original_file_path: 原始文件路径
            profiles: 转码配置列表
        """
        from app.database.session import SessionLocal
        from app.services.video_service import VideoService
        
        db = SessionLocal()
        try:
            # 更新视频状态为转码中
            video = VideoService.get_video_by_id(db, video_id)
            video.transcoding_status = TranscodingStatus.PROCESSING
            db.commit()
            
            # 为每个配置执行转码
            for profile in profiles:
                try:
                    output_path = f"/tmp/{profile.id}.mp4"  # 临时输出路径
                    config = VideoTranscodingService.TRANSCODING_PROFILES[profile.profile_name]
                    
                    # 构建FFmpeg命令
                    cmd = [
                        'ffmpeg', '-i', original_file_path,
                        '-vf', f'scale={config["width"]}:{config["height"]}',
                        '-c:v', 'libx264',
                        '-b:v', config['video_bitrate'],
                        '-profile:v', config['profile'],
                        '-level', config['level'],
                        '-c:a', 'aac', 
                        '-b:a', config['audio_bitrate'],
                        '-y', output_path
                    ]
                    
                    # 执行转码
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        # 转码成功，上传到存储
                        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                        # 这里应该上传到云存储，示例中省略
                        # await StorageService.upload_file(output_path, profile.file_key)
                        
                        # 更新转码配置状态
                        profile.status = TranscodingStatus.COMPLETED
                        profile.file_size = file_size
                        profile.cdn_url = f"{settings.CDN_BASE_URL}/{profile.file_key}"
                        db.commit()
                        
                        logger.info(f"Transcoding completed for profile {profile.profile_name} of video {video_id}")
                        
                        # 清理临时文件
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    else:
                        logger.error(f"Transcoding failed for profile {profile.profile_name}: {stderr.decode()}")
                        profile.status = TranscodingStatus.FAILED
                        db.commit()
                        
                        # 清理临时文件
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        
                except Exception as e:
                    logger.error(f"Error in transcoding profile {profile.profile_name}: {str(e)}", exc_info=True)
                    profile.status = TranscodingStatus.FAILED
                    db.commit()
            
            # 检查所有转码任务是否完成
            completed = all(p.status == TranscodingStatus.COMPLETED for p in profiles)
            failed = any(p.status == TranscodingStatus.FAILED for p in profiles)
            
            # 更新视频转码状态
            if completed:
                video.transcoding_status = TranscodingStatus.COMPLETED
                video.status = "ready"
            elif failed:
                video.transcoding_status = TranscodingStatus.FAILED
                
            db.commit()
            
            # 生成缩略图
            await VideoTranscodingService.generate_thumbnails(db, video_id, original_file_path)
            
        except Exception as e:
            logger.error(f"Transcoding process failed for video {video_id}: {str(e)}", exc_info=True)
        finally:
            db.close()
    
    @staticmethod
    async def generate_thumbnails(db: Session, video_id: str, original_file_path: str, timepoints: Optional[List[float]] = None) -> None:
        """
        生成缩略图
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            original_file_path: 原始文件路径
            timepoints: 时间点列表，默认为[10, 30, 60]
        """
        if timepoints is None:
            timepoints = [10, 30, 60]  # 默认在10秒、30秒、60秒处生成
            
        for timepoint in timepoints:
            try:
                output_path = f"/tmp/thumbnail_{video_id}_{timepoint}.jpg"
                
                cmd = [
                    'ffmpeg', '-i', original_file_path,
                    '-ss', str(timepoint),
                    '-vframes', '1',
                    '-vf', 'scale=320:180',
                    '-y', output_path
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    # 生成成功，上传到存储
                    file_key = f"thumbnails/{video_id}/thumb_{timepoint}.jpg"
                    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    # await StorageService.upload_file(output_path, file_key)
                    
                    thumbnail = VideoThumbnail(
                        video_id=video_id,
                        thumbnail_type="generated",
                        time_offset=timepoint,
                        width=320,
                        height=180,
                        file_key=file_key,
                        file_size=file_size,
                        format="jpg",
                        cdn_url=f"{settings.CDN_BASE_URL}/{file_key}"
                    )
                    db.add(thumbnail)
                    db.commit()
                    
                    logger.info(f"Thumbnail generated at {timepoint}s for video {video_id}")
                    
                    # 清理临时文件
                    if os.path.exists(output_path):
                        os.remove(output_path)
                else:
                    logger.error(f"Thumbnail generation failed at {timepoint}s: {stderr.decode()}")
                    # 清理临时文件
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    
            except Exception as e:
                logger.error(f"Thumbnail generation failed for video {video_id} at {timepoint}s: {str(e)}", exc_info=True)
                # 清理临时文件
                if 'output_path' in locals() and os.path.exists(output_path):
                    os.remove(output_path)
    
    @staticmethod
    def get_transcoding_progress(db: Session, video_id: str) -> Dict[str, Any]:
        """
        获取转码进度
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            转码进度信息字典
        """
        profiles = db.query(VideoTranscodingProfile).filter(
            VideoTranscodingProfile.video_id == video_id
        ).all()
        
        total = len(profiles)
        completed = sum(1 for p in profiles if p.status == TranscodingStatus.COMPLETED)
        failed = sum(1 for p in profiles if p.status == TranscodingStatus.FAILED)
        
        progress = (completed / total * 100) if total > 0 else 0
        
        return {
            "total_profiles": total,
            "completed": completed,
            "failed": failed,
            "progress": progress,
            "profiles": [{
                "name": p.profile_name,
                "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                "cdn_url": p.cdn_url
            } for p in profiles]
        }