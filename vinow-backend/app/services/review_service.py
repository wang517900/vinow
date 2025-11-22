商家系统7评价管理
"""
评价相关业务服务类

本模块提供了评价相关的业务逻辑处理，包括：
- 评价列表获取与过滤
- 评价回复创建
- 评价统计信息获取
- 评价状态更新
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.crud.review import ReviewCRUD
from app.crud.reply import ReplyCRUD
from app.schemas.review import ReviewCreate, ReviewSummary
from app.schemas.reply import ReplyCreate
from app.database import supabase

class ReviewService:
    """
    评价业务服务类
    
    负责处理评价相关的业务逻辑，协调数据访问层(CRUD)完成具体操作
    """
    
    def __init__(self):
        """
        初始化评价服务对象
        
        创建评价和回复的数据访问对象实例
        """
        # 初始化评价数据访问对象
        self.review_crud = ReviewCRUD(supabase)
        
        # 初始化回复数据访问对象
        self.reply_crud = ReplyCRUD(supabase)

    async def get_review_list(
        self,
        merchant_id: int,
        page: int = 1,
        limit: int = 20,
        rating: Optional[int] = None,
        date_range: Optional[str] = None,
        has_reply: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        获取商户的评价列表（业务层封装）
        
        Args:
            merchant_id (int): 商户ID
            page (int): 页码，默认为1
            limit (int): 每页数量，默认为20
            rating (Optional[int]): 评分过滤条件（1-5星）
            date_range (Optional[str]): 时间范围过滤（today/week/month/year）
            has_reply (Optional[bool]): 是否有回复过滤条件
            
        Returns:
            Dict[str, Any]: 包含评价列表和分页信息的字典
        """
        # 调用数据访问层方法获取评价列表
        return await self.review_crud.get_reviews(
            merchant_id=merchant_id,
            page=page,
            limit=limit,
            rating=rating,
            date_range=date_range,
            has_reply=has_reply
        )

    async def create_review_reply(
        self,
        merchant_id: int,
        review_id: int,
        reply_data: ReplyCreate
    ) -> Dict[str, Any]:
        """
        创建评价回复
        
        Args:
            merchant_id (int): 商户ID
            review_id (int): 评价ID
            reply_data (ReplyCreate): 回复创建数据
            
        Returns:
            Dict[str, Any]: 创建成功的回复数据
            
        Raises:
            ValueError: 当评价不存在、无权限访问或已存在回复时抛出异常
        """
        # 检查评价是否存在且属于该商户（权限验证）
        review_result = supabase.table("merchant_reviews").select("*").eq("id", review_id).eq("merchant_id", merchant_id).execute()
        if not review_result.data:
            raise ValueError("评价不存在或无权访问")
        
        # 检查该评价是否已经存在回复，避免重复回复
        existing_reply = await self.reply_crud.get_reply_by_review_id(review_id)
        if existing_reply:
            raise ValueError("该评价已回复，请勿重复回复")
        
        # 构造回复创建对象，补充商户ID和评价ID
        reply_create = ReplyCreate(
            **reply_data.model_dump(),
            merchant_id=merchant_id,
            review_id=review_id
        )
        
        # 调用数据访问层创建回复
        result = await self.reply_crud.create_reply(reply_create)
        if not result:
            raise ValueError("回复创建失败")
        
        # 返回创建成功的回复数据
        return result

    async def get_review_summary(self, merchant_id: int) -> Dict[str, Any]:
        """
        获取商户评价统计摘要信息（业务层封装）
        
        Args:
            merchant_id (int): 商户ID
            
        Returns:
            Dict[str, Any]: 包含各种统计信息的字典
        """
        # 调用数据访问层方法获取评价统计摘要
        return await self.review_crud.get_review_summary(merchant_id)

    async def update_review_status(
        self,
        review_id: int,
        merchant_id: int,
        status: str
    ) -> bool:
        """
        更新评价状态
        
        Args:
            review_id (int): 评价ID
            merchant_id (int): 商户ID
            status (str): 新的状态值（active/hidden/deleted）
            
        Returns:
            bool: 更新成功返回True，否则返回False
            
        Raises:
            ValueError: 当状态值不在有效范围内时抛出异常
        """
        # 定义有效的状态值列表
        valid_statuses = ["active", "hidden", "deleted"]
        
        # 验证状态值是否有效
        if status not in valid_statuses:
            raise ValueError(f"状态必须是: {', '.join(valid_statuses)}")
        
        # 调用数据访问层方法更新评价状态
        return await self.review_crud.update_review_status(review_id, merchant_id, status)

        内容系统-完整的评价服务
  import asyncio
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.database.connection import DatabaseManager, supabase
from app.models.review_models import (
    Review, ReviewDimensionConfig, ReviewHelpfulVote,
    ReviewStatus, ReviewVerificationStatus, ReviewDimension,
    ReviewCreate, ReviewUpdate, ReviewResponse, ReviewSummary,
    BusinessReplyCreate, ReviewHelpfulVoteCreate, ReviewDimensionScore
)
from app.models.content_models import Content, ContentType, ContentStatus
from app.schemas.review_schemas import (
    ReviewCreateSchema, ReviewUpdateSchema, ReviewResponseSchema,
    BusinessReplyCreateSchema, ReviewHelpfulVoteCreateSchema, ReviewSummarySchema
)
from app.services.content_service import content_service
from app.services.moderation_service import moderation_service
from app.utils.cache import cache_manager
from app.utils.pagination import PaginationParams
from app.utils.security import get_current_user
from app.utils.validation import validate_review_creation, sanitize_content_text
import logging
from sqlalchemy import and_, or_, desc, asc, func, text

