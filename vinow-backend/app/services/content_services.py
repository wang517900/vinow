from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from fastapi import HTTPException
from app.database.connection import supabase
from app.models.content_models import (
    ContentType, ContentStatus, ContentCreate, 
    ContentUpdate, ContentResponse, MediaFile
)
from app.schemas.content_schemas import ContentCreateSchema, ContentUpdateSchema
import logging

logger = logging.getLogger(__name__)

class ContentService:
    """内容服务类 - 处理内容相关的业务逻辑"""
    
    def __init__(self):
        self.table_name = "contents"
        self.media_table = "content_media"
    
    async def create_content(self, content_data: ContentCreateSchema, author_id: str, media_files: List[str] = None) -> ContentResponse:
        """
        创建新内容
        
        Args:
            content_data: 内容数据
            author_id: 作者ID
            media_files: 媒体文件URL列表
            
        Returns:
            创建的内容对象
        """
        try:
            # 生成内容ID
            content_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            # 构建内容数据
            content_record = {
                "id": content_id,
                "title": content_data.title,
                "description": content_data.description,
                "content_type": content_data.content_type.value,
                "author_id": author_id,
                "target_entity_type": content_data.target_entity_type,
                "target_entity_id": content_data.target_entity_id,
                "status": ContentStatus.PENDING.value,
                "visibility": content_data.visibility,
                "tags": content_data.tags,
                "categories": content_data.categories,
                "location_data": content_data.location_data,
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "view_count": 0,
                "media_urls": media_files or [],
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # 插入到数据库
            insert_response = supabase.table(self.table_name).insert(content_record).execute()
            
            if insert_response.data:
                logger.info(f"内容创建成功: {content_id}, 作者: {author_id}")
                return await self._format_content_response(insert_response.data[0])
            else:
                raise HTTPException(status_code=500, detail="内容创建失败")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"内容创建异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内容创建失败: {str(e)}")
    
    async def get_content(self, content_id: str) -> Optional[ContentResponse]:
        """
        根据ID获取内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            内容对象或None
        """
        try:
            response = supabase.table(self.table_name).select("*").eq("id", content_id).execute()
            
            if response.data:
                # 增加浏览计数
                await self._increment_view_count(content_id)
                return await self._format_content_response(response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取内容异常: {str(e)}")
            return None
    
    async def update_content(self, content_id: str, update_data: ContentUpdateSchema, user_id: str) -> Optional[ContentResponse]:
        """
        更新内容
        
        Args:
            content_id: 内容ID
            update_data: 更新数据
            user_id: 用户ID（用于权限验证）
            
        Returns:
            更新后的内容对象
        """
        try:
            # 验证内容存在且用户有权限
            existing_content = await self.get_content(content_id)
            if not existing_content:
                raise HTTPException(status_code=404, detail="内容不存在")
                
            if existing_content.author_id != user_id:
                raise HTTPException(status_code=403, detail="无权限修改此内容")
            
            # 构建更新数据
            update_fields = {}
            if update_data.title is not None:
                update_fields["title"] = update_data.title
            if update_data.description is not None:
                update_fields["description"] = update_data.description
            if update_data.tags is not None:
                update_fields["tags"] = update_data.tags
            if update_data.categories is not None:
                update_fields["categories"] = update_data.categories
            if update_data.status is not None:
                update_fields["status"] = update_data.status.value
            if update_data.visibility is not None:
                update_fields["visibility"] = update_data.visibility
                
            update_fields["updated_at"] = datetime.utcnow().isoformat()
            
            # 执行更新
            update_response = supabase.table(self.table_name).update(update_fields).eq("id", content_id).execute()
            
            if update_response.data:
                logger.info(f"内容更新成功: {content_id}")
                return await self._format_content_response(update_response.data[0])
            else:
                raise HTTPException(status_code=500, detail="内容更新失败")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"内容更新异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内容更新失败: {str(e)}")
    
    async def delete_content(self, content_id: str, user_id: str) -> bool:
        """
        删除内容（软删除）
        
        Args:
            content_id: 内容ID
            user_id: 用户ID
            
        Returns:
            删除是否成功
        """
        try:
            # 验证内容存在且用户有权限
            existing_content = await self.get_content(content_id)
            if not existing_content:
                raise HTTPException(status_code=404, detail="内容不存在")
                
            if existing_content.author_id != user_id:
                raise HTTPException(status_code=403, detail="无权限删除此内容")
            
            # 软删除：更新状态为DELETED
            update_response = supabase.table(self.table_name).update({
                "status": ContentStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", content_id).execute()
            
            success = bool(update_response.data)
            if success:
                logger.info(f"内容删除成功: {content_id}")
            else:
                logger.error(f"内容删除失败: {content_id}")
                
            return success
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"内容删除异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内容删除失败: {str(e)}")
    
    async def list_contents(
        self, 
        content_type: Optional[ContentType] = None,
        author_id: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        status: Optional[ContentStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取内容列表
        
        Args:
            content_type: 内容类型过滤
            author_id: 作者ID过滤
            target_entity_type: 目标实体类型过滤
            target_entity_id: 目标实体ID过滤
            status: 状态过滤
            page: 页码
            page_size: 每页数量
            
        Returns:
            内容列表和分页信息
        """
        try:
            # 构建查询
            query = supabase.table(self.table_name).select("*", count="exact")
            
            # 添加过滤条件
            if content_type:
                query = query.eq("content_type", content_type.value)
            if author_id:
                query = query.eq("author_id", author_id)
            if target_entity_type:
                query = query.eq("target_entity_type", target_entity_type)
            if target_entity_id:
                query = query.eq("target_entity_id", target_entity_id)
            if status:
                query = query.eq("status", status.value)
            else:
                # 默认只返回已发布的内容
                query = query.eq("status", ContentStatus.PUBLISHED.value)
            
            # 添加排序和分页
            query = query.order("created_at", desc=True)
            start_index = (page - 1) * page_size
            query = query.range(start_index, start_index + page_size - 1)
            
            # 执行查询
            response = query.execute()
            
            # 格式化响应
            contents = [await self._format_content_response(item) for item in response.data]
            
            return {
                "contents": contents,
                "total_count": response.count or 0,
                "page": page,
                "page_size": page_size,
                "has_next": (response.count or 0) > (start_index + page_size)
            }
            
        except Exception as e:
            logger.error(f"获取内容列表异常: {str(e)}")
            return {
                "contents": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "has_next": False
            }
    
    async def _increment_view_count(self, content_id: str):
        """增加内容浏览计数"""
        try:
            supabase.rpc("increment_view_count", {"content_id": content_id}).execute()
        except Exception as e:
            logger.warning(f"增加浏览计数失败: {str(e)}")
    
    async def _format_content_response(self, db_data: Dict[str, Any]) -> ContentResponse:
        """格式化数据库数据为ContentResponse对象"""
        return ContentResponse(
            id=db_data["id"],
            title=db_data["title"],
            description=db_data["description"],
            content_type=ContentType(db_data["content_type"]),
            author_id=db_data["author_id"],
            target_entity_type=db_data["target_entity_type"],
            target_entity_id=db_data["target_entity_id"],
            status=ContentStatus(db_data["status"]),
            visibility=db_data["visibility"],
            tags=db_data.get("tags", []),
            categories=db_data.get("categories", []),
            location_data=db_data.get("location_data"),
            like_count=db_data.get("like_count", 0),
            comment_count=db_data.get("comment_count", 0),
            share_count=db_data.get("share_count", 0),
            view_count=db_data.get("view_count", 0),
            media_urls=db_data.get("media_urls", []),
            created_at=datetime.fromisoformat(db_data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(db_data["updated_at"].replace('Z', '+00:00'))
        )

# 全局内容服务实例
content_service = ContentService()

内容系统
import asyncio
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.database.connection import DatabaseManager, supabase
from app.models.content_models import (
    Content, ContentMedia, ContentInteraction, ContentType, 
    ContentStatus, MediaType, InteractionType,
    ContentCreate, ContentUpdate, ContentResponse,
    ContentMediaCreate, ContentInteractionCreate
)
from app.models.review_models import Review, ReviewCreate, ReviewResponse
from app.schemas.content_schemas import ContentCreateSchema, ContentUpdateSchema, ContentListResponseSchema
from app.schemas.review_schemas import ReviewCreateSchema, ReviewResponseSchema
from app.services.storage_service import storage_service
from app.services.moderation_service import moderation_service
from app.utils.cache import cache_manager
from app.utils.pagination import PaginationParams, paginate
from app.utils.security import get_current_user
from app.utils.validation import validate_content_creation, sanitize_content_text
import logging
from sqlalchemy import and_, or_, desc, asc, func, text

logger = logging.getLogger(__name__)

class ContentService:
    """增强的内容服务类 - 生产级别"""
    
    def __init__(self):
        self.supabase = supabase
        self.cache = cache_manager
    
    async def create_content(
        self, 
        content_data: ContentCreateSchema, 
        user_id: str,
        user_name: Optional[str] = None,
        user_avatar: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
        db: Session = None
    ) -> ContentResponse:
        """
        创建新内容 - 增强版本
        
        Args:
            content_data: 内容数据
            user_id: 用户ID
            user_name: 用户名称
            user_avatar: 用户头像
            background_tasks: 后台任务
            db: 数据库会话
            
        Returns:
            创建的内容对象
        """
        try:
            # 验证内容数据
            await validate_content_creation(content_data)
            
            # 清理文本内容
            sanitized_title = sanitize_content_text(content_data.title) if content_data.title else None
            sanitized_description = sanitize_content_text(content_data.description) if content_data.description else None
            
            # 生成内容ID
            content_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # 构建内容记录
            content_record = {
                "id": content_id,
                "content_type": content_data.content_type.value,
                "title": sanitized_title,
                "description": sanitized_description,
                "author_id": user_id,
                "author_name": user_name if not content_data.is_anonymous else None,
                "author_avatar": user_avatar if not content_data.is_anonymous else None,
                "target_entity_type": content_data.target_entity_type,
                "target_entity_id": content_data.target_entity_id,
                "target_entity_name": content_data.target_entity_name,
                "status": ContentStatus.PENDING_REVIEW.value,
                "visibility": content_data.visibility,
                "is_anonymous": content_data.is_anonymous,
                "tags": content_data.tags,
                "categories": content_data.categories,
                "location_data": content_data.location_data,
                "language": content_data.language,
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "view_count": 0,
                "bookmark_count": 0,
                "report_count": 0,
                "quality_score": 0.0,
                "engagement_rate": 0.0,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # 插入到数据库
            insert_response = self.supabase.table("contents").insert(content_record).execute()
            
            if not insert_response.data:
                logger.error(f"内容创建失败: {insert_response}")
                raise HTTPException(status_code=500, detail="内容创建失败")
            
            created_content = insert_response.data[0]
            
            # 处理媒体文件
            media_files = []
            if content_data.media_files:
                for media_data in content_data.media_files:
                    media_file = await self._create_content_media(
                        content_id, media_data, user_id
                    )
                    media_files.append(media_file)
            
            # 更新内容的媒体文件URL
            media_urls = [media["file_url"] for media in media_files]
            self.supabase.table("contents").update({
                "media_urls": media_urls,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", content_id).execute()
            
            # 触发自动审核
            if background_tasks and settings.AUTO_MODERATION_ENABLED:
                background_tasks.add_task(
                    moderation_service.auto_moderate_content,
                    content_id,
                    created_content["content_type"],
                    sanitized_title,
                    sanitized_description,
                    media_urls
                )
            
            # 清除相关缓存
            await self.cache.delete_pattern(f"user:{user_id}:contents:*")
            await self.cache.delete_pattern(f"feed:*")
            
            logger.info(f"内容创建成功: {content_id}, 类型: {content_data.content_type}, 用户: {user_id}")
            
            return await self._format_content_response(created_content, user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"内容创建异常: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"内容创建失败: {str(e)}")
    
    async def get_content(self, content_id: str, user_id: Optional[str] = None) -> Optional[ContentResponse]:
        """
        获取内容详情 - 增强版本
        
        Args:
            content_id: 内容ID
            user_id: 当前用户ID（用于获取用户互动状态）
            
        Returns:
            内容对象或None
        """
        try:
            # 尝试从缓存获取
            cache_key = f"content:{content_id}"
            cached_content = await self.cache.get(cache_key)
            if cached_content:
                logger.debug(f"从缓存获取内容: {content_id}")
                return ContentResponse(**cached_content)
            
            # 从数据库获取
            response = self.supabase.table("contents").select("*").eq("id", content_id).execute()
            
            if not response.data:
                return None
            
            content_data = response.data[0]
            
            # 检查内容状态
            if content_data["status"] not in [ContentStatus.PUBLISHED.value, ContentStatus.APPROVED.value]:
                # 只有作者或管理员可以查看未发布的内容
                if user_id != content_data["author_id"]:
                    raise HTTPException(status_code=404, detail="内容不存在")
            
            # 增加浏览计数
            await self._increment_view_count(content_id, user_id)
            
            # 获取媒体文件
            media_files = await self._get_content_media(content_id)
            
            # 格式化响应
            content_response = await self._format_content_response(content_data, user_id, media_files)
            
            # 缓存内容（5分钟）
            await self.cache.set(cache_key, content_response.dict(), expire=300)
            
            return content_response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取内容异常: {str(e)}", exc_info=True)
            return None
    
    async def update_content(
        self, 
        content_id: str, 
        update_data: ContentUpdateSchema, 
        user_id: str
    ) -> Optional[ContentResponse]:
        """
        更新内容 - 增强版本
        
        Args:
            content_id: 内容ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            更新后的内容对象
        """
        try:
            # 验证内容存在且用户有权限
            existing_content = await self.get_content(content_id, user_id)
            if not existing_content:
                raise HTTPException(status_code=404, detail="内容不存在")
                
            if existing_content.author_id != user_id:
                raise HTTPException(status_code=403, detail="无权限修改此内容")
            
            # 构建更新数据
            update_fields = {}
            if update_data.title is not None:
                update_fields["title"] = sanitize_content_text(update_data.title)
            if update_data.description is not None:
                update_fields["description"] = sanitize_content_text(update_data.description)
            if update_data.tags is not None:
                update_fields["tags"] = update_data.tags
            if update_data.categories is not None:
                update_fields["categories"] = update_data.categories
            if update_data.status is not None:
                update_fields["status"] = update_data.status.value
            if update_data.visibility is not None:
                update_fields["visibility"] = update_data.visibility
            if update_data.is_anonymous is not None:
                update_fields["is_anonymous"] = update_data.is_anonymous
            
            update_fields["updated_at"] = datetime.utcnow().isoformat()
            
            # 如果内容被修改，重置审核状态
            if any(field in update_fields for field in ["title", "description", "tags"]):
                update_fields["status"] = ContentStatus.PENDING_REVIEW.value
                update_fields["moderated_at"] = None
                update_fields["moderator_id"] = None
                update_fields["moderation_notes"] = None
            
            # 执行更新
            update_response = self.supabase.table("contents").update(update_fields).eq("id", content_id).execute()
            
            if not update_response.data:
                raise HTTPException(status_code=500, detail="内容更新失败")
            
            # 清除缓存
            await self.cache.delete(f"content:{content_id}")
            await self.cache.delete_pattern(f"user:{user_id}:contents:*")
            
            logger.info(f"内容更新成功: {content_id}, 用户: {user_id}")
            
            return await self.get_content(content_id, user_id)
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"内容更新异常: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"内容更新失败: {str(e)}")
    
    async def delete_content(self, content_id: str, user_id: str) -> bool:
        """
        删除内容 - 增强版本
        
        Args:
            content_id: 内容ID
            user_id: 用户ID
            
        Returns:
            删除是否成功
        """
        try:
            # 验证内容存在且用户有权限
            existing_content = await self.get_content(content_id, user_id)
            if not existing_content:
                raise HTTPException(status_code=404, detail="内容不存在")
                
            if existing_content.author_id != user_id:
                raise HTTPException(status_code=403, detail="无权限删除此内容")
            
            # 软删除：更新状态为DELETED
            update_response = self.supabase.table("contents").update({
                "status": ContentStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", content_id).execute()
            
            success = bool(update_response.data)
            
            if success:
                # 清除缓存
                await self.cache.delete(f"content:{content_id}")
                await self.cache.delete_pattern(f"user:{user_id}:contents:*")
                await self.cache.delete_pattern(f"feed:*")
                
                # 记录删除活动
                await self._log_content_activity(content_id, "delete", user_id)
                
                logger.info(f"内容删除成功: {content_id}, 用户: {user_id}")
            else:
                logger.error(f"内容删除失败: {content_id}")
                
            return success
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"内容删除异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内容删除失败: {str(e)}")
    
    async def list_contents(
        self,
        pagination: PaginationParams,
        content_type: Optional[ContentType] = None,
        author_id: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        status: Optional[ContentStatus] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> ContentListResponseSchema:
        """
        获取内容列表 - 增强版本
        
        Args:
            pagination: 分页参数
            content_type: 内容类型过滤
            author_id: 作者ID过滤
            target_entity_type: 目标实体类型过滤
            target_entity_id: 目标实体ID过滤
            status: 状态过滤
            tags: 标签过滤
            categories: 分类过滤
            user_id: 当前用户ID
            sort_by: 排序字段
            sort_order: 排序方向
            
        Returns:
            内容列表和分页信息
        """
        try:
            # 构建缓存键
            cache_key_parts = [
                "contents",
                f"type:{content_type.value}" if content_type else "type:all",
                f"author:{author_id}" if author_id else "author:all",
                f"target_type:{target_entity_type}" if target_entity_type else "target_type:all",
                f"target_id:{target_entity_id}" if target_entity_id else "target_id:all",
                f"status:{status.value}" if status else "status:published",
                f"tags:{','.join(sorted(tags))}" if tags else "tags:all",
                f"categories:{','.join(sorted(categories))}" if categories else "categories:all",
                f"page:{pagination.page}",
                f"size:{pagination.page_size}",
                f"sort:{sort_by}:{sort_order}"
            ]
            cache_key = ":".join(cache_key_parts)
            
            # 尝试从缓存获取
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"从缓存获取内容列表: {cache_key}")
                return ContentListResponseSchema(**cached_result)
            
            # 构建查询
            query = self.supabase.table("contents").select("*", count="exact")
            
            # 添加过滤条件
            if content_type:
                query = query.eq("content_type", content_type.value)
            if author_id:
                query = query.eq("author_id", author_id)
            if target_entity_type:
                query = query.eq("target_entity_type", target_entity_type)
            if target_entity_id:
                query = query.eq("target_entity_id", target_entity_id)
            if status:
                query = query.eq("status", status.value)
            else:
                # 默认只返回已发布的内容
                query = query.eq("status", ContentStatus.PUBLISHED.value)
            
            # 标签过滤
            if tags:
                for tag in tags:
                    query = query.contains("tags", [tag])
            
            # 分类过滤
            if categories:
                for category in categories:
                    query = query.contains("categories", [category])
            
            # 添加排序
            if sort_order.lower() == "asc":
                query = query.order(sort_by)
            else:
                query = query.order(sort_by, desc=True)
            
            # 添加分页
            start_index = (pagination.page - 1) * pagination.page_size
            query = query.range(start_index, start_index + pagination.page_size - 1)
            
            # 执行查询
            response = query.execute()
            
            # 格式化响应
            contents = []
            for item in response.data:
                content_response = await self._format_content_response(item, user_id)
                contents.append(content_response)
            
            result = ContentListResponseSchema(
                contents=contents,
                total_count=response.count or 0,
                page=pagination.page,
                page_size=pagination.page_size,
                has_next=(response.count or 0) > (start_index + pagination.page_size)
            )
            
            # 缓存结果（2分钟）
            await self.cache.set(cache_key, result.dict(), expire=120)
            
            return result
            
        except Exception as e:
            logger.error(f"获取内容列表异常: {str(e)}", exc_info=True)
            return ContentListResponseSchema(
                contents=[],
                total_count=0,
                page=pagination.page,
                page_size=pagination.page_size,
                has_next=False
            )
    
    async def add_interaction(
        self,
        content_id: str,
        interaction_data: ContentInteractionCreate,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        添加内容互动 - 增强版本
        
        Args:
            content_id: 内容ID
            interaction_data: 互动数据
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            操作是否成功
        """
        try:
            # 验证内容存在
            content = await self.get_content(content_id)
            if not content:
                raise HTTPException(status_code=404, detail="内容不存在")
            
            # 检查是否已经互动过（某些互动类型不能重复）
            existing_interaction = self.supabase.table("content_interactions").select("*").match({
                "content_id": content_id,
                "user_id": user_id,
                "interaction_type": interaction_data.interaction_type.value
            }).execute()
            
            if existing_interaction.data and interaction_data.interaction_type in [InteractionType.LIKE, InteractionType.BOOKMARK]:
                # 取消互动
                return await self._remove_interaction(
                    content_id, interaction_data.interaction_type, user_id
                )
            
            # 创建互动记录
            interaction_id = str(uuid.uuid4())
            interaction_record = {
                "id": interaction_id,
                "content_id": content_id,
                "user_id": user_id,
                "interaction_type": interaction_data.interaction_type.value,
                "interaction_data": interaction_data.interaction_data,
                "device_fingerprint": interaction_data.device_fingerprint,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            insert_response = self.supabase.table("content_interactions").insert(interaction_record).execute()
            
            if not insert_response.data:
                return False
            
            # 更新内容统计
            await self._update_content_stats(content_id, interaction_data.interaction_type, 1)
            
            # 清除缓存
            await self.cache.delete(f"content:{content_id}")
            await self.cache.delete_pattern(f"user:{user_id}:interactions:*")
            
            logger.info(f"内容互动添加成功: {content_id}, 类型: {interaction_data.interaction_type}, 用户: {user_id}")
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"添加内容互动异常: {str(e)}")
            return False
    
    # 私有辅助方法
    async def _create_content_media(self, content_id: str, media_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """创建内容媒体记录"""
        try:
            media_id = str(uuid.uuid4())
            media_record = {
                "id": media_id,
                "content_id": content_id,
                "file_url": media_data["file_url"],
                "file_type": media_data["file_type"],
                "file_name": media_data["file_name"],
                "file_size": media_data["file_size"],
                "mime_type": media_data["mime_type"],
                "duration": media_data.get("duration"),
                "width": media_data.get("width"),
                "height": media_data.get("height"),
                "thumbnail_url": media_data.get("thumbnail_url"),
                "processing_status": "completed",
                "display_order": media_data.get("display_order", 0),
                "caption": media_data.get("caption"),
                "alt_text": media_data.get("alt_text"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            insert_response = self.supabase.table("content_media").insert(media_record).execute()
            
            if insert_response.data:
                return insert_response.data[0]
            else:
                logger.error(f"创建媒体记录失败: {insert_response}")
                return media_record
                
        except Exception as e:
            logger.error(f"创建媒体记录异常: {str(e)}")
            return media_data
    
    async def _get_content_media(self, content_id: str) -> List[Dict[str, Any]]:
        """获取内容媒体文件"""
        try:
            response = self.supabase.table("content_media").select("*").eq("content_id", content_id).order("display_order").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"获取内容媒体异常: {str(e)}")
            return []
    
    async def _increment_view_count(self, content_id: str, user_id: Optional[str] = None):
        """增加内容浏览计数"""
        try:
            # 使用Supabase的RPC功能增加计数
            self.supabase.rpc("increment_view_count", {"content_id": content_id}).execute()
            
            # 记录浏览互动（如果用户已登录）
            if user_id:
                view_interaction = ContentInteractionCreate(
                    interaction_type=InteractionType.VIEW,
                    device_fingerprint=None,
                    ip_address=None,
                    user_agent=None
                )
                await self.add_interaction(content_id, view_interaction, user_id)
                
        except Exception as e:
            logger.warning(f"增加浏览计数失败: {str(e)}")
    
    async def _update_content_stats(self, content_id: str, interaction_type: InteractionType, delta: int):
        """更新内容统计"""
        try:
            field_map = {
                InteractionType.LIKE: "like_count",
                InteractionType.COMMENT: "comment_count", 
                InteractionType.SHARE: "share_count",
                InteractionType.BOOKMARK: "bookmark_count",
                InteractionType.REPORT: "report_count"
            }
            
            field_name = field_map.get(interaction_type)
            if field_name:
                # 获取当前值
                current_response = self.supabase.table("contents").select(field_name).eq("id", content_id).execute()
                if current_response.data:
                    current_value = current_response.data[0].get(field_name, 0)
                    new_value = max(0, current_value + delta)
                    
                    update_data = {
                        field_name: new_value,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    self.supabase.table("contents").update(update_data).eq("id", content_id).execute()
                    
        except Exception as e:
            logger.error(f"更新内容统计失败: {str(e)}")
    
    async def _remove_interaction(self, content_id: str, interaction_type: InteractionType, user_id: str) -> bool:
        """移除互动"""
        try:
            # 删除互动记录
            delete_response = self.supabase.table("content_interactions").delete().match({
                "content_id": content_id,
                "user_id": user_id,
                "interaction_type": interaction_type.value
            }).execute()
            
            if delete_response.data:
                # 更新内容统计
                await self._update_content_stats(content_id, interaction_type, -1)
                
                # 清除缓存
                await self.cache.delete(f"content:{content_id}")
                
                logger.info(f"内容互动移除成功: {content_id}, 类型: {interaction_type}, 用户: {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"移除内容互动异常: {str(e)}")
            return False
    
    async def _format_content_response(
        self, 
        db_data: Dict[str, Any], 
        user_id: Optional[str] = None,
        media_files: Optional[List[Dict[str, Any]]] = None
    ) -> ContentResponse:
        """格式化数据库数据为ContentResponse对象"""
        # 获取用户互动状态
        user_interactions = {}
        if user_id:
            interactions_response = self.supabase.table("content_interactions").select("interaction_type").match({
                "content_id": db_data["id"],
                "user_id": user_id
            }).execute()
            
            if interactions_response.data:
                for interaction in interactions_response.data:
                    user_interactions[interaction["interaction_type"]] = True
        
        # 获取媒体文件
        if media_files is None:
            media_files = await self._get_content_media(db_data["id"])
        
        return ContentResponse(
            id=db_data["id"],
            title=db_data["title"],
            description=db_data["description"],
            content_type=ContentType(db_data["content_type"]),
            author_id=db_data["author_id"],
            author_name=db_data.get("author_name"),
            author_avatar=db_data.get("author_avatar"),
            target_entity_type=db_data["target_entity_type"],
            target_entity_id=db_data["target_entity_id"],
            target_entity_name=db_data.get("target_entity_name"),
            status=ContentStatus(db_data["status"]),
            visibility=db_data["visibility"],
            is_anonymous=db_data["is_anonymous"],
            tags=db_data.get("tags", []),
            categories=db_data.get("categories", []),
            location_data=db_data.get("location_data"),
            language=db_data.get("language", "vi"),
            like_count=db_data.get("like_count", 0),
            comment_count=db_data.get("comment_count", 0),
            share_count=db_data.get("share_count", 0),
            view_count=db_data.get("view_count", 0),
            bookmark_count=db_data.get("bookmark_count", 0),
            report_count=db_data.get("report_count", 0),
            quality_score=db_data.get("quality_score", 0.0),
            engagement_rate=db_data.get("engagement_rate", 0.0),
            media_files=media_files,
            created_at=datetime.fromisoformat(db_data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(db_data["updated_at"].replace('Z', '+00:00')),
            published_at=datetime.fromisoformat(db_data["published_at"].replace('Z', '+00:00')) if db_data.get("published_at") else None,
            moderated_at=datetime.fromisoformat(db_data["moderated_at"].replace('Z', '+00:00')) if db_data.get("moderated_at") else None,
            moderator_id=db_data.get("moderator_id"),
            moderation_notes=db_data.get("moderation_notes"),
            user_has_liked=user_interactions.get("like", False),
            user_has_bookmarked=user_interactions.get("bookmark", False),
            user_has_reported=user_interactions.get("report", False)
        )
    
    async def _log_content_activity(self, content_id: str, action: str, user_id: str):
        """记录内容活动日志"""
        # 这里可以实现详细的活动日志记录
        logger.info(f"内容活动: {action} - {content_id} by {user_id}")

# 全局内容服务实例
content_service = ContentService()

内容模块

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime
import json

from app.database.supabase_client import db_manager, Tables
from app.models.content import (
    ContentCreate, ContentUpdate, ContentResponse, ContentInDB,
    ContentInteractionCreate, ContentQualityScore, ContentSearchQuery,
    ContentType, ContentStatus, ModerationStatus
)
from app.core.exceptions import ContentNotFoundException, DatabaseException, PermissionDeniedException

logger = logging.getLogger(__name__)

class ContentService:
    """内容服务类"""
    
    def __init__(self):
        self.db = db_manager
    
    async def create_content(self, content_data: ContentCreate) -> Dict[str, Any]:
        """创建新内容"""
        try:
            # 准备内容数据
            content_dict = content_data.dict()
            content_dict["id"] = str(uuid4())  # 生成唯一ID
            content_dict["created_at"] = datetime.utcnow().isoformat()
            content_dict["updated_at"] = datetime.utcnow().isoformat()
            
            # 插入内容数据
            content = await self.db.insert(Tables.CONTENT, content_dict)
            
            # 创建质量评分记录
            quality_score = ContentQualityScore(content_id=UUID(content["id"]))
            await self.db.insert(
                Tables.CONTENT_QUALITY_SCORES,
                quality_score.dict()
            )
            
            # 添加到审核队列
            moderation_item = {
                "content_id": content["id"],
                "priority": "normal",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await self.db.insert(Tables.MODERATION_QUEUE, moderation_item)
            
            # 更新用户统计信息
            from app.services.user_service import UserService
            user_service = UserService()
            
            # 获取用户当前统计
            user_profile = await user_service.get_user_profile(content_data.creator_id)
            current_stats = user_profile.get("profile", {}).get("statistics", {})
            current_uploads = current_stats.get("total_uploads", 0)
            
            # 更新上传计数
            await user_service.update_user_statistics(
                str(content_data.creator_id),
                {"total_uploads": current_uploads + 1}
            )
            
            logger.info(f"内容创建成功: {content['id']}")
            return content
            
        except Exception as e:
            logger.error(f"创建内容失败: {str(e)}")
            raise DatabaseException(f"创建内容失败: {str(e)}")
    
    async def get_content_by_id(self, content_id: str) -> Dict[str, Any]:
        """根据ID获取内容"""
        try:
            contents = await self.db.select(
                Tables.CONTENT,
                filters={"id": content_id}
            )
            if not contents:
                raise ContentNotFoundException(content_id)
            
            content = contents[0]
            
            # 获取质量评分
            quality_scores = await self.db.select(
                Tables.CONTENT_QUALITY_SCORES,
                filters={"content_id": content_id}
            )
            if quality_scores:
                content["quality_score"] = quality_scores[0].get("overall_score", 0.0)
            
            # 获取创作者信息
            from app.services.user_service import UserService
            user_service = UserService()
            try:
                creator = await user_service.get_user_by_id(str(content["creator_id"]))
                if creator:
                    content["creator_info"] = {
                        "username": creator.get("username"),
                        "avatar_url": creator.get("avatar_url")
                    }
            except Exception:
                pass  # 忽略获取创作者信息失败
            
            return content
            
        except ContentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取内容失败 {content_id}: {str(e)}")
            raise DatabaseException(f"获取内容失败: {str(e)}")
    
    async def update_content(self, content_id: str, update_data: ContentUpdate, user_id: str) -> Dict[str, Any]:
        """更新内容"""
        try:
            # 检查内容是否存在且用户有权限
            content = await self.get_content_by_id(content_id)
            if str(content["creator_id"]) != user_id:
                raise PermissionDeniedException()
            
            # 准备更新数据
            update_dict = update_data.dict(exclude_unset=True)
            if update_dict:
                update_dict["updated_at"] = datetime.utcnow().isoformat()
                updated_contents = await self.db.update(
                    Tables.CONTENT,
                    update_dict,
                    {"id": content_id}
                )
                
                logger.info(f"内容更新成功: {content_id}")
                return updated_contents[0] if updated_contents else content
            
            return content
            
        except (ContentNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.error(f"更新内容失败 {content_id}: {str(e)}")
            raise DatabaseException(f"更新内容失败: {str(e)}")
    
    async def delete_content(self, content_id: str, user_id: str) -> None:
        """删除内容"""
        try:
            # 检查内容是否存在且用户有权限
            content = await self.get_content_by_id(content_id)
            if str(content["creator_id"]) != user_id:
                raise PermissionDeniedException()
            
            # 软删除：更新状态为已删除
            await self.db.update(
                Tables.CONTENT,
                {
                    "status": "deleted",
                    "updated_at": datetime.utcnow().isoformat()
                },
                {"id": content_id}
            )
            
            logger.info(f"内容删除成功: {content_id}")
            
        except (ContentNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.error(f"删除内容失败 {content_id}: {str(e)}")
            raise DatabaseException(f"删除内容失败: {str(e)}")
    
    async def record_interaction(self, interaction_data: ContentInteractionCreate, user_id: str) -> Dict[str, Any]:
        """记录用户互动"""
        try:
            # 检查内容是否存在
            content = await self.get_content_by_id(str(interaction_data.content_id))
            
            # 准备互动数据
            interaction_dict = interaction_data.dict()
            interaction_dict["id"] = str(uuid4())
            interaction_dict["user_id"] = user_id
            interaction_dict["created_at"] = datetime.utcnow().isoformat()
            
            # 插入互动记录
            interaction = await self.db.insert(Tables.CONTENT_INTERACTIONS, interaction_dict)
            
            # 更新内容统计
            update_fields = {}
            if interaction_data.interaction_type == "view":
                update_fields["view_count"] = content.get("view_count", 0) + 1
            elif interaction_data.interaction_type == "like":
                update_fields["like_count"] = content.get("like_count", 0) + 1
            elif interaction_data.interaction_type == "share":
                update_fields["share_count"] = content.get("share_count", 0) + 1
            
            if update_fields:
                update_fields["updated_at"] = datetime.utcnow().isoformat()
                await self.db.update(
                    Tables.CONTENT,
                    update_fields,
                    {"id": str(interaction_data.content_id)}
                )
            
            # 更新用户统计
            from app.services.user_service import UserService
            user_service = UserService()
            user_profile = await user_service.get_user_profile(str(content["creator_id"]))
            current_stats = user_profile.get("profile", {}).get("statistics", {})
            
            stats_updates = {}
            if interaction_data.interaction_type == "view":
                stats_updates["total_views"] = current_stats.get("total_views", 0) + 1
            elif interaction_data.interaction_type == "like":
                stats_updates["total_likes"] = current_stats.get("total_likes", 0) + 1
            elif interaction_data.interaction_type == "share":
                stats_updates["total_shares"] = current_stats.get("total_shares", 0) + 1
            
            if stats_updates:
                await user_service.update_user_statistics(
                    str(content["creator_id"]),
                    stats_updates
                )
            
            logger.info(f"互动记录成功: {interaction_data.interaction_type} for content {interaction_data.content_id}")
            return interaction
            
        except ContentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"记录互动失败: {str(e)}")
            raise DatabaseException(f"记录互动失败: {str(e)}")
    
    async def search_content(self, search_query: ContentSearchQuery) -> Dict[str, Any]:
        """搜索内容"""
        try:
            # 构建查询条件
            filters = {}
            
            if search_query.content_type:
                filters["content_type"] = search_query.content_type.value
            
            if search_query.creator_id:
                filters["creator_id"] = str(search_query.creator_id)
            
            # 状态过滤：只显示已审核通过的内容
            filters["moderation_status"] = "approved"
            filters["status"] = "approved"
            
            # 执行查询
            contents = await self.db.select(
                Tables.CONTENT,
                columns="*",
                filters=filters
            )
            
            # 应用其他过滤条件
            filtered_contents = []
            for content in contents:
                # 标签过滤
                if search_query.tags:
                    content_tags = content.get("tags", [])
                    if not any(tag in content_tags for tag in search_query.tags):
                        continue
                
                # 质量分数过滤
                if search_query.min_quality_score is not None:
                    quality_scores = await self.db.select(
                        Tables.CONTENT_QUALITY_SCORES,
                        filters={"content_id": content["id"]}
                    )
                    quality_score = quality_scores[0].get("overall_score", 0.0) if quality_scores else 0.0
                    if quality_score < search_query.min_quality_score:
                        continue
                
                # 日期范围过滤
                if search_query.date_from:
                    content_date = datetime.fromisoformat(content["created_at"].replace('Z', '+00:00'))
                    if content_date < search_query.date_from:
                        continue
                
                if search_query.date_to:
                    content_date = datetime.fromisoformat(content["created_at"].replace('Z', '+00:00'))
                    if content_date > search_query.date_to:
                        continue
                
                filtered_contents.append(content)
            
            # 排序
            sort_key = search_query.sort_by
            reverse = search_query.sort_order == "desc"
            
            filtered_contents.sort(
                key=lambda x: x.get(sort_key, 0),
                reverse=reverse
            )
            
            # 分页
            total = len(filtered_contents)
            start_idx = (search_query.page - 1) * search_query.size
            end_idx = start_idx + search_query.size
            paginated_contents = filtered_contents[start_idx:end_idx]
            
            # 添加质量分数和创作者信息
            for content in paginated_contents:
                quality_scores = await self.db.select(
                    Tables.CONTENT_QUALITY_SCORES,
                    filters={"content_id": content["id"]}
                )
                if quality_scores:
                    content["quality_score"] = quality_scores[0].get("overall_score", 0.0)
                
                from app.services.user_service import UserService
                user_service = UserService()
                try:
                    creator = await user_service.get_user_by_id(str(content["creator_id"]))
                    if creator:
                        content["creator_info"] = {
                            "username": creator.get("username"),
                            "avatar_url": creator.get("avatar_url")
                        }
                except Exception:
                    pass
            
            result = {
                "items": paginated_contents,
                "total": total,
                "page": search_query.page,
                "size": search_query.size,
                "pages": (total + search_query.size - 1) // search_query.size
            }
            
            return result
            
        except Exception as e:
            logger.error(f"搜索内容失败: {str(e)}")
            raise DatabaseException(f"搜索内容失败: {str(e)}")
    
    async def get_user_content(self, user_id: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取用户的内容列表"""
        try:
            contents = await self.db.select(
                Tables.CONTENT,
                filters={"creator_id": user_id, "status": ["draft", "approved"]}
            )
            
            # 分页
            total = len(contents)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_contents = contents[start_idx:end_idx]
            
            # 添加质量分数
            for content in paginated_contents:
                quality_scores = await self.db.select(
                    Tables.CONTENT_QUALITY_SCORES,
                    filters={"content_id": content["id"]}
                )
                if quality_scores:
                    content["quality_score"] = quality_scores[0].get("overall_score", 0.0)
            
            result = {
                "items": paginated_contents,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取用户内容失败 {user_id}: {str(e)}")
            raise DatabaseException(f"获取用户内容失败: {str(e)}")