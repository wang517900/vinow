# app/services/refund_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.database import supabase
from app.models.order import OrderInDB, OrderStatus
import logging

logger = logging.getLogger(__name__)

class RefundService:
    """退款服务类"""
    
    @staticmethod
    async def create_refund_request(
        order_id: str, 
        reason: str, 
        explanation: Optional[str] = None,
        evidence_images: Optional[List[str]] = None
    ) -> Optional[OrderInDB]:
        """创建退款申请"""
        try:
            # 获取订单
            order_response = supabase.table("orders").select("*").eq("id", order_id).execute()
            
            if not order_response.data:
                return None
                
            order_data = order_response.data[0]
            order = OrderInDB(**order_data)
            
            # 检查订单状态是否允许退款
            if order.status not in [OrderStatus.PENDING, OrderStatus.VERIFIED]:
                return None
            
            # 更新订单状态为退款中
            update_response = supabase.table("orders").update({
                "status": OrderStatus.REFUNDING,
                "refund_reason": reason,
                "refund_explanation": explanation,
                "refund_evidence": evidence_images,
                "updated_at": datetime.now().isoformat()
            }).eq("id", order_id).execute()
            
            if update_response.data:
                return OrderInDB(**update_response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建退款申请失败: {e}")
            return None
    
    @staticmethod
    async def approve_refund(order_id: str, processed_by: str) -> Optional[OrderInDB]:
        """批准退款申请"""
        try:
            # 更新订单状态为已退款
            update_response = supabase.table("orders").update({
                "status": OrderStatus.REFUNDED,
                "refunded_at": datetime.now().isoformat(),
                "refund_processed_by": processed_by,
                "updated_at": datetime.now().isoformat()
            }).eq("id", order_id).execute()
            
            if update_response.data:
                return OrderInDB(**update_response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"批准退款失败: {e}")
            return None
    
    @staticmethod
    async def reject_refund(
        order_id: str, 
        reject_reason: str, 
        processed_by: str
    ) -> Optional[OrderInDB]:
        """拒绝退款申请"""
        try:
            # 获取订单原始状态（退款前状态）
            order_response = supabase.table("orders").select("*").eq("id", order_id).execute()
            
            if not order_response.data:
                return None
                
            order_data = order_response.data[0]
            previous_status = OrderStatus.PENDING  # 默认状态
            
            # 根据订单情况决定恢复的状态
            if order_data.get("verified_at"):
                previous_status = OrderStatus.VERIFIED
            else:
                previous_status = OrderStatus.PENDING
            
            # 更新订单状态
            update_response = supabase.table("orders").update({
                "status": previous_status,
                "refund_reject_reason": reject_reason,
                "refund_processed_by": processed_by,
                "updated_at": datetime.now().isoformat()
            }).eq("id", order_id).execute()
            
            if update_response.data:
                return OrderInDB(**update_response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"拒绝退款失败: {e}")
            return None
    
    @staticmethod
    async def get_pending_refunds(
        merchant_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[OrderInDB], int]:
        """获取待处理的退款申请"""
        try:
            query = supabase.table("orders").select("*", count="exact").eq("merchant_id", merchant_id).eq("status", OrderStatus.REFUNDING)
            
            start_index = (page - 1) * page_size
            response = query.order("updated_at", desc=True).range(start_index, start_index + page_size - 1).execute()
            
            orders = [OrderInDB(**item) for item in response.data]
            total_count = response.count or 0
            
            return orders, total_count
            
        except Exception as e:
            logger.error(f"获取退款申请失败: {e}")
            return [], 0
    
    @staticmethod
    async def get_refund_stats(merchant_id: str, days: int = 30) -> Dict[str, Any]:
        """获取退款统计"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 退款申请统计
            refunding_response = supabase.table("orders").select("id", count="exact").eq("merchant_id", merchant_id).eq("status", OrderStatus.REFUNDING).gte("updated_at", start_date.isoformat()).execute()
            
            # 已退款统计
            refunded_response = supabase.table("orders").select("paid_amount").eq("merchant_id", merchant_id).eq("status", OrderStatus.REFUNDED).gte("refunded_at", start_date.isoformat()).execute()
            
            # 退款原因统计
            reason_response = supabase.table("orders").select("refund_reason").eq("merchant_id", merchant_id).eq("status", OrderStatus.REFUNDED).gte("refunded_at", start_date.isoformat()).execute()
            
            pending_count = refunding_response.count or 0
            refunded_amount = sum(item["paid_amount"] for item in refunded_response.data)
            refunded_count = len(refunded_response.data)
            
            # 退款原因分析
            reason_stats = {}
            for item in reason_response.data:
                reason = item.get("refund_reason", "其他")
                if reason not in reason_stats:
                    reason_stats[reason] = 0
                reason_stats[reason] += 1
            
            return {
                "pending_count": pending_count,
                "refunded_count": refunded_count,
                "refunded_amount": refunded_amount,
                "reason_stats": reason_stats
            }
            
        except Exception as e:
            logger.error(f"获取退款统计失败: {e}")
            return {
                "pending_count": 0,
                "refunded_count": 0,
                "refunded_amount": 0,
                "reason_stats": {}
            }

refund_service = RefundService()