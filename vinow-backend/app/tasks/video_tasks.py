"""
视频处理任务模块

本模块提供了基于Celery的异步视频处理任务，包括：
1. 视频文件下载和信息提取
2. 多分辨率视频转码
3. 视频缩略图生成
4. 处理文件上传和元数据更新
5. 旧文件清理任务

依赖的外部工具：
- FFmpeg：视频转码和缩略图生成
- FFprobe：视频信息提取

所有任务都支持重试机制和错误处理。
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from celery import shared_task
from app.config import settings
from app.database.connection import supabase
from app.utils.file_utils import get_video_duration, get_image_dimensions
import logging
import subprocess
import tempfile
import requests
from datetime import datetime, timedelta

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = [
    'process_video_file',
    'cleanup_old_video_files'
]


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_video_file(self, media_id: str, file_url: str, file_path: str) -> Dict[str, Any]:
    """
    处理视频文件任务 - 生成多分辨率版本和缩略图
    
    Args:
        self: Celery任务实例
        media_id: 媒体文件ID
        file_url: 文件URL
        file_path: 文件路径
        
    Returns:
        处理结果字典
        
    Raises:
        Exception: 处理失败时抛出异常以触发重试
    """
    try:
        # 记录任务开始
        logger.info(f"开始处理视频文件: {media_id}, 路径: {file_path}")
        
        # 更新媒体文件状态为处理中
        update_media_status(media_id, "processing")
        
        # 下载视频文件到临时目录
        temp_file_path = download_video_file(file_url)
        if not temp_file_path:
            raise Exception("视频文件下载失败")
        
        try:
            # 获取视频信息
            video_info = get_video_info(temp_file_path)
            
            # 生成多分辨率版本
            resolutions = settings.VIDEO_TRANSCODE_RESOLUTIONS
            processed_files = {}
            
            for resolution in resolutions:
                # 生成该分辨率的视频文件
                processed_file = transcode_video(temp_file_path, resolution)
                if processed_file:
                    # 上传处理后的文件
                    uploaded_url = upload_processed_file(processed_file, file_path, resolution)
                    if uploaded_url:
                        processed_files[resolution] = uploaded_url
                    
                    # 清理临时文件
                    os.remove(processed_file)
            
            # 生成缩略图
            thumbnail_urls = generate_video_thumbnails(temp_file_path, file_path, settings.VIDEO_THUMBNAIL_COUNT)
            
            # 更新媒体文件记录
            update_media_metadata(
                media_id, 
                video_info, 
                processed_files, 
                thumbnail_urls
            )
            
            # 记录任务成功
            logger.info(f"视频文件处理完成: {media_id}")
            
            return {
                "success": True,
                "media_id": media_id,
                "processed_files": processed_files,
                "thumbnails": thumbnail_urls,
                "video_info": video_info
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        # 记录任务失败
        logger.error(f"视频文件处理失败: {media_id}, 错误: {str(e)}", exc_info=True)
        
        # 更新媒体文件状态为失败
        update_media_status(media_id, "failed", str(e))
        
        # 重试任务
        if self.request.retries < self.max_retries:
            # 计算重试延迟（指数退避）
            retry_delay = self.default_retry_delay * (2 ** self.request.retries)
            raise self.retry(countdown=retry_delay, exc=e)
        else:
            # 重试次数已用完，返回失败结果
            return {
                "success": False,
                "media_id": media_id,
                "error": str(e)
            }


def download_video_file(file_url: str) -> Optional[str]:
    """
    下载视频文件到临时目录
    
    Args:
        file_url: 文件URL
        
    Returns:
        临时文件路径或None
    """
    try:
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_file_path = temp_file.name
        temp_file.close()
        
        # 使用requests下载文件
        logger.info(f"下载视频文件: {file_url} -> {temp_file_path}")
        
        response = requests.get(file_url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(temp_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"视频文件下载完成: {temp_file_path}")
        return temp_file_path
        
    except Exception as e:
        logger.error(f"视频文件下载失败: {str(e)}", exc_info=True)
        # 清理临时文件
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return None


def get_video_info(file_path: str) -> Dict[str, Any]:
    """
    获取视频文件信息
    
    Args:
        file_path: 视频文件路径
        
    Returns:
        视频信息字典
    """
    try:
        # 使用FFprobe获取视频信息
        cmd = [
            'ffprobe', 
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            
            # 提取视频流信息
            video_stream = next((stream for stream in info['streams'] if stream['codec_type'] == 'video'), None)
            
            if video_stream:
                return {
                    "duration": float(info['format']['duration']) if 'duration' in info['format'] else 0,
                    "width": int(video_stream['width']) if 'width' in video_stream else 0,
                    "height": int(video_stream['height']) if 'height' in video_stream else 0,
                    "codec": video_stream.get('codec_name', 'unknown'),
                    "bitrate": int(info['format'].get('bit_rate', 0)) if 'bit_rate' in info['format'] else 0,
                    "size": int(info['format'].get('size', 0)) if 'size' in info['format'] else os.path.getsize(file_path)
                }
        
        # 如果FFprobe失败，使用备用方法
        return {
            "duration": get_video_duration(open(file_path, 'rb').read()) or 0,
            "width": 0,
            "height": 0,
            "codec": "unknown",
            "bitrate": 0,
            "size": os.path.getsize(file_path)
        }
        
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}", exc_info=True)
        return {
            "duration": 0,
            "width": 0,
            "height": 0,
            "codec": "unknown",
            "bitrate": 0,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }


def transcode_video(input_path: str, resolution: str) -> Optional[str]:
    """
    转码视频到指定分辨率
    
    Args:
        input_path: 输入文件路径
        resolution: 目标分辨率
        
    Returns:
        输出文件路径或None
    """
    try:
        # 创建输出文件
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{resolution}.mp4")
        output_path = output_file.name
        output_file.close()
        
        # 分辨率映射
        resolution_map = {
            "360p": "640x360",
            "480p": "854x480", 
            "720p": "1280x720",
            "1080p": "1920x1080"
        }
        
        resolution_str = resolution_map.get(resolution, "640x360")
        
        # 使用FFmpeg转码
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'scale={resolution_str}',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',  # 覆盖输出文件
            output_path
        ]
        
        logger.info(f"转码视频: {input_path} -> {output_path} ({resolution})")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"视频转码完成: {output_path}")
            return output_path
        else:
            logger.error(f"视频转码失败: {result.stderr}")
            # 清理临时文件
            if os.path.exists(output_path):
                os.remove(output_path)
            return None
            
    except Exception as e:
        logger.error(f"视频转码异常: {str(e)}", exc_info=True)
        # 清理临时文件
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        return None


def generate_video_thumbnails(input_path: str, original_path: str, count: int) -> List[str]:
    """
    生成视频缩略图
    
    Args:
        input_path: 输入文件路径
        original_path: 原始文件路径
        count: 缩略图数量
        
    Returns:
        缩略图URL列表
    """
    try:
        thumbnail_urls = []
        
        # 获取视频时长
        video_info = get_video_info(input_path)
        duration = video_info.get("duration", 0)
        
        if duration <= 0:
            logger.warning("视频时长无效，无法生成缩略图")
            return []
        
        # 计算缩略图时间点
        intervals = [i * duration / (count + 1) for i in range(1, count + 1)]
        
        for i, interval in enumerate(intervals):
            # 创建缩略图文件
            thumbnail_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_thumb_{i}.jpg")
            thumbnail_path = thumbnail_file.name
            thumbnail_file.close()
            
            try:
                # 使用FFmpeg生成缩略图
                cmd = [
                    'ffmpeg',
                    '-ss', str(interval),  # 跳转到指定时间
                    '-i', input_path,
                    '-vframes', '1',  # 只取一帧
                    '-q:v', '2',  # 质量
                    '-y',  # 覆盖输出文件
                    thumbnail_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    # 上传缩略图
                    thumbnail_url = upload_thumbnail(thumbnail_path, original_path, i)
                    if thumbnail_url:
                        thumbnail_urls.append(thumbnail_url)
                else:
                    logger.error(f"缩略图生成失败: {result.stderr}")
            finally:
                # 清理临时文件
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
        
        logger.info(f"生成 {len(thumbnail_urls)} 个缩略图")
        return thumbnail_urls
        
    except Exception as e:
        logger.error(f"生成视频缩略图异常: {str(e)}", exc_info=True)
        return []


def upload_processed_file(file_path: str, original_path: str, resolution: str) -> Optional[str]:
    """
    上传处理后的文件
    
    Args:
        file_path: 文件路径
        original_path: 原始文件路径
        resolution: 分辨率
        
    Returns:
        上传后的文件URL或None
    """
    try:
        # 生成新的文件路径
        file_extension = os.path.splitext(original_path)[1]
        new_path = f"{os.path.splitext(original_path)[0]}_{resolution}{file_extension}"
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # 上传到Supabase存储
        upload_response = supabase.storage.from_("content-media").upload(
            new_path, file_content
        )
        
        if isinstance(upload_response, dict) and upload_response.get('error'):
            logger.error(f"文件上传失败: {upload_response['error'].get('message', '未知错误')}")
            return None
        
        # 获取公开URL
        public_url = supabase.storage.from_("content-media").get_public_url(new_path)
        
        logger.info(f"处理文件上传成功: {new_path}")
        return public_url
        
    except Exception as e:
        logger.error(f"上传处理文件异常: {str(e)}", exc_info=True)
        return None


def upload_thumbnail(file_path: str, original_path: str, index: int) -> Optional[str]:
    """
    上传缩略图
    
    Args:
        file_path: 缩略图文件路径
        original_path: 原始文件路径
        index: 缩略图索引
        
    Returns:
        缩略图URL或None
    """
    try:
        # 生成缩略图路径
        thumbnail_path = f"{os.path.splitext(original_path)[0]}_thumb_{index}.jpg"
        
        # 读取缩略图文件
        with open(file_path, 'rb') as f:
            thumbnail_content = f.read()
        
        # 上传到Supabase存储
        upload_response = supabase.storage.from_("content-media").upload(
            thumbnail_path, thumbnail_content
        )
        
        if isinstance(upload_response, dict) and upload_response.get('error'):
            logger.error(f"缩略图上传失败: {upload_response['error'].get('message', '未知错误')}")
            return None
        
        # 获取公开URL
        public_url = supabase.storage.from_("content-media").get_public_url(thumbnail_path)
        
        logger.info(f"缩略图上传成功: {thumbnail_path}")
        return public_url
        
    except Exception as e:
        logger.error(f"上传缩略图异常: {str(e)}", exc_info=True)
        return None


def update_media_status(media_id: str, status: str, error_message: Optional[str] = None) -> None:
    """
    更新媒体文件状态
    
    Args:
        media_id: 媒体文件ID
        status: 状态
        error_message: 错误消息
    """
    try:
        update_data = {
            "processing_status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if error_message:
            update_data["processing_metadata"] = {"error": error_message}
        
        response = supabase.table("content_media").update(update_data).eq("id", media_id).execute()
        
        if isinstance(response, dict) and response.get('error'):
            logger.error(f"更新媒体状态失败: {response['error'].get('message', '未知错误')}")
        
    except Exception as e:
        logger.error(f"更新媒体状态异常: {str(e)}", exc_info=True)


def update_media_metadata(media_id: str, video_info: Dict[str, Any], processed_files: Dict[str, str], thumbnails: List[str]) -> None:
    """
    更新媒体文件元数据
    
    Args:
        media_id: 媒体文件ID
        video_info: 视频信息
        processed_files: 处理后的文件
        thumbnails: 缩略图列表
    """
    try:
        update_data = {
            "processing_status": "completed",
            "duration": video_info.get("duration"),
            "width": video_info.get("width"),
            "height": video_info.get("height"),
            "thumbnail_url": thumbnails[0] if thumbnails else None,
            "processing_metadata": {
                "video_info": video_info,
                "processed_files": processed_files,
                "thumbnails": thumbnails
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("content_media").update(update_data).eq("id", media_id).execute()
        
        if isinstance(response, dict) and response.get('error'):
            logger.error(f"更新媒体元数据失败: {response['error'].get('message', '未知错误')}")
        
    except Exception as e:
        logger.error(f"更新媒体元数据异常: {str(e)}", exc_info=True)


@shared_task
def cleanup_old_video_files(days_old: int = 30) -> Dict[str, Any]:
    """
    清理旧的视频文件任务
    
    Args:
        days_old: 文件天数阈值
        
    Returns:
        清理结果字典
    """
    try:
        logger.info(f"开始清理 {days_old} 天前的视频文件")
        
        # 计算截止日期
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # 查询旧的媒体文件记录
        response = supabase.table("content_media") \
            .select("id, file_url, created_at") \
            .lt("created_at", cutoff_date.isoformat()) \
            .execute()
        
        if isinstance(response, dict) and response.get('error'):
            raise Exception(f"查询旧文件失败: {response['error'].get('message', '未知错误')}")
        
        cleaned_files = 0
        if hasattr(response, 'data') and response.data:
            for media_record in response.data:
                try:
                    # 删除存储中的文件
                    file_path = media_record.get("file_url", "")
                    if file_path:
                        # 从URL中提取文件路径
                        # 这里需要根据实际的文件路径格式进行调整
                        delete_response = supabase.storage.from_("content-media").remove([file_path])
                        
                        if isinstance(delete_response, dict) and delete_response.get('error'):
                            logger.warning(f"删除文件失败: {file_path}, 错误: {delete_response['error'].get('message', '未知错误')}")
                        else:
                            cleaned_files += 1
                
                except Exception as e:
                    logger.warning(f"清理单个文件异常: {str(e)}")
        
        logger.info(f"视频文件清理完成，共清理 {cleaned_files} 个文件")
        
        return {"success": True, "cleaned_files": cleaned_files}
        
    except Exception as e:
        logger.error(f"清理视频文件异常: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}