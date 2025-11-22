内容板块-文件工具文件
"""
文件处理工具模块

本模块提供了文件处理相关的实用工具函数，包括：
1. 文件哈希生成
2. 文件类型和大小验证
3. 文件名处理和清理
4. 唯一文件名生成
5. 媒体文件元数据提取
6. 分片大小计算
7. 临时文件管理
8. 文件大小格式化

支持的特性：
- 多种文件类型检测（MIME类型）
- 安全的文件名处理
- 大文件分片上传支持
- 媒体文件元数据提取（图片尺寸等）
"""

import hashlib
import os
import uuid
from typing import Optional, Tuple, List
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
import magic
from app.config import settings
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = [
    'generate_file_hash',
    'validate_file_type',
    'validate_file_size',
    'get_file_extension',
    'sanitize_filename',
    'generate_unique_filename',
    'get_image_dimensions',
    'get_video_duration',
    'calculate_chunk_size',
    'create_temp_file',
    'cleanup_temp_file',
    'format_file_size'
]


def generate_file_hash(file_content: bytes) -> str:
    """
    生成文件内容的哈希值（用于唯一标识文件）
    
    Args:
        file_content: 文件内容字节
        
    Returns:
        文件的SHA256哈希值
    """
    try:
        # 使用SHA256算法生成文件内容的哈希值
        file_hash = hashlib.sha256(file_content).hexdigest()
        # 返回哈希值
        return file_hash
    except Exception as e:
        # 记录哈希生成异常
        logger.error(f"文件哈希生成异常: {str(e)}")
        # 生成随机哈希作为后备
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()


def validate_file_type(file: UploadFile, allowed_types: List[str]) -> bool:
    """
    验证文件类型
    
    Args:
        file: 上传的文件对象
        allowed_types: 允许的文件类型列表
        
    Returns:
        文件类型是否允许
    """
    try:
        # 检查文件内容类型是否在允许列表中
        if file.content_type in allowed_types:
            return True
        
        # 如果不支持的内容类型，尝试使用python-magic检测实际类型
        file_content = file.file.read(1024)  # 读取前1024字节用于检测
        file.file.seek(0)  # 重置文件指针
        
        # 使用python-magic检测文件实际类型
        actual_type = magic.from_buffer(file_content, mime=True)
        
        # 检查实际类型是否在允许列表中
        if actual_type in allowed_types:
            return True
        
        # 文件类型不允许
        logger.warning(f"文件类型验证失败: 声明类型={file.content_type}, 实际类型={actual_type}, 允许类型={allowed_types}")
        return False
        
    except Exception as e:
        # 记录文件类型验证异常
        logger.error(f"文件类型验证异常: {str(e)}")
        return False


def validate_file_size(file: UploadFile, max_size: int) -> bool:
    """
    验证文件大小
    
    Args:
        file: 上传的文件对象
        max_size: 最大文件大小（字节）
        
    Returns:
        文件大小是否在限制内
    """
    try:
        # 获取当前文件位置
        current_position = file.file.tell()
        # 移动到文件末尾
        file.file.seek(0, 2)  # 0=偏移量, 2=文件末尾
        # 获取文件大小
        file_size = file.file.tell()
        # 重置文件指针到原始位置
        file.file.seek(current_position)
        
        # 检查文件大小是否超过限制
        if file_size > max_size:
            logger.warning(f"文件大小超过限制: {file_size} > {max_size}")
            return False
        
        return True
        
    except Exception as e:
        # 记录文件大小验证异常
        logger.error(f"文件大小验证异常: {str(e)}")
        return False


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        文件扩展名（小写，不带点）
    """
    try:
        # 使用pathlib获取文件后缀（包括点）
        suffix = Path(filename).suffix
        # 移除点并转换为小写
        extension = suffix.lower().lstrip('.')
        # 返回扩展名
        return extension
    except Exception as e:
        # 记录扩展名获取异常
        logger.error(f"文件扩展名获取异常: {str(e)}")
        return ""


def sanitize_filename(filename: str) -> str:
    """
    清理文件名（移除不安全字符）
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    try:
        # 获取文件扩展名
        extension = get_file_extension(filename)
        # 获取文件名（不含扩展名）
        name_without_ext = Path(filename).stem
        
        # 只允许字母、数字、下划线、连字符和点
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
        # 过滤不安全字符
        safe_name = ''.join(c for c in name_without_ext if c in safe_chars)
        
        # 如果过滤后名称为空，使用默认名称
        if not safe_name:
            safe_name = "file"
        
        # 重新组合文件名和扩展名
        if extension:
            safe_filename = f"{safe_name}.{extension}"
        else:
            safe_filename = safe_name
        
        # 返回安全的文件名
        return safe_filename
        
    except Exception as e:
        # 记录文件名清理异常
        logger.error(f"文件名清理异常: {str(e)}")
        # 返回默认文件名
        return f"file_{uuid.uuid4().hex}"


def generate_unique_filename(original_filename: str, user_id: str, content_type: str) -> str:
    """
    生成唯一的文件名
    
    Args:
        original_filename: 原始文件名
        user_id: 用户ID
        content_type: 内容类型
        
    Returns:
        唯一的文件名
    """
    try:
        # 清理原始文件名
        safe_filename = sanitize_filename(original_filename)
        # 获取文件扩展名
        extension = get_file_extension(safe_filename)
        # 生成时间戳目录（年/月/日）
        from datetime import datetime
        timestamp_dir = datetime.utcnow().strftime("%Y/%m/%d")
        # 生成唯一文件名（使用UUID）
        unique_name = uuid.uuid4().hex
        # 组合完整文件路径
        if extension:
            filename = f"{content_type}/{timestamp_dir}/{user_id}/{unique_name}.{extension}"
        else:
            filename = f"{content_type}/{timestamp_dir}/{user_id}/{unique_name}"
        
        # 返回完整的文件路径
        return filename
        
    except Exception as e:
        # 记录唯一文件名生成异常
        logger.error(f"唯一文件名生成异常: {str(e)}")
        # 生成后备文件名
        return f"{content_type}/fallback/{user_id}/{uuid.uuid4().hex}"


def get_image_dimensions(file_content: bytes) -> Tuple[Optional[int], Optional[int]]:
    """
    获取图片尺寸
    
    Args:
        file_content: 图片文件内容
        
    Returns:
        (宽度, 高度) 元组
    """
    try:
        # 导入PIL库（如果可用）
        try:
            from PIL import Image
            import io
            
            # 打开图片
            image = Image.open(io.BytesIO(file_content))
            # 获取图片尺寸
            width, height = image.size
            # 返回尺寸
            return width, height
            
        except ImportError:
            # PIL不可用，返回None
            logger.warning("PIL库未安装，无法获取图片尺寸")
            return None, None
            
    except Exception as e:
        # 记录图片尺寸获取异常
        logger.error(f"图片尺寸获取异常: {str(e)}")
        return None, None


def get_video_duration(file_content: bytes) -> Optional[int]:
    """
    获取视频时长（秒）
    
    Args:
        file_content: 视频文件内容
        
    Returns:
        视频时长（秒）或None
    """
    try:
        # 尝试使用moviepy库获取视频时长
        try:
            import io
            from moviepy.editor import VideoFileClip
            
            # 创建临时文件
            temp_file_path = create_temp_file(file_content, ".mp4")
            try:
                # 加载视频文件
                clip = VideoFileClip(temp_file_path)
                # 获取时长
                duration = int(clip.duration)
                # 关闭clip
                clip.close()
                # 清理临时文件
                cleanup_temp_file(temp_file_path)
                return duration
            except Exception:
                # 清理临时文件
                cleanup_temp_file(temp_file_path)
                raise
                
        except ImportError:
            # moviepy不可用
            logger.warning("moviepy库未安装，无法获取视频时长")
            return None
            
    except Exception as e:
        # 记录视频时长获取异常
        logger.error(f"视频时长获取异常: {str(e)}")
        return None


def calculate_chunk_size(file_size: int, max_chunk_size: int = 5 * 1024 * 1024) -> int:
    """
    计算分片大小
    
    Args:
        file_size: 文件大小（字节）
        max_chunk_size: 最大分片大小（默认5MB）
        
    Returns:
        建议的分片大小
    """
    try:
        # 如果文件很小，使用文件大小作为分片大小
        if file_size <= max_chunk_size:
            return file_size
        
        # 计算分片数量
        chunk_count = (file_size + max_chunk_size - 1) // max_chunk_size
        
        # 如果分片数量过多，增加分片大小
        if chunk_count > 100:
            # 重新计算分片大小，确保分片数量不超过100
            adjusted_chunk_size = (file_size + 99) // 100
            return min(adjusted_chunk_size, 10 * 1024 * 1024)  # 不超过10MB
        
        # 使用最大分片大小
        return max_chunk_size
        
    except Exception as e:
        # 记录分片大小计算异常
        logger.error(f"分片大小计算异常: {str(e)}")
        # 返回默认分片大小
        return max_chunk_size


def create_temp_file(file_content: bytes, suffix: str = ".tmp") -> str:
    """
    创建临时文件
    
    Args:
        file_content: 文件内容
        suffix: 文件后缀
        
    Returns:
        临时文件路径
        
    Raises:
        HTTPException: 创建临时文件失败时抛出
    """
    try:
        # 创建临时目录
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        
        # 生成临时文件路径
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}{suffix}")
        
        # 写入文件内容
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(file_content)
        
        # 返回临时文件路径
        return temp_file_path
        
    except Exception as e:
        # 记录临时文件创建异常
        logger.error(f"临时文件创建异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="临时文件创建失败"
        )


def cleanup_temp_file(file_path: str) -> None:
    """
    清理临时文件
    
    Args:
        file_path: 临时文件路径
    """
    try:
        # 检查文件是否存在
        if os.path.exists(file_path):
            # 删除文件
            os.remove(file_path)
            logger.debug(f"临时文件已清理: {file_path}")
    except Exception as e:
        # 记录临时文件清理异常（但不抛出异常）
        logger.warning(f"临时文件清理异常: {str(e)}")


def format_file_size(size_in_bytes: int) -> str:
    """
    格式化文件大小（人类可读格式）
    
    Args:
        size_in_bytes: 文件大小（字节）
        
    Returns:
        格式化的文件大小字符串
    """
    try:
        # 定义大小单位
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        # 初始化单位索引
        unit_index = 0
        # 初始化大小
        size = float(size_in_bytes)
        
        # 循环直到找到合适的单位
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        # 格式化大小字符串
        if unit_index == 0:
            # 字节，不显示小数
            return f"{int(size)} {units[unit_index]}"
        else:
            # 其他单位，显示1位小数
            return f"{size:.1f} {units[unit_index]}"
            
    except Exception as e:
        # 记录文件大小格式化异常
        logger.error(f"文件大小格式化异常: {str(e)}")
        return f"{size_in_bytes} B"