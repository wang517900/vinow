内容板块-CDN分发服务
"""
CDN分发服务模块

本模块提供了基于S3兼容存储的CDN分发服务，包括：
1. 预签名URL生成（用于安全访问私有文件）
2. 分片上传支持（大文件上传）
3. 文件信息查询
4. 文件删除操作

当前实现基于Supabase Storage，但可以适配其他S3兼容的存储服务。
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from app.config import settings
from app.core.exceptions import BusinessException

logger = logging.getLogger(__name__)

__all__ = ['CDNService', 'cdn_service']


class CDNService:
    """CDN分发服务"""
    
    def __init__(self):
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self) -> None:
        """
        初始化S3客户端
        """
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.SUPABASE_STORAGE_URL,  # Supabase Storage URL
                aws_access_key_id=settings.SUPABASE_SERVICE_ROLE_KEY,
                aws_secret_access_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                region_name=settings.SUPABASE_REGION or 'us-east-1'
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}", exc_info=True)
            raise BusinessException("CDN服务初始化失败")
    
    def generate_presigned_url(
        self, 
        file_key: str, 
        operation: str = 'get_object',
        expires_in: int = 3600
    ) -> str:
        """
        生成预签名URL
        
        Args:
            file_key: 文件键
            operation: 操作类型 ('get_object' 或 'put_object')
            expires_in: 过期时间（秒）
            
        Returns:
            预签名URL字符串
            
        Raises:
            BusinessException: 生成URL失败时抛出
        """
        try:
            if operation == 'put_object':
                url = self.s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': settings.STORAGE_BUCKET,
                        'Key': file_key,
                    },
                    ExpiresIn=expires_in
                )
            else:  # get_object
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.STORAGE_BUCKET,
                        'Key': file_key,
                    },
                    ExpiresIn=expires_in
                )
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {file_key}: {str(e)}", exc_info=True)
            raise BusinessException("生成预签名URL失败")
    
    def initiate_multipart_upload(self, file_key: str) -> Dict[str, Any]:
        """
        初始化分片上传
        
        Args:
            file_key: 文件键
            
        Returns:
            包含上传ID和文件键的字典
            
        Raises:
            BusinessException: 初始化失败时抛出
        """
        try:
            response = self.s3_client.create_multipart_upload(
                Bucket=settings.STORAGE_BUCKET,
                Key=file_key
            )
            
            return {
                "upload_id": response['UploadId'],
                "file_key": file_key
            }
            
        except ClientError as e:
            logger.error(f"Failed to initiate multipart upload for {file_key}: {str(e)}", exc_info=True)
            raise BusinessException("初始化分片上传失败")
    
    def generate_presigned_upload_url(
        self, 
        file_key: str, 
        upload_id: str, 
        part_number: int
    ) -> str:
        """
        生成分片上传预签名URL
        
        Args:
            file_key: 文件键
            upload_id: 上传ID
            part_number: 分片编号
            
        Returns:
            预签名上传URL字符串
            
        Raises:
            BusinessException: 生成URL失败时抛出
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': settings.STORAGE_BUCKET,
                    'Key': file_key,
                    'UploadId': upload_id,
                    'PartNumber': part_number
                },
                ExpiresIn=3600
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate upload URL for part {part_number}: {str(e)}", exc_info=True)
            raise BusinessException("生成上传URL失败")
    
    def complete_multipart_upload(
        self, 
        file_key: str, 
        upload_id: str, 
        parts: List[Dict[str, Any]]
    ) -> bool:
        """
        完成分片上传
        
        Args:
            file_key: 文件键
            upload_id: 上传ID
            parts: 分片信息列表
            
        Returns:
            操作是否成功
            
        Raises:
            BusinessException: 完成上传失败时抛出
        """
        try:
            self.s3_client.complete_multipart_upload(
                Bucket=settings.STORAGE_BUCKET,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            logger.info(f"Multipart upload completed for {file_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to complete multipart upload for {file_key}: {str(e)}", exc_info=True)
            raise BusinessException("完成分片上传失败")
    
    def get_file_info(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_key: 文件键
            
        Returns:
            文件信息字典或None（文件不存在时）
            
        Raises:
            BusinessException: 获取文件信息失败时抛出
        """
        try:
            response = self.s3_client.head_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=file_key
            )
            
            return {
                "file_size": response['ContentLength'],
                "last_modified": response['LastModified'],
                "content_type": response['ContentType'],
                "etag": response['ETag']
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Failed to get file info for {file_key}: {str(e)}", exc_info=True)
            raise BusinessException("获取文件信息失败")
    
    def delete_file(self, file_key: str) -> bool:
        """
        删除文件
        
        Args:
            file_key: 文件键
            
        Returns:
            操作是否成功
            
        Raises:
            BusinessException: 删除文件失败时抛出
        """
        try:
            self.s3_client.delete_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=file_key
            )
            
            logger.info(f"File deleted from CDN: {file_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file {file_key}: {str(e)}", exc_info=True)
            raise BusinessException("删除文件失败")


# 全局CDN服务实例
cdn_service = CDNService()