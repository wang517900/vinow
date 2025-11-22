商家系统7评价管理
"""
评价统计分析相关API路由模块

本模块定义了商户评价统计分析相关的RESTful API接口，包括：
- 获取评分趋势分析数据
- 获取与周边商家的对比数据
- 刷新统计缓存
"""

from fastapi import APIRouter, HTTPException, Path, Query
from app.services.analytics_service import ReviewAnalyticsService

# 创建API路由实例，设置路径前缀和标签
router = APIRouter(prefix="/api/v1/merchants/{merchant_id}/statistics", tags=["statistics"])

# 初始化统计分析服务实例
analytics_service = ReviewAnalyticsService()

@router.get("/trend")
async def get_trend_analysis(
    merchant_id: int = Path(..., description="商家ID"),
    days: int = Query(7, ge=1, le=30, description="天数")
):
    """
    获取评分趋势分析数据
    
    返回指定天数内商户评价的各项指标趋势数据
    
    Args:
        merchant_id (int): 商户ID，路径参数
        days (int): 分析天数，默认7天，范围1-30天，查询参数
        
    Returns:
        dict: 包含趋势分析数据的响应
        
    Raises:
        HTTPException: 当获取趋势分析失败时抛出500错误
    """
    try:
        # 调用统计分析服务获取趋势分析数据
        trend_data = await analytics_service.get_trend_analysis(merchant_id, days)
        
        # 返回成功响应，包含趋势数据
        return {
            "success": True,
            "data": trend_data
        }
    except Exception as e:
        # 捕获异常并抛出自定义HTTP异常
        raise HTTPException(status_code=500, detail=f"获取趋势分析失败: {str(e)}")

@router.get("/comparison")
async def get_comparison_data(merchant_id: int = Path(..., description="商家ID")):
    """
    获取与周边商家的对比数据
    
    返回当前商户与同行业或同区域商家的评价数据对比
    
    Args:
        merchant_id (int): 商户ID，路径参数
        
    Returns:
        dict: 包含对比数据的响应
        
    Raises:
        HTTPException: 当获取对比数据失败时抛出500错误
    """
    try:
        # 调用统计分析服务获取商家对比数据
        comparison_data = await analytics_service.get_comparison_data(merchant_id)
        
        # 返回成功响应，包含对比数据
        return {
            "success": True,
            "data": comparison_data
        }
    except Exception as e:
        # 捕获异常并抛出自定义HTTP异常
        raise HTTPException(status_code=500, detail=f"获取对比数据失败: {str(e)}")

@router.post("/refresh-cache")
async def refresh_statistics_cache(merchant_id: int = Path(..., description="商家ID")):
    """
    刷新统计缓存
    
    手动触发统计缓存的更新，确保数据的实时性
    
    Args:
        merchant_id (int): 商户ID，路径参数
        
    Returns:
        dict: 缓存刷新结果信息
        
    Raises:
        HTTPException: 当缓存刷新失败时抛出500错误
    """
    try:
        # 调用统计分析服务更新统计缓存
        success = await analytics_service.update_statistics_cache(merchant_id)
        if not success:
            # 如果缓存刷新失败，抛出500错误
            raise HTTPException(status_code=500, detail="缓存刷新失败")
        
        # 返回成功响应
        return {
            "success": True,
            "message": "统计缓存刷新成功"
        }
    except Exception as e:
        # 捕获异常并抛出自定义HTTP异常
        raise HTTPException(status_code=500, detail=f"刷新缓存失败: {str(e)}")