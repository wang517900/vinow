内容系统

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel

from app.models.recommendation import (
    RecommendationRequest, RecommendationResponse, 
    SimilarContentRequest, TrendingContentRequest,
    RecommendationFeedback, RecommendationAlgorithm
)
from app.services.recommendation_service import RecommendationService
from app.api.v1.dependencies import (
    GetRecommendationService, GetCurrentActiveUser, RateLimitPerMinute
)
from app.utils.logger import logger

# 创建推荐路由
router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.post("/personalized", response_model=RecommendationResponse)
async def get_personalized_recommendations(
    request: RecommendationRequest,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    recommendation_service: RecommendationService = Depends(GetRecommendationService),
    rate_limit = Depends(RateLimitPerMinute)
):
    """获取个性化推荐内容
    
    根据用户的历史行为、偏好和兴趣生成个性化内容推荐。
    """
    try:
        # 确保请求中的用户ID与当前用户一致
        request.user_id = current_user["id"]
        
        # 获取推荐结果
        recommendations = await recommendation_service.get_personalized_recommendations(request)
        
        logger.info(f"生成个性化推荐成功: {current_user['id']}, 数量: {recommendations.total}")
        return recommendations
        
    except Exception as e:
        logger.error(f"获取个性化推荐失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取推荐内容失败"
        )

