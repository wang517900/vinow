商家系统7评价管理
"""
评价相关数据库操作类

本模块提供了对商户评价数据的增删改查操作，包括：
- 评价列表查询与过滤
- 新评价创建
- 评价统计数据获取
- 评价状态更新
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import Client
from app.schemas.review import ReviewCreate, ReviewUpdate
import math

class ReviewCRUD:
    """
    评价数据访问层类
    
    负责处理与评价相关的数据库操作
    """
    
    def __init__(self, db: Client):
        """
        初始化评价数据访问对象
        
        Args:
            db (Client): Supabase数据库客户端实例
        """
        self.db = db

    async def get_reviews(
        self, 
        merchant_id: int, 
        page: int = 1, 
        limit: int = 20,
        rating: Optional[int] = None,
        date_range: Optional[str] = None,
        has_reply: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        获取商户的评价列表，支持多种过滤条件和分页
        
        Args:
            merchant_id (int): 商户ID
            page (int): 页码，默认为1
            limit (int): 每页数量，默认为20
            rating (Optional[int]): 评分过滤条件（1-5星）
            date_range (Optional[str]): 时间范围过滤（today/week/month/year）
            has_reply (Optional[bool]): 是否有回复过滤条件
            
        Returns:
            Dict[str, Any]: 包含评价列表和分页信息的字典
        """
        # 构建基础查询条件：指定商户且状态为活跃的评价
        query = self.db.table("merchant_reviews").select("*")
        query = query.eq("merchant_id", merchant_id).eq("status", "active")
        
        # 应用评分过滤器
        if rating:
            query = query.eq("rating", rating)
            
        # 应用时间范围过滤器
        if date_range:
            # 设置结束时间为当前时间
            end_date = datetime.utcnow()
            
            # 根据不同时间范围计算起始时间
            if date_range == "today":
                # 今天：当天0点开始
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_range == "week":
                # 最近一周
                start_date = end_date - timedelta(days=7)
            elif date_range == "month":
                # 最近一个月
                start_date = end_date - timedelta(days=30)
            else:
                # 默认：最近一年
                start_date = end_date - timedelta(days=365)
            
            # 应用时间范围查询条件
            query = query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        
        # 获取符合条件的总记录数
        count_query = query
        count_result = count_query.execute()
        total = len(count_result.data) if count_result.data else 0
        
        # 应用分页：计算起始索引并设置查询范围
        start_index = (page - 1) * limit
        query = query.range(start_index, start_index + limit - 1)
        
        # 按创建时间倒序排列（最新的在前）
        query = query.order("created_at", desc=True)
        
        # 执行查询获取评价数据
        result = query.execute()
        reviews = result.data if result.data else []
        
        # 处理每条评论的回复信息
        reviews_with_reply = []
        for review in reviews:
            # 查询该评价是否有回复
            reply_result = self.db.table("review_replies").select("*").eq("review_id", review["id"]).execute()
            has_reply_flag = len(reply_result.data) > 0 if reply_result.data else False
            
            # 如果有回复，获取第一条回复的内容和创建时间
            reply_content = None
            reply_created_at = None
            if has_reply_flag and reply_result.data:
                reply_content = reply_result.data[0].get("content")
                reply_created_at = reply_result.data[0].get("created_at")
            
            # 检查是否满足has_reply过滤条件，不满足则跳过该评价
            if has_reply is not None:
                if has_reply != has_reply_flag:
                    continue
            
            # 构造包含回复信息的评价数据
            review_data = {
                **review,
                "has_reply": has_reply_flag,
                "reply_content": reply_content,
                "reply_created_at": reply_created_at
            }
            reviews_with_reply.append(review_data)
        
        # 返回包含评价列表和分页信息的结果
        return {
            "reviews": reviews_with_reply,
            "total": total,
            "page": page,
            "limit": limit
        }

    async def create_review(self, review: ReviewCreate) -> Dict[str, Any]:
        """
        创建新的评价记录
        
        Args:
            review (ReviewCreate): 评价创建请求数据
            
        Returns:
            Dict[str, Any]: 创建成功的评价数据，失败返回None
        """
        # 将Pydantic模型转换为字典并插入数据库
        result = self.db.table("merchant_reviews").insert(review.model_dump()).execute()
        
        # 如果插入成功，返回第一条数据；否则返回None
        if result.data:
            return result.data[0]
        return None

    async def get_review_summary(self, merchant_id: int) -> Dict[str, Any]:
        """
        获取商户评价统计摘要信息
        
        Args:
            merchant_id (int): 商户ID
            
        Returns:
            Dict[str, Any]: 包含各种统计信息的字典
        """
        # 计算今日评价数：从今天0点开始的评价
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = self.db.table("merchant_reviews").select(
            "id", count="exact"
        ).eq("merchant_id", merchant_id).eq("status", "active").gte(
            "created_at", today_start.isoformat()
        ).execute()
        
        today_reviews = len(today_result.data) if today_result.data else 0
        
        # 计算待回复评价数：查找没有回复的活跃评价
        pending_result = self.db.table("merchant_reviews").select(
            "id"
        ).eq("merchant_id", merchant_id).eq("status", "active").execute()
        
        pending_count = 0
        if pending_result.data:
            for review in pending_result.data:
                # 检查该评价是否有回复
                reply_result = self.db.table("review_replies").select("id").eq("review_id", review["id"]).execute()
                if not reply_result.data:
                    pending_count += 1
        
        # 获取评价统计信息：平均评分、回复率、周趋势等
        stats_result = self.db.table("review_statistics").select("*").eq("merchant_id", merchant_id).execute()
        if stats_result.data:
            stats = stats_result.data[0]
            average_rating = stats.get("average_rating", 0.0)
            reply_rate = stats.get("reply_rate", 0.0)
            weekly_trend = stats.get("last_7_days_trend", 0.0)
        else:
            # 如果没有统计数据，则使用默认值
            average_rating = 0.0
            reply_rate = 0.0
            weekly_trend = 0.0
        
        # 返回格式化的统计摘要信息
        return {
            "today_reviews": today_reviews,           # 今日新增评价数
            "pending_replies": pending_count,         # 待回复评价数
            "average_rating": round(average_rating, 1),  # 平均评分（保留1位小数）
            "reply_rate": round(reply_rate, 2),       # 回复率（保留2位小数）
            "weekly_trend": round(weekly_trend, 1)    # 周趋势（保留1位小数）
        }

    async def update_review_status(self, review_id: int, merchant_id: int, status: str) -> bool:
        """
        更新评价的状态
        
        Args:
            review_id (int): 评价ID
            merchant_id (int): 商户ID
            status (str): 新的状态值（active/hidden/deleted）
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        # 执行更新操作，同时更新状态和更新时间
        result = self.db.table("merchant_reviews").update(
            {"status": status, "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", review_id).eq("merchant_id", merchant_id).execute()
        
        # 根据更新结果判断是否成功
        return len(result.data) > 0 if result.data else False