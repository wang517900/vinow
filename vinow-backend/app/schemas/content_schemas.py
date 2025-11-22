内容系统
"""
内容管理模块的请求/响应Schema定义

本模块定义了内容管理系统中API接口的请求参数和响应数据格式，
包括内容的创建、更新、查询等相关Schema。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.models.content_models import ContentType, ContentStatus

__all__ = [
    'ContentCreateSchema',
    'ContentUpdateSchema',
    'ContentResponseSchema',
    'ContentListResponseSchema',
    'MediaUploadResponseSchema'
]


class ContentCreateSchema(BaseModel):
    """创建内容的请求Schema"""
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = Field(None, max_length=200, description="内容标题")
    description: Optional[str] = Field(None, max_length=1000, description="内容描述")
    content_type: ContentType = Field(..., description="内容类型")
    target_entity_type: Optional[str] = Field(None, description="目标实体类型")
    target_entity_id: Optional[str] = Field(None, description="目标实体ID")
    tags: List[str] = Field(default_factory=list, description="内容标签")
    categories: List[str] = Field(default_factory=list, description="内容分类")
    location_data: Optional[Dict[str, Any]] = Field(None, description="地理位置信息")
    visibility: str = Field(default="public", description="可见性设置")


class ContentUpdateSchema(BaseModel):
    """更新内容的请求Schema"""
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000) 
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    status: Optional[ContentStatus] = None
    visibility: Optional[str] = None


class ContentResponseSchema(BaseModel):
    """内容响应Schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="内容ID")
    title: Optional[str] = Field(None, description="内容标题")
    description: Optional[str] = Field(None, description="内容描述")
    content_type: ContentType = Field(..., description="内容类型")
    author_id: str = Field(..., description="作者ID")
    target_entity_type: Optional[str] = Field(None, description="目标实体类型")
    target_entity_id: Optional[str] = Field(None, description="目标实体ID")
    status: ContentStatus = Field(..., description="内容状态")
    visibility: str = Field(..., description="可见性设置")
    tags: List[str] = Field(default_factory=list, description="内容标签")
    categories: List[str] = Field(default_factory=list, description="内容分类")
    location_data: Optional[Dict[str, Any]] = Field(None, description="地理位置信息")
    like_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    share_count: int = Field(default=0, description="分享数") 
    view_count: int = Field(default=0, description="浏览数")
    media_urls: List[str] = Field(default_factory=list, description="媒体文件URL列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 作者信息
    author_name: Optional[str] = Field(None, description="作者名称")
    author_avatar: Optional[str] = Field(None, description="作者头像")


class ContentListResponseSchema(BaseModel):
    """内容列表响应Schema"""
    model_config = ConfigDict(from_attributes=True)
    
    contents: List[ContentResponseSchema] = Field(..., description="内容列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    has_next: bool = Field(..., description="是否有下一页")


class MediaUploadResponseSchema(BaseModel):
    """媒体上传响应Schema"""
    model_config = ConfigDict(from_attributes=True)
    
    file_url: str = Field(..., description="文件URL")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小")
    file_type: str = Field(..., description="文件类型")
    upload_id: str = Field(..., description="上传ID")