@router.get("/trending", response_model=RecommendationResponse)
async def get_trending_recommendations(
    content_type: str = Query(None, description="内容类型"),
    time_window: str = Query("24h", description="时间窗口: 1h, 24h, 7d, 30d"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """获取热门推荐内容
    
    获取当前系统中最受欢迎的内容，基于浏览量、点赞数等指标。
    """
    try:
        # 构建热门内容请求
        trending_request = TrendingContentRequest(
            content_type=content_type,
            time_window=time_window,
            limit=limit
        )
        
        # 获取热门内容
        trending_content = await recommendation_service.get_trending_recommendations(trending_request)
        
        # 构建响应
        response = RecommendationResponse(
            items=trending_content,
            total=len(trending_content),
            algorithm=RecommendationAlgorithm.TRENDING,
            reasoning=f"基于{time_window}时间窗口的热门内容"
        )
        
        logger.info(f"获取热门推荐成功, 数量: {len(trending_content)}")
        return response
        
    except Exception as e:
        logger.error(f"获取热门推荐失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取热门内容失败"
        )

@router.get("/similar/{content_id}", response_model=RecommendationResponse)
async def get_similar_content(
    content_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """获取相似内容推荐
    
    根据指定内容的特征，推荐与其相似的其他内容。
    """
    try:
        # 构建相似内容请求
        similar_request = SimilarContentRequest(
            content_id=UUID(content_id),
            limit=limit
        )
        
        # 获取相似内容
        similar_content = await recommendation_service.get_similar_content(similar_request)
        
        logger.info(f"获取相似内容推荐成功: {content_id}, 数量: {similar_content.total}")
        return similar_content
        
    except Exception as e:
        logger.error(f"获取相似内容推荐失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取相似内容失败"
        )

@router.get("/for-you", response_model=RecommendationResponse)
async def get_for_you_recommendations(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    content_types: List[str] = Query(None, description="内容类型过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    recommendation_service: RecommendationService = Depends(GetRecommendationService),
    rate_limit = Depends(RateLimitPerMinute)
):
    """获取'为你推荐'内容（简化接口）
    
    为当前用户推荐个性化内容的简化接口。
    """
    try:
        # 构建推荐请求
        from app.models.content import ContentType
        
        request_content_types = None
        if content_types:
            request_content_types = [ContentType(ct) for ct in content_types]
        
        request = RecommendationRequest(
            user_id=current_user["id"],
            content_types=request_content_types,
            limit=limit,
            exclude_viewed=True
        )
        
        # 获取推荐结果
        recommendations = await recommendation_service.get_personalized_recommendations(request)
        
        logger.info(f"获取'为你推荐'成功: {current_user['id']}, 数量: {recommendations.total}")
        return recommendations
        
    except Exception as e:
        logger.error(f"获取'为你推荐'失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取推荐内容失败"
        )

@router.get("/discover", response_model=RecommendationResponse)
async def get_discovery_recommendations(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """获取发现推荐（探索新内容）
    
    推荐用户可能感兴趣但尚未接触过的全新内容。
    """
    try:
        # 构建发现推荐请求 - 专门推荐用户没看过但可能感兴趣的内容
        request = RecommendationRequest(
            user_id=current_user["id"],
            limit=limit,
            exclude_viewed=True,
            diversity_factor=0.8  # 增加多样性因子
        )
        
        # 获取推荐结果
        recommendations = await recommendation_service.get_personalized_recommendations(request)
        
        logger.info(f"获取发现推荐成功: {current_user['id']}, 数量: {recommendations.total}")
        return recommendations
        
    except Exception as e:
        logger.error(f"获取发现推荐失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取发现内容失败"
        )

@router.post("/feedback")
async def submit_recommendation_feedback(
    feedback: RecommendationFeedback,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """提交推荐反馈
    
    用户对推荐内容的反馈，用于优化推荐算法。
    """
    try:
        # 添加用户ID到反馈数据
        feedback.user_id = current_user["id"]
        
        # 记录反馈
        await recommendation_service.record_feedback(feedback)
        
        logger.info(f"推荐反馈记录成功: 用户 {current_user['id']}, 内容 {feedback.content_id}, 评分 {feedback.rating}")
        return {"message": "反馈记录成功"}
        
    except Exception as e:
        logger.error(f"记录推荐反馈失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="记录反馈失败"
        )

@router.get("/history")
async def get_recommendation_history(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """获取推荐历史
    
    获取用户收到的推荐内容历史记录。
    """
    try:
        history = await recommendation_service.get_recommendation_history(
            user_id=current_user["id"],
            page=page,
            size=size
        )
        
        logger.info(f"获取推荐历史成功: 用户 {current_user['id']}, 数量 {len(history.items)}")
        return history
        
    except Exception as e:
        logger.error(f"获取推荐历史失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取推荐历史失败"
        )

@router.delete("/history/{content_id}")
async def remove_from_recommendation_history(
    content_id: str,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """从推荐历史中移除内容
    
    用户可以选择将某些内容从推荐历史中移除，避免重复推荐。
    """
    try:
        await recommendation_service.remove_from_history(
            user_id=current_user["id"],
            content_id=content_id
        )
        
        logger.info(f"从推荐历史移除内容成功: 用户 {current_user['id']}, 内容 {content_id}")
        return {"message": "内容已从推荐历史中移除"}
        
    except Exception as e:
        logger.error(f"从推荐历史移除内容失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除内容失败"
        )

@router.get("/algorithms")
async def get_available_algorithms():
    """获取可用的推荐算法列表
    
    返回系统支持的所有推荐算法及其描述。
    """
    try:
        algorithms = [
            {
                "name": "collaborative_filtering",
                "description": "协同过滤推荐算法",
                "type": "个性化推荐"
            },
            {
                "name": "content_based",
                "description": "基于内容的推荐算法",
                "type": "个性化推荐"
            },
            {
                "name": "trending",
                "description": "热门内容推荐算法",
                "type": "热门推荐"
            },
            {
                "name": "hybrid",
                "description": "混合推荐算法",
                "type": "综合推荐"
            }
        ]
        
        return {"algorithms": algorithms}
        
    except Exception as e:
        logger.error(f"获取推荐算法列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取算法列表失败"
        )

@router.get("/explain/{content_id}")
async def explain_recommendation(
    content_id: str,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """解释推荐理由
    
    解释为什么某个内容被推荐给用户。
    """
    try:
        explanation = await recommendation_service.explain_recommendation(
            user_id=current_user["id"],
            content_id=content_id
        )
        
        return explanation
        
    except Exception as e:
        logger.error(f"获取推荐解释失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取推荐解释失败"
        )

@router.post("/refresh")
async def refresh_recommendations(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    recommendation_service: RecommendationService = Depends(GetRecommendationService)
):
    """刷新推荐内容
    
    强制刷新用户的推荐内容，重新计算推荐结果。
    """
    try:
        await recommendation_service.refresh_user_recommendations(current_user["id"])
        
        logger.info(f"推荐内容刷新成功: 用户 {current_user['id']}")
        return {"message": "推荐内容已刷新"}
        
    except Exception as e:
        logger.error(f"刷新推荐内容失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新推荐内容失败"
        )