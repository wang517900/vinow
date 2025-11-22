商家系统7评价管理
"""
评价相关API路由模块

本模块定义了商户评价相关的RESTful API接口，包括：
- 获取评价列表及筛选
- 获取评价统计概览
- 创建评价回复
- 获取回复模板推荐
- 更新评价状态
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from app.services.review_service import ReviewService
from app.services.reply_template_service import ReplyTemplateService
from app.schemas.review import ReviewListResponse, ReviewSummaryResponse
from app.schemas.reply import ReplyCreate, ReplyResponse

# 创建API路由实例，设置路径前缀和标签
router = APIRouter(prefix="/api/v1/merchants/{merchant_id}/reviews", tags=["reviews"])

# 初始化服务层实例
review_service = ReviewService()          # 评价业务服务
template_service = ReplyTemplateService() # 回复模板服务

@router.get("/", response_model=ReviewListResponse)
async def get_reviews(
    merchant_id: int = Path(..., description="商家ID"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="评分过滤"),
    date_range: Optional[str] = Query(None, description="时间范围: today/week/month"),
    has_reply: Optional[bool] = Query(None, description="是否已回复")
):
    """
    获取商户评价列表
    
    支持多种筛选条件和分页功能
    
    Args:
        merchant_id (int): 商户ID，路径参数
        page (int): 页码，默认为1，最小值为1
        limit (int): 每页数量，默认为20，范围1-100
        rating (Optional[int]): 评分过滤条件，范围1-5星
        date_range (Optional[str]): 时间范围过滤，可选值: today/week/month
        has_reply (Optional[bool]): 是否已回复过滤条件
        
    Returns:
        ReviewListResponse: 包含评价列表和分页信息的响应数据
        
    Raises:
        HTTPException: 当获取评价列表失败时抛出500错误
    """
    try:
        # 调用服务层获取评价列表
        result = await review_service.get_review_list(
            merchant_id=merchant_id,
            page=page,
            limit=limit,
            rating=rating,
            date_range=date_range,
            has_reply=has_reply
        )
        
        # 使用响应模型创建标准化响应
        return ReviewListResponse.create_response(
            reviews=result["reviews"],
            total=result["total"],
            page=result["page"],
            limit=result["limit"]
        )
    except Exception as e:
        # 捕获异常并抛出自定义HTTP异常
        raise HTTPException(status_code=500, detail=f"获取评价列表失败: {str(e)}")

@router.get("/summary", response_model=ReviewSummaryResponse)
async def get_review_summary(merchant_id: int = Path(..., description="商家ID")):
    """
    获取商户评价统计概览
    
    返回商户的关键评价统计数据
    
    Args:
        merchant_id (int): 商户ID，路径参数
        
    Returns:
        ReviewSummaryResponse: 包含评价统计数据的响应数据
        
    Raises:
        HTTPException: 当获取评价概览失败时抛出500错误
    """
    try:
        # 调用服务层获取评价统计摘要
        summary_data = await review_service.get_review_summary(merchant_id)
        
        # 使用响应模型包装数据
        return ReviewSummaryResponse(data=summary_data)
    except Exception as e:
        # 捕获异常并抛出自定义HTTP异常
        raise HTTPException(status_code=500, detail=f"获取评价概览失败: {str(e)}")

@router.post("/{review_id}/reply", response_model=ReplyResponse)
async def create_review_reply(
    merchant_id: int = Path(..., description="商家ID"),
    review_id: int = Path(..., description="评价ID"),
    reply_data: ReplyCreate = ...
):
    """
    为指定评价创建回复
    
    Args:
        merchant_id (int): 商户ID，路径参数
        review_id (int): 评价ID，路径参数
        reply_data (ReplyCreate): 回复创建数据，请求体参数
        
    Returns:
        ReplyResponse: 创建成功的回复数据
        
    Raises:
        HTTPException: 当参数错误时抛出400错误，当服务器错误时抛出500错误
    """
    try:
        # 调用服务层创建评价回复
        result = await review_service.create_review_reply(
            merchant_id=merchant_id,
            review_id=review_id,
            reply_data=reply_data
        )
        
        # 使用响应模型包装数据
        return ReplyResponse(data=result)
    except ValueError as e:
        # 处理业务逻辑错误（如评价不存在、重复回复等）
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 处理服务器错误
        raise HTTPException(status_code=500, detail=f"创建回复失败: {str(e)}")

@router.get("/{review_id}/templates")
async def get_reply_templates(
    merchant_id: int = Path(..., description="商家ID"),
    review_id: int = Path(..., description="评价ID")
):
    """
    获取评价回复模板推荐
    
    根据评价的评分和其他因素推荐合适的回复模板
    
    Args:
        merchant_id (int): 商户ID，路径参数
        review_id (int): 评价ID，路径参数
        
    Returns:
        dict: 包含评分相关模板和常用模板的响应数据
        
    Raises:
        HTTPException: 当评价不存在时抛出404错误，当获取模板失败时抛出500错误
    """
    try:
        # 获取评价信息以确定评分
        review_result = review_service.review_crud.db.table("merchant_reviews").select("rating").eq("id", review_id).execute()
        if not review_result.data:
            # 如果评价不存在，抛出404错误
            raise HTTPException(status_code=404, detail="评价不存在")
        
        # 获取评价评分
        rating = review_result.data[0]["rating"]
        
        # 根据评分获取推荐模板
        templates = await template_service.get_templates_by_rating(rating)
        
        # 获取商户常用回复模板
        frequent_templates = await template_service.get_frequently_used(merchant_id)
        
        # 返回包含不同类型模板的响应数据
        return {
            "success": True,
            "data": {
                "rating_based": templates,      # 基于评分的推荐模板
                "frequently_used": frequent_templates  # 商户常用模板
            }
        }
    except HTTPException:
        # 重新抛出已有的HTTP异常（如404）
        raise
    except Exception as e:
        # 处理其他服务器错误
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")

@router.put("/{review_id}/status")
async def update_review_status(
    merchant_id: int = Path(..., description="商家ID"),
    review_id: int = Path(..., description="评价ID"),
    status: str = Query(..., description="状态: active/hidden/deleted")
):
    """
    更新评价状态
    
    允许商户更新评价的显示状态
    
    Args:
        merchant_id (int): 商户ID，路径参数
        review_id (int): 评价ID，路径参数
        status (str): 新的状态值，查询参数，可选值: active/hidden/deleted
        
    Returns:
        dict: 状态更新结果信息
        
    Raises:
        HTTPException: 当状态值无效时抛出400错误，当更新失败时抛出500错误
    """
    try:
        # 调用服务层更新评价状态
        success = await review_service.update_review_status(review_id, merchant_id, status)
        if not success:
            # 如果更新失败，抛出400错误
            raise HTTPException(status_code=400, detail="状态更新失败")
        
        # 返回成功响应
        return {"success": True, "message": "状态更新成功"}
    except ValueError as e:
        # 处理状态值无效等业务逻辑错误
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 处理服务器错误
        raise HTTPException(status_code=500, detail=f"状态更新失败: {str(e)}")

        内容系统
from typing import List, Optional, Dict, Any  # 导入类型注解
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request  # 导入FastAPI相关依赖
from sqlalchemy.orm import Session  # 导入数据库会话
from app.schemas.review_schemas import (  # 导入评价相关的数据模式
    ReviewCreateSchema, 
    ReviewUpdateSchema, 
    ReviewResponseSchema,
    BusinessReplyCreateSchema,
    ReviewHelpfulVoteCreateSchema,
    ReviewSummarySchema
)
from app.schemas.response_schemas import (  # 导入响应模式
    StandardResponse, 
    PaginatedResponse, 
    create_success_response,
    create_error_response
)
from app.services.review_service import review_service  # 导入评价服务
from app.utils.pagination import PaginationParams, get_pagination_params  # 导入分页工具
from app.utils.security import get_current_user, get_current_user_optional  # 导入安全工具
from app.models.content_models import ContentStatus  # 导入内容模型
import logging  # 导入日志模块

# 创建评价路由的APIRouter实例
router = APIRouter(prefix="/reviews", tags=["reviews"])

# 获取日志记录器
logger = logging.getLogger(__name__)

@router.post("/", response_model=StandardResponse[ReviewResponseSchema], status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreateSchema,  # 评价创建数据
    background_tasks: BackgroundTasks,  # 后台任务管理器
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    创建新评价
    
    Args:
        review_data: 评价创建数据
        background_tasks: 后台任务管理器
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        创建的评价响应
    """
    try:
        # 从当前用户信息中提取用户ID、姓名和头像
        user_id = current_user.get("user_id")
        user_name = current_user.get("name")
        user_avatar = current_user.get("avatar_url")
        
        # 调用评价服务创建评价
        created_review = await review_service.create_review(
            review_data=review_data,
            user_id=user_id,
            user_name=user_name,
            user_avatar=user_avatar,
            background_tasks=background_tasks
        )
        
        # 记录成功日志
        logger.info(f"评价创建成功: {created_review.id}, 目标实体: {review_data.target_entity_type}:{review_data.target_entity_id}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=created_review,
            message="评价创建成功",
            status_code=status.HTTP_201_CREATED
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"创建评价异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="评价创建失败，请稍后重试"
        )

@router.get("/{review_id}", response_model=StandardResponse[ReviewResponseSchema])
async def get_review(
    review_id: str,  # 评价ID路径参数
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),  # 可选当前用户
    request: Request = None  # 请求对象
):
    """
    根据ID获取评价详情
    
    Args:
        review_id: 评价ID
        current_user: 当前用户信息（可选）
        request: HTTP请求对象
        
    Returns:
        评价详情响应
    """
    try:
        # 从当前用户信息中提取用户ID（如果用户已登录）
        user_id = current_user.get("user_id") if current_user else None
        
        # 调用评价服务获取评价详情
        review = await review_service.get_review(review_id, user_id)
        
        # 检查评价是否存在
        if not review:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="评价不存在"
            )
        
        # 返回成功响应
        return create_success_response(
            data=review,
            message="获取评价成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"获取评价异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取评价失败，请稍后重试"
        )

@router.put("/{review_id}", response_model=StandardResponse[ReviewResponseSchema])
async def update_review(
    review_id: str,  # 评价ID路径参数
    update_data: ReviewUpdateSchema,  # 评价更新数据
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    更新评价信息
    
    Args:
        review_id: 评价ID
        update_data: 评价更新数据
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        更新后的评价响应
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用评价服务更新评价
        updated_review = await review_service.update_review(
            review_id=review_id,
            update_data=update_data,
            user_id=user_id
        )
        
        # 检查评价是否成功更新
        if not updated_review:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="评价不存在或更新失败"
            )
        
        # 记录成功日志
        logger.info(f"评价更新成功: {review_id}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=updated_review,
            message="评价更新成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"更新评价异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="评价更新失败，请稍后重试"
        )

@router.delete("/{review_id}", response_model=StandardResponse[bool])
async def delete_review(
    review_id: str,  # 评价ID路径参数
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    删除评价（软删除）
    
    Args:
        review_id: 评价ID
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        删除操作结果
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用评价服务删除评价
        success = await review_service.delete_review(review_id, user_id)
        
        # 检查删除是否成功
        if not success:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="评价不存在或删除失败"
            )
        
        # 记录成功日志
        logger.info(f"评价删除成功: {review_id}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=True,
            message="评价删除成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"删除评价异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="评价删除失败，请稍后重试"
        )

@router.get("/", response_model=PaginatedResponse[ReviewResponseSchema])
async def list_reviews(
    target_entity_type: Optional[str] = Query(None, description="目标实体类型过滤"),  # 目标实体类型查询参数
    target_entity_id: Optional[str] = Query(None, description="目标实体ID过滤"),  # 目标实体ID查询参数
    author_id: Optional[str] = Query(None, description="作者ID过滤"),  # 作者ID查询参数
    status: Optional[ContentStatus] = Query(None, description="评价状态过滤"),  # 评价状态查询参数
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="最低评分过滤"),  # 最低评分查询参数
    max_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="最高评分过滤"),  # 最高评分查询参数
    has_media: Optional[bool] = Query(None, description="是否有媒体文件过滤"),  # 媒体文件查询参数
    is_verified: Optional[bool] = Query(None, description="是否已验证过滤"),  # 验证状态查询参数
    pagination: PaginationParams = Depends(get_pagination_params),  # 分页参数依赖注入
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),  # 可选当前用户
    request: Request = None  # 请求对象
):
    """
    获取评价列表（支持多种过滤条件和分页）
    
    Args:
        target_entity_type: 目标实体类型过滤
        target_entity_id: 目标实体ID过滤
        author_id: 作者ID过滤
        status: 评价状态过滤
        min_rating: 最低评分过滤
        max_rating: 最高评分过滤
        has_media: 是否有媒体文件过滤
        is_verified: 是否已验证过滤
        pagination: 分页参数
        current_user: 当前用户信息（可选）
        request: HTTP请求对象
        
    Returns:
        分页的评价列表响应
    """
    try:
        # 从当前用户信息中提取用户ID（如果用户已登录）
        user_id = current_user.get("user_id") if current_user else None
        
        # 调用评价服务获取评价列表
        result = await review_service.list_reviews(
            pagination=pagination,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            author_id=author_id,
            status=status,
            min_rating=min_rating,
            max_rating=max_rating,
            has_media=has_media,
            is_verified=is_verified,
            user_id=user_id
        )
        
        # 返回成功响应
        return create_success_response(
            data=result,
            message="获取评价列表成功"
        )
        
    except Exception as e:
        # 记录错误日志
        logger.error(f"获取评价列表异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取评价列表失败，请稍后重试"
        )

@router.post("/{review_id}/business-reply", response_model=StandardResponse[bool])
async def add_business_reply(
    review_id: str,  # 评价ID路径参数
    reply_data: BusinessReplyCreateSchema,  # 商家回复数据
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    添加商家回复
    
    Args:
        review_id: 评价ID
        reply_data: 商家回复数据
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        回复操作结果
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用评价服务添加商家回复
        success = await review_service.add_business_reply(
            review_id=review_id,
            reply_data=reply_data,
            user_id=user_id
        )
        
        # 检查回复是否成功添加
        if not success:
            # 返回400错误
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商家回复添加失败"
            )
        
        # 记录成功日志
        logger.info(f"商家回复添加成功: {review_id}, 商家用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=True,
            message="商家回复添加成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"添加商家回复异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="商家回复添加失败，请稍后重试"
        )

@router.post("/{review_id}/helpful-votes", response_model=StandardResponse[bool])
async def add_helpful_vote(
    review_id: str,  # 评价ID路径参数
    vote_data: ReviewHelpfulVoteCreateSchema,  # 有用性投票数据
    current_user: Dict[str, Any] = Depends(get_current_user),  # 当前用户依赖注入
    request: Request = None  # 请求对象
):
    """
    添加有用性投票
    
    Args:
        review_id: 评价ID
        vote_data: 有用性投票数据
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        投票操作结果
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 从请求中获取客户端IP地址
        client_ip = request.client.host if request else None
        
        # 调用评价服务添加有用性投票
        success = await review_service.add_helpful_vote(
            review_id=review_id,
            vote_data=vote_data,
            user_id=user_id,
            ip_address=client_ip
        )
        
        # 检查投票是否成功添加
        if not success:
            # 返回400错误
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="有用性投票添加失败"
            )
        
        # 记录成功日志
        logger.info(f"有用性投票添加成功: {review_id}, 用户: {user_id}, 有用: {vote_data.is_helpful}")
        
        # 返回成功响应
        return create_success_response(
            data=True,
            message="有用性投票添加成功"
        )
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误日志
        logger.error(f"添加有用性投票异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="有用性投票添加失败，请稍后重试"
        )

@router.get("/summary/{target_entity_type}/{target_entity_id}", response_model=StandardResponse[ReviewSummarySchema])
async def get_review_summary(
    target_entity_type: str,  # 目标实体类型路径参数
    target_entity_id: str,  # 目标实体ID路径参数
    request: Request = None  # 请求对象
):
    """
    获取评价汇总信息
    
    Args:
        target_entity_type: 目标实体类型
        target_entity_id: 目标实体ID
        request: HTTP请求对象
        
    Returns:
        评价汇总信息响应
    """
    try:
        # 调用评价服务获取评价汇总信息
        summary = await review_service.get_review_summary(target_entity_type, target_entity_id)
        
        # 返回成功响应
        return create_success_response(
            data=summary,
            message="获取评价汇总信息成功"
        )
        
    except Exception as e:
        # 记录错误日志
        logger.error(f"获取评价汇总信息异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取评价汇总信息失败，请稍后重试"
        )    