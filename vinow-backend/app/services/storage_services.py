内容系统
"""
存储服务模块

本模块提供了基于Supabase存储的文件上传、下载和删除功能，
用于处理用户上传的内容媒体文件。
"""

import uuid
import os
from typing import Optional, Dict, Any, Union
from fastapi import UploadFile, HTTPException
import aiofiles
from app.config import settings
from app.database.connection import supabase
import logging

logger = logging.getLogger(__name__)

__all__ = ['StorageService', 'storage_service']


class StorageService:
    """存储服务类 - 处理文件上传和存储"""
    
    def __init__(self):
        self.bucket_name = "content-media"
        self.max_file_size = settings.max_file_size
        
    async def upload_file(self, file: UploadFile, user_id: str) -> Dict[str, Any]:
        """
        上传文件到Supabase存储
        
        Args:
            file: 上传的文件对象
            user_id: 用户ID
            
        Returns:
            包含文件信息的字典
            {
                "file_url": str,
                "file_name": str,
                "file_size": int,
                "file_type": str,
                "upload_id": str
            }
            
        Raises:
            HTTPException: 上传过程中出现错误时抛出
        """
        try:
            # 验证文件类型
            await self._validate_file_type(file)
            
            # 验证文件大小
            await self._validate_file_size(file)
            
            # 生成唯一文件名
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ".bin"
            unique_filename = f"{user_id}/{uuid.uuid4()}{file_extension}"
            
            # 读取文件内容
            file_content = await file.read()
            
            # 上传到Supabase存储
            upload_response = supabase.storage.from_(self.bucket_name).upload(
                unique_filename, 
                file_content,
                {"content-type": file.content_type}
            )
            
            # 检查上传响应
            if isinstance(upload_response, dict) and upload_response.get('error'):
                raise HTTPException(
                    status_code=500, 
                    detail=f"文件上传失败: {upload_response['error'].get('message', '未知错误')}"
                )
            
            # 获取文件公开URL
            public_url_response = supabase.storage.from_(self.bucket_name).get_public_url(unique_filename)
            
            logger.info(f"文件上传成功: {unique_filename}, 用户: {user_id}")
            
            return {
                "file_url": public_url_response,
                "file_name": unique_filename,
                "file_size": len(file_content),
                "file_type": file.content_type,
                "upload_id": str(uuid.uuid4())
            }
            
        except HTTPException:
            # 重新抛出已知的HTTP异常
            raise
        except Exception as e:
            logger.error(f"文件上传异常: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    async def _validate_file_type(self, file: UploadFile) -> None:
        """
        验证文件类型
        
        Args:
            file: 上传的文件对象
            
        Raises:
            HTTPException: 文件类型不支持时抛出
        """
        if file.content_type is None:
            raise HTTPException(status_code=400, detail="无法识别文件类型")
            
        allowed_types = settings.allowed_image_types + settings.allowed_video_types
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file.content_type}。支持的类型: {', '.join(allowed_types)}"
            )
    
    async def _validate_file_size(self, file: UploadFile) -> None:
        """
        验证文件大小
        
        Args:
            file: 上传的文件对象
            
        Raises:
            HTTPException: 文件大小超出限制时抛出
        """
        # 由于FastAPI已经读取了文件内容到内存中，我们可以直接检查size属性
        # 注意：这依赖于FastAPI的内部实现，在某些情况下可能不可用
        file_size = getattr(file, "size", None)
        
        # 如果没有size属性，则回退到读取文件内容的方式来计算大小
        if file_size is None:
            # 保存当前位置
            current_pos = file.file.tell()
            # 移动到文件末尾获取大小
            file.file.seek(0, 2)
            file_size = file.file.tell()
            # 回到原来位置
            file.file.seek(current_pos)
        
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {file_size} > {self.max_file_size}"
            )
    
    async def delete_file(self, file_path: str) -> bool:
        """
        删除存储中的文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            删除是否成功
        """
        try:
            delete_response = supabase.storage.from_(self.bucket_name).remove([file_path])
            
            # 检查删除响应
            if isinstance(delete_response, dict) and delete_response.get('error'):
                logger.error(f"文件删除失败: {delete_response['error'].get('message', '未知错误')}")
                return False
                
            logger.info(f"文件删除成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件删除异常: {str(e)}", exc_info=True)
            return False


# 全局存储服务实例
storage_service = StorageService()

