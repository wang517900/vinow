"""商家系统 - merchant_router"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from uuid import UUID
import logging

from app.models.merchant_models import (
    MerchantCreate, MerchantUpdate, MerchantResponse, 
    MerchantListResponse, MerchantSearchParams,
    PromotionCreate, PromotionUpdate, PromotionResponse,
    CouponCreate, CouponUpdate, CouponResponse,
    AdvertisementCreate, AdvertisementUpdate, AdvertisementResponse,
    ReviewCreate, ReviewResponse
)
from app.services.merchant_service import MerchantService
from app.core.dependencies import get_merchant_service, get_current_user

logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(
    prefix="/merchants",
    tags=["商家管理"],
    responses={404: {"description": "未找到"}}
)

# --------------------------------------------------------------
# 商家管理路由
# --------------------------------------------------------------

@router.post("/", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    merchant_data: MerchantCreate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    创建新商家
    
    Args:
        merchant_data: 商家创建数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        MerchantResponse: 创建的商家信息
        
    Raises:
        HTTPException: 创建失败时抛出异常
    """
    try:
        merchant = await service.create_merchant(merchant_data, current_user["id"])
        return merchant
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建商家失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建商家失败"
        )


@router.get("/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: str,
    service: MerchantService = Depends(get_merchant_service)
):
    """
    获取商家详情
    
    Args:
        merchant_id: 商家ID
        service: 商家服务实例
        
    Returns:
        MerchantResponse: 商家详细信息
        
    Raises:
        HTTPException: 商家不存在时抛出404异常
    """
    try:
        merchant = await service.get_merchant(merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在"
            )
        return merchant
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商家详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商家详情失败"
        )


@router.put("/{merchant_id}", response_model=MerchantResponse)
async def update_merchant(
    merchant_id: str,
    update_data: MerchantUpdate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    更新商家信息
    
    Args:
        merchant_id: 商家ID
        update_data: 商家更新数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        MerchantResponse: 更新后的商家信息
        
    Raises:
        HTTPException: 无权限或商家不存在时抛出异常
    """
    try:
        merchant = await service.update_merchant(merchant_id, update_data, current_user["id"])
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在或无权限更新"
            )
        return merchant
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新商家失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新商家失败"
        )


@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant(
    merchant_id: str,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    删除商家（软删除）
    
    Args:
        merchant_id: 商家ID
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Raises:
        HTTPException: 无权限或商家不存在时抛出异常
    """
    try:
        success = await service.delete_merchant(merchant_id, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在或无权限删除"
            )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除商家失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除商家失败"
        )


@router.get("/", response_model=MerchantListResponse)
async def list_merchants(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    获取当前用户的所有商家列表
    
    Args:
        page: 页码
        page_size: 每页数量
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        MerchantListResponse: 商家列表和分页信息
    """
    try:
        merchants = await service.list_merchants(current_user["id"], page, page_size)
        return merchants
    except Exception as e:
        logger.error(f"获取商家列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商家列表失败"
        )


@router.get("/search/", response_model=MerchantListResponse)
async def search_merchants(
    params: MerchantSearchParams = Depends(),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    搜索商家
    
    Args:
        params: 搜索参数
        service: 商家服务实例
        
    Returns:
        MerchantListResponse: 搜索结果和分页信息
    """
    try:
        results = await service.search_merchants(params)
        return results
    except Exception as e:
        logger.error(f"搜索商家失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索商家失败"
        )


# --------------------------------------------------------------
# 营销功能路由
# --------------------------------------------------------------

@router.post("/{merchant_id}/promotions/", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    merchant_id: str,
    promotion_data: PromotionCreate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    为商家创建促销活动
    
    Args:
        merchant_id: 商家ID
        promotion_data: 促销活动数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        PromotionResponse: 创建的促销活动信息
    """
    try:
        # 这里需要在MerchantService中实现create_promotion方法
        promotion = await service.create_promotion(merchant_id, promotion_data.dict(), current_user["id"])
        return PromotionResponse(**promotion)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建促销活动失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建促销活动失败"
        )


@router.put("/promotions/{promotion_id}", response_model=PromotionResponse)
async def update_promotion(
    promotion_id: str,
    update_data: PromotionUpdate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    更新促销活动
    
    Args:
        promotion_id: 促销活动ID
        update_data: 促销活动更新数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        PromotionResponse: 更新后的促销活动信息
    """
    try:
        # 这里需要在MerchantService中实现update_promotion方法
        promotion = await service.update_promotion(promotion_id, update_model_dump(exclude_unset=True), current_user["id"])
        if not promotion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="促销活动不存在或无权限更新"
            )
        return PromotionResponse(**promotion)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新促销活动失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新促销活动失败"
        )


@router.post("/{merchant_id}/coupons/", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    merchant_id: str,
    coupon_data: CouponCreate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    为商家创建优惠券
    
    Args:
        merchant_id: 商家ID
        coupon_data: 优惠券数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        CouponResponse: 创建的优惠券信息
    """
    try:
        # 这里需要在MerchantService中实现create_coupon方法
        coupon = await service.create_coupon(merchant_id, coupon_data.dict(), current_user["id"])
        return CouponResponse(**coupon)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建优惠券失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建优惠券失败"
        )


@router.post("/{merchant_id}/reviews/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    merchant_id: str,
    review_data: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    为商家创建评价
    
    Args:
        merchant_id: 商家ID
        review_data: 评价数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        ReviewResponse: 创建的评价信息
    """
    try:
        # 确保评价数据中的merchant_id与路径参数一致
        review_data.merchant_id = merchant_id
        review_data.user_id = current_user["id"]
        
        review = await service.create_review(review_data)
        return review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建评价失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建评价失败"
        )


@router.post("/{merchant_id}/advertisements/", response_model=AdvertisementResponse, status_code=status.HTTP_201_CREATED)
async def create_advertisement(
    merchant_id: str,
    advertisement_data: AdvertisementCreate,
    current_user: dict = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service)
):
    """
    为商家创建广告
    
    Args:
        merchant_id: 商家ID
        advertisement_data: 广告数据
        current_user: 当前登录用户信息
        service: 商家服务实例
        
    Returns:
        AdvertisementResponse: 创建的广告信息
    """
    try:
        # 这里需要在MerchantService中实现create_advertisement方法
        advertisement = await service.create_advertisement(merchant_id, advertisement_data.dict(), current_user["id"])
        return AdvertisementResponse(**advertisement)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建广告失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建广告失败"
        )

# TODO: 实现商家系统相关功能
# 可能还需要添加的路由：
# 1. 获取商家的促销活动列表
# 2. 获取商家的优惠券列表
# 3. 获取商家的广告列表
# 4. 获取商家的评价列表
# 5. 获取商家统计数据