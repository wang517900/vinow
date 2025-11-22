# [文件: app/analytics/router.py] [行号: 1001-1200]
"""
数据分析路由 - v1.5.0
完整的用户行为分析、消费分析、数据报告功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta
from collections import Counter

from app.common.database import supabase
from app.common.models import (
    AnalyticsRequest, AnalyticsPeriod, UserAnalytics, 
    SuccessResponse, UserProfile
)
from app.common.auth import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# 模拟数据存储（生产环境用数据库）
user_analytics_storage = {}
user_events_storage = {}
monthly_reports_storage = {}

# 模拟事件类型
EVENT_TYPES = [
    "view_merchant", "view_product", "search", "add_to_favorite",
    "remove_favorite", "place_order", "cancel_order", "write_review",
    "view_order", "update_profile", "login", "logout"
]

def record_user_event(user_id: str, event_type: str, event_data: Dict[str, Any] = None):
    """记录用户事件"""
    event_data = event_data or {}
    
    event = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": event_type,
        "event_data": event_data,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        supabase.table("user_events").insert(event).execute()
    except Exception:
        if user_id not in user_events_storage:
            user_events_storage[user_id] = []
        user_events_storage[user_id].append(event)

def get_user_events(user_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """获取用户事件"""
    since_date = datetime.now() - timedelta(days=days)
    
    try:
        result = supabase.table("user_events").select("*").eq("user_id", user_id).gte("created_at", since_date.isoformat()).execute()
        return result.data if result.data else []
    except Exception:
        events = user_events_storage.get(user_id, [])
        return [e for e in events if datetime.fromisoformat(e.get("created_at", "2000-01-01")) >= since_date]

def generate_monthly_report(user_id: str, year: int, month: int) -> Dict[str, Any]:
    """生成月度报告"""
    # 计算月份的开始和结束
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year+1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month+1, 1) - timedelta(days=1)
    
    # 获取该月的订单
    try:
        orders_result = supabase.table("orders").select("*").eq("user_id", user_id).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).execute()
        orders = orders_result.data if orders_result.data else []
    except Exception:
        orders = [o for o in orders_storage.values() if o.get("user_id") == user_id and start_date <= datetime.fromisoformat(o.get("created_at", "2000-01-01")) <= end_date]
    
    # 获取该月的评价
    try:
        reviews_result = supabase.table("reviews").select("*").eq("user_id", user_id).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).execute()
        reviews = reviews_result.data if reviews_result.data else []
    except Exception:
        reviews = [r for r in reviews_storage.values() if r.get("user_id") == user_id and start_date <= datetime.fromisoformat(r.get("created_at", "2000-01-01")) <= end_date]
    
    # 获取该月的事件
    events = get_user_events(user_id, days=(end_date - start_date).days + 10)  # 多取几天确保覆盖
    month_events = [e for e in events if start_date <= datetime.fromisoformat(e.get("created_at", "2000-01-01")) <= end_date]
    
    # 计算统计
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.get("status") == "completed"])
    cancelled_orders = len([o for o in orders if o.get("status") == "cancelled"])
    total_spent = sum(o.get("final_amount", 0) for o in orders if o.get("status") == "completed")
    money_saved = sum(o.get("discount_amount", 0) for o in orders)
    
    # 事件统计
    event_counts = Counter(e.get("event_type") for e in month_events)
    
    # 最喜欢的商家（按订单数）
    merchant_orders = Counter(o.get("merchant_id") for o in orders)
    favorite_merchant = merchant_orders.most_common(1)
    favorite_merchant_id = favorite_merchant[0][0] if favorite_merchant else None
    favorite_merchant_name = MOCK_MERCHANTS.get(favorite_merchant_id, {}).get("name") if favorite_merchant_id else None
    
    # 生成报告
    report = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "report_month": start_date.strftime("%Y-%m-%d"),
        "orders_count": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_spent": total_spent,
        "money_saved": money_saved,
        "reviews_written": len(reviews),
        "new_merchants_tried": len(set(o.get("merchant_id") for o in orders)),
        "favorite_merchant": favorite_merchant_name,
        "event_summary": dict(event_counts),
        "generated_at": datetime.now().isoformat()
    }
    
    # 保存报告
    try:
        supabase.table("monthly_user_reports").insert(report).execute()
    except Exception:
        if user_id not in monthly_reports_storage:
            monthly_reports_storage[user_id] = []
        monthly_reports_storage[user_id].append(report)
    
    return report

@router.get("/user/overview")
async def get_user_analytics_overview(current_user: UserProfile = Depends(get_current_user)):
    """获取用户数据分析总览"""
    try:
        user_id = current_user.id
        
        # 从数据库获取用户分析数据
        try:
            result = supabase.table("user_analytics").select("*").eq("user_id", user_id).execute()
            analytics = result.data[0] if result.data else None
        except Exception:
            analytics = user_analytics_storage.get(user_id)
        
        if not analytics:
            # 生成默认分析数据
            analytics = await generate_user_analytics(user_id)
        
        return SuccessResponse(
            message="数据分析总览获取成功",
            data=analytics
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据分析总览失败: {str(e)}"
        )

async def generate_user_analytics(user_id: str) -> Dict[str, Any]:
    """生成用户分析数据"""
    # 获取用户的所有订单
    try:
        orders_result = supabase.table("orders").select("*").eq("user_id", user_id).execute()
        orders = orders_result.data if orders_result.data else []
    except Exception:
        orders = [o for o in orders_storage.values() if o.get("user_id") == user_id]
    
    # 获取用户的所有评价
    try:
        reviews_result = supabase.table("reviews").select("*").eq("user_id", user_id).execute()
        reviews = reviews_result.data if reviews_result.data else []
    except Exception:
        reviews = [r for r in reviews_storage.values() if r.get("user_id") == user_id]
    
    # 计算统计
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.get("status") == "completed"])
    total_spent = sum(o.get("final_amount", 0) for o in orders if o.get("status") == "completed")
    money_saved = sum(o.get("discount_amount", 0) for o in orders)
    average_rating = round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 1) if reviews else 0
    
    # 获取最常订购的商家
    merchant_orders = Counter(o.get("merchant_id") for o in orders)
    favorite_merchants = [merchant_id for merchant_id, count in merchant_orders.most_common(3)]
    
    # 获取最常点的菜系（从商家信息中获取）
    cuisines = []
    for merchant_id in merchant_orders:
        merchant = MOCK_MERCHANTS.get(merchant_id, {})
        cuisine = merchant.get("cuisine")
        if cuisine:
            cuisines.append(cuisine)
    favorite_cuisines = [cuisine for cuisine, count in Counter(cuisines).most_common(3)]
    
    # 最后订单时间
    last_order = max(orders, key=lambda x: x.get("created_at", ""), default=None)
    last_order_at = last_order.get("created_at") if last_order else None
    
    analytics_data = {
        "user_id": user_id,
        "total_orders": total_orders,
        "total_spent": total_spent,
        "money_saved": money_saved,
        "favorite_cuisines": favorite_cuisines,
        "average_rating": average_rating,
        "review_count": len(reviews),
        "review_helpful_count": sum(r.get("helpful_count", 0) for r in reviews),
        "favorite_merchants": favorite_merchants,
        "last_order_at": last_order_at,
        "updated_at": datetime.now().isoformat()
    }
    
    # 保存到数据库
    try:
        supabase.table("user_analytics").upsert(analytics_data).execute()
    except Exception:
        user_analytics_storage[user_id] = analytics_data
    
    return analytics_data

@router.get("/user/behavior")
async def get_user_behavior_analytics(
    current_user: UserProfile = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    """获取用户行为分析"""
    try:
        user_id = current_user.id
        
        # 获取用户事件
        events = get_user_events(user_id, days=days)
        
        # 事件类型统计
        event_types = Counter(e.get("event_type") for e in events)
        
        # 每日活动统计
        daily_activity = {}
        for event in events:
            date = datetime.fromisoformat(event.get("created_at")).strftime("%Y-%m-%d")
            daily_activity[date] = daily_activity.get(date, 0) + 1
        
        # 最活跃时段
        hour_activity = Counter(datetime.fromisoformat(e.get("created_at")).hour for e in events)
        most_active_hour = hour_activity.most_common(1)[0] if hour_activity else (12, 0)  # 默认中午12点
        
        behavior_data = {
            "period_days": days,
            "total_events": len(events),
            "event_type_breakdown": dict(event_types),
            "daily_activity": daily_activity,
            "most_active_hour": most_active_hour[0],
            "average_events_per_day": round(len(events) / days, 1) if days > 0 else 0
        }
        
        return SuccessResponse(
            message="用户行为分析获取成功",
            data=behavior_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户行为分析失败: {str(e)}"
        )

@router.get("/user/spending")
async def get_user_spending_analytics(
    current_user: UserProfile = Depends(get_current_user),
    months: int = Query(6, ge=1, le=12)
):
    """获取用户消费分析"""
    try:
        user_id = current_user.id
        
        # 获取用户订单
        try:
            orders_result = supabase.table("orders").select("*").eq("user_id", user_id).execute()
            orders = orders_result.data if orders_result.data else []
        except Exception:
            orders = [o for o in orders_storage.values() if o.get("user_id") == user_id]
        
        # 只考虑已完成的订单
        completed_orders = [o for o in orders if o.get("status") == "completed"]
        
        # 按月统计消费
        monthly_spending = {}
        for order in completed_orders:
            order_date = datetime.fromisoformat(order.get("created_at", ""))
            month_key = order_date.strftime("%Y-%m")
            if month_key not in monthly_spending:
                monthly_spending[month_key] = 0
            monthly_spending[month_key] += order.get("final_amount", 0)
        
        # 获取最近N个月的数据
        recent_months = []
        for i in range(months-1, -1, -1):
            date = datetime.now() - timedelta(days=30*i)
            month_key = date.strftime("%Y-%m")
            recent_months.append(month_key)
        
        # 构建响应数据
        spending_data = {
            "analysis_period_months": months,
            "total_spent": sum(monthly_spending.values()),
            "average_monthly_spent": sum(monthly_spending.values()) / len(monthly_spending) if monthly_spending else 0,
            "monthly_breakdown": {month: monthly_spending.get(month, 0) for month in recent_months},
            "total_orders": len(completed_orders),
            "average_order_value": sum(monthly_spending.values()) / len(completed_orders) if completed_orders else 0
        }
        
        return SuccessResponse(
            message="消费分析获取成功",
            data=spending_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取消费分析失败: {str(e)}"
        )

@router.get("/user/influence")
async def get_user_influence_analytics(current_user: UserProfile = Depends(get_current_user)):
    """获取用户影响力分析"""
    try:
        user_id = current_user.id
        
        # 获取用户评价
        try:
            reviews_result = supabase.table("reviews").select("*").eq("user_id", user_id).execute()
            reviews = reviews_result.data if reviews_result.data else []
        except Exception:
            reviews = [r for r in reviews_storage.values() if r.get("user_id") == user_id]
        
        # 计算影响力指标
        total_reviews = len(reviews)
        total_helpful_votes = sum(r.get("helpful_count", 0) for r in reviews)
        average_rating = round(sum(r.get("rating", 0) for r in reviews) / total_reviews, 1) if total_reviews > 0 else 0
        total_views = sum(r.get("view_count", 0) for r in reviews)
        
        # 评价质量评分（基于点赞数和浏览量）
        quality_score = 0
        for review in reviews:
            helpful_count = review.get("helpful_count", 0)
            view_count = review.get("view_count", 0)
            if view_count > 0:
                helpful_ratio = helpful_count / view_count
                quality_score += helpful_ratio * 10  # 放大倍数
        
        # 影响力等级
        influence_level = "初级"
        if quality_score >= 50:
            influence_level = "高级"
        elif quality_score >= 20:
            influence_level = "中级"
        
        influence_data = {
            "total_reviews": total_reviews,
            "total_helpful_votes": total_helpful_votes,
            "average_rating": average_rating,
            "total_views": total_views,
            "quality_score": round(quality_score, 1),
            "influence_level": influence_level,
            "helpful_ratio": round(total_helpful_votes / total_views, 2) if total_views > 0 else 0
        }
        
        return SuccessResponse(
            message="影响力分析获取成功",
            data=influence_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取影响力分析失败: {str(e)}"
        )

@router.get("/user/savings")
async def get_user_savings_analytics(current_user: UserProfile = Depends(get_current_user)):
    """获取用户省钱报告"""
    try:
        user_id = current_user.id
        
        # 获取用户订单
        try:
            orders_result = supabase.table("orders").select("*").eq("user_id", user_id).execute()
            orders = orders_result.data if orders_result.data else []
        except Exception:
            orders = [o for o in orders_storage.values() if o.get("user_id") == user_id]
        
        # 计算省钱统计
        total_savings = sum(o.get("discount_amount", 0) for o in orders)
        completed_orders = [o for o in orders if o.get("status") == "completed"]
        average_saving_per_order = total_savings / len(completed_orders) if completed_orders else 0
        
        # 获取优惠类型分布（模拟数据）
        discount_types = {
            "满减优惠": total_savings * 0.6,
            "新用户优惠": total_savings * 0.2,
            "会员优惠": total_savings * 0.1,
            "节日优惠": total_savings * 0.1
        }
        
        savings_data = {
            "total_savings": total_savings,
            "average_saving_per_order": round(average_saving_per_order, 2),
            "savings_percentage": round((total_savings / (sum(o.get("final_amount", 0) for o in completed_orders) + total_savings)) * 100, 1) if completed_orders else 0,
            "discount_type_breakdown": discount_types,
            "estimated_yearly_savings": total_savings * 12  # 简单估算年节省
        }
        
        return SuccessResponse(
            message="省钱报告获取成功",
            data=savings_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取省钱报告失败: {str(e)}"
        )

@router.post("/events")
async def record_analytics_event(
    event_type: str = Query(..., description="事件类型"),
    event_data: Dict[str, Any] = None,
    current_user: UserProfile = Depends(get_current_user)
):
    """记录用户分析事件"""
    try:
        user_id = current_user.id
        
        if event_type not in EVENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"事件类型必须是: {', '.join(EVENT_TYPES)}"
            )
        
        record_user_event(user_id, event_type, event_data)
        
        return SuccessResponse(message="事件记录成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录事件失败: {str(e)}"
        )

@router.get("/reports/monthly")
async def get_monthly_reports(
    current_user: UserProfile = Depends(get_current_user),
    year: int = Query(None, description="年份"),
    month: int = Query(None, description="月份")
):
    """获取月度报告"""
    try:
        user_id = current_user.id
        
        # 如果指定了年月，生成该月报告；否则获取所有报告
        if year and month:
            report = generate_monthly_report(user_id, year, month)
            return SuccessResponse(
                message="月度报告生成成功",
                data=report
            )
        else:
            # 获取所有月度报告
            try:
                result = supabase.table("monthly_user_reports").select("*").eq("user_id", user_id).execute()
                reports = result.data if result.data else []
            except Exception:
                reports = monthly_reports_storage.get(user_id, [])
            
            # 按月份倒序排序
            reports.sort(key=lambda x: x.get("report_month", ""), reverse=True)
            
            return SuccessResponse(
                message="月度报告列表获取成功",
                data=reports
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取月度报告失败: {str(e)}"
        )

# 开发环境调试端点
@router.get("/debug/events")
async def debug_analytics_events(current_user: UserProfile = Depends(get_current_user)):
    """查看分析事件（仅开发环境）"""
    user_id = current_user.id
    
    return {
        "user_events": user_events_storage.get(user_id, []),
        "user_analytics": user_analytics_storage.get(user_id),
        "monthly_reports": monthly_reports_storage.get(user_id, [])
    }