内容系统
import asyncio
import uuid
import os
from typing import Optional, Dict, Any, List, Tuple
from fastapi import UploadFile, HTTPException, BackgroundTasks
import aiofiles
from supabase import Client
from app.config import settings
from app.database.connection import supabase, DatabaseManager
from app.utils.file_utils import validate_file_type, validate_file_size, generate_file_hash
import logging
from datetime import datetime, timedelta
import magic
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageService:
    """增强的存储服务类 - 生产级别"""
    
    def __init__(self):
        self.bucket_name = settings.STORAGE_BUCKET
        self.backup_bucket = settings.BACKUP_BUCKET
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_types = settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_VIDEO_TYPES
        
    async def upload_file(
        self, 
        file: UploadFile, 
        user_id: str, 
        content_type: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        上传文件到Supabase存储 - 增强版本
        
        Args:
            file: 上传的文件对象
            user_id: 用户ID
            content_type: 内容类型
            background_tasks: 后台任务管理器
            
        Returns:
            文件上传结果
        """
        try:
            # 读取文件内容到内存
            file_content = await file.read()
            
            # 验证文件类型和大小
            await self._validate_file(file, file_content)
            
            # 生成文件元数据
            file_metadata = await self._generate_file_metadata(file, file_content, user_id, content_type)
            
            # 上传到主存储桶
            upload_result = await self._upload_to_supabase(
                file_metadata["file_path"], 
                file_content, 
                file.content_type
            )
            
            # 创建备份任务
            if background_tasks:
                background_tasks.add_task(
                    self._create_backup, 
                    file_metadata["file_path"], 
                    file_content
                )
            
            # 记录上传日志
            await self._log_upload_activity(file_metadata, user_id)
            
            logger.info(f"文件上传成功: {file_metadata['file_path']}, 用户: {user_id}")
            
            return {
                **file_metadata,
                "upload_id": upload_result.get("id", str(uuid.uuid4())),
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"文件上传异常: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    async def upload_chunked_file(
        self,
        chunk: UploadFile,
        upload_id: str,
        chunk_number: int,
        total_chunks: int,
        user_id: str,
        original_filename: str
    ) -> Dict[str, Any]:
        """
        分片上传文件 - 支持大文件上传
        
        Args:
            chunk: 文件分片
            upload_id: 上传会话ID
            chunk_number: 当前分片序号
            total_chunks: 总分片数
            user_id: 用户ID
            original_filename: 原始文件名
            
        Returns:
            分片上传结果
        """
        try:
            # 验证分片
            chunk_content = await chunk.read()
            await self._validate_chunk(chunk, chunk_content, chunk_number, total_chunks)
            
            # 存储分片到临时位置
            chunk_key = f"chunks/{upload_id}/{chunk_number}"
            await self._upload_to_supabase(chunk_key, chunk_content, chunk.content_type)
            
            # 检查是否所有分片都已上传
            all_chunks_uploaded = await self._check_all_chunks_uploaded(upload_id, total_chunks)
            
            result = {
                "upload_id": upload_id,
                "chunk_number": chunk_number,
                "total_chunks": total_chunks,
                "chunk_size": len(chunk_content),
                "all_chunks_uploaded": all_chunks_uploaded
            }
            
            # 如果所有分片都已上传，触发合并
            if all_chunks_uploaded:
                result["final_file"] = await self._merge_chunks(
                    upload_id, total_chunks, user_id, original_filename
                )
            
            return result
            
        except Exception as e:
            logger.error(f"分片上传异常: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"分片上传失败: {str(e)}")
    
    async def delete_file(self, file_path: str, user_id: str) -> bool:
        """
        删除存储中的文件 - 增强版本
        
        Args:
            file_path: 文件路径
            user_id: 用户ID
            
        Returns:
            删除是否成功
        """
        try:
            # 验证用户权限
            if not await self._verify_file_ownership(file_path, user_id):
                raise HTTPException(status_code=403, detail="无权限删除此文件")
            
            # 从主存储桶删除
            delete_response = supabase.storage.from_(self.bucket_name).remove([file_path])
            
            if delete_response.get('error'):
                logger.error(f"文件删除失败: {delete_response['error']['message']}")
                return False
            
            # 从备份存储桶删除（如果有）
            try:
                supabase.storage.from_(self.backup_bucket).remove([file_path])
            except Exception as e:
                logger.warning(f"备份文件删除失败: {str(e)}")
            
            # 记录删除活动
            await self._log_delete_activity(file_path, user_id)
            
            logger.info(f"文件删除成功: {file_path}, 用户: {user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"文件删除异常: {str(e)}")
            return False
    
    async def generate_presigned_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        生成预签名URL - 用于安全访问私有文件
        
        Args:
            file_path: 文件路径
            expires_in: URL过期时间（秒）
            
        Returns:
            预签名URL或None
        """
        try:
            # 使用Supabase的签名URL功能
            response = supabase.storage.from_(self.bucket_name).create_signed_url(
                file_path, 
                expires_in
            )
            
            if response.get('signedURL'):
                return response['signedURL']
            else:
                logger.error(f"生成预签名URL失败: {response.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"生成预签名URL异常: {str(e)}")
            return None
    
    async def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件元数据或None
        """
        try:
            # 获取文件信息
            response = supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            
            if response:
                # 这里可以添加更多元数据获取逻辑
                return {
                    "file_path": file_path,
                    "url": response,
                    "bucket": self.bucket_name
                }
            return None
            
        except Exception as e:
            logger.error(f"获取文件元数据异常: {str(e)}")
            return None
    
    async def cleanup_orphaned_files(self, older_than_days: int = 7) -> int:
        """
        清理孤儿文件（没有关联内容的文件）
        
        Args:
            older_than_days: 清理多少天前的文件
            
        Returns:
            清理的文件数量
        """
        try:
            # 获取所有文件列表
            files_response = supabase.storage.from_(self.bucket_name).list()
            
            if files_response.get('error'):
                logger.error(f"获取文件列表失败: {files_response['error']['message']}")
                return 0
            
            orphaned_files = []
            cutoff_time = datetime.utcnow() - timedelta(days=older_than_days)
            
            # 这里需要实现逻辑来识别孤儿文件
            # 简化版本：假设所有文件都应该有数据库记录
            # 实际实现应该检查数据库中的文件引用
            
            # 删除孤儿文件
            if orphaned_files:
                delete_response = supabase.storage.from_(self.bucket_name).remove(orphaned_files)
                
                if delete_response.get('error'):
                    logger.error(f"清理孤儿文件失败: {delete_response['error']['message']}")
                    return 0
                
                logger.info(f"成功清理 {len(orphaned_files)} 个孤儿文件")
                return len(orphaned_files)
            
            return 0
            
        except Exception as e:
            logger.error(f"清理孤儿文件异常: {str(e)}")
            return 0
    
    # 私有方法
    async def _validate_file(self, file: UploadFile, file_content: bytes):
        """验证文件"""
        # 验证文件类型
        file_type = magic.from_buffer(file_content, mime=True)
        if file_type not in self.allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_type}"
            )
        
        # 验证文件大小
        file_size = len(file_content)
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {file_size} > {self.max_file_size}"
            )
    
    async def _generate_file_metadata(
        self, 
        file: UploadFile, 
        file_content: bytes, 
        user_id: str, 
        content_type: str
    ) -> Dict[str, Any]:
        """生成文件元数据"""
        file_extension = Path(file.filename).suffix if file.filename else ".bin"
        file_hash = generate_file_hash(file_content)
        
        # 生成唯一文件路径
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        unique_filename = f"{file_hash}{file_extension}"
        file_path = f"{content_type}/{timestamp}/{user_id}/{unique_filename}"
        
        return {
            "file_path": file_path,
            "file_name": file.filename or "unknown",
            "file_size": len(file_content),
            "file_type": file.content_type,
            "file_hash": file_hash,
            "mime_type": file.content_type,
            "uploaded_by": user_id,
            "content_type": content_type
        }
    
    async def _upload_to_supabase(self, file_path: str, file_content: bytes, content_type: str) -> Dict[str, Any]:
        """上传文件到Supabase"""
        upload_response = supabase.storage.from_(self.bucket_name).upload(
            file_path, 
            file_content,
            {"contentType": content_type}
        )
        
        if upload_response.get('error'):
            raise HTTPException(
                status_code=500, 
                detail=f"文件上传失败: {upload_response['error']['message']}"
            )
        
        return upload_response
    
    async def _create_backup(self, file_path: str, file_content: bytes):
        """创建文件备份"""
        try:
            supabase.storage.from_(self.backup_bucket).upload(
                file_path,
                file_content,
                {"contentType": "application/octet-stream"}
            )
        except Exception as e:
            logger.warning(f"文件备份失败: {str(e)}")
    
    async def _validate_chunk(self, chunk: UploadFile, chunk_content: bytes, chunk_number: int, total_chunks: int):
        """验证文件分片"""
        if chunk_number < 1 or chunk_number > total_chunks:
            raise HTTPException(status_code=400, detail="无效的分片序号")
        
        if len(chunk_content) > 10 * 1024 * 1024:  # 每个分片最大10MB
            raise HTTPException(status_code=400, detail="分片大小超过限制")
    
    async def _check_all_chunks_uploaded(self, upload_id: str, total_chunks: int) -> bool:
        """检查是否所有分片都已上传"""
        try:
            # 列出所有分片
            chunks_response = supabase.storage.from_(self.bucket_name).list(f"chunks/{upload_id}")
            
            if chunks_response.get('error'):
                return False
            
            uploaded_chunks = len(chunks_response)
            return uploaded_chunks == total_chunks
            
        except Exception as e:
            logger.error(f"检查分片上传状态异常: {str(e)}")
            return False
    
    async def _merge_chunks(self, upload_id: str, total_chunks: int, user_id: str, original_filename: str) -> Dict[str, Any]:
        """合并文件分片"""
        try:
            # 读取所有分片
            chunks = []
            for chunk_number in range(1, total_chunks + 1):
                chunk_path = f"chunks/{upload_id}/{chunk_number}"
                chunk_response = supabase.storage.from_(self.bucket_name).download(chunk_path)
                
                if chunk_response:
                    chunks.append(chunk_response)
            
            # 合并分片
            merged_content = b''.join(chunks)
            
            # 生成最终文件元数据
            file_metadata = await self._generate_file_metadata(
                UploadFile(filename=original_filename), 
                merged_content, 
                user_id, 
                "chunked_upload"
            )
            
            # 上传合并后的文件
            upload_result = await self._upload_to_supabase(
                file_metadata["file_path"], 
                merged_content, 
                "application/octet-stream"
            )
            
            # 清理临时分片
            chunk_paths = [f"chunks/{upload_id}/{i}" for i in range(1, total_chunks + 1)]
            supabase.storage.from_(self.bucket_name).remove(chunk_paths)
            
            return {
                **file_metadata,
                "upload_id": upload_id,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"合并文件分片异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件合并失败: {str(e)}")
    
    async def _verify_file_ownership(self, file_path: str, user_id: str) -> bool:
        """验证文件所有权"""
        # 简化实现：检查文件路径是否包含用户ID
        # 实际实现应该查询数据库验证文件所有权
        return user_id in file_path
    
    async def _log_upload_activity(self, file_metadata: Dict[str, Any], user_id: str):
        """记录上传活动"""
        # 这里可以实现上传日志记录到数据库
        logger.info(f"文件上传活动: {file_metadata['file_path']} by {user_id}")
    
    async def _log_delete_activity(self, file_path: str, user_id: str):
        """记录删除活动"""
        # 这里可以实现删除日志记录到数据库
        logger.info(f"文件删除活动: {file_path} by {user_id}")

# 全局存储服务实例
storage_service = StorageService()

内容板块-储存服务

import logging
import magic
from typing import Optional, Dict, Any, List
from fastapi import UploadFile, HTTPException
import aiofiles
import os
from datetime import datetime

from app.config import settings
from app.utils.exceptions import FileUploadException
from app.services.cdn_service import cdn_service

logger = logging.getLogger(__name__)


class StorageService:
    """存储服务"""
    
    @staticmethod
    async def validate_file(file: UploadFile, max_size: int = None, allowed_types: List[str] = None) -> bool:
        """验证文件"""
        if max_size is None:
            max_size = settings.MAX_FILE_SIZE
        if allowed_types is None:
            allowed_types = settings.ALLOWED_VIDEO_FORMATS + settings.ALLOWED_IMAGE_FORMATS
        
        # 检查文件大小
        if hasattr(file, 'size') and file.size > max_size:
            raise FileUploadException(f"文件大小超过限制: {max_size} bytes")
        
        # 检查文件类型
        content = await file.read(1024)  # 读取前1024字节进行类型检测
        await file.seek(0)  # 重置文件指针
        
        file_type = magic.from_buffer(content, mime=True)
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        if file_type.split('/')[0] not in ['video', 'image']:
            raise FileUploadException("不支持的文件类型")
        
        if file_extension and file_extension not in allowed_types:
            raise FileUploadException(f"不支持的文件格式: {file_extension}")
        
        return True
    
    @staticmethod
    async def upload_file(file: UploadFile, file_key: str) -> Dict[str, Any]:
        """上传文件到存储"""
        try:
            # 验证文件
            await StorageService.validate_file(file)
            
            # 使用CDN服务上传
            upload_url = await cdn_service.generate_presigned_url(file_key, 'put_object')
            
            # 这里应该实现实际的文件上传逻辑
            # 示例中使用本地存储作为演示
            local_path = f"uploads/{file_key}"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            async with aiofiles.open(local_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            file_info = await cdn_service.get_file_info(file_key)
            
            return {
                "file_key": file_key,
                "file_size": file_info["file_size"] if file_info else len(content),
                "content_type": file.content_type,
                "upload_time": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            raise FileUploadException(f"文件上传失败: {str(e)}")
    
    @staticmethod
    async def delete_file(file_key: str) -> bool:
        """删除文件"""
        try:
            return await cdn_service.delete_file(file_key)
        except Exception as e:
            logger.error(f"File deletion error: {str(e)}")
            return False
    
    @staticmethod
    async def get_file_url(file_key: str, expires_in: int = 3600) -> str:
        """获取文件访问URL"""
        try:
            return await cdn_service.generate_presigned_url(file_key, 'get_object', expires_in)
        except Exception as e:
            logger.error(f"Get file URL error: {str(e)}")
            raise FileUploadException("获取文件URL失败")