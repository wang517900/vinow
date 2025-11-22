# -*- coding: utf-8 -*-
"""商品路由模块"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import List, Optional
from decimal import Decimal
import logging

from app.services.product_service import ProductService
from app.models.product_models import (
    ProductCreate, ProductUpdate, ProductResponse, ProductStatus,
    ProductListResponse, ProductSearchParams, BulkUpdateStatus,
    BulkStockUpdate, ProductType
)
from app.dependencies import get_supabase_client, get_current_user

# 创建路由实例
router = APIRouter()

# 配置日志
logger = logging.getLogger(__name__)

def get_product_service(supabase=Depends(get_supabase_client)) -> ProductService:
    """获取商品服务实例"""
    return ProductService(supabase)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    创建商品
    - **name**: 商品名称 (必填)
    - **description**: 商品描述
    - **product_type**: 商品类型 (physical, digital, service)
    - **merchant_id**: 商家ID (必填)
    - **variants**: 商品规格列表 (至少一个)
    """
    try:
        product = await product_service.create_product(product_data, current_user["id"])
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建商品失败，请稍后重试"
        )

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str = Path(..., description="商品ID"),
    product_service: ProductService = Depends(get_product_service)
):
    """
    获取商品详情
    - **product_id**: 商品ID
    """
    try:
        product = await product_service.get_product(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商品失败，请稍后重试"
        )

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str = Path(..., description="商品ID"),
    update_data: ProductUpdate = None,  # 修正：添加默认值None
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    更新商品信息
    - **product_id**: 商品ID
    - **name**: 商品名称
    - **description**: 商品描述
    - **status**: 商品状态
    - **is_featured**: 是否推荐
    """
    try:
        product = await product_service.update_product(product_id, update_data, current_user["id"])
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新商品失败，请稍后重试"
        )

@router.delete("/{product_id}")
async def delete_product(
    product_id: str = Path(..., description="商品ID"),
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    删除商品（软删除）
    - **product_id**: 商品ID
    """
    try:
        success = await product_service.delete_product(product_id, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        return {"message": "商品删除成功"}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"删除商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除商品失败，请稍后重试"
        )

