内容系统
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from pydantic import BaseModel

from app.models.content import (
    ContentCreate, ContentUpdate, ContentResponse, ContentListResponse,
    ContentInteractionCreate, ContentSearchQuery, ContentType
)
from app.services.content_service import ContentService
from app.api.v1.dependencies import (
    GetContentService, GetCurrentActiveUser, RateLimitPerMinute
)
from app.utils.logger import logger

# 创建内容路由
router = APIRouter(prefix="/content", tags=["content"])

@router.post("", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    content_data: ContentCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService),
    rate_limit = Depends(RateLimitPerMinute)
):
    """创建内容
    
    创建新的内容条目，包括文章、视频、图片等不同类型的内容。
    """
    try:
        # 设置创建者ID
        content_data.creator_id = current_user["id"]
        
        # 创建内容
        content = await content_service.create_content(content_data)
        
        # 后台处理任务（如生成缩略图、内容分析等）
        background_tasks.add_task(process_content_after_creation, content["id"])
        
        # 返回内容响应
        content_response = ContentResponse(**content)
        return content_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建内容失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建内容失败: {str(e)}"
        )

@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService)
):
    """获取内容详情
    
    根据内容ID获取内容的详细信息，包括统计数据和创作者信息。
    """
    try:
        user_id = str(current_user["id"]) if current_user else None
        content = await content_service.get_content_by_id(content_id)
        content_response = ContentResponse(**content)
        return content_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取内容失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="内容不存在"
        )

@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: str,
    update_data: ContentUpdate,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService)
):
    """更新内容
    
    更新已有内容的信息，只有内容创建者才能更新内容。
    """
    try:
        user_id = str(current_user["id"])
        updated_content = await content_service.update_content(content_id, update_data, user_id)
        
        content_response = ContentResponse(**updated_content)
        return content_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新内容失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新内容失败"
        )

@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService)
):
    """删除内容
    
    删除指定内容，这是一个软删除操作，只会标记内容为已删除状态。
    """
    try:
        user_id = str(current_user["id"])
        await content_service.delete_content(content_id, user_id)
        
        return {"message": "内容删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除内容失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="删除内容失败"
        )

@router.post("/{content_id}/interactions", status_code=status.HTTP_201_CREATED)
async def record_interaction(
    content_id: str,
    interaction_data: ContentInteractionCreate,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService),
    rate_limit = Depends(RateLimitPerMinute)
):
    """记录内容互动
    
    记录用户对内容的各种互动行为，如点赞、分享、评论等。
    """
    try:
        user_id = str(current_user["id"])
        interaction_data.content_id = content_id
        
        interaction = await content_service.record_interaction(interaction_data, user_id)
        
        return {
            "message": "互动记录成功",
            "interaction_id": interaction["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记录互动失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="记录互动失败"
        )

@router.get("", response_model=ContentListResponse)
async def search_content(
    query: str = Query(None, description="搜索关键词"),
    content_type: ContentType = Query(None, description="内容类型"),
    tags: List[str] = Query(None, description="标签过滤"),
    creator_id: str = Query(None, description="创作者ID"),
    min_quality_score: float = Query(None, description="最低质量分数"),
    date_from: str = Query(None, description="起始日期 (YYYY-MM-DD)"),
    date_to: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 (asc/desc)"),
    content_service: ContentService = Depends(GetContentService)
):
    """搜索内容
    
    根据多种条件搜索和过滤内容，支持全文搜索、类型过滤、标签过滤等。
    """
    try:
        # 构建搜索查询
        search_query = ContentSearchQuery(
            query=query,
            content_type=content_type,
            tags=tags,
            creator_id=creator_id,
            min_quality_score=min_quality_score,
            date_from=date_from,
            date_to=date_to,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 执行搜索
        result = await content_service.search_content(search_query)
        
        return ContentListResponse(**result)
        
    except Exception as e:
        logger.error(f"搜索内容失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索内容失败"
        )

@router.get("/user/{user_id}", response_model=ContentListResponse)
async def get_user_content(
    user_id: str,
    status_filter: str = Query(None, description="内容状态过滤 (draft/approved/deleted)"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    content_service: ContentService = Depends(GetContentService)
):
    """获取用户的内容列表
    
    获取指定用户创建的所有内容列表。
    """
    try:
        result = await content_service.get_user_content(user_id, page, size)
        return ContentListResponse(**result)
        
    except Exception as e:
        logger.error(f"获取用户内容失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取用户内容失败"
        )

@router.get("/types/{content_type}", response_model=ContentListResponse)
async def get_content_by_type(
    content_type: ContentType,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    content_service: ContentService = Depends(GetContentService)
):
    """按类型获取内容
    
    根据内容类型获取相关内容列表。
    """
    try:
        search_query = ContentSearchQuery(
            content_type=content_type,
            page=page,
            size=size
        )
        
        result = await content_service.search_content(search_query)
        return ContentListResponse(**result)
        
    except Exception as e:
        logger.error(f"按类型获取内容失败 {content_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取内容失败"
        )

@router.get("/trending", response_model=ContentListResponse)
async def get_trending_content(
    limit: int = Query(10, ge=1, le=100, description="返回内容数量"),
    content_service: ContentService = Depends(GetContentService)
):
    """获取热门内容
    
    获取当前最热门的内容列表，基于浏览量、点赞数等指标排序。
    """
    try:
        trending_contents = await content_service.get_trending_content(limit)
        
        # 构造符合ContentListResponse格式的响应
        result = {
            "items": trending_contents,
            "total": len(trending_contents),
            "page": 1,
            "size": limit,
            "pages": 1
        }
        
        return ContentListResponse(**result)
        
    except Exception as e:
        logger.error(f"获取热门内容失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取热门内容失败"
        )

@router.get("/{content_id}/statistics")
async def get_content_statistics(
    content_id: str,
    content_service: ContentService = Depends(GetContentService)
):
    """获取内容统计信息
    
    获取指定内容的详细统计信息，包括浏览量、点赞数、分享数等。
    """
    try:
        statistics = await content_service.get_content_statistics(content_id)
        return statistics
        
    except Exception as e:
        logger.error(f"获取内容统计失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取内容统计失败"
        )

@router.post("/{content_id}/report")
async def report_content(
    content_id: str,
    reason: str = Query(..., description="举报原因"),
    details: str = Query(None, description="详细说明"),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService)
):
    """举报内容
    
    用户举报不当内容，系统将记录举报信息并触发审核流程。
    """
    try:
        user_id = str(current_user["id"])
        
        # 创建举报互动记录
        interaction_data = ContentInteractionCreate(
            content_id=content_id,
            interaction_type="report",
            interaction_data={
                "reason": reason,
                "details": details
            }
        )
        
        interaction = await content_service.record_interaction(interaction_data, user_id)
        
        # 触发内容重新审核
        # 这里可以调用审核服务的重新审核方法
        
        return {
            "message": "举报成功，我们将尽快处理",
            "interaction_id": interaction["id"]
        }
        
    except Exception as e:
        logger.error(f"举报内容失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="举报内容失败"
        )

@router.get("/recommendations", response_model=ContentListResponse)
async def get_recommendations(
    user_id: str = Query(None, description="用户ID，为空则使用当前用户"),
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    current_user: Optional[Dict[str, Any]] = Depends(GetCurrentActiveUser),
    content_service: ContentService = Depends(GetContentService)
):
    """获取推荐内容
    
    根据用户兴趣和行为推荐相关内容。
    """
    try:
        # 如果没有提供user_id，则使用当前用户ID
        effective_user_id = user_id or (str(current_user["id"]) if current_user else None)
        
        # 这里应该实现推荐算法，暂时返回热门内容
        trending_contents = await content_service.get_trending_content(limit)
        
        # 构造符合ContentListResponse格式的响应
        result = {
            "items": trending_contents,
            "total": len(trending_contents),
            "page": 1,
            "size": limit,
            "pages": 1
        }
        
        return ContentListResponse(**result)
        
    except Exception as e:
        logger.error(f"获取推荐内容失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取推荐内容失败"
        )

# 后台任务函数
async def process_content_after_creation(content_id: str):
    """内容创建后的后台处理
    
    内容创建完成后执行的后台任务，包括质量评分、缩略图生成等。
    
    Args:
        content_id: 内容ID
    """
    try:
        # 在实际应用中，这里可以执行各种后台处理任务
        # 如：生成缩略图、内容分析、质量评分计算等
        
        logger.info(f"开始后台处理内容: {content_id}")
        
        # 模拟处理延迟
        import asyncio
        await asyncio.sleep(5)
        
        logger.info(f"内容后台处理完成: {content_id}")
        
    except Exception as e:
        logger.error(f"内容后台处理失败 {content_id}: {str(e)}")