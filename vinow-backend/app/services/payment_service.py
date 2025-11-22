交易系统

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
import asyncio
import logging
from app.database import supabase
from app.models.order import Order, OrderItem, OrderStatus, OrderStatistics
from app.schemas.order import OrderCreate, OrderUpdate, OrderQueryParams
from app.utils.id_generator_api import IdGenerator
from app.utils.logger_api import OrderLogger, logger
from app.config import settings
from app.utils.cache import cache_get, cache_set

# 创建模块级日志记录器
module_logger = logging.getLogger(__name__)

class OrderService:
    """
    订单服务类
    
    提供订单的创建、查询、更新和统计等核心功能
    处理订单生命周期管理和相关业务逻辑
    """
    
    def __init__(self):
        """初始化订单服务"""
        self.table = "orders"
        self.items_table = "order_items"
        self.max_retries = 3  # 最大重试次数
        
        module_logger.info("order_service_initialized")
    
    async def create_order(self, order_data: OrderCreate, user_id: str) -> Order:
        """
        创建新订单
        
        Args:
            order_data (OrderCreate): 订单创建数据
            user_id (str): 用户ID
            
        Returns:
            Order: 创建的订单对象
            
        Raises:
            HTTPException: 创建失败时抛出相应异常
            
        Example:
            >>> order_create = OrderCreate(
            ...     merchant_id="merchant_123",
            ...     shipping_address="北京市朝阳区xxx街道",
            ...     contact_info={"phone": "13800138000"},
            ...     items=[OrderItemCreate(...)]
            ... )
            >>> order = await order_service.create_order(order_create, "user_123")
        """
        try:
            module_logger.info(
                "order_creation_started",
                user_id=user_id,
                merchant_id=order_data.merchant_id,
                items_count=len(order_data.items)
            )
            
            # 计算订单金额
            total_amount = sum(item.unit_price * item.quantity for item in order_data.items)
            discount_amount = await self._calculate_discount(order_data, user_id)
            final_amount = max(0, total_amount - discount_amount)  # 确保金额不为负
            
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
                "total_amount": float(total_amount),
                "discount_amount": float(discount_amount),
                "final_amount": float(final_amount),
                "currency": order_data.currency or "VND",
                "shipping_address": order_data.shipping_address,
                "contact_info": order_data.contact_info,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 重试机制插入订单
            order_id = None
            for attempt in range(self.max_retries):
                try:
                    response = supabase.table(self.table).insert(order_record).execute()
                    if response.data:
                        order_id = response.data[0]["id"]
                        break
                    elif attempt == self.max_retries - 1:
                        raise Exception("Failed to insert order after retries")
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避
            
            if not order_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create order"
                )
            
            # 创建订单项
            order_items = []
            for idx, item in enumerate(order_data.items):
                item_total = item.unit_price * item.quantity
                item_record = {
                    "order_id": order_id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "product_image": item.product_image,
                    "unit_price": float(item.unit_price),
                    "quantity": item.quantity,
                    "total_price": float(item_total),
                    "sort_order": idx,  # 添加排序字段
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                order_items.append(item_record)
            
            # 批量插入订单项（带重试）
            await self._batch_insert_order_items(order_items)
            
            # 获取完整的订单数据
            complete_order = await self.get_order_by_id(order_id, user_id)
            
            # 记录日志
            OrderLogger.log_order_creation(
                order_id=order_id,
                user_id=user_id,
                amount=float(final_amount),
                items=order_data.items
            )
            
            module_logger.info(
                "order_created_successfully",
                order_id=order_id,
                order_number=order_number,
                user_id=user_id,
                final_amount=float(final_amount)
            )
            
            return complete_order
            
        except HTTPException:
            raise
        except Exception as e:
            module_logger.error(
                "order_creation_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create order: {str(e)}"
            )
    
    async def _batch_insert_order_items(self, order_items: List[Dict]) -> None:
        """
        批量插入订单项（带重试机制）
        
        Args:
            order_items (List[Dict]): 订单项列表
        """
        for attempt in range(self.max_retries):
            try:
                supabase.table(self.items_table).insert(order_items).execute()
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to insert order items: {str(e)}"
                    )
                await asyncio.sleep(0.1 * (2 ** attempt))
    
    async def _calculate_discount(self, order_data: OrderCreate, user_id: str) -> float:
        """
        计算订单折扣金额
        
        Args:
            order_data (OrderCreate): 订单创建数据
            user_id (str): 用户ID
            
        Returns:
            float: 折扣金额
        """
        # 这里可以实现复杂的折扣计算逻辑
        # 例如：会员等级折扣、优惠券折扣、满减活动等
        discount = 0.0
        
        # 示例：根据用户等级给予折扣
        try:
            user_response = supabase.table("users").select("level").eq("id", user_id).execute()
            if user_response.data:
                user_level = user_response.data[0].get("level", "normal")
                if user_level == "vip":
                    discount = sum(item.unit_price * item.quantity for item in order_data.items) * 0.05  # VIP 5% 折扣
                elif user_level == "premium":
                    discount = sum(item.unit_price * item.quantity for item in order_data.items) * 0.02  # Premium 2% 折扣
        except Exception as e:
            module_logger.warning(
                "discount_calculation_failed",
                user_id=user_id,
                error=str(e)
            )
        
        return discount
    
    async def get_order_by_id(self, order_id: str, user_id: str, use_cache: bool = True) -> Order:
        """
        根据ID获取订单详情
        
        Args:
            order_id (str): 订单ID
            user_id (str): 用户ID
            use_cache (bool): 是否使用缓存
            
        Returns:
            Order: 订单对象
            
        Raises:
            HTTPException: 订单不存在或无权限时抛出相应异常
        """
        cache_key = f"order:{order_id}:{user_id}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_order = await cache_get(cache_key)
            if cached_order:
                module_logger.debug("order_loaded_from_cache", order_id=order_id)
                return Order(**cached_order)
        
        try:
            module_logger.debug("order_loading_from_database", order_id=order_id, user_id=user_id)
            
            # 查询订单
            response = supabase.table(self.table).select("*").eq("id", order_id).execute()
            if not response.data:
                module_logger.warning("order_not_found", order_id=order_id, user_id=user_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found"
                )
            
            order_data = response.data[0]
            
            # 权限检查
            if order_data["user_id"] != user_id:
                module_logger.warning(
                    "order_access_denied",
                    order_id=order_id,
                    user_id=user_id,
                    owner_id=order_data["user_id"]
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
            
            # 查询订单项
            items_response = supabase.table(self.items_table).select("*").eq("order_id", order_id).order("sort_order").execute()
            order_items = [OrderItem(**item) for item in items_response.data]
            
            # 构建订单对象
            order = Order(
                **order_data,
                items=order_items
            )
            
            # 缓存订单数据（10分钟）
            await cache_set(cache_key, order.dict(), expire=600)
            
            module_logger.debug("order_loaded_successfully", order_id=order_id)
            
            return order
            
        except HTTPException:
            raise
        except Exception as e:
            module_logger.error(
                "order_loading_failed",
                order_id=order_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def update_order_status(self, order_id: str, status: OrderStatus, user_id: str, 
                                reason: Optional[str] = None, force: bool = False) -> Order:
        """
        更新订单状态
        
        Args:
            order_id (str): 订单ID
            status (OrderStatus): 新状态
            user_id (str): 用户ID
            reason (str, optional): 状态变更原因
            force (bool): 是否强制更新（跳过状态验证）
            
        Returns:
            Order: 更新后的订单对象
            
        Raises:
            HTTPException: 状态更新失败时抛出相应异常
        """
        try:
            module_logger.info(
                "order_status_update_requested",
                order_id=order_id,
                user_id=user_id,
                new_status=status.value,
                reason=reason
            )
            
            # 获取当前订单
            current_order = await self.get_order_by_id(order_id, user_id, use_cache=False)
            
            # 验证状态转换
            if not force and not self._is_valid_status_transition(current_order.status, status):
                error_msg = f"Invalid status transition from {current_order.status.value} to {status.value}"
                module_logger.warning(
                    "invalid_status_transition",
                    order_id=order_id,
                    current_status=current_order.status.value,
                    requested_status=status.value
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # 准备更新数据
            update_data = {
                "status": status.value,
                "updated_at": datetime.now().isoformat()
            }
            
            # 根据状态设置时间戳
            timestamp_fields = {
                OrderStatus.PAID: "paid_at",
                OrderStatus.CONFIRMED: "confirmed_at",
                OrderStatus.SHIPPED: "shipped_at",
                OrderStatus.COMPLETED: "completed_at",
                OrderStatus.CANCELLED: "cancelled_at",
                OrderStatus.REFUNDED: "refunded_at"
            }
            
            if status in timestamp_fields:
                update_data[timestamp_fields[status]] = datetime.now().isoformat()
            
            # 设置取消原因
            if status == OrderStatus.CANCELLED and reason:
                update_data["cancellation_reason"] = reason
            
            # 更新订单
            response = supabase.table(self.table).update(update_data).eq("id", order_id).execute()
            if not response.data:
                module_logger.error("order_status_update_failed", order_id=order_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update order status"
                )
            
            # 清除缓存
            cache_key = f"order:{order_id}:{user_id}"
            await cache_set(cache_key, None)  # 删除缓存
            
            # 记录状态变更
            OrderLogger.log_order_status_change(
                order_id=order_id,
                old_status=current_order.status.value,
                new_status=status.value,
                reason=reason
            )
            
            updated_order = await self.get_order_by_id(order_id, user_id)
            
            module_logger.info(
                "order_status_updated_successfully",
                order_id=order_id,
                old_status=current_order.status.value,
                new_status=status.value
            )
            
            return updated_order
            
        except HTTPException:
            raise
        except Exception as e:
            module_logger.error(
                "order_status_update_failed",
                order_id=order_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def list_orders(self, query_params: OrderQueryParams, user_id: str) -> Dict[str, Any]:
        """
        查询订单列表
        
        Args:
            query_params (OrderQueryParams): 查询参数
            user_id (str): 用户ID
            
        Returns:
            Dict[str, Any]: 订单列表和分页信息
        """
        try:
            module_logger.debug(
                "order_list_query_started",
                user_id=user_id,
                query_params=query_params.dict(exclude_unset=True)
            )
            
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
            end_idx = start_idx + query_params.size - 1
            query = query.range(start_idx, end_idx)
            
            # 执行查询
            response = query.execute()
            
            # 构建响应
            orders = []
            order_ids = [order_data["id"] for order_data in response.data]
            
            if order_ids:
                # 批量查询订单项
                items_response = supabase.table(self.items_table).select("*").in_("order_id", order_ids).order("sort_order").execute()
                
                # 按订单ID分组订单项
                items_by_order = {}
                for item in items_response.data:
                    order_id = item["order_id"]
                    if order_id not in items_by_order:
                        items_by_order[order_id] = []
                    items_by_order[order_id].append(OrderItem(**item))
                
                # 构建订单对象
                for order_data in response.data:
                    order_items = items_by_order.get(order_data["id"], [])
                    order = Order(**order_data, items=order_items)
                    orders.append(order)
            
            result = {
                "items": orders,
                "total": response.count or 0,
                "page": query_params.page,
                "size": query_params.size,
                "has_next": (response.count or 0) > end_idx
            }
            
            module_logger.debug(
                "order_list_query_completed",
                user_id=user_id,
                total_items=len(orders),
                total_count=result["total"]
            )
            
            return result
            
        except Exception as e:
            module_logger.error(
                "order_list_query_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def get_order_statistics(self, user_id: str, days: int = 30) -> OrderStatistics:
        """
        获取订单统计信息
        
        Args:
            user_id (str): 用户ID
            days (int): 统计天数，默认30天
            
        Returns:
            OrderStatistics: 订单统计对象
        """
        try:
            cache_key = f"order_stats:{user_id}:{days}"
            
            # 尝试从缓存获取
            cached_stats = await cache_get(cache_key)
            if cached_stats:
                module_logger.debug("order_statistics_loaded_from_cache", user_id=user_id)
                return OrderStatistics(**cached_stats)
            
            module_logger.debug("order_statistics_calculating", user_id=user_id, days=days)
            
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
            total_amount = sum(float(order["final_amount"]) for order in orders)
            
            status_counts = {}
            for order in orders:
                status = order["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            average_order_value = total_amount / total_orders if total_orders > 0 else 0
            
            stats = OrderStatistics(
                total_orders=total_orders,
                total_amount=total_amount,
                pending_orders=status_counts.get(OrderStatus.PENDING.value, 0),
                paid_orders=status_counts.get(OrderStatus.PAID.value, 0),
                confirmed_orders=status_counts.get(OrderStatus.CONFIRMED.value, 0),
                shipped_orders=status_counts.get(OrderStatus.SHIPPED.value, 0),
                completed_orders=status_counts.get(OrderStatus.COMPLETED.value, 0),
                cancelled_orders=status_counts.get(OrderStatus.CANCELLED.value, 0),
                refunded_orders=status_counts.get(OrderStatus.REFUNDED.value, 0),
                average_order_value=average_order_value
            )
            
            # 缓存统计结果（5分钟）
            await cache_set(cache_key, stats.dict(), expire=300)
            
            module_logger.debug(
                "order_statistics_calculated",
                user_id=user_id,
                total_orders=total_orders,
                total_amount=total_amount
            )
            
            return stats
            
        except Exception as e:
            module_logger.error(
                "order_statistics_calculation_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    def _is_valid_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """
        验证订单状态转换是否有效
        
        Args:
            current_status (OrderStatus): 当前状态
            new_status (OrderStatus): 目标状态
            
        Returns:
            bool: 状态转换是否有效
        """
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.CONFIRMED, OrderStatus.REFUNDED],
            OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.COMPLETED],
            OrderStatus.COMPLETED: [],
            OrderStatus.CANCELLED: [OrderStatus.PENDING],  # 允许重新激活
            OrderStatus.REFUNDED: []
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    async def cancel_order(self, order_id: str, user_id: str, reason: str) -> Order:
        """
        取消订单
        
        Args:
            order_id (str): 订单ID
            user_id (str): 用户ID
            reason (str): 取消原因
            
        Returns:
            Order: 取消后的订单对象
        """
        return await self.update_order_status(
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            user_id=user_id,
            reason=reason
        )
    
    async def delete_order(self, order_id: str, user_id: str) -> bool:
        """
        删除订单（软删除）
        
        Args:
            order_id (str): 订单ID
            user_id (str): 用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 检查订单是否存在和权限
            order = await self.get_order_by_id(order_id, user_id)
            
            # 只能删除已取消或已完成很久的订单
            if order.status not in [OrderStatus.CANCELLED, OrderStatus.COMPLETED, OrderStatus.REFUNDED]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only cancelled, completed or refunded orders can be deleted"
                )
            
            # 检查是否超过删除时限（例如：完成超过30天）
            if order.status == OrderStatus.COMPLETED:
                completed_at = getattr(order, 'completed_at', None)
                if completed_at:
                    completed_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    if (datetime.now() - completed_time).days < 30:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Completed orders can only be deleted after 30 days"
                        )
            
            # 软删除：更新deleted_at字段
            update_data = {
                "deleted_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table(self.table).update(update_data).eq("id", order_id).execute()
            
            if response.data:
                # 清除缓存
                cache_key = f"order:{order_id}:{user_id}"
                await cache_set(cache_key, None)
                
                module_logger.info("order_deleted", order_id=order_id, user_id=user_id)
                return True
            else:
                return False
                
        except HTTPException:
            raise
        except Exception as e:
            module_logger.error(
                "order_deletion_failed",
                order_id=order_id,
                user_id=user_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete order"
            )

# 创建全局订单服务实例
order_service = OrderService()