@router.get("/merchant/{merchant_id}", response_model=ProductListResponse)
async def list_merchant_products(
    merchant_id: str = Path(..., description="商家ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    获取商家的商品列表
    - **merchant_id**: 商家ID
    - **page**: 页码 (默认: 1)
    - **page_size**: 每页数量 (默认: 20, 最大: 100)
    """
    try:
        # 验证商家所有权
        from app.services.merchant_service import MerchantService
        merchant_service = MerchantService(product_service.supabase)
        merchant = await merchant_service.get_merchant(merchant_id)
        
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在"
            )
        
        if merchant.owner_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问该商家的商品"
            )
        
        return await product_service.list_products(merchant_id, page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商家商品列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取商品列表失败，请稍后重试"
        )

@router.get("/search/public", response_model=ProductListResponse)
async def search_products(
    query: Optional[str] = Query(None, description="搜索关键词"),
    merchant_id: Optional[str] = Query(None, description="商家ID"),
    category_id: Optional[str] = Query(None, description="分类ID"),
    product_type: Optional[ProductType] = Query(None, description="商品类型"),
    status: Optional[ProductStatus] = Query(ProductStatus.ACTIVE, description="商品状态"),  # 修正：默认只显示上架商品
    min_price: Optional[Decimal] = Query(None, ge=0, description="最低价格"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="最高价格"),
    in_stock_only: bool = Query(False, description="仅显示有库存"),
    is_featured: Optional[bool] = Query(None, description="是否推荐商品"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    product_service: ProductService = Depends(get_product_service)
):
    """
    公开搜索商品
    - **query**: 搜索关键词
    - **merchant_id**: 商家ID
    - **category_id**: 分类ID
    - **product_type**: 商品类型
    - **status**: 商品状态 (默认: active)
    - **min_price**: 最低价格
    - **max_price**: 最高价格
    - **in_stock_only**: 仅显示有库存
    - **is_featured**: 是否推荐
    - **sort_by**: 排序字段 (created_at, price, name)
    - **sort_order**: 排序方向 (asc, desc)
    - **page**: 页码
    - **page_size**: 每页数量
    """
    try:
        search_params = ProductSearchParams(
            query=query,
            merchant_id=merchant_id,
            category_id=category_id,
            product_type=product_type,
            status=status,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only,
            is_featured=is_featured,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        return await product_service.search_products(search_params)
    except Exception as e:
        logger.error(f"搜索商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索商品失败，请稍后重试"
        )

@router.post("/bulk/status", status_code=status.HTTP_200_OK)
async def bulk_update_product_status(
    update_data: BulkUpdateStatus,
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    批量更新商品状态
    - **product_ids**: 商品ID列表
    - **status**: 目标状态 (draft, active, inactive, sold_out)
    """
    try:
        success = await product_service.bulk_update_status(update_data, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="批量更新状态失败"
            )
        
        action_map = {
            ProductStatus.ACTIVE: "上架",
            ProductStatus.INACTIVE: "下架",
            ProductStatus.SOLD_OUT: "标记为售罄",
            ProductStatus.DRAFT: "保存为草稿",
            ProductStatus.DELETED: "删除"
        }
        
        action = action_map.get(update_data.status, "更新")
        return {"message": f"成功{action} {len(update_data.product_ids)} 个商品"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"批量更新商品状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量更新状态失败，请稍后重试"
        )

@router.put("/{product_id}/stock", status_code=status.HTTP_200_OK)
async def update_product_stock(
    product_id: str = Path(..., description="商品ID"),
    stock_updates: BulkStockUpdate = None,  # 修正：添加默认值None
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    更新商品库存
    - **product_id**: 商品ID
    - **updates**: 库存更新列表
      - **variant_sku**: 规格SKU
      - **quantity**: 数量
      - **operation**: 操作类型 (set, increment, decrement)
    """
    try:
        success = await product_service.update_stock(product_id, stock_updates, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新库存失败"
            )
        return {"message": "库存更新成功"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新商品库存失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新库存失败，请稍后重试"
        )

@router.post("/{product_id}/publish", response_model=ProductResponse)
async def publish_product(
    product_id: str = Path(..., description="商品ID"),
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    上架商品
    - **product_id**: 商品ID
    """
    try:
        # 验证商品所有权
        product = await product_service.get_product(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        
        # 验证商家权限
        from app.services.merchant_service import MerchantService
        merchant_service = MerchantService(product_service.supabase)
        merchant = await merchant_service.get_merchant(product.merchant_id)
        if not merchant or merchant.owner_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该商品"
            )
        
        update_data = BulkUpdateStatus(
            product_ids=[product_id],
            status=ProductStatus.ACTIVE
        )
        
        success = await product_service.bulk_update_status(update_data, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上架商品失败"
            )
        
        product = await product_service.get_product(product_id)
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上架商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上架商品失败，请稍后重试"
        )

@router.post("/{product_id}/unpublish", response_model=ProductResponse)
async def unpublish_product(
    product_id: str = Path(..., description="商品ID"),
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """
    下架商品
    - **product_id**: 商品ID
    """
    try:
        # 验证商品所有权
        product = await product_service.get_product(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        
        # 验证商家权限
        from app.services.merchant_service import MerchantService
        merchant_service = MerchantService(product_service.supabase)
        merchant = await merchant_service.get_merchant(product.merchant_id)
        if not merchant or merchant.owner_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该商品"
            )
        
        update_data = BulkUpdateStatus(
            product_ids=[product_id],
            status=ProductStatus.INACTIVE
        )
        
        success = await product_service.bulk_update_status(update_data, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="下架商品失败"
            )
        
        product = await product_service.get_product(product_id)
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下架商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下架商品失败，请稍后重试"
        )