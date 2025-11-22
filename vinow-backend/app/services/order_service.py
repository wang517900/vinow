# app/services/order_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import supabase
from app.models.order import OrderInDB, OrderCreate, OrderUpdate, OrderStatus, OrderListItem
from app.models.verification import VerificationRecordCreate
import logging

logger = logging.getLogger(__name__)

class OrderService:
    """订单服务类"""
    
    @staticmethod
    async def create_order(order_data: OrderCreate) -> Optional[OrderInDB]:
        """创建新订单"""
        try:
            # 生成订单数据
            order_dict = order_data.model_dump()
            order_dict["created_at"] = datetime.now().isoformat()
            order_dict["updated_at"] = datetime.now().isoformat()
            
            # 插入数据库
            response = supabase.table("orders").insert(order_dict).execute()
            
            if response.data:
                return OrderInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return None
    
    @staticmethod
    async def get_order_by_id(order_id: str) -> Optional[OrderInDB]:
        """根据ID获取订单"""
        try:
            response = supabase.table("orders").select("*").eq("id", order_id).execute()
            
            if response.data:
                return OrderInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取订单失败: {e}")
            return None
    
    @staticmethod
    async def get_order_by_number(order_number: str) -> Optional[OrderInDB]:
        """根据订单号获取订单"""
        try:
            response = supabase.table("orders").select("*").eq("order_number", order_number).execute()
            
            if response.data:
                return OrderInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取订单失败: {e}")
            return None
    
    @staticmethod
    async def list_orders(
        merchant_id: str,
        status: Optional[OrderStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> tuple[List[OrderListItem], int]:
        """获取订单列表"""
        try:
            query = supabase.table("orders").select("*", count="exact").eq("merchant_id", merchant_id)
            
            # 状态筛选
            if status:
                query = query.eq("status", status)
            
            # 时间筛选
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            # 搜索条件
            if search:
                query = query.or_(f"order_number.ilike.%{search}%,user_phone.ilike.%{search}%,product_name.ilike.%{search}%")
            
            # 分页和排序
            start_index = (page - 1) * page_size
            response = query.order("created_at", desc=True).range(start_index, start_index + page_size - 1).execute()
            
            orders = [OrderListItem(**item) for item in response.data]
            total_count = response.count or 0
            
            return orders, total_count
            
        except Exception as e:
            logger.error(f"获取订单列表失败: {e}")
            return [], 0
    
    @staticmethod
    async def update_order_status(order_id: str, status: OrderStatus, **kwargs) -> Optional[OrderInDB]:
        """更新订单状态"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            # 根据状态设置特定时间字段
            if status == OrderStatus.VERIFIED:
                update_data["verified_at"] = datetime.now().isoformat()
            elif status == OrderStatus.REFUNDED:
                update_data["refunded_at"] = datetime.now().isoformat()
            
            # 添加其他更新字段
            update_data.update(kwargs)
            
            response = supabase.table("orders").update(update_data).eq("id", order_id).execute()
            
            if response.data:
                return OrderInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"更新订单状态失败: {e}")
            return None
    
    @staticmethod
    async def get_today_stats(merchant_id: str) -> Dict[str, Any]:
        """获取今日统计数据"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 今日订单总数
            total_response = supabase.table("orders").select("id", count="exact").eq("merchant_id", merchant_id).gte("created_at", today_start.isoformat()).lte("created_at", today_end.isoformat()).execute()
            
            # 待核销订单数
            pending_response = supabase.table("orders").select("id", count="exact").eq("merchant_id", merchant_id).eq("status", OrderStatus.PENDING).gte("created_at", today_start.isoformat()).lte("created_at", today_end.isoformat()).execute()
            
            # 已完成金额
            completed_response = supabase.table("orders").select("paid_amount").eq("merchant_id", merchant_id).eq("status", OrderStatus.VERIFIED).gte("created_at", today_start.isoformat()).lte("created_at", today_end.isoformat()).execute()
            
            total_orders = total_response.count or 0
            pending_orders = pending_response.count or 0
            completed_amount = sum(item["paid_amount"] for item in completed_response.data)
            
            # 计算核销率
            verification_rate = 0
            if total_orders > 0:
                verified_orders = total_orders - pending_orders
                verification_rate = round((verified_orders / total_orders) * 100, 2)
            
            return {
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "completed_amount": completed_amount,
                "verification_rate": verification_rate
            }
            
        except Exception as e:
            logger.error(f"获取今日统计失败: {e}")
            return {
                "total_orders": 0,
                "pending_orders": 0,
                "completed_amount": 0,
                "verification_rate": 0
            }
    
    @staticmethod
    async def get_recent_orders(merchant_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近订单"""
        try:
            response = supabase.table("orders").select("order_number, product_name, paid_amount, created_at").eq("merchant_id", merchant_id).order("created_at", desc=True).limit(limit).execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"获取最近订单失败: {e}")
            return []

order_service = OrderService()"""商家系统 - order_service"""

# TODO: 实现商家系统相关功能


商家系统

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from app.database import supabase
from app.models.order import Order, OrderItem, OrderStatus, OrderStatistics
from app.schemas.order import OrderCreate, OrderUpdate, OrderQueryParams
from app.utils.id_generator import IdGenerator
from app.utils.logger import OrderLogger
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class OrderService:
    """订单服务"""
    
    def __init__(self):
        self.table = "orders"
        self.items_table = "order_items"
    
    async def create_order(self, order_data: OrderCreate, user_id: str) -> Order:
        """创建订单"""
        try:
            # 计算订单金额
            total_amount = sum(item.unit_price * item.quantity for item in order_data.items)
            discount_amount = 0  # 可根据业务规则计算折扣
            final_amount = total_amount - discount_amount
            
            # 生成订单号
            order_number = IdGenerator.generate_order_number()
            
            # 设置过期时间
            expires_at = datetime.now() + timedelta(minutes=settings.order_timeout_minutes)
            
            # 创建订单记录
            order_record = {
                "order_number": order_number,
                "user_id": user_id,
                "merchant_id": order_data.merchant_id,
                "status": OrderStatus.PENDING.value,
                "total_amount": total_amount,
                "discount_amount": discount_amount,
                "final_amount": final_amount,
                "currency": "VND",
                "shipping_address": order_data.shipping_address,
                "contact_info": order_data.contact_info,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 插入订单
            response = supabase.table(self.table).insert(order_record).execute()
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create order"
                )
            
            order_id = response.data[0]["id"]
            
            # 创建订单项
            order_items = []
            for item in order_data.items:
                item_total = item.unit_price * item.quantity
                item_record = {
                    "order_id": order_id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "product_image": item.product_image,
                    "unit_price": item.unit_price,
                    "quantity": item.quantity,
                    "total_price": item_total,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                order_items.append(item_record)
            
            # 批量插入订单项
            supabase.table(self.items_table).insert(order_items).execute()
            
            # 获取完整的订单数据
            complete_order = await self.get_order_by_id(order_id, user_id)
            
            # 记录日志
            OrderLogger.log_order_creation(order_id, user_id, final_amount)
            
            return complete_order
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create order: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def get_order_by_id(self, order_id: str, user_id: str) -> Order:
        """根据ID获取订单"""
        try:
            # 查询订单
            response = supabase.table(self.table).select("*").eq("id", order_id).execute()
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found"
                )
            
            order_data = response.data[0]
            
            # 权限检查
            if order_data["user_id"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
            
            # 查询订单项
            items_response = supabase.table(self.items_table).select("*").eq("order_id", order_id).execute()
            order_items = [OrderItem(**item) for item in items_response.data]
            
            # 构建订单对象
            order = Order(
                **order_data,
                items=order_items
            )
            
            return order
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get order: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def update_order_status(self, order_id: str, status: OrderStatus, user_id: str, reason: Optional[str] = None) -> Order:
        """更新订单状态"""
        try:
            # 获取当前订单
            current_order = await self.get_order_by_id(order_id, user_id)
            
            # 验证状态转换
            if not self._is_valid_status_transition(current_order.status, status):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status transition from {current_order.status} to {status}"
                )
            
            # 准备更新数据
            update_data = {
                "status": status.value,
                "updated_at": datetime.now().isoformat()
            }
            
            # 根据状态设置时间戳
            if status == OrderStatus.PAID:
                update_data["paid_at"] = datetime.now().isoformat()
            elif status == OrderStatus.COMPLETED:
                update_data["completed_at"] = datetime.now().isoformat()
            elif status == OrderStatus.CANCELLED:
                update_data["cancelled_at"] = datetime.now().isoformat()
                if reason:
                    update_data["cancellation_reason"] = reason
            
            # 更新订单
            response = supabase.table(self.table).update(update_data).eq("id", order_id).execute()
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update order status"
                )
            
            # 记录状态变更
            OrderLogger.log_order_status_change(order_id, current_order.status.value, status.value)
            
            return await self.get_order_by_id(order_id, user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update order status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def list_orders(self, query_params: OrderQueryParams, user_id: str) -> Dict[str, Any]:
        """查询订单列表"""
        try:
            # 构建查询
            query = supabase.table(self.table).select("*", count="exact")
            
            # 添加过滤条件
            query = query.eq("user_id", user_id)
            
            if query_params.status:
                query = query.eq("status", query_params.status.value)
            if query_params.merchant_id:
                query = query.eq("merchant_id", query_params.merchant_id)
            if query_params.start_date:
                query = query.gte("created_at", query_params.start_date.isoformat())
            if query_params.end_date:
                query = query.lte("created_at", query_params.end_date.isoformat())
            if query_params.search:
                query = query.ilike("order_number", f"%{query_params.search}%")
            
            # 添加排序和分页
            query = query.order("created_at", desc=True)
            start_idx = (query_params.page - 1) * query_params.size
            query = query.range(start_idx, start_idx + query_params.size - 1)
            
            # 执行查询
            response = query.execute()
            
            # 构建响应
            orders = []
            for order_data in response.data:
                # 获取订单项
                items_response = supabase.table(self.items_table).select("*").eq("order_id", order_data["id"]).execute()
                order_items = [OrderItem(**item) for item in items_response.data]
                
                order = Order(**order_data, items=order_items)
                orders.append(order)
            
            return {
                "items": orders,
                "total": response.count or 0,
                "page": query_params.page,
                "size": query_params.size,
                "has_next": (response.count or 0) > start_idx + query_params.size
            }
            
        except Exception as e:
            logger.error(f"Failed to list orders: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def get_order_statistics(self, user_id: str, days: int = 30) -> OrderStatistics:
        """获取订单统计"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 查询基础统计
            response = supabase.table(self.table).select(
                "status, total_amount, final_amount"
            ).eq(
                "user_id", user_id
            ).gte(
                "created_at", start_date.isoformat()
            ).execute()
            
            orders = response.data
            
            # 计算统计指标
            total_orders = len(orders)
            total_amount = sum(order["final_amount"] for order in orders)
            
            status_counts = {}
            for order in orders:
                status = order["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            average_order_value = total_amount / total_orders if total_orders > 0 else 0
            
            return OrderStatistics(
                total_orders=total_orders,
                total_amount=total_amount,
                pending_orders=status_counts.get(OrderStatus.PENDING.value, 0),
                completed_orders=status_counts.get(OrderStatus.COMPLETED.value, 0),
                cancelled_orders=status_counts.get(OrderStatus.CANCELLED.value, 0),
                average_order_value=average_order_value
            )
            
        except Exception as e:
            logger.error(f"Failed to get order statistics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    def _is_valid_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """验证状态转换是否有效"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.CONFIRMED, OrderStatus.REFUNDED],
            OrderStatus.CONFIRMED: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
            OrderStatus.COMPLETED: [],
            OrderStatus.CANCELLED: [],
            OrderStatus.REFUNDED: []
        }
        
        return new_status in valid_transitions.get(current_status, [])