logger = logging.getLogger(__name__)

class ReviewService:
    """评价服务类 - 生产级别，包含完整评价业务逻辑"""
    
    def __init__(self):
        # 初始化Supabase客户端
        self.supabase = supabase
        # 初始化缓存管理器
        self.cache = cache_manager
        # 评价维度配置缓存
        self.dimension_config_cache = {}
    
    async def create_review(
        self, 
        review_data: ReviewCreateSchema, 
        user_id: str,
        user_name: Optional[str] = None,
        user_avatar: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
        db: Session = None
    ) -> ReviewResponse:
        """
        创建新评价 - 完整实现
        
        Args:
            review_data: 评价数据
            user_id: 用户ID
            user_name: 用户名称
            user_avatar: 用户头像
            background_tasks: 后台任务
            db: 数据库会话
            
        Returns:
            创建的评价对象
        """
        try:
            # 验证评价数据完整性
            await validate_review_creation(review_data)
            
            # 验证用户是否已经对同一目标实体评价过
            existing_review = await self._get_user_review_for_entity(
                user_id, 
                review_data.target_entity_type, 
                review_data.target_entity_id
            )
            if existing_review:
                raise HTTPException(status_code=400, detail="您已经对该商家进行过评价")
            
            # 清理文本内容，防止XSS攻击
            sanitized_title = sanitize_content_text(review_data.title) if review_data.title else None
            sanitized_description = sanitize_content_text(review_data.description)
            
            # 生成评价ID和内容ID
            review_id = str(uuid.uuid4())
            content_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # 构建维度评分字典
            rating_breakdown = {
                score.dimension: score.score 
                for score in review_data.dimension_scores
            }
            # 添加总体评分到维度评分中
            rating_breakdown["overall"] = review_data.overall_rating
            
            # 首先创建内容记录
            content_record = {
                "id": content_id,
                "content_type": ContentType.REVIEW.value,
                "title": sanitized_title,
                "description": sanitized_description,
                "author_id": user_id,
                "author_name": user_name if not review_data.is_anonymous else None,
                "author_avatar": user_avatar if not review_data.is_anonymous else None,
                "target_entity_type": review_data.target_entity_type,
                "target_entity_id": review_data.target_entity_id,
                "status": ContentStatus.PENDING_REVIEW.value,
                "visibility": "public",
                "is_anonymous": review_data.is_anonymous,
                "tags": review_data.tags,
                "categories": [],
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
            
            # 插入内容记录到数据库
            content_insert_response = self.supabase.table("contents").insert(content_record).execute()
            if not content_insert_response.data:
                logger.error(f"内容记录创建失败: {content_insert_response}")
                raise HTTPException(status_code=500, detail="评价创建失败")
            
            # 构建评价记录
            review_record = {
                "id": review_id,
                "content_id": content_id,
                "overall_rating": float(review_data.overall_rating),
                "rating_breakdown": rating_breakdown,
                "verification_status": await self._determine_verification_status(review_data.order_id),
                "order_id": review_data.order_id,
                "purchase_date": review_data.purchase_date.isoformat() if review_data.purchase_date else None,
                "pros": review_data.pros,
                "cons": review_data.cons,
                "review_tags": review_data.tags,
                "helpful_votes": 0,
                "unhelpful_votes": 0,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # 插入评价记录到数据库
            review_insert_response = self.supabase.table("reviews").insert(review_record).execute()
            if not review_insert_response.data:
                # 回滚内容记录
                self.supabase.table("contents").delete().eq("id", content_id).execute()
                logger.error(f"评价记录创建失败: {review_insert_response}")
                raise HTTPException(status_code=500, detail="评价创建失败")
            
            # 处理媒体文件
            media_files = []
            if review_data.media_files:
                for media_data in review_data.media_files:
                    media_file = await content_service._create_content_media(content_id, media_data, user_id)
                    media_files.append(media_file)
            
            # 更新内容的媒体文件URL
            if media_files:
                media_urls = [media["file_url"] for media in media_files]
                self.supabase.table("contents").update({
                    "media_urls": media_urls,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", content_id).execute()
            
            # 触发自动审核
            if background_tasks and settings.AUTO_MODERATION_ENABLED:
                background_tasks.add_task(
                    moderation_service.auto_moderate_review,
                    review_id,
                    sanitized_title,
                    sanitized_description,
                    media_urls if media_files else []
                )
            
            # 更新目标实体的评价统计
            background_tasks.add_task(
                self._update_entity_review_stats,
                review_data.target_entity_type,
                review_data.target_entity_id
            )
            
            # 清除相关缓存
            await self.cache.delete_pattern(f"user:{user_id}:reviews:*")
            await self.cache.delete_pattern(f"entity:{review_data.target_entity_type}:{review_data.target_entity_id}:reviews:*")
            await self.cache.delete_pattern(f"entity:{review_data.target_entity_type}:{review_data.target_entity_id}:summary")
            
            logger.info(f"评价创建成功: {review_id}, 目标实体: {review_data.target_entity_type}:{review_data.target_entity_id}, 用户: {user_id}")
            
            # 返回创建的评价
            return await self.get_review(review_id, user_id)
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录异常详情
            logger.error(f"评价创建异常: {str(e)}", exc_info=True)
            # 返回服务器错误
            raise HTTPException(status_code=500, detail=f"评价创建失败: {str(e)}")
    
    async def get_review(self, review_id: str, user_id: Optional[str] = None) -> Optional[ReviewResponse]:
        """
        获取评价详情
        
        Args:
            review_id: 评价ID
            user_id: 当前用户ID
            
        Returns:
            评价对象或None
        """
        try:
            # 构建缓存键
            cache_key = f"review:{review_id}"
            # 尝试从缓存获取评价
            cached_review = await self.cache.get(cache_key)
            if cached_review:
                logger.debug(f"从缓存获取评价: {review_id}")
                return ReviewResponse(**cached_review)
            
            # 查询评价记录
            review_response = self.supabase.table("reviews").select("*, contents(*)").eq("id", review_id).execute()
            if not review_response.data:
                return None
            
            # 获取评价数据和关联的内容数据
            review_data = review_response.data[0]
            content_data = review_data.get("contents", {})
            
            # 检查评价状态，只有已发布或已审核的评价可以被查看
            if content_data.get("status") not in [ContentStatus.PUBLISHED.value, ContentStatus.APPROVED.value]:
                # 只有作者或管理员可以查看未发布的评价
                if user_id != content_data.get("author_id"):
                    raise HTTPException(status_code=404, detail="评价不存在")
            
            # 增加浏览计数
            await content_service._increment_view_count(content_data["id"], user_id)
            
            # 获取媒体文件
            media_files = await content_service._get_content_media(content_data["id"])
            
            # 获取用户投票状态
            user_vote_status = None
            if user_id:
                user_vote_status = await self._get_user_helpful_vote(review_id, user_id)
            
            # 格式化评价响应
            review_response_obj = await self._format_review_response(
                review_data, content_data, media_files, user_id, user_vote_status
            )
            
            # 缓存评价数据，有效期5分钟
            await self.cache.set(cache_key, review_response_obj.dict(), expire=300)
            
            return review_response_obj
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录异常详情
            logger.error(f"获取评价异常: {str(e)}", exc_info=True)
            return None
    
    async def update_review(
        self, 
        review_id: str, 
        update_data: ReviewUpdateSchema, 
        user_id: str
    ) -> Optional[ReviewResponse]:
        """
        更新评价
        
        Args:
            review_id: 评价ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            更新后的评价对象
        """
        try:
            # 验证评价存在且用户有权限
            existing_review = await self.get_review(review_id, user_id)
            if not existing_review:
                raise HTTPException(status_code=404, detail="评价不存在")
                
            if existing_review.author_id != user_id:
                raise HTTPException(status_code=403, detail="无权限修改此评价")
            
            # 构建更新数据
            update_fields = {}
            if update_data.title is not None:
                update_fields["title"] = sanitize_content_text(update_data.title)
            if update_data.description is not None:
                update_fields["description"] = sanitize_content_text(update_data.description)
            if update_data.tags is not None:
                update_fields["tags"] = update_data.tags
            if update_data.pros is not None:
                update_fields["pros"] = update_data.pros
            if update_data.cons is not None:
                update_fields["cons"] = update_data.cons
            if update_data.is_anonymous is not None:
                update_fields["is_anonymous"] = update_data.is_anonymous
            
            # 如果评价内容被修改，重置审核状态
            if any(field in update_fields for field in ["title", "description", "tags", "pros", "cons"]):
                update_fields["status"] = ContentStatus.PENDING_REVIEW.value
                update_fields["moderated_at"] = None
                update_fields["moderator_id"] = None
                update_fields["moderation_notes"] = None
            
            update_fields["updated_at"] = datetime.utcnow().isoformat()
            
            # 更新内容记录
            update_response = self.supabase.table("contents").update(update_fields).eq("id", existing_review.content_id).execute()
            
            if not update_response.data:
                raise HTTPException(status_code=500, detail="评价更新失败")
            
            # 清除缓存
            await self.cache.delete(f"review:{review_id}")
            await self.cache.delete_pattern(f"user:{user_id}:reviews:*")
            await self.cache.delete_pattern(f"entity:{existing_review.target_entity_type}:{existing_review.target_entity_id}:*")
            
            logger.info(f"评价更新成功: {review_id}, 用户: {user_id}")
            
            return await self.get_review(review_id, user_id)
                
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录异常详情
            logger.error(f"评价更新异常: {str(e)}", exc_info=True)
            # 返回服务器错误
            raise HTTPException(status_code=500, detail=f"评价更新失败: {str(e)}")
    
    async def delete_review(self, review_id: str, user_id: str) -> bool:
        """
        删除评价
        
        Args:
            review_id: 评价ID
            user_id: 用户ID
            
        Returns:
            删除是否成功
        """
        try:
            # 验证评价存在且用户有权限
            existing_review = await self.get_review(review_id, user_id)
            if not existing_review:
                raise HTTPException(status_code=404, detail="评价不存在")
                
            if existing_review.author_id != user_id:
                raise HTTPException(status_code=403, detail="无权限删除此评价")
            
            # 软删除：更新状态为DELETED
            update_response = self.supabase.table("contents").update({
                "status": ContentStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", existing_review.content_id).execute()
            
            success = bool(update_response.data)
            
            if success:
                # 更新目标实体的评价统计
                asyncio.create_task(
                    self._update_entity_review_stats(
                        existing_review.target_entity_type,
                        existing_review.target_entity_id
                    )
                )
                
                # 清除缓存
                await self.cache.delete(f"review:{review_id}")
                await self.cache.delete_pattern(f"user:{user_id}:reviews:*")
                await self.cache.delete_pattern(f"entity:{existing_review.target_entity_type}:{existing_review.target_entity_id}:*")
                
                # 记录删除活动
                await self._log_review_activity(review_id, "delete", user_id)
                
                logger.info(f"评价删除成功: {review_id}, 用户: {user_id}")
            else:
                logger.error(f"评价删除失败: {review_id}")
                
            return success
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录异常详情
            logger.error(f"评价删除异常: {str(e)}")
            # 返回服务器错误
            raise HTTPException(status_code=500, detail=f"评价删除失败: {str(e)}")
    
    async def list_reviews(
        self,
        pagination: PaginationParams,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        author_id: Optional[str] = None,
        status: Optional[ContentStatus] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        has_media: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        user_id: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取评价列表
        
        Args:
            pagination: 分页参数
            target_entity_type: 目标实体类型过滤
            target_entity_id: 目标实体ID过滤
            author_id: 作者ID过滤
            status: 状态过滤
            min_rating: 最低评分过滤
            max_rating: 最高评分过滤
            has_media: 是否有媒体文件过滤
            is_verified: 是否已验证过滤
            user_id: 当前用户ID
            sort_by: 排序字段
            sort_order: 排序方向
            
        Returns:
            评价列表和分页信息
        """
        try:
            # 构建缓存键
            cache_key_parts = [
                "reviews",
                f"target_type:{target_entity_type}" if target_entity_type else "target_type:all",
                f"target_id:{target_entity_id}" if target_entity_id else "target_id:all",
                f"author:{author_id}" if author_id else "author:all",
                f"status:{status.value}" if status else "status:published",
                f"min_rating:{min_rating}" if min_rating else "min_rating:all",
                f"max_rating:{max_rating}" if max_rating else "max_rating:all",
                f"has_media:{has_media}" if has_media is not None else "has_media:all",
                f"is_verified:{is_verified}" if is_verified is not None else "is_verified:all",
                f"page:{pagination.page}",
                f"size:{pagination.page_size}",
                f"sort:{sort_by}:{sort_order}"
            ]
            cache_key = ":".join(cache_key_parts)
            
            # 尝试从缓存获取
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"从缓存获取评价列表: {cache_key}")
                return cached_result
            
            # 构建查询 - 联表查询评价和内容
            query = self.supabase.table("reviews").select("*, contents(*)")
            
            # 添加过滤条件
            if target_entity_type:
                query = query.eq("contents.target_entity_type", target_entity_type)
            if target_entity_id:
                query = query.eq("contents.target_entity_id", target_entity_id)
            if author_id:
                query = query.eq("contents.author_id", author_id)
            if status:
                query = query.eq("contents.status", status.value)
            else:
                # 默认只返回已发布的内容
                query = query.eq("contents.status", ContentStatus.PUBLISHED.value)
            
            # 评分过滤
            if min_rating is not None:
                query = query.gte("overall_rating", min_rating)
            if max_rating is not None:
                query = query.lte("overall_rating", max_rating)
            
            # 媒体文件过滤
            if has_media is not None:
                if has_media:
                    query = query.neq("contents.media_urls", "[]")
                else:
                    query = query.eq("contents.media_urls", "[]")
            
            # 验证状态过滤
            if is_verified is not None:
                if is_verified:
                    query = query.neq("verification_status", ReviewVerificationStatus.UNVERIFIED.value)
                else:
                    query = query.eq("verification_status", ReviewVerificationStatus.UNVERIFIED.value)
            
            # 添加排序
            sort_field_map = {
                "created_at": "contents.created_at",
                "rating": "overall_rating",
                "helpful": "helpful_votes",
                "updated_at": "contents.updated_at"
            }
            actual_sort_field = sort_field_map.get(sort_by, "contents.created_at")
            
            if sort_order.lower() == "asc":
                query = query.order(actual_sort_field)
            else:
                query = query.order(actual_sort_field, desc=True)
            
            # 添加分页
            start_index = (pagination.page - 1) * pagination.page_size
            query = query.range(start_index, start_index + pagination.page_size - 1)
            
            # 执行查询
            response = query.execute()
            
            # 格式化响应
            reviews = []
            for item in response.data:
                review_data = item
                content_data = item.get("contents", {})
                
                # 获取媒体文件
                media_files = await content_service._get_content_media(content_data["id"])
                
                # 获取用户投票状态
                user_vote_status = None
                if user_id:
                    user_vote_status = await self._get_user_helpful_vote(review_data["id"], user_id)
                
                review_response = await self._format_review_response(
                    review_data, content_data, media_files, user_id, user_vote_status
                )
                reviews.append(review_response)
            
            result = {
                "reviews": reviews,
                "total_count": getattr(response, 'count', len(response.data)),
                "page": pagination.page,
                "page_size": pagination.page_size,
                "has_next": getattr(response, 'count', len(response.data)) > (start_index + pagination.page_size)
            }
            
            # 缓存结果，有效期2分钟
            await self.cache.set(cache_key, result, expire=120)
            
            return result
            
        except Exception as e:
            # 记录异常详情
            logger.error(f"获取评价列表异常: {str(e)}", exc_info=True)
            # 返回空结果
            return {
                "reviews": [],
                "total_count": 0,
                "page": pagination.page,
                "page_size": pagination.page_size,
                "has_next": False
            }
    
    async def add_business_reply(
        self, 
        review_id: str, 
        reply_data: BusinessReplyCreateSchema, 
        user_id: str
    ) -> bool:
        """
        添加商家回复
        
        Args:
            review_id: 评价ID
            reply_data: 回复数据
            user_id: 用户ID（商家用户）
            
        Returns:
            操作是否成功
        """
        try:
            # 验证评价存在
            existing_review = await self.get_review(review_id)
            if not existing_review:
                raise HTTPException(status_code=404, detail="评价不存在")
            
            # 这里应该验证用户是否有权限回复（通常是商家管理员）
            # 简化实现：假设用户有权限
            
            # 清理回复文本
            sanitized_reply = sanitize_content_text(reply_data.reply_text)
            
            # 更新商家回复
            update_response = self.supabase.table("reviews").update({
                "business_reply": sanitized_reply,
                "business_replier_id": user_id,
                "business_reply_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", review_id).execute()
            
            success = bool(update_response.data)
            
            if success:
                # 清除缓存
                await self.cache.delete(f"review:{review_id}")
                
                # 记录回复活动
                await self._log_review_activity(review_id, "business_reply", user_id)
                
                logger.info(f"商家回复添加成功: {review_id}, 商家用户: {user_id}")
            else:
                logger.error(f"商家回复添加失败: {review_id}")
                
            return success
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录异常详情
            logger.error(f"添加商家回复异常: {str(e)}")
            # 返回服务器错误
            raise HTTPException(status_code=500, detail=f"添加商家回复失败: {str(e)}")
    
    async def add_helpful_vote(
        self, 
        review_id: str, 
        vote_data: ReviewHelpfulVoteCreateSchema, 
        user_id: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        添加有用性投票
        
        Args:
            review_id: 评价ID
            vote_data: 投票数据
            user_id: 用户ID
            ip_address: IP地址
            
        Returns:
            操作是否成功
        """
        try:
            # 验证评价存在
            existing_review = await self.get_review(review_id)
            if not existing_review:
                raise HTTPException(status_code=404, detail="评价不存在")
            
            # 检查用户是否已经投过票
            existing_vote = await self._get_user_helpful_vote(review_id, user_id)
            if existing_vote is not None:
                # 如果已经投过票，更新投票
                return await self._update_helpful_vote(review_id, user_id, vote_data.is_helpful)
            
            # 创建投票记录
            vote_id = str(uuid.uuid4())
            vote_record = {
                "id": vote_id,
                "review_id": review_id,
                "user_id": user_id,
                "is_helpful": vote_data.is_helpful,
                "device_fingerprint": vote_data.device_fingerprint,
                "ip_address": ip_address,
                "created_at": datetime.utcnow().isoformat()
            }
            
            insert_response = self.supabase.table("review_helpful_votes").insert(vote_record).execute()
            
            if not insert_response.data:
                return False
            
            # 更新评价的有用性投票统计
            await self._update_helpful_votes_count(review_id, vote_data.is_helpful, 1)
            
            # 清除缓存
            await self.cache.delete(f"review:{review_id}")
            
            logger.info(f"有用性投票添加成功: {review_id}, 用户: {user_id}, 有用: {vote_data.is_helpful}")
            
            return True
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录异常详情
            logger.error(f"添加有用性投票异常: {str(e)}")
            return False
    
    async def get_review_summary(
        self, 
        target_entity_type: str, 
        target_entity_id: str
    ) -> ReviewSummary:
        """
        获取评价汇总信息
        
        Args:
            target_entity_type: 目标实体类型
            target_entity_id: 目标实体ID
            
        Returns:
            评价汇总信息
        """
        try:
            # 构建缓存键
            cache_key = f"entity:{target_entity_type}:{target_entity_id}:summary"
            
            # 尝试从缓存获取
            cached_summary = await self.cache.get(cache_key)
            if cached_summary:
                return ReviewSummary(**cached_summary)
            
            # 查询评价统计信息
            reviews_response = self.supabase.table("reviews").select(
                "overall_rating, rating_breakdown, verification_status, helpful_votes, contents!inner(status)"
            ).eq("contents.target_entity_type", target_entity_type).eq(
                "contents.target_entity_id", target_entity_id
            ).eq("contents.status", ContentStatus.PUBLISHED.value).execute()
            
            if not reviews_response.data:
                # 如果没有评价，返回空汇总
                empty_summary = ReviewSummary(
                    target_entity_type=target_entity_type,
                    target_entity_id=target_entity_id,
                    average_rating=0.0,
                    rating_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                    total_reviews=0,
                    dimension_averages={},
                    popular_tags=[],
                    verified_reviews_count=0,
                    helpful_reviews_count=0
                )
                await self.cache.set(cache_key, empty_summary.dict(), expire=300)
                return empty_summary
            
            reviews = reviews_response.data
            
            # 计算平均评分
            total_rating = sum(review["overall_rating"] for review in reviews)
            average_rating = round(total_rating / len(reviews), 1)
            
            # 计算评分分布
            rating_distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            for review in reviews:
                rating = int(round(review["overall_rating"]))
                if 1 <= rating <= 5:
                    rating_distribution[str(rating)] += 1
            
            # 计算各维度平均分
            dimension_totals = {}
            dimension_counts = {}
            
            for review in reviews:
                rating_breakdown = review.get("rating_breakdown", {})
                for dimension, score in rating_breakdown.items():
                    if dimension != "overall":  # 跳过总体评分
                        if dimension not in dimension_totals:
                            dimension_totals[dimension] = 0
                            dimension_counts[dimension] = 0
                        dimension_totals[dimension] += score
                        dimension_counts[dimension] += 1
            
            dimension_averages = {
                dim: round(dimension_totals[dim] / dimension_counts[dim], 1)
                for dim in dimension_totals
            }
            
            # 计算已验证评价数量
            verified_reviews_count = sum(
                1 for review in reviews 
                if review.get("verification_status") != ReviewVerificationStatus.UNVERIFIED.value
            )
            
            # 计算高有用性评价数量（有用投票数大于3）
            helpful_reviews_count = sum(
                1 for review in reviews 
                if review.get("helpful_votes", 0) > 3
            )
            
            # 获取热门标签（简化实现）
            popular_tags = await self._get_popular_tags_for_entity(target_entity_type, target_entity_id)
            
            # 构建汇总对象
            summary = ReviewSummary(
                target_entity_  
    