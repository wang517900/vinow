内容系统
import logging
import os
import aiofiles
import magic
from typing import Dict, List, Optional, Any, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import UploadFile, HTTPException
import shutil
from pathlib import Path

from app.config import settings
from app.core.exceptions import FileUploadException
from app.utils.logger import logger

class FileService:
    """文件服务类 - 处理文件上传、验证、存储和管理"""
    
    def __init__(self):
        """初始化文件服务"""
        # 创建存储目录
        self.upload_dir = Path(settings.upload_dir)
        self.video_dir = self.upload_dir / "videos"
        self.image_dir = self.upload_dir / "images"
        self.document_dir = self.upload_dir / "documents"
        self.temp_dir = self.upload_dir / "temp"
        
        # 确保目录存在
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的存储目录"""
        try:
            directories = [
                self.video_dir,
                self.image_dir,
                self.document_dir,
                self.temp_dir
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            logger.info("文件存储目录创建成功")
        except Exception as e:
            logger.error(f"创建存储目录失败: {str(e)}")
            raise FileUploadException("无法创建文件存储目录")
    
    async def validate_file(self, file: UploadFile, file_type: str = "video") -> Dict[str, Any]:
        """验证上传文件
        
        Args:
            file: 上传的文件对象
            file_type: 文件类型 ("video", "image", "document")
            
        Returns:
            包含文件信息的字典
            
        Raises:
            FileUploadException: 文件验证失败
        """
        try:
            # 检查文件大小
            file_size = 0
            if hasattr(file, 'size'):
                file_size = file.size
            else:
                # 对于流式上传，需要读取内容来获取大小
                content = await file.read()
                file_size = len(content)
                await file.seek(0)  # 重置文件指针
            
            # 根据文件类型检查大小限制
            max_size = getattr(settings, f'max_{file_type}_size', settings.max_file_size)
            if file_size > max_size:
                raise FileUploadException(f"文件大小超过限制: {file_size} > {max_size}")
            
            # 检查文件类型
            content_type = file.content_type
            allowed_types_attr = f'allowed_{file_type}_types'
            allowed_types = getattr(settings, allowed_types_attr, [])
            
            if not allowed_types:
                # 如果没有特定类型设置，则使用通用设置
                allowed_types = getattr(settings, 'allowed_file_types', [])
            
            if content_type not in allowed_types:
                # 使用python-magic进行更精确的文件类型检测
                file_content = await file.read(1024)  # 读取前1024字节进行检测
                await file.seek(0)  # 重置文件指针
                
                detected_type = magic.from_buffer(file_content, mime=True)
                if detected_type not in allowed_types:
                    raise FileUploadException(f"不支持的文件类型: {detected_type}")
            
            # 生成文件信息
            file_info = {
                "original_filename": file.filename,
                "content_type": content_type,
                "file_size": file_size,
                "file_extension": self._get_file_extension(file.filename),
                "is_valid": True,
                "validation_time": datetime.utcnow().isoformat()
            }
            
            logger.info(f"文件验证成功: {file.filename}, 类型: {content_type}, 大小: {file_size}")
            return file_info
            
        except FileUploadException:
            raise
        except Exception as e:
            logger.error(f"文件验证失败 {file.filename}: {str(e)}")
            raise FileUploadException(f"文件验证失败: {str(e)}")
    
    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            文件扩展名（小写）
        """
        return Path(filename).suffix.lower()
    
    async def save_upload_file(self, file: UploadFile, file_type: str = "video", 
                              user_id: Optional[str] = None) -> Dict[str, Any]:
        """保存上传的文件
        
        Args:
            file: 上传的文件对象
            file_type: 文件类型 ("video", "image", "document")
            user_id: 用户ID（用于权限控制）
            
        Returns:
            包含文件存储信息的字典
            
        Raises:
            FileUploadException: 文件保存失败
        """
        try:
            # 验证文件
            file_info = await self.validate_file(file, file_type)
            
            # 生成唯一文件名
            file_id = str(uuid4())
            file_extension = file_info["file_extension"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{file_id}_{timestamp}{file_extension}"
            
            # 确定存储目录
            storage_dir = self._get_storage_directory(file_type)
            file_path = storage_dir / new_filename
            
            # 保存文件
            async with aiofiles.open(file_path, "wb") as buffer:
                content = await file.read()
                await buffer.write(content)
            
            # 更新文件信息
            file_info.update({
                "file_id": file_id,
                "storage_path": str(file_path),
                "filename": new_filename,
                "url": self._generate_file_url(file_type, new_filename),
                "saved_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "checksum": self._calculate_checksum(content)
            })
            
            logger.info(f"文件保存成功: {file_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"保存文件失败 {file.filename}: {str(e)}")
            raise FileUploadException(f"保存文件失败: {str(e)}")
    
    def _get_storage_directory(self, file_type: str) -> Path:
        """获取指定类型的存储目录
        
        Args:
            file_type: 文件类型
            
        Returns:
            存储目录路径
        """
        directory_mapping = {
            "video": self.video_dir,
            "image": self.image_dir,
            "document": self.document_dir
        }
        return directory_mapping.get(file_type, self.temp_dir)
    
    def _generate_file_url(self, file_type: str, filename: str) -> str:
        """生成文件访问URL
        
        Args:
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            文件访问URL
        """
        # 在实际应用中，这里应该生成CDN URL或预签名URL
        # 这里使用简化版本，返回相对路径
        return f"/api/v1/files/{file_type}/{filename}"
    
    def _calculate_checksum(self, content: bytes) -> str:
        """计算文件校验和
        
        Args:
            content: 文件内容
            
        Returns:
            MD5校验和
        """
        import hashlib
        return hashlib.md5(content).hexdigest()
    
    async def generate_thumbnail(self, video_path: str, output_path: str) -> bool:
        """生成视频缩略图
        
        Args:
            video_path: 视频文件路径
            output_path: 输出缩略图路径
            
        Returns:
            是否成功生成缩略图
        """
        try:
            # 检查是否安装了ffmpeg-python
            try:
                import ffmpeg
                # 使用ffmpeg生成缩略图
                (
                    ffmpeg
                    .input(video_path, ss=1)
                    .filter('scale', 320, -1)
                    .output(output_path, vframes=1)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                logger.info(f"缩略图生成成功: {output_path}")
                return True
            except ImportError:
                # 如果没有安装ffmpeg-python，创建占位符
                logger.warning("未安装ffmpeg-python，创建占位符缩略图")
                thumbnail_path = Path(output_path)
                thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiofiles.open(thumbnail_path, "wb") as f:
                    await f.write(b"thumbnail_placeholder")
                
                logger.info(f"占位符缩略图创建成功: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"生成缩略图失败 {video_path}: {str(e)}")
            return False
    
    async def process_video_upload(self, file: UploadFile, user_id: Optional[str] = None) -> Dict[str, Any]:
        """处理视频上传 - 包括验证、保存和生成缩略图
        
        Args:
            file: 上传的视频文件
            user_id: 用户ID
            
        Returns:
            包含视频和缩略图信息的字典
            
        Raises:
            FileUploadException: 视频处理失败
        """
        try:
            # 保存视频文件
            video_info = await self.save_upload_file(file, "video", user_id)
            
            # 生成缩略图
            video_path = video_info["storage_path"]
            thumbnail_filename = f"{video_info['file_id']}_thumbnail.jpg"
            thumbnail_path = self.image_dir / thumbnail_filename
            
            thumbnail_generated = await self.generate_thumbnail(video_path, str(thumbnail_path))
            
            if thumbnail_generated:
                video_info["thumbnail_url"] = self._generate_file_url("image", thumbnail_filename)
                video_info["thumbnail_path"] = str(thumbnail_path)
            else:
                # 使用默认缩略图
                video_info["thumbnail_url"] = "/static/default_thumbnail.jpg"
                video_info["thumbnail_path"] = None
            
            # 获取视频元数据（简化实现）
            video_info["metadata"] = await self._extract_video_metadata(video_path)
            
            logger.info(f"视频处理完成: {video_info['file_id']}")
            return video_info
            
        except Exception as e:
            logger.error(f"视频处理失败: {str(e)}")
            raise FileUploadException(f"视频处理失败: {str(e)}")
    
    async def _extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """提取视频元数据
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频元数据字典
        """
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            
            if video_stream:
                return {
                    "duration": float(probe['format'].get('duration', 0)),
                    "width": int(video_stream.get('width', 0)),
                    "height": int(video_stream.get('height', 0)),
                    "codec": video_stream.get('codec_name', ''),
                    "bitrate": int(probe['format'].get('bit_rate', 0)),
                    "fps": eval(video_stream.get('avg_frame_rate', '0'))
                }
        except Exception as e:
            logger.warning(f"提取视频元数据失败: {str(e)}")
        
        # 默认元数据
        return {
            "duration": 0,
            "width": 0,
            "height": 0,
            "codec": "unknown",
            "bitrate": 0,
            "fps": 0
        }
    
    async def delete_file(self, file_path: str, user_id: Optional[str] = None) -> bool:
        """删除文件
        
        Args:
            file_path: 文件路径
            user_id: 用户ID（用于权限验证）
            
        Returns:
            是否成功删除
        """
        try:
            path = Path(file_path)
            if path.exists():
                # 检查权限（简化实现）
                if user_id:
                    # 这里应该检查文件所有权
                    pass
                
                path.unlink()
                logger.info(f"文件删除成功: {file_path}")
                return True
            else:
                logger.warning(f"文件不存在，无法删除: {file_path}")
                return False
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {str(e)}")
            return False
    
    async def cleanup_temp_files(self, older_than_hours: int = 24):
        """清理临时文件
        
        Args:
            older_than_hours: 清理多少小时前的文件
        """
        try:
            temp_dir = self.temp_dir
            current_time = datetime.now().timestamp()
            
            deleted_count = 0
            for temp_file in temp_dir.iterdir():
                if temp_file.is_file():
                    file_age = current_time - temp_file.stat().st_mtime
                    if file_age > older_than_hours * 3600:  # 转换为秒
                        temp_file.unlink()
                        deleted_count += 1
                        logger.info(f"清理临时文件: {temp_file}")
            
            logger.info(f"临时文件清理完成，共删除 {deleted_count} 个文件")
        except Exception as e:
            logger.error(f"清理临时文件失败: {str(e)}")
    
    def get_file_info(self, file_type: str, filename: str) -> Optional[Dict[str, Any]]:
        """获取文件信息
        
        Args:
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            文件信息字典，如果文件不存在则返回None
        """
        try:
            storage_dir = self._get_storage_directory(file_type)
            file_path = storage_dir / filename
            
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            file_info = {
                "filename": filename,
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": self._generate_file_url(file_type, filename)
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"获取文件信息失败 {filename}: {str(e)}")
            return None
    
    async def batch_process_files(self, files: List[UploadFile], file_type: str = "image", 
                                 user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """批量处理文件上传
        
        Args:
            files: 文件列表
            file_type: 文件类型
            user_id: 用户ID
            
        Returns:
            处理结果列表
        """
        results = []
        for file in files:
            try:
                if file_type == "video":
                    result = await self.process_video_upload(file, user_id)
                else:
                    result = await self.save_upload_file(file, file_type, user_id)
                results.append(result)
            except Exception as e:
                error_result = {
                    "filename": file.filename,
                    "error": str(e),
                    "success": False
                }
                results.append(error_result)
                logger.error(f"批量处理文件失败 {file.filename}: {str(e)}")
        
        return results
    
    async def move_file(self, source_path: str, destination_type: str, 
                       new_filename: Optional[str] = None) -> Optional[str]:
        """移动文件到指定目录
        
        Args:
            source_path: 源文件路径
            destination_type: 目标文件类型
            new_filename: 新文件名（可选）
            
        Returns:
            新文件路径，失败则返回None
        """
        try:
            source = Path(source_path)
            if not source.exists():
                logger.error(f"源文件不存在: {source_path}")
                return None
            
            destination_dir = self._get_storage_directory(destination_type)
            if new_filename:
                destination = destination_dir / new_filename
            else:
                destination = destination_dir / source.name
            
            shutil.move(str(source), str(destination))
            logger.info(f"文件移动成功: {source} -> {destination}")
            return str(destination)
            
        except Exception as e:
            logger.error(f"移动文件失败 {source_path}: {str(e)}")
            return None

# 全局文件服务实例
file_service = FileService()