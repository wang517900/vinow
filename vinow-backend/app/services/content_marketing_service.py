# app/content_marketing/services.py
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.database import supabase
from app.content_marketing.models import (
    ContentInDB, ContentCreate, ContentUpdate, ContentStats,
    CollaborationInDB, CollaborationCreate, CollaborationStatus,
    CollaborationApplicationInDB, CollaborationApplicationCreate, ApplicationStatus,
    ContentMarketingDashboard, ContentType, ContentStatus
)
import logging
import uuid

logger = logging.getLogger(__name__)

class ContentMarketingService:
    """内容营销服务类"""
    
    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
    
    # ===== 内容管理相关方法 =====
    
    async def create_content(self, content_data: ContentCreate) -> Optional[ContentInDB]:
        """创建内容"""
        try:
            content_dict = content_data.model_dump()
            content_dict["tracking_code"] = f"CONTENT_{uuid.uuid4()}"
            content_dict["created_at"] = datetime.now().isoformat()
            content_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_contents").insert(content_dict).execute()
            
            if response.data:
                return ContentInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建内容失败: {e}")
            return None
    
    async def get_content(self, content_id: str) -> Optional[ContentInDB]:
        """获取内容详情"""
        try:
            response = supabase.table("merchant_orders.cm_contents").select("*").eq("id", content_id).eq("merchant_id", self.merchant_id).execute()
            
            if response.data:
                return ContentInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取内容失败: {e}")
            return None
    
    async def list_contents(
        self,
        content_type: Optional[ContentType] = None,
        status: Optional[ContentStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ContentInDB], int]:
        """获取内容列表"""
        try:
            query = supabase.table("merchant_orders.cm_contents").select("*", count="exact").eq("merchant_id", self.merchant_id)
            
            if content_type:
                query = query.eq("content_type", content_type)
            if status:
                query = query.eq("status", status)
            
            start_index = (page - 1) * page_size
            response = query.order("created_at", desc=True).range(start_index, start_index + page_size - 1).execute()
            
            contents = [ContentInDB(**item) for item in response.data]
            total_count = response.count or 0
            
            return contents, total_count
            
        except Exception as e:
            logger.error(f"获取内容列表失败: {e}")
            return [], 0
    
    async def update_content(self, content_id: str, update_data: ContentUpdate) -> Optional[ContentInDB]:
        """更新内容"""
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_contents").update(update_dict).eq("id", content_id).eq("merchant_id", self.merchant_id).execute()
            
            if response.data:
                return ContentInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"更新内容失败: {e}")
            return None
    
    async def get_content_stats(self, content_id: str, days: int = 30) -> Dict[str, Any]:
        """获取内容统计数据"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 获取历史统计数据
            stats_response = supabase.table("merchant_orders.cm_content_stats").select("*").eq("content_id", content_id).gte("stat_date", start_date.date()).execute()
            
            # 计算总计
            total_views = sum(item["view_count"] for item in stats_response.data)
            total_orders = sum(item["order_count"] for item in stats_response.data)
            total_revenue = sum(item["revenue_amount"] for item in stats_response.data)
            
            # 获取趋势数据
            trends = [
                {
                    "date": item["stat_date"],
                    "views": item["view_count"],
                    "orders": item["order_count"],
                    "revenue": float(item["revenue_amount"])
                }
                for item in stats_response.data
            ]
            
            return {
                "total_views": total_views,
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "trends": sorted(trends, key=lambda x: x["date"])
            }
            
        except Exception as e:
            logger.error(f"获取内容统计失败: {e}")
            return {"total_views": 0, "total_orders": 0, "total_revenue": 0, "trends": []}
    
    # ===== 合作任务相关方法 =====
    
    async def create_collaboration(self, collaboration_data: CollaborationCreate) -> Optional[CollaborationInDB]:
        """创建合作任务"""
        try:
            collaboration_dict = collaboration_data.model_dump()
            collaboration_dict["status"] = CollaborationStatus.RECRUITING
            collaboration_dict["created_at"] = datetime.now().isoformat()
            collaboration_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_collaborations").insert(collaboration_dict).execute()
            
            if response.data:
                return CollaborationInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建合作任务失败: {e}")
            return None
    
    async def list_collaborations(
        self,
        status: Optional[CollaborationStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CollaborationInDB], int]:
        """获取合作任务列表"""
        try:
            query = supabase.table("merchant_orders.cm_collaborations").select("*", count="exact").eq("merchant_id", self.merchant_id)
            
            if status:
                query = query.eq("status", status)
            
            start_index = (page - 1) * page_size
            response = query.order("created_at", desc=True).range(start_index, start_index + page_size - 1).execute()
            
            collaborations = [CollaborationInDB(**item) for item in response.data]
            total_count = response.count or 0
            
            return collaborations, total_count
            
        except Exception as e:
            logger.error(f"获取合作任务列表失败: {e}")
            return [], 0
    
    async def create_application(self, application_data: CollaborationApplicationCreate) -> Optional[CollaborationApplicationInDB]:
        """创建合作申请"""
        try:
            application_dict = application_data.model_dump()
            application_dict["applied_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_collaboration_applications").insert(application_dict).execute()
            
            if response.data:
                return CollaborationApplicationInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建合作申请失败: {e}")
            return None
    
    async def list_applications(
        self,
        collaboration_id: Optional[str] = None,
        status: Optional[ApplicationStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CollaborationApplicationInDB], int]:
        """获取合作申请列表"""
        try:
            query = supabase.table("merchant_orders.cm_collaboration_applications").select("*", count="exact").eq("merchant_id", self.merchant_id)
            
            if collaboration_id:
                query = query.eq("collaboration_id", collaboration_id)
            if status:
                query = query.eq("status", status)
            
            start_index = (page - 1) * page_size
            response = query.order("applied_at", desc=True).range(start_index, start_index + page_size - 1).execute()
            
            applications = [CollaborationApplicationInDB(**item) for item in response.data]
            total_count = response.count or 0
            
            return applications, total_count
            
        except Exception as e:
            logger.error(f"获取合作申请列表失败: {e}")
            return [], 0
    
    async def update_application_status(
        self, 
        application_id: str, 
        status: ApplicationStatus,
        final_content_id: Optional[str] = None
    ) -> Optional[CollaborationApplicationInDB]:
        """更新申请状态"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if status == ApplicationStatus.ACCEPTED:
                update_data["accepted_at"] = datetime.now().isoformat()
            elif status == ApplicationStatus.COMPLETED:
                update_data["completed_at"] = datetime.now().isoformat()
            
            if final_content_id:
                update_data["final_content_id"] = final_content_id
            
            response = supabase.table("merchant_orders.cm_collaboration_applications").update(update_data).eq("id", application_id).eq("merchant_id", self.merchant_id).execute()
            
            if response.data:
                return CollaborationApplicationInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"更新申请状态失败: {e}")
            return None
    
    # ===== 数据看板相关方法 =====
    
    async def get_dashboard_data(self) -> ContentMarketingDashboard:
        """获取内容营销数据看板"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 获取今日通过内容带来的订单
            today_orders_response = supabase.table("merchant_orders.cm_order_tracking").select("order_amount").eq("merchant_id", self.merchant_id).gte("created_at", today_start.isoformat()).lte("created_at", today_end.isoformat()).execute()
            
            today_orders = len(today_orders_response.data)
            today_revenue = sum(item["order_amount"] for item in today_orders_response.data)
            
            # 获取热门内容TOP3（按收入排序）
            top_contents_response = supabase.table("merchant_orders.cm_content_stats").select("content_id, revenue_amount, cm_contents(title, content_type)").eq("merchant_id", self.merchant_id).gte("stat_date", (datetime.now() - timedelta(days=7)).date()).execute()
            
            # 按内容ID分组统计
            content_revenue = {}
            for item in top_contents_response.data:
                content_id = item["content_id"]
                if content_id not in content_revenue:
                    content_revenue[content_id] = {
                        "content_id": content_id,
                        "revenue": 0,
                        "title": item.get("cm_contents", [{}])[0].get("title", "未知") if item.get("cm_contents") else "未知",
                        "type": item.get("cm_contents", [{}])[0].get("content_type", "未知") if item.get("cm_contents") else "未知"
                    }
                content_revenue[content_id]["revenue"] += float(item["revenue_amount"])
            
            top_contents = sorted(content_revenue.values(), key=lambda x: x["revenue"], reverse=True)[:3]
            
            # 获取待处理申请数
            pending_applications_response = supabase.table("merchant_orders.cm_collaboration_applications").select("id", count="exact").eq("merchant_id", self.merchant_id).eq("status", ApplicationStatus.APPLIED).execute()
            
            # 获取进行中合作数
            active_collaborations_response = supabase.table("merchant_orders.cm_collaborations").select("id", count="exact").eq("merchant_id", self.merchant_id).eq("status", CollaborationStatus.IN_PROGRESS).execute()
            
            # 简化计算ROI（实际中需要更复杂的计算）
            total_revenue_response = supabase.table("merchant_orders.cm_content_stats").select("revenue_amount").eq("merchant_id", self.merchant_id).execute()
            total_revenue = sum(float(item["revenue_amount"]) for item in total_revenue_response.data)
            
            # 假设投入为总收入的10%（实际中需要根据实际投入计算）
            roi = (total_revenue - (total_revenue * 0.1)) / (total_revenue * 0.1) if total_revenue > 0 else 0
            
            return ContentMarketingDashboard(
                today_orders=today_orders,
                today_revenue=today_revenue,
                top_contents=top_contents,
                roi=round(roi, 2),
                pending_applications=pending_applications_response.count or 0,
                active_collaborations=active_collaborations_response.count or 0
            )
            
        except Exception as e:
            logger.error(f"获取数据看板失败: {e}")
            return ContentMarketingDashboard()