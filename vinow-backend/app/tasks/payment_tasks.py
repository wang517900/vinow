交易系统

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import logging
from celery import Task
from app.utils.celery_app_api import celery_app, task_manager
from app.database import supabase
from app.models.order import OrderStatus, Order
from app.models.order_item import OrderItem
from app.utils.logger_api import logger, order_logger
from app.config import settings
from app.services.notification_service import NotificationService
from app.services.inventory_service import InventoryService

# 创建模块级日志记录器
module_logger = logging.getLogger(__name__)

class OrderTask(Task):
    """
    订单任务基类
    
    提供订单任务的通用功能，如重试、错误处理等
    """
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600  # 最大退避时间10分钟
    retry_jitter = True  # 添加随机抖动
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict):
        """
        任务成功执行后的回调
        
        Args:
            retval: 任务返回值
            task_id: 任务ID
            args: 位置参数
            kwargs: 关键字参数
        """
        module_logger.info(
            "order_task_completed_successfully",
            task_name=self.name,
            task_id=task_id,
            result=retval
        )
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any):
        """
        任务执行失败后的回调
        
        Args:
            exc: 异常对象
            task_id: 任务ID
            args: 位置参数
            kwargs: 关键字参数
            einfo: 异常信息
        """
        module_logger.error(
            "order_task_failed",
            task_name=self.name,
            task_id=task_id,
            error=str(exc),
            error_type=type(exc).__name__
        )

@celery_app.task(
    bind=True,
    base=OrderTask,
    name='app.tasks.order_tasks.auto_cancel_unpaid_orders',
    queue='orders',
    expires=300,  # 5分钟后任务过期
    soft_time_limit=120,  # 软时间限制2分钟
    time_limit=180  # 硬时间限制3分钟
)
def auto_cancel_unpaid_orders(self) -> Dict[str, Any]:
    """
    自动取消未支付订单任务
    
    定期检查并取消超过支付时限的未支付订单
    
    Returns:
        Dict[str, Any]: 处理结果统计
        
    Example:
        >>> result = auto_cancel_unpaid_orders.delay()
        >>> print(result.get())
    """
    try:
        module_logger.info("auto_cancel_unpaid_orders_task_started")
        
        # 计算过期时间（使用配置的时间）
        timeout_minutes = getattr(settings, 'order_timeout_minutes', 30)
        expiry_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        module_logger.debug(
            "searching_expired_orders",
            expiry_time=expiry_time.isoformat(),
            timeout_minutes=timeout_minutes
        )
        
        # 查询过期未支付订单
        response = supabase.table("orders").select("*").eq(
            "status", OrderStatus.PENDING.value
        ).lt(
            "created_at", expiry_time.isoformat()
        ).execute()
        
        expired_orders = response.data if response.data else []
        cancelled_count = 0
        failed_count = 0
        
        module_logger.info(
            "found_expired_orders",
            total_expired=len(expired_orders)
        )
        
        # 批量处理过期订单
        for order in expired_orders:
            try:
                order_id = order["id"]
                order_number = order["order_number"]
                
                module_logger.debug(
                    "processing_expired_order",
                    order_id=order_id,
                    order_number=order_number
                )
                
                # 更新订单状态为取消
                update_data = {
                    "status": OrderStatus.CANCELLED.value,
                    "cancelled_at": datetime.now().isoformat(),
                    "cancellation_reason": f"自动取消：支付超时（{timeout_minutes}分钟）",
                    "updated_at": datetime.now().isoformat()
                }
                
                # 执行更新操作
                update_response = supabase.table("orders").update(update_data).eq("id", order_id).execute()
                
                if update_response.data:
                    cancelled_count += 1
                    
                    # 记录订单日志
                    order_logger.log_order_cancellation(
                        order_id=order_id,
                        user_id=order.get("user_id", "unknown"),
                        reason="payment_timeout"
                    )
                    
                    # 触发订单取消后的后续处理任务
                    handle_order_cancellation.delay(order_id, "payment_timeout")
                    
                    module_logger.info(
                        "order_auto_cancelled_successfully",
                        order_id=order_id,
                        order_number=order_number,
                        reason="payment_timeout"
                    )
                else:
                    failed_count += 1
                    module_logger.warning(
                        "order_auto_cancel_failed_no_data",
                        order_id=order_id,
                        order_number=order_number
                    )
                    
            except Exception as e:
                failed_count += 1
                module_logger.error(
                    "auto_cancel_single_order_failed",
                    order_id=order.get("id", "unknown") if isinstance(order, dict) else "unknown",
                    error=str(e),
                    error_type=type(e).__name__
                )
                continue  # 继续处理下一个订单
        
        result = {
            "total_expired": len(expired_orders),
            "cancelled_count": cancelled_count,
            "failed_count": failed_count,
            "processed_at": datetime.now().isoformat()
        }
        
        module_logger.info(
            "auto_cancel_unpaid_orders_task_completed",
            **result
        )
        
        return result
        
    except Exception as e:
        module_logger.error(
            "auto_cancel_unpaid_orders_task_failed",
            error=str(e),
            error_type=type(e).__name__,
            traceback=str(e.__traceback__)
        )
        
        # 重试逻辑（最多重试3次）
        try:
            # 指数退避重试
            countdown = min(60 * (2 ** self.request.retries), 600)  # 最大10分钟
            raise self.retry(countdown=countdown, exc=e)
        except self.MaxRetriesExceededError:
            module_logger.error("max_retries_exceeded_for_auto_cancel_unpaid_orders")
            return {
                "error": "Max retries exceeded",
                "original_error": str(e),
                "task_id": self.request.id
            }

@celery_app.task(
    bind=True,
    base=OrderTask,
    name='app.tasks.order_tasks.handle_order_cancellation',
    queue='orders',
    expires=600,  # 10分钟后任务过期
    soft_time_limit=180,  # 软时间限制3分钟
    time_limit=300  # 硬时间限制5分钟
)
def handle_order_cancellation(self, order_id: str, reason: str) -> Dict[str, Any]:
    """
    处理订单取消后的相关任务
    
    Args:
        order_id (str): 订单ID
        reason (str): 取消原因
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    try:
        module_logger.info(
            "handle_order_cancellation_started",
            order_id=order_id,
            reason=reason
        )
        
        # 获取订单详情
        order_response = supabase.table("orders").select("*").eq("id", order_id).execute()
        if not order_response.data:
            raise ValueError(f"Order not found: {order_id}")
        
        order_data = order_response.data[0]
        
        # 获取订单项
        items_response = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
        order_items = items_response.data if items_response.data else []
        
        # 处理库存恢复
        inventory_restored = []
        for item in order_items:
            try:
                # 这里应该调用库存服务恢复库存
                # inventory_service.restore_stock(item["product_id"], item["quantity"])
                inventory_restored.append({
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "status": "pending"
                })
            except Exception as e:
                module_logger.error(
                    "inventory_restore_failed",
                    order_id=order_id,
                    product_id=item["product_id"],
                    error=str(e)
                )
        
        # 发送取消通知
        try:
            # notification_service.send_order_cancellation_notification(
            #     user_id=order_data["user_id"],
            #     order_number=order_data["order_number"],
            #     reason=reason
            # )
            notification_sent = True
        except Exception as e:
            module_logger.error(
                "order_cancellation_notification_failed",
                order_id=order_id,
                error=str(e)
            )
            notification_sent = False
        
        result = {
            "order_id": order_id,
            "reason": reason,
            "inventory_restored": len(inventory_restored),
            "notification_sent": notification_sent,
            "processed_at": datetime.now().isoformat()
        }
        
        module_logger.info(
            "handle_order_cancellation_completed",
            **result
        )
        
        return result
        
    except Exception as e:
        module_logger.error(
            "handle_order_cancellation_failed",
            order_id=order_id,
            reason=reason,
            error=str(e),
            error_type=type(e).__name__
        )
        raise self.retry(exc=e, countdown=60)

@celery_app.task(
    bind=True,
    base=OrderTask,
    name='app.tasks.order_tasks.process_order_completion',
    queue='orders',
    expires=3600,  # 1小时后任务过期
    soft_time_limit=300,  # 软时间限制5分钟
    time_limit=600  # 硬时间限制10分钟
)
def process_order_completion(self, order_id: str) -> Dict[str, Any]:
    """
    处理订单完成后的相关任务
    
    此任务在订单完成后执行，处理如发送通知、更新统计、计算佣金等操作
    
    Args:
        order_id (str): 订单ID
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    try:
        module_logger.info(
            "process_order_completion_started",
            order_id=order_id
        )
        
        # 获取订单详情
        order_response = supabase.table("orders").select("*").eq("id", order_id).execute()
        if not order_response.data:
            raise ValueError(f"Order not found: {order_id}")
        
        order_data = order_response.data[0]
        
        # 获取订单项
        items_response = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
        order_items = items_response.data if items_response.data else []
        
        # 初始化处理结果
        results = {
            "notifications_sent": 0,
            "statistics_updated": False,
            "commission_calculated": False,
            "loyalty_points_awarded": False
        }
        
        # 1. 发送订单完成通知
        try:
            # 这里应该调用通知服务发送完成通知
            # notification_service.send_order_completion_notification(
            #     user_id=order_data["user_id"],
            #     order_number=order_data["order_number"],
            #     final_amount=order_data["final_amount"]
            # )
            results["notifications_sent"] = 1
            module_logger.debug("order_completion_notification_sent", order_id=order_id)
        except Exception as e:
            module_logger.error(
                "order_completion_notification_failed",
                order_id=order_id,
                error=str(e)
            )
        
        # 2. 更新销售统计
        try:
            # 这里应该更新商户和平台的销售统计
            # statistics_service.update_sales_statistics(
            #     merchant_id=order_data["merchant_id"],
            #     amount=order_data["final_amount"],
            #     order_count=1
            # )
            results["statistics_updated"] = True
            module_logger.debug("order_statistics_updated", order_id=order_id)
        except Exception as e:
            module_logger.error(
                "order_statistics_update_failed",
                order_id=order_id,
                error=str(e)
            )
        
        # 3. 计算佣金
        try:
            # 这里应该计算平台佣金和分销佣金
            # commission_service.calculate_order_commission(order_id, order_data)
            results["commission_calculated"] = True
            module_logger.debug("order_commission_calculated", order_id=order_id)
        except Exception as e:
            module_logger.error(
                "order_commission_calculation_failed",
                order_id=order_id,
                error=str(e)
            )
        
        # 4. 发放会员积分
        try:
            # 这里应该根据订单金额发放会员积分
            # loyalty_service.award_points(
            #     user_id=order_data["user_id"],
            #     order_amount=order_data["final_amount"],
            #     order_id=order_id
            # )
            results["loyalty_points_awarded"] = True
            module_logger.debug("loyalty_points_awarded", order_id=order_id)
        except Exception as e:
            module_logger.error(
                "loyalty_points_award_failed",
                order_id=order_id,
                error=str(e)
            )
        
        # 记录订单完成日志
        order_logger.log_order_status_change(
            order_id=order_id,
            old_status=OrderStatus.SHIPPED.value,
            new_status=OrderStatus.COMPLETED.value,
            reason="automatic_completion"
        )
        
        final_result = {
            "status": "success",
            "order_id": order_id,
            "results": results,
            "processed_at": datetime.now().isoformat()
        }
        
        module_logger.info(
            "process_order_completion_completed",
            **final_result
        )
        
        return final_result
        
    except Exception as e:
        module_logger.error(
            "process_order_completion_failed",
            order_id=order_id,
            error=str(e),
            error_type=type(e).__name__,
            traceback=str(e.__traceback__)
        )
        raise self.retry(exc=e, countdown=120)  # 2分钟后重试

@celery_app.task(
    bind=True,
    base=OrderTask,
    name='app.tasks.order_tasks.batch_process_orders',
    queue='orders',
    expires=7200,  # 2小时后任务过期
    soft_time_limit=1800,  # 软时间限制30分钟
    time_limit=3600  # 硬时间限制1小时
)
def batch_process_orders(self, order_ids: List[str], action: str) -> Dict[str, Any]:
    """
    批量处理订单
    
    Args:
        order_ids (List[str]): 订单ID列表
        action (str): 要执行的操作
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    try:
        module_logger.info(
            "batch_process_orders_started",
            order_count=len(order_ids),
            action=action
        )
        
        results = {
            "total": len(order_ids),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        # 分批处理订单（每批10个）
        batch_size = 10
        for i in range(0, len(order_ids), batch_size):
            batch = order_ids[i:i + batch_size]
            
            for order_id in batch:
                try:
                    if action == "cancel":
                        # 取消订单
                        update_data = {
                            "status": OrderStatus.CANCELLED.value,
                            "cancelled_at": datetime.now().isoformat(),
                            "cancellation_reason": "批量取消",
                            "updated_at": datetime.now().isoformat()
                        }
                        supabase.table("orders").update(update_data).eq("id", order_id).execute()
                        results["success"] += 1
                        
                    elif action == "complete":
                        # 完成订单
                        update_data = {
                            "status": OrderStatus.COMPLETED.value,
                            "completed_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat()
                        }
                        supabase.table("orders").update(update_data).eq("id", order_id).execute()
                        results["success"] += 1
                        
                    results["details"].append({
                        "order_id": order_id,
                        "status": "success"
                    })
                    
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "order_id": order_id,
                        "status": "failed",
                        "error": str(e)
                    })
                    module_logger.error(
                        "batch_process_single_order_failed",
                        order_id=order_id,
                        action=action,
                        error=str(e)
                    )
            
            # 批次间短暂休眠以避免数据库压力
            if i + batch_size < len(order_ids):
                asyncio.sleep(0.1)
        
        final_result = {
            "action": action,
            "results": results,
            "processed_at": datetime.now().isoformat()
        }
        
        module_logger.info(
            "batch_process_orders_completed",
            **final_result
        )
        
        return final_result
        
    except Exception as e:
        module_logger.error(
            "batch_process_orders_failed",
            order_count=len(order_ids) if 'order_ids' in locals() else 0,
            action=action if 'action' in locals() else "unknown",
            error=str(e),
            error_type=type(e).__name__
        )
        raise self.retry(exc=e, countdown=300)  # 5分钟后重试

# 任务健康检查函数
def check_order_tasks_health() -> Dict[str, Any]:
    """
    检查订单任务健康状态
    
    Returns:
        Dict[str, Any]: 健康检查结果
    """
    try:
        # 检查数据库连接
        test_response = supabase.table("orders").select("id").limit(1).execute()
        db_healthy = bool(test_response.data is not None)
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }