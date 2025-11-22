from datetime import datetime, timedelta
from app.utils.celery_app import celery_app
from app.database import supabase
from app.models.order import OrderStatus
from app.utils.logger import logger

@celery_app.task(bind=True, max_retries=3)
def auto_cancel_unpaid_orders(self):
    """自动取消未支付订单"""
    try:
        # 计算过期时间
        expiry_time = datetime.now() - timedelta(minutes=30)  # 30分钟未支付
        
        # 查询过期未支付订单
        response = supabase.table("orders").select("*").eq(
            "status", OrderStatus.PENDING.value
        ).lt(
            "created_at", expiry_time.isoformat()
        ).execute()
        
        expired_orders = response.data
        cancelled_count = 0
        
        for order in expired_orders:
            try:
                # 更新订单状态为取消
                update_data = {
                    "status": OrderStatus.CANCELLED.value,
                    "cancelled_at": datetime.now().isoformat(),
                    "cancellation_reason": "自动取消：支付超时",
                    "updated_at": datetime.now().isoformat()
                }
                
                supabase.table("orders").update(update_data).eq("id", order["id"]).execute()
                cancelled_count += 1
                
                logger.info(
                    "order_auto_cancelled",
                    order_id=order["id"],
                    order_number=order["order_number"],
                    reason="payment_timeout"
                )
                
            except Exception as e:
                logger.error(
                    "auto_cancel_order_failed",
                    order_id=order["id"],
                    error=str(e)
                )
                continue
        
        logger.info(
            "auto_cancel_completed",
            total_expired=len(expired_orders),
            cancelled_count=cancelled_count
        )
        
        return {
            "total_expired": len(expired_orders),
            "cancelled_count": cancelled_count
        }
        
    except Exception as e:
        logger.error(f"Auto cancel unpaid orders error: {str(e)}")
        # 重试逻辑
        try:
            self.retry(countdown=60, exc=e)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for auto_cancel_unpaid_orders")
        return {"error": str(e)}

@celery_app.task
def process_order_completion(order_id: str):
    """处理订单完成后的相关任务"""
    try:
        # 这里可以执行订单完成后的各种操作
        # 例如：发送通知、更新库存、计算佣金等
        
        logger.info(
            "order_completion_processed",
            order_id=order_id
        )
        
        return {"status": "success", "order_id": order_id}
        
    except Exception as e:
        logger.error(
            "order_completion_failed",
            order_id=order_id,
            error=str(e)
        )
        return {"status": "failed", "error": str(e)}