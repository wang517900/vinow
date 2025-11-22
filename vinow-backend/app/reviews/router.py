# [文件: app/reviews/router.py] [行号: 801-1000]
"""
评价系统路由 - v1.4.0
完整的评价、评分、评价管理功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta

from app.common.database import supabase
from app.common.models import (
    CreateReviewRequest, ReviewResponse, ReviewRating, 
    SuccessResponse, PaginatedResponse, UserProfile
)
from app.common.auth import get_current_user

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

# 模拟数据存储（生产环境用数据库）
reviews_storage = {}
review_ratings_storage = {}
review_helpful_votes_storage = {}
review_replies_storage = {}

# 模拟订单数据（用于评价关联）
MOCK_ORDERS = {
    "order_1": {
        "id": "order_1",
        "order_number": "VN202403150001",
        "merchant_id": "merchant_1",
        "merchant_name": "Pho 24",
        "items": [
            {"product_name": "Pho Bo", "quantity": 2},
            {"product_name": "Goi Cuon", "quantity": 1}
        ],
        "final_amount": 155000,
        "completed_at": "2024-03-15T12:30:00Z"
    },
    "order_2": {
        "id": "order_2",
        "order_number": "VN202403160002", 
        "merchant_id": "merchant_2",
        "merchant_name": "Banh Mi Huynh Hoa",
        "items": [
            {"product_name": "Banh Mi Thit", "quantity": 3}
        ],
        "final_amount": 105000,
        "completed_at": "2024-03-16T10:15:00Z"
    },
    "order_3": {
        "id": "order_3",
        "order_number": "VN202403170003",
        "merchant_id": "merchant_3", 
        "merchant_name": "Pizza 4P's",
        "items": [
            {"product_name": "Margherita Pizza", "quantity": 1}
        ],
        "final_amount": 140000,
        "completed_at": "2024-03-17T19:45:00Z"
    }
}

# 模拟商家数据
MOCK_MERCHANTS = {
    "merchant_1": {
        "id": "merchant_1",
        "name": "Pho 24",
        "cuisine": "越南菜",
        "rating": 4.5,
        "review_count": 128
    },
    "merchant_2": {
        "id": "merchant_2",
        "name": "Banh Mi Huynh Hoa",
        "cuisine": "越南菜",
        "rating": 4.8, 
        "review_count": 89
    },
    "merchant_3": {
        "id": "merchant_3",
        "name": "Pizza 4P's",
        "cuisine": "意大利菜",
        "rating": 4.7,
        "review_count": 203
    }
}

def validate_review_eligibility(order_id: str, user_id: str) -> Dict[str, Any]:
    """验证评价资格"""
    # 检查订单是否存在
    order = MOCK_ORDERS.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )
    
    # 检查订单是否已完成
    if not order.get("completed_at"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="订单未完成，无法评价"
        )
    
    # 检查是否已评价过该订单
    try:
        existing_review = supabase.table("reviews").select("*").eq("order_id", order_id).execute()
        if existing_review.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该订单已评价过"
            )
    except Exception:
        existing_reviews = [r for r in reviews_storage.values() if r.get("order_id") == order_id]
        if existing_reviews:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该订单已评价过"
            )
    
    return order

def calculate_merchant_ratings(merchant_id: str):
    """重新计算商家的评分"""
    try:
        # 获取商家的所有评价
        reviews_result = supabase.table("reviews").select("rating", "detailed_ratings").eq("merchant_id", merchant_id).eq("status", "active").execute()
        reviews = reviews_result.data if reviews_result.data else []
    except Exception:
        reviews = [r for r in reviews_storage.values() if r.get("merchant_id") == merchant_id and r.get("status") == "active"]
    
    if not reviews:
        return {"average_rating": 0, "review_count": 0}
    
    # 计算平均评分
    total_rating = sum(review.get("rating", 0) for review in reviews)
    average_rating = round(total_rating / len(reviews), 1)
    
    # 更新商家评分
    update_data = {
        "rating": average_rating,
        "review_count": len(reviews),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        supabase.table("merchants").update(update_data).eq("id", merchant_id).execute()
    except Exception:
        # 内存存储处理
        if merchant_id in MOCK_MERCHANTS:
            MOCK_MERCHANTS[merchant_id].update(update_data)
    
    return {
        "average_rating": average_rating,
        "review_count": len(reviews)
    }

@router.post("/orders/{order_id}", response_model=ReviewResponse)
async def create_review(
    order_id: str,
    request: CreateReviewRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """提交订单评价"""
    try:
        user_id = current_user.id
        
        # 验证评价资格
        order = validate_review_eligibility(order_id, user_id)
        
        # 验证评分范围
        if request.rating < 1 or request.rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评分必须在1-5分之间"
            )
        
        # 创建评价数据
        review_id = str(uuid.uuid4())
        review_data = {
            "id": review_id,
            "user_id": user_id,
            "order_id": order_id,
            "merchant_id": order["merchant_id"],
            "rating": request.rating,
            "title": request.title,
            "content": request.content,
            "image_urls": request.image_urls or [],
            "is_anonymous": request.is_anonymous,
            "helpful_count": 0,
            "view_count": 0,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 保存评价到数据库
        try:
            review_result = supabase.table("reviews").insert(review_data).execute()
            saved_review = review_result.data[0] if review_result.data else review_data
        except Exception:
            reviews_storage[review_id] = review_data
            saved_review = review_data
        
        # 保存详细评分（如果有）
        if request.detailed_ratings:
            detailed_ratings_data = {
                "id": str(uuid.uuid4()),
                "review_id": review_id,
                "taste": request.detailed_ratings.taste,
                "service": request.detailed_ratings.service,
                "environment": request.detailed_ratings.environment,
                "value": request.detailed_ratings.value,
                "created_at": datetime.now().isoformat()
            }
            
            try:
                supabase.table("review_ratings").insert(detailed_ratings_data).execute()
            except Exception:
                if review_id not in review_ratings_storage:
                    review_ratings_storage[review_id] = []
                review_ratings_storage[review_id].append(detailed_ratings_data)
            
            saved_review["detailed_ratings"] = request.detailed_ratings
        
        # 重新计算商家评分
        calculate_merchant_ratings(order["merchant_id"])
        
        # 添加用户资料信息（非匿名评价）
        if not request.is_anonymous:
            saved_review["user_profile"] = {
                "id": current_user.id,
                "username": current_user.username,
                "avatar_url": current_user.avatar_url
            }
        
        print(f"✅ 评价提交成功: {review_id} - 订单 {order_id}")
        
        return ReviewResponse(**saved_review)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交评价失败: {str(e)}"
        )

@router.get("/", response_model=PaginatedResponse)
async def get_my_reviews(
    current_user: UserProfile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rating: Optional[int] = Query(None, ge=1, le=5)
):
    """获取我的评价列表"""
    try:
        user_id = current_user.id
        
        # 从数据库获取评价
        try:
            query = supabase.table("reviews").select("*").eq("user_id", user_id)
            if rating:
                query = query.eq("rating", rating)
            result = query.execute()
            reviews = result.data if result.data else []
        except Exception:
            reviews = [r for r in reviews_storage.values() if r.get("user_id") == user_id]
            if rating:
                reviews = [r for r in reviews if r.get("rating") == rating]
        
        # 获取详细评分和商家信息
        for review in reviews:
            review_id = review["id"]
            merchant_id = review.get("merchant_id")
            
            # 获取详细评分
            try:
                ratings_result = supabase.table("review_ratings").select("*").eq("review_id", review_id).execute()
                if ratings_result.data:
                    review["detailed_ratings"] = ratings_result.data[0]
            except Exception:
                if review_id in review_ratings_storage:
                    review["detailed_ratings"] = review_ratings_storage[review_id][0]
            
            # 添加商家信息
            if merchant_id:
                review["merchant_info"] = MOCK_MERCHANTS.get(merchant_id, {})
        
        # 按创建时间倒序排序
        reviews.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = reviews[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(reviews),
            page=page,
            page_size=page_size,
            has_next=end_idx < len(reviews)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评价列表失败: {str(e)}"
        )

@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review_detail(
    review_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """获取评价详情"""
    try:
        # 从数据库获取评价
        try:
            review_result = supabase.table("reviews").select("*").eq("id", review_id).execute()
            if not review_result.data:
                raise HTTPException(404, "评价不存在")
            review = review_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            review = reviews_storage.get(review_id)
            if not review:
                raise HTTPException(404, "评价不存在")
        
        # 检查查看权限（只能查看自己的或公开的评价）
        if review.get("user_id") != current_user.id and review.get("is_anonymous", False):
            raise HTTPException(403, "无权查看该评价")
        
        # 增加查看次数
        review["view_count"] = review.get("view_count", 0) + 1
        try:
            supabase.table("reviews").update({"view_count": review["view_count"]}).eq("id", review_id).execute()
        except Exception:
            if review_id in reviews_storage:
                reviews_storage[review_id]["view_count"] = review["view_count"]
        
        # 获取详细评分
        try:
            ratings_result = supabase.table("review_ratings").select("*").eq("review_id", review_id).execute()
            if ratings_result.data:
                review["detailed_ratings"] = ratings_result.data[0]
        except Exception:
            if review_id in review_ratings_storage:
                review["detailed_ratings"] = review_ratings_storage[review_id][0]
        
        # 获取商家信息
        merchant_id = review.get("merchant_id")
        if merchant_id:
            review["merchant_info"] = MOCK_MERCHANTS.get(merchant_id, {})
        
        # 获取订单信息
        order_id = review.get("order_id")
        if order_id:
            review["order_info"] = MOCK_ORDERS.get(order_id, {})
        
        # 获取用户资料（非匿名评价）
        if not review.get("is_anonymous", False):
            user_id = review.get("user_id")
            # 这里应该从数据库获取用户资料，这里使用当前用户资料作为示例
            review["user_profile"] = {
                "id": current_user.id,
                "username": current_user.username,
                "avatar_url": current_user.avatar_url
            }
        
        # 获取商家回复
        try:
            reply_result = supabase.table("review_replies").select("*").eq("review_id", review_id).execute()
            if reply_result.data:
                review["merchant_reply"] = reply_result.data[0]
        except Exception:
            if review_id in review_replies_storage:
                review["merchant_reply"] = review_replies_storage[review_id][0]
        
        # 检查当前用户是否已点赞
        try:
            vote_result = supabase.table("review_helpful_votes").select("*").eq("review_id", review_id).eq("user_id", current_user.id).execute()
            review["has_helpful_voted"] = bool(vote_result.data)
        except Exception:
            user_votes = [v for v in review_helpful_votes_storage.values() if v.get("review_id") == review_id and v.get("user_id") == current_user.id]
            review["has_helpful_voted"] = len(user_votes) > 0
        
        return ReviewResponse(**review)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评价详情失败: {str(e)}"
        )

@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    request: CreateReviewRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """更新评价"""
    try:
        user_id = current_user.id
        
        # 从数据库获取评价
        try:
            review_result = supabase.table("reviews").select("*").eq("id", review_id).eq("user_id", user_id).execute()
            if not review_result.data:
                raise HTTPException(404, "评价不存在")
            review = review_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            review = reviews_storage.get(review_id)
            if not review or review.get("user_id") != user_id:
                raise HTTPException(404, "评价不存在")
        
        # 验证评分范围
        if request.rating < 1 or request.rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评分必须在1-5分之间"
            )
        
        # 更新评价数据
        update_data = {
            "rating": request.rating,
            "title": request.title,
            "content": request.content,
            "image_urls": request.image_urls or [],
            "is_anonymous": request.is_anonymous,
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("reviews").update(update_data).eq("id", review_id).execute()
            review.update(update_data)
        except Exception:
            reviews_storage[review_id].update(update_data)
        
        # 更新详细评分（如果有）
        if request.detailed_ratings:
            detailed_update = {
                "taste": request.detailed_ratings.taste,
                "service": request.detailed_ratings.service,
                "environment": request.detailed_ratings.environment,
                "value": request.detailed_ratings.value
            }
            
            try:
                supabase.table("review_ratings").update(detailed_update).eq("review_id", review_id).execute()
            except Exception:
                if review_id in review_ratings_storage:
                    review_ratings_storage[review_id][0].update(detailed_update)
        
        # 重新计算商家评分
        merchant_id = review.get("merchant_id")
        if merchant_id:
            calculate_merchant_ratings(merchant_id)
        
        print(f"✅ 评价更新成功: {review_id}")
        
        return ReviewResponse(**review)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新评价失败: {str(e)}"
        )

@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """删除评价"""
    try:
        user_id = current_user.id
        
        # 从数据库获取评价
        try:
            review_result = supabase.table("reviews").select("*").eq("id", review_id).eq("user_id", user_id).execute()
            if not review_result.data:
                raise HTTPException(404, "评价不存在")
            review = review_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            review = reviews_storage.get(review_id)
            if not review or review.get("user_id") != user_id:
                raise HTTPException(404, "评价不存在")
        
        # 软删除评价
        update_data = {
            "status": "deleted",
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("reviews").update(update_data).eq("id", review_id).execute()
        except Exception:
            if review_id in reviews_storage:
                reviews_storage[review_id].update(update_data)
        
        # 重新计算商家评分
        merchant_id = review.get("merchant_id")
        if merchant_id:
            calculate_merchant_ratings(merchant_id)
        
        print(f"✅ 评价删除成功: {review_id}")
        
        return SuccessResponse(message="评价删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除评价失败: {str(e)}"
        )

@router.post("/{review_id}/helpful")
async def mark_review_helpful(
    review_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """标记评价为有帮助"""
    try:
        user_id = current_user.id
        
        # 检查评价是否存在
        try:
            review_result = supabase.table("reviews").select("*").eq("id", review_id).execute()
            if not review_result.data:
                raise HTTPException(404, "评价不存在")
            review = review_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            review = reviews_storage.get(review_id)
            if not review:
                raise HTTPException(404, "评价不存在")
        
        # 检查是否已点赞
        try:
            existing_vote = supabase.table("review_helpful_votes").select("*").eq("review_id", review_id).eq("user_id", user_id).execute()
            if existing_vote.data:
                raise HTTPException(400, "已标记过该评价")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            user_votes = [v for v in review_helpful_votes_storage.values() if v.get("review_id") == review_id and v.get("user_id") == user_id]
            if user_votes:
                raise HTTPException(400, "已标记过该评价")
        
        # 创建点赞记录
        vote_data = {
            "id": str(uuid.uuid4()),
            "review_id": review_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("review_helpful_votes").insert(vote_data).execute()
        except Exception:
            review_helpful_votes_storage[vote_data["id"]] = vote_data
        
        # 更新评价的有帮助计数
        new_count = review.get("helpful_count", 0) + 1
        try:
            supabase.table("reviews").update({"helpful_count": new_count}).eq("id", review_id).execute()
        except Exception:
            if review_id in reviews_storage:
                reviews_storage[review_id]["helpful_count"] = new_count
        
        print(f"✅ 评价点赞成功: {review_id} - 用户 {user_id}")
        
        return SuccessResponse(
            message="标记成功",
            data={"helpful_count": new_count}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"标记评价失败: {str(e)}"
        )

@router.get("/stats/summary")
async def get_review_stats_summary(current_user: UserProfile = Depends(get_current_user)):
    """获取评价统计摘要"""
    try:
        user_id = current_user.id
        
        # 从数据库获取用户的所有评价
        try:
            reviews_result = supabase.table("reviews").select("*").eq("user_id", user_id).execute()
            user_reviews = reviews_result.data if reviews_result.data else []
        except Exception:
            user_reviews = [r for r in reviews_storage.values() if r.get("user_id") == user_id]
        
        # 计算统计信息
        total_reviews = len(user_reviews)
        average_rating = round(sum(r.get("rating", 0) for r in user_reviews) / total_reviews, 1) if total_reviews > 0 else 0
        
        # 评分分布
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in user_reviews:
            rating = review.get("rating", 0)
            if 1 <= rating <= 5:
                rating_distribution[rating] += 1
        
        # 获取总点赞数
        total_helpful = sum(r.get("helpful_count", 0) for r in user_reviews)
        
        # 获取最近评价
        recent_reviews = sorted(user_reviews, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        
        stats = {
            "summary": {
                "total_reviews": total_reviews,
                "average_rating": average_rating,
                "total_helpful_votes": total_helpful,
                "first_review_date": min([r.get("created_at") for r in user_reviews]) if user_reviews else None
            },
            "rating_distribution": rating_distribution,
            "recent_activity": {
                "last_30_days_reviews": len([r for r in user_reviews if datetime.fromisoformat(r.get("created_at", "2000-01-01")) >= datetime.now() - timedelta(days=30)]),
                "recent_reviews": recent_reviews
            }
        }
        
        return SuccessResponse(
            message="评价统计获取成功",
            data=stats
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评价统计失败: {str(e)}"
        )

# 商家回复端点（模拟商家操作）
@router.post("/{review_id}/reply")
async def add_review_reply(
    review_id: str,
    content: str = Query(..., description="回复内容"),
    current_user: UserProfile = Depends(get_current_user)
):
    """商家回复评价"""
    try:
        # 检查评价是否存在
        try:
            review_result = supabase.table("reviews").select("*").eq("id", review_id).execute()
            if not review_result.data:
                raise HTTPException(404, "评价不存在")
            review = review_result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            review = reviews_storage.get(review_id)
            if not review:
                raise HTTPException(404, "评价不存在")
        
        # 检查是否已回复
        try:
            existing_reply = supabase.table("review_replies").select("*").eq("review_id", review_id).execute()
            if existing_reply.data:
                raise HTTPException(400, "已回复过该评价")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            if review_id in review_replies_storage:
                raise HTTPException(400, "已回复过该评价")
        
        # 创建回复
        reply_data = {
            "id": str(uuid.uuid4()),
            "review_id": review_id,
            "merchant_id": review.get("merchant_id"),
            "content": content,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("review_replies").insert(reply_data).execute()
        except Exception:
            review_replies_storage[review_id] = [reply_data]
        
        print(f"✅ 评价回复成功: {review_id} - 商家 {review.get('merchant_id')}")
        
        return SuccessResponse(message="回复成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回复评价失败: {str(e)}"
        )

# 开发环境调试端点
@router.get("/debug/data")
async def debug_review_data(current_user: UserProfile = Depends(get_current_user)):
    """查看评价数据（仅开发环境）"""
    user_id = current_user.id
    
    user_reviews = [r for r in reviews_storage.values() if r.get("user_id") == user_id]
    
    return {
        "reviews": user_reviews,
        "review_ratings": review_ratings_storage,
        "helpful_votes": review_helpful_votes_storage,
        "replies": review_replies_storage,
        "mock_orders": MOCK_ORDERS,
        "mock_merchants": MOCK_MERCHANTS
    }