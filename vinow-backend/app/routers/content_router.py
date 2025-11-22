内容系统
"""
内容管理路由模块

本模块实现了内容管理系统的RESTful API接口，包括：
1. 内容的创建、查询、更新、删除
2. 内容互动功能（点赞、收藏、分享等）
3. 内容列表和搜索
4. 内容统计和分析
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.schemas.content_schemas import (
    ContentCreateSchema, 
    ContentUpdateSchema, 
    ContentResponseSchema,
    ContentListResponseSchema
)
from app.schemas.response_schemas import (
    StandardResponse, 
    PaginatedResponse, 
    create_success_response,
    create_error_response
)
from app.services.content_service import content_service
from app.services.storage_service import storage_service
from app.utils.pagination import PaginationParams, get_pagination_params
from app.utils.security import get_current_user, get_current_user_optional
from app.models.content_models import ContentType, ContentStatus
import logging

# 创建内容路由的APIRouter实例
router = APIRouter(prefix="/contents", tags=["contents"])

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = ['router']


@router.post("/", response_model=StandardResponse[ContentResponseSchema], status_code=status.HTTP_201_CREATED)
async def create_content(
    content_data: ContentCreateSchema,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    创建新内容 - 支持多种内容类型（评价、视频、图文等）
    
    Args:
        content_data: 内容创建数据
        background_tasks: 后台任务管理器
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        创建的内容响应
        
    Raises:
        HTTPException: 创建失败时抛出相应错误
    """
    try:
        # 从当前用户信息中提取用户ID、姓名和头像
        user_id = current_user.get("user_id")
        user_name = current_user.get("name")
        user_avatar = current_user.get("avatar_url")
        
        # 调用内容服务创建内容
        created_content = await content_service.create_content(
            content_data=content_data,
            user_id=user_id,
            user_name=user_name,
            user_avatar=user_avatar,
            background_tasks=background_tasks
        )
        
        # 记录成功日志
        logger.info(f"内容创建成功: {created_content.id}, 类型: {content_data.content_type}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=created_content,
            message="内容创建成功",
            status_code=status.HTTP_201_CREATED
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"创建内容异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内容创建失败，请稍后重试"
        )


@router.get("/{content_id}", response_model=StandardResponse[ContentResponseSchema])
async def get_content(
    content_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    根据ID获取内容详情
    
    Args:
        content_id: 内容ID
        current_user: 当前用户信息（可选）
        request: HTTP请求对象
        
    Returns:
        内容详情响应
        
    Raises:
        HTTPException: 内容不存在或获取失败时抛出相应错误
    """
    try:
        # 从当前用户信息中提取用户ID（如果用户已登录）
        user_id = current_user.get("user_id") if current_user else None
        
        # 调用内容服务获取内容详情
        content = await content_service.get_content(content_id, user_id)
        
        # 检查内容是否存在
        if not content:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 返回成功响应
        return create_success_response(
            data=content,
            message="获取内容成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"获取内容异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取内容失败，请稍后重试"
        )


@router.put("/{content_id}", response_model=StandardResponse[ContentResponseSchema])
async def update_content(
    content_id: str,
    update_data: ContentUpdateSchema,
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    更新内容信息
    
    Args:
        content_id: 内容ID
        update_data: 内容更新数据
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        更新后的内容响应
        
    Raises:
        HTTPException: 内容不存在、无权限或更新失败时抛出相应错误
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用内容服务更新内容
        updated_content = await content_service.update_content(
            content_id=content_id,
            update_data=update_data,
            user_id=user_id
        )
        
        # 检查内容是否成功更新
        if not updated_content:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在或更新失败"
            )
        
        # 记录成功日志
        logger.info(f"内容更新成功: {content_id}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=updated_content,
            message="内容更新成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"更新内容异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内容更新失败，请稍后重试"
        )


@router.delete("/{content_id}", response_model=StandardResponse[bool])
async def delete_content(
    content_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    删除内容（软删除）
    
    Args:
        content_id: 内容ID
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        删除操作结果
        
    Raises:
        HTTPException: 内容不存在、无权限或删除失败时抛出相应错误
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 调用内容服务删除内容
        success = await content_service.delete_content(content_id, user_id)
        
        # 检查删除是否成功
        if not success:
            # 返回404错误
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在或删除失败"
            )
        
        # 记录成功日志
        logger.info(f"内容删除成功: {content_id}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=True,
            message="内容删除成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"删除内容异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="内容删除失败，请稍后重试"
        )


@router.get("/", response_model=PaginatedResponse[ContentResponseSchema])
async def list_contents(
    content_type: Optional[ContentType] = Query(None, description="内容类型过滤"),
    author_id: Optional[str] = Query(None, description="作者ID过滤"),
    target_entity_type: Optional[str] = Query(None, description="目标实体类型过滤"),
    target_entity_id: Optional[str] = Query(None, description="目标实体ID过滤"),
    status: Optional[ContentStatus] = Query(None, description="内容状态过滤"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    categories: Optional[List[str]] = Query(None, description="分类过滤"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    获取内容列表（支持多种过滤条件和分页）
    
    Args:
        content_type: 内容类型过滤
        author_id: 作者ID过滤
        target_entity_type: 目标实体类型过滤
        target_entity_id: 目标实体ID过滤
        status: 内容状态过滤
        tags: 标签过滤
        categories: 分类过滤
        pagination: 分页参数
        current_user: 当前用户信息（可选）
        request: HTTP请求对象
        
    Returns:
        分页的内容列表响应
        
    Raises:
        HTTPException: 获取列表失败时抛出相应错误
    """
    try:
        # 从当前用户信息中提取用户ID（如果用户已登录）
        user_id = current_user.get("user_id") if current_user else None
        
        # 调用内容服务获取内容列表
        result = await content_service.list_contents(
            pagination=pagination,
            content_type=content_type,
            author_id=author_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            status=status,
            tags=tags,
            categories=categories,
            user_id=user_id
        )
        
        # 返回成功响应
        return create_success_response(
            data=result,
            message="获取内容列表成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"获取内容列表异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取内容列表失败，请稍后重试"
        )


@router.post("/{content_id}/interactions", response_model=StandardResponse[bool])
async def add_content_interaction(
    content_id: str,
    interaction_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    添加内容互动（点赞、收藏、分享等）
    
    Args:
        content_id: 内容ID
        interaction_data: 互动数据
        current_user: 当前用户信息
        request: HTTP请求对象
        
    Returns:
        互动操作结果
        
    Raises:
        HTTPException: 互动添加失败时抛出相应错误
    """
    try:
        # 从当前用户信息中提取用户ID
        user_id = current_user.get("user_id")
        
        # 从请求中获取客户端IP地址和用户代理
        client_ip = request.client.host if request else None
        user_agent = request.headers.get("user-agent") if request else None
        
        # 调用内容服务添加互动
        success = await content_service.add_interaction(
            content_id=content_id,
            interaction_data=interaction_data,
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # 检查互动是否成功添加
        if not success:
            # 返回400错误
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="互动添加失败"
            )
        
        # 记录成功日志
        logger.info(f"内容互动添加成功: {content_id}, 类型: {interaction_data.get('interaction_type')}, 用户: {user_id}")
        
        # 返回成功响应
        return create_success_response(
            data=True,
            message="互动添加成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"添加内容互动异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="互动添加失败，请稍后重试"
        )


@router.get("/{content_id}/interactions", response_model=StandardResponse[List[Dict[str, Any]]])
async def get_content_interactions(
    content_id: str,
    interaction_type: Optional[str] = Query(None, description="互动类型过滤"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    request: Request = None
):
    """
    获取内容的互动列表
    
    Args:
        content_id: 内容ID
        interaction_type: 互动类型过滤
        current_user: 当前用户信息（可选）
        request: HTTP请求对象
        
    Returns:
        互动列表响应
        
    Raises:
        HTTPException: 获取互动列表失败时抛出相应错误
    """
    try:
        # 调用内容服务获取互动列表
        interactions = await content_service.get_interactions(
            content_id=content_id,
            interaction_type=interaction_type
        )
        
        # 返回成功响应
        return create_success_response(
            data=interactions,
            message="获取互动列表成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        logger.error(f"获取内容互动列表异常: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取互动列表失败，请稍后重试"
        )


@router.get("/health", response_model=StandardResponse[bool])
async def health_check():
    """
    内容服务健康检查
    
    Returns:
        服务健康状态
    """
    return create_success_response(
        data=True,
        message="内容服务运行正常"
    )