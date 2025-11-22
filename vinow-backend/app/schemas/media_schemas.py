内容板块
"""
媒体文件模式定义模块

本模块定义了媒体文件管理相关的数据传输对象（DTO），包括：
1. 媒体上传响应模型（MediaUploadResponseSchema）
2. 分片上传响应模型（ChunkedUploadResponseSchema）
3. 预签名URL响应模型（PresignedUrlResponseSchema）
4. 媒体文件信息模型（MediaFileInfoSchema）
5. 媒体上传请求模型（MediaUploadRequestSchema）
6. 分片上传请求模型（ChunkedUploadRequestSchema）
7. 文件元数据模型（FileMetadataSchema）
8. 上传初始化响应模型（UploadInitiationResponseSchema）

所有模型都使用Pydantic V2语法，并支持从ORM对象创建。
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

__all__ = [
    'MediaUploadResponseSchema',
    'ChunkedUploadResponseSchema',
    'PresignedUrlResponseSchema',
    'MediaFileInfoSchema',
    'MediaUploadRequestSchema',
    'ChunkedUploadRequestSchema',
    'FileMetadataSchema',
    'UploadInitiationResponseSchema'
]


class MediaUploadResponseSchema(BaseModel):
    """
    媒体上传响应模型 - 用于文件上传成功后的响应
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    file_url: str = Field(..., description="文件访问URL")  # 文件URL
    file_name: str = Field(..., description="文件名")  # 文件名
    file_size: int = Field(..., description="文件大小（字节）")  # 文件大小
    file_type: str = Field(..., description="文件类型")  # 文件类型
    upload_id: str = Field(..., description="上传ID")  # 上传ID
    uploaded_at: str = Field(..., description="上传时间")  # 上传时间


class ChunkedUploadResponseSchema(BaseModel):
    """
    分片上传响应模型 - 用于分片上传的响应
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    upload_id: str = Field(..., description="上传会话ID")  # 上传ID
    chunk_number: int = Field(..., description="当前分片序号")  # 分片序号
    total_chunks: int = Field(..., description="总分片数")  # 总分片数
    chunk_size: int = Field(..., description="分片大小")  # 分片大小
    all_chunks_uploaded: bool = Field(..., description="是否所有分片已上传")  # 是否完成
    final_file: Optional[Dict[str, Any]] = Field(None, description="最终文件信息")  # 最终文件


class PresignedUrlResponseSchema(BaseModel):
    """
    预签名URL响应模型 - 用于生成预签名URL的响应
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    presigned_url: str = Field(..., description="预签名URL")  # 预签名URL
    expires_in: int = Field(..., description="过期时间（秒）")  # 过期时间


class MediaFileInfoSchema(BaseModel):
    """
    媒体文件信息模型 - 用于存储媒体文件的详细信息
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    id: str = Field(..., description="文件ID")  # 文件ID
    content_id: str = Field(..., description="关联内容ID")  # 内容ID
    file_url: str = Field(..., description="文件URL")  # 文件URL
    file_type: str = Field(..., description="文件类型")  # 文件类型
    file_name: str = Field(..., description="文件名")  # 文件名
    file_size: int = Field(..., description="文件大小（字节）")  # 文件大小
    mime_type: str = Field(..., description="MIME类型")  # MIME类型
    duration: Optional[int] = Field(None, description="时长（秒）")  # 时长
    width: Optional[int] = Field(None, description="宽度")  # 宽度
    height: Optional[int] = Field(None, description="高度")  # 高度
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")  # 缩略图
    processing_status: str = Field(..., description="处理状态")  # 处理状态
    display_order: int = Field(0, description="显示顺序")  # 显示顺序
    caption: Optional[str] = Field(None, description="标题")  # 标题
    alt_text: Optional[str] = Field(None, description="替代文本")  # 替代文本
    created_at: datetime = Field(..., description="创建时间")  # 创建时间
    updated_at: datetime = Field(..., description="更新时间")  # 更新时间


class MediaUploadRequestSchema(BaseModel):
    """
    媒体上传请求模型 - 用于文件上传的请求参数
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    content_type: str = Field(..., description="内容类型")  # 内容类型
    description: Optional[str] = Field(None, description="文件描述")  # 文件描述
    tags: List[str] = Field(default_factory=list, description="文件标签")  # 文件标签


class ChunkedUploadRequestSchema(BaseModel):
    """
    分片上传请求模型 - 用于分片上传的请求参数
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    upload_id: str = Field(..., description="上传会话ID")  # 上传ID
    chunk_number: int = Field(..., ge=1, description="当前分片序号")  # 分片序号
    total_chunks: int = Field(..., ge=1, description="总分片数")  # 总分片数
    original_filename: str = Field(..., description="原始文件名")  # 原始文件名


class FileMetadataSchema(BaseModel):
    """
    文件元数据模型 - 用于存储文件的元数据信息
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    file_path: str = Field(..., description="文件路径")  # 文件路径
    file_name: str = Field(..., description="文件名")  # 文件名
    file_size: int = Field(..., description="文件大小")  # 文件大小
    file_type: str = Field(..., description="文件类型")  # 文件类型
    file_hash: str = Field(..., description="文件哈希")  # 文件哈希
    mime_type: str = Field(..., description="MIME类型")  # MIME类型
    uploaded_by: str = Field(..., description="上传用户")  # 上传用户
    content_type: str = Field(..., description="内容类型")  # 内容类型
    uploaded_at: datetime = Field(..., description="上传时间")  # 上传时间


class UploadInitiationResponseSchema(BaseModel):
    """
    上传初始化响应模型 - 用于分片上传初始化的响应
    """
    model_config = ConfigDict(from_attributes=True)  # 允许从ORM对象创建
    
    upload_id: str = Field(..., description="上传会话ID")  # 上传ID
    chunk_size: int = Field(..., description="分片大小")  # 分片大小
    total_chunks: int = Field(..., description="总分片数")  # 总分片数
    file_name: str = Field(..., description="文件名")  # 文件名
    file_size: int = Field(..., description="文件大小")  # 文件大小