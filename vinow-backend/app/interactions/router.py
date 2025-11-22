# [文件: app/interactions/router.py] [行号: 401-600]
"""
用户互动数据路由 - v1.2.0
完整的收藏、浏览历史、搜索历史功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta

from app.common.database import supabase
from app.common.models import (
    FavoriteRequest, FavoriteType, BrowsingHistory, SearchHistory,
    SuccessResponse, PaginatedResponse, UserProfile
)
from app.common.auth import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["interactions"])

# 模拟数据存储（生产环境用数据库）
user_favorites_storage = {}
browsing_history_storage = {}
search_history_storage = {}

# 模拟商家和商品数据
MOCK_MERCHANTS = {
    "merchant_1": {
        "id": "merchant_1",
        "name": "Pho 24",
        "cuisine": "越南菜",
        "rating": 4.5,
        "delivery_time": "20-30分钟",
        "image_url": "/images/merchants/pho24.jpg"
    },
    "merchant_2": {
        "id": "merchant_2", 
        "name": "Banh Mi Huynh Hoa",
        "cuisine": "越南菜",
        "rating": 4.8,
        "delivery_time": "15-25分钟",
        "image_url": "/images/merchants/banhmi.jpg"
    },
    "merchant_3": {
        "id": "merchant_3",
        "name": "Pizza 4P's",
        "cuisine": "意大利菜",
        "rating": 4.7,
        "delivery_time": "30-40分钟",
        "image_url": "/images/merchants/pizza4ps.jpg"
    }
}

MOCK_PRODUCTS = {
    "product_1": {
        "id": "product_1",
        "name": "Pho Bo",
        "description": "经典越南牛肉粉",
        "price": 65000,
        "image_url": "/images/products/phobo.jpg",
        "merchant_id": "merchant_1"
    },
    "product_2": {
        "id": "product_2",
        "name": "Banh Mi Thit",
        "description": "越南烤肉三明治",
        "price": 35000,
        "image_url": "/images/products/banhmithit.jpg",
        "merchant_id": "merchant_2"
    },
    "product_3": {
        "id": "product_3",
        "name": "Margherita Pizza",
        "description": "经典玛格丽特披萨",
        "price": 120000,
        "image_url": "/images/products/pizza.jpg",
        "merchant_id": "merchant_3"
    }
}

def get_favorite_details(favorite_type: str, target_id: str) -> Dict[str, Any]:
    """获取收藏项的详细信息"""
    if favorite_type == "merchant":
        return MOCK_MERCHANTS.get(target_id, {"id": target_id, "name": f"商家{target_id}"})
    elif favorite_type == "product":
        return MOCK_PRODUCTS.get(target_id, {"id": target_id, "name": f"商品{target_id}"})
    return {"id": target_id, "name": "未知项目"}

# ========== 收藏管理 ==========

@router.get("/favorites/merchants")
async def get_favorite_merchants(
    current_user: UserProfile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取收藏的商家列表"""
    try:
        user_id = current_user.id
        
        # 从数据库获取收藏的商家
        try:
            result = supabase.table("user_favorites").select("*").eq("user_id", user_id).eq("favorite_type", "merchant").execute()
            favorites = result.data if result.data else []
        except Exception:
            favorites = [fav for fav in user_favorites_storage.get(user_id, []) if fav.get("favorite_type") == "merchant"]
        
        # 添加商家详情
        merchants_with_details = []
        for fav in favorites:
            merchant_details = get_favorite_details("merchant", fav.get("merchant_id", ""))
            merchants_with_details.append({
                **fav,
                "merchant_details": merchant_details
            })
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = merchants_with_details[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(merchants_with_details),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(merchants_with_details)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取收藏商家失败: {str(e)}"
        )

@router.get("/favorites/products")
async def get_favorite_products(
    current_user: UserProfile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取收藏的商品列表"""
    try:
        user_id = current_user.id
        
        # 从数据库获取收藏的商品
        try:
            result = supabase.table("user_favorites").select("*").eq("user_id", user_id).eq("favorite_type", "product").execute()
            favorites = result.data if result.data else []
        except Exception:
            favorites = [fav for fav in user_favorites_storage.get(user_id, []) if fav.get("favorite_type") == "product"]
        
        # 添加商品详情
        products_with_details = []
        for fav in favorites:
            product_details = get_favorite_details("product", fav.get("product_id", ""))
            products_with_details.append({
                **fav,
                "product_details": product_details
            })
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = products_with_details[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(products_with_details),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(products_with_details)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取收藏商品失败: {str(e)}"
        )

@router.post("/favorites/merchants")
async def add_favorite_merchant(
    merchant_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """收藏商家"""
    try:
        user_id = current_user.id
        
        # 检查商家是否存在
        if merchant_id not in MOCK_MERCHANTS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在"
            )
        
        # 检查是否已收藏
        try:
            existing = supabase.table("user_favorites").select("*").eq("user_id", user_id).eq("merchant_id", merchant_id).execute()
            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="已收藏该商家"
                )
        except Exception:
            existing_favs = user_favorites_storage.get(user_id, [])
            if any(fav.get("merchant_id") == merchant_id for fav in existing_favs):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="已收藏该商家"
                )
        
        # 创建收藏记录
        favorite_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "merchant_id": merchant_id,
            "favorite_type": "merchant",
            "created_at": datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            result = supabase.table("user_favorites").insert(favorite_data).execute()
            saved_favorite = result.data[0] if result.data else favorite_data
        except Exception:
            if user_id not in user_favorites_storage:
                user_favorites_storage[user_id] = []
            user_favorites_storage[user_id].append(favorite_data)
            saved_favorite = favorite_data
        
        print(f"✅ 商家收藏成功: {user_id} -> {merchant_id}")
        
        return SuccessResponse(
            message="商家收藏成功",
            data={"favorite_id": saved_favorite["id"]}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"收藏商家失败: {str(e)}"
        )

@router.post("/favorites/products")
async def add_favorite_product(
    product_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """收藏商品"""
    try:
        user_id = current_user.id
        
        # 检查商品是否存在
        if product_id not in MOCK_PRODUCTS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )
        
        # 检查是否已收藏
        try:
            existing = supabase.table("user_favorites").select("*").eq("user_id", user_id).eq("product_id", product_id).execute()
            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="已收藏该商品"
                )
        except Exception:
            existing_favs = user_favorites_storage.get(user_id, [])
            if any(fav.get("product_id") == product_id for fav in existing_favs):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="已收藏该商品"
                )
        
        # 创建收藏记录
        favorite_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "product_id": product_id,
            "favorite_type": "product",
            "created_at": datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            result = supabase.table("user_favorites").insert(favorite_data).execute()
            saved_favorite = result.data[0] if result.data else favorite_data
        except Exception:
            if user_id not in user_favorites_storage:
                user_favorites_storage[user_id] = []
            user_favorites_storage[user_id].append(favorite_data)
            saved_favorite = favorite_data
        
        print(f"✅ 商品收藏成功: {user_id} -> {product_id}")
        
        return SuccessResponse(
            message="商品收藏成功",
            data={"favorite_id": saved_favorite["id"]}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"收藏商品失败: {str(e)}"
        )

@router.delete("/favorites/merchants/{merchant_id}")
async def remove_favorite_merchant(
    merchant_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """取消收藏商家"""
    try:
        user_id = current_user.id
        
        # 从数据库删除
        try:
            result = supabase.table("user_favorites").delete().eq("user_id", user_id).eq("merchant_id", merchant_id).execute()
            if not result.data:
                raise HTTPException(404, "未找到收藏记录")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            # 内存存储处理
            if user_id in user_favorites_storage:
                original_count = len(user_favorites_storage[user_id])
                user_favorites_storage[user_id] = [
                    fav for fav in user_favorites_storage[user_id] 
                    if not (fav.get("merchant_id") == merchant_id and fav.get("favorite_type") == "merchant")
                ]
                if len(user_favorites_storage[user_id]) == original_count:
                    raise HTTPException(404, "未找到收藏记录")
        
        print(f"✅ 取消商家收藏成功: {user_id} -> {merchant_id}")
        
        return SuccessResponse(message="取消收藏成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消收藏失败: {str(e)}"
        )

@router.delete("/favorites/products/{product_id}")
async def remove_favorite_product(
    product_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """取消收藏商品"""
    try:
        user_id = current_user.id
        
        # 从数据库删除
        try:
            result = supabase.table("user_favorites").delete().eq("user_id", user_id).eq("product_id", product_id).execute()
            if not result.data:
                raise HTTPException(404, "未找到收藏记录")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            # 内存存储处理
            if user_id in user_favorites_storage:
                original_count = len(user_favorites_storage[user_id])
                user_favorites_storage[user_id] = [
                    fav for fav in user_favorites_storage[user_id] 
                    if not (fav.get("product_id") == product_id and fav.get("favorite_type") == "product")
                ]
                if len(user_favorites_storage[user_id]) == original_count:
                    raise HTTPException(404, "未找到收藏记录")
        
        print(f"✅ 取消商品收藏成功: {user_id} -> {product_id}")
        
        return SuccessResponse(message="取消收藏成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消收藏失败: {str(e)}"
        )

# ========== 浏览历史 ==========

@router.get("/history/merchants")
async def get_browsing_history(
    current_user: UserProfile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    days: int = Query(30, ge=1, le=365)  # 最近多少天的历史
):
    """获取商家浏览历史"""
    try:
        user_id = current_user.id
        
        # 计算时间范围
        since_date = datetime.now() - timedelta(days=days)
        
        # 从数据库获取浏览历史
        try:
            result = supabase.table("browsing_history").select("*").eq("user_id", user_id).gte("viewed_at", since_date.isoformat()).execute()
            history = result.data if result.data else []
        except Exception:
            history = browsing_history_storage.get(user_id, [])
            # 过滤时间范围
            history = [h for h in history if datetime.fromisoformat(h.get("viewed_at", "2000-01-01")) >= since_date]
        
        # 添加商家详情并排序（最近访问在前）
        history_with_details = []
        for item in history:
            merchant_details = get_favorite_details("merchant", item.get("merchant_id", ""))
            history_with_details.append({
                **item,
                "merchant_details": merchant_details
            })
        
        # 按时间倒序排序
        history_with_details.sort(key=lambda x: x.get("viewed_at", ""), reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = history_with_details[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(history_with_details),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(history_with_details)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取浏览历史失败: {str(e)}"
        )

@router.post("/history/merchants")
async def record_browsing_history(
    merchant_id: str,
    duration_seconds: int = 0,
    current_user: UserProfile = Depends(get_current_user)
):
    """记录商家浏览历史"""
    try:
        user_id = current_user.id
        
        # 检查商家是否存在
        if merchant_id not in MOCK_MERCHANTS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商家不存在"
            )
        
        # 创建浏览记录
        history_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "merchant_id": merchant_id,
            "viewed_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds
        }
        
        # 保存到数据库
        try:
            result = supabase.table("browsing_history").insert(history_data).execute()
            saved_history = result.data[0] if result.data else history_data
        except Exception:
            if user_id not in browsing_history_storage:
                browsing_history_storage[user_id] = []
            browsing_history_storage[user_id].append(history_data)
            saved_history = history_data
        
        print(f"✅ 浏览历史记录成功: {user_id} -> {merchant_id}")
        
        return SuccessResponse(
            message="浏览历史记录成功",
            data={"history_id": saved_history["id"]}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录浏览历史失败: {str(e)}"
        )

@router.delete("/history/merchants")
async def clear_browsing_history(current_user: UserProfile = Depends(get_current_user)):
    """清空浏览历史"""
    try:
        user_id = current_user.id
        
        # 从数据库删除
        try:
            supabase.table("browsing_history").delete().eq("user_id", user_id).execute()
        except Exception:
            # 内存存储处理
            if user_id in browsing_history_storage:
                browsing_history_storage[user_id] = []
        
        print(f"✅ 浏览历史清空成功: {user_id}")
        
        return SuccessResponse(message="浏览历史已清空")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空浏览历史失败: {str(e)}"
        )

# ========== 搜索历史 ==========

@router.get("/history/searches")
async def get_search_history(
    current_user: UserProfile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取搜索历史"""
    try:
        user_id = current_user.id
        
        # 从数据库获取搜索历史
        try:
            result = supabase.table("search_history").select("*").eq("user_id", user_id).execute()
            searches = result.data if result.data else []
        except Exception:
            searches = search_history_storage.get(user_id, [])
        
        # 按时间倒序排序
        searches.sort(key=lambda x: x.get("searched_at", ""), reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = searches[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(searches),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(searches)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索历史失败: {str(e)}"
        )

@router.post("/history/searches")
async def record_search_history(
    query_text: str,
    search_type: str = "general",
    filters: Dict[str, Any] = None,
    result_count: int = 0,
    current_user: UserProfile = Depends(get_current_user)
):
    """记录搜索历史"""
    try:
        user_id = current_user.id
        
        # 创建搜索记录
        search_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "query_text": query_text,
            "search_type": search_type,
            "filters": filters or {},
            "result_count": result_count,
            "searched_at": datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            result = supabase.table("search_history").insert(search_data).execute()
            saved_search = result.data[0] if result.data else search_data
        except Exception:
            if user_id not in search_history_storage:
                search_history_storage[user_id] = []
            search_history_storage[user_id].append(search_data)
            saved_search = search_data
        
        print(f"✅ 搜索历史记录成功: {user_id} -> {query_text}")
        
        return SuccessResponse(
            message="搜索历史记录成功",
            data={"search_id": saved_search["id"]}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录搜索历史失败: {str(e)}"
        )

@router.delete("/history/searches")
async def clear_search_history(current_user: UserProfile = Depends(get_current_user)):
    """清空搜索历史"""
    try:
        user_id = current_user.id
        
        # 从数据库删除
        try:
            supabase.table("search_history").delete().eq("user_id", user_id).execute()
        except Exception:
            # 内存存储处理
            if user_id in search_history_storage:
                search_history_storage[user_id] = []
        
        print(f"✅ 搜索历史清空成功: {user_id}")
        
        return SuccessResponse(message="搜索历史已清空")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空搜索历史失败: {str(e)}"
        )

# ========== 统计信息 ==========

@router.get("/interactions/stats")
async def get_interaction_stats(current_user: UserProfile = Depends(get_current_user)):
    """获取互动数据统计"""
    try:
        user_id = current_user.id
        
        # 获取收藏统计
        try:
            fav_result = supabase.table("user_favorites").select("favorite_type").eq("user_id", user_id).execute()
            favorites = fav_result.data if fav_result.data else []
        except Exception:
            favorites = user_favorites_storage.get(user_id, [])
        
        merchant_fav_count = len([f for f in favorites if f.get("favorite_type") == "merchant"])
        product_fav_count = len([f for f in favorites if f.get("favorite_type") == "product"])
        
        # 获取浏览历史统计
        try:
            browse_result = supabase.table("browsing_history").select("*").eq("user_id", user_id).execute()
            browse_history = browse_result.data if browse_result.data else []
        except Exception:
            browse_history = browsing_history_storage.get(user_id, [])
        
        # 获取搜索历史统计
        try:
            search_result = supabase.table("search_history").select("*").eq("user_id", user_id).execute()
            search_history = search_result.data if search_result.data else []
        except Exception:
            search_history = search_history_storage.get(user_id, [])
        
        stats = {
            "favorites": {
                "merchants": merchant_fav_count,
                "products": product_fav_count,
                "total": merchant_fav_count + product_fav_count
            },
            "browsing_history": {
                "total_views": len(browse_history),
                "recent_views": len([h for h in browse_history if datetime.fromisoformat(h.get("viewed_at", "2000-01-01")) >= datetime.now() - timedelta(days=7)])
            },
            "search_history": {
                "total_searches": len(search_history),
                "recent_searches": len([s for s in search_history if datetime.fromisoformat(s.get("searched_at", "2000-01-01")) >= datetime.now() - timedelta(days=7)]),
                "popular_queries": self._get_popular_queries(search_history)
            }
        }
        
        return SuccessResponse(
            message="互动统计获取成功",
            data=stats
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取互动统计失败: {str(e)}"
        )

def _get_popular_queries(search_history: List[Dict]) -> List[Dict]:
    """获取热门搜索查询"""
    from collections import Counter
    queries = [item.get("query_text", "") for item in search_history]
    query_counts = Counter(queries)
    return [{"query": query, "count": count} for query, count in query_counts.most_common(5)]

# 开发环境调试端点
@router.get("/debug/interactions")
async def debug_interactions(current_user: UserProfile = Depends(get_current_user)):
    """查看互动数据（仅开发环境）"""
    user_id = current_user.id
    
    return {
        "favorites": user_favorites_storage.get(user_id, []),
        "browsing_history": browsing_history_storage.get(user_id, []),
        "search_history": search_history_storage.get(user_id, []),
        "mock_merchants": MOCK_MERCHANTS,
        "mock_products": MOCK_PRODUCTS
    }