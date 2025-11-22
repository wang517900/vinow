# app/services/verification_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import supabase
from app.models.order import OrderInDB, OrderStatus
from app.models.verification import VerificationRecordInDB, VerificationRecordCreate, BatchVerificationRequest
import logging

logger = logging.getLogger(__name__)

class VerificationService:
    """核销服务类"""
    
    @staticmethod
    async def verify_order_by_code(
        verification_code: str, 
        staff_id: str, 
        staff_name: str,
        method: str = "manual"
    ) -> Optional[OrderInDB]:
        """通过核销码核销订单"""
        try:
            # 查找订单
            response = supabase.table("orders").select("*").eq("verification_code", verification_code).execute()
            
            if not response.data:
                return None
                
            order_data = response.data[0]
            order = OrderInDB(**order_data)
            
            # 检查订单状态
            if order.status != OrderStatus.PENDING:
                return None
            
            # 更新订单状态
            update_response = supabase.table("orders").update({
                "status": OrderStatus.VERIFIED,
                "verified_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).eq("id", order.id).execute()
            
            if not update_response.data:
                return None
            
            # 创建核销记录
            verification_record = VerificationRecordCreate(
                order_id=order.id,
                merchant_id=order.merchant_id,
                store_id=order.store_id,
                staff_id=staff_id,
                staff_name=staff_name,
                verification_method=method
            )
            
            await VerificationService.create_verification_record(verification_record)
            
            return OrderInDB(**update_response.data[0])
            
        except Exception as e:
            logger.error(f"核销订单失败: {e}")
            return None
    
    @staticmethod
    async def verify_order_by_qr(
        qr_data: str, 
        staff_id: str, 
        staff_name: str
    ) -> Optional[OrderInDB]:
        """通过二维码核销订单"""
        try:
            # 解析二维码数据（这里假设二维码包含订单ID或核销码）
            # 实际实现可能需要根据具体的二维码格式进行解析
            if qr_data.startswith("order_"):
                # 按订单ID查找
                response = supabase.table("orders").select("*").eq("id", qr_data).execute()
            else:
                # 按核销码查找
                response = supabase.table("orders").select("*").eq("verification_code", qr_data).execute()
            
            if not response.data:
                return None
                
            order_data = response.data[0]
            order = OrderInDB(**order_data)
            
            # 检查订单状态
            if order.status != OrderStatus.PENDING:
                return None
            
            # 更新订单状态
            update_response = supabase.table("orders").update({
                "status": OrderStatus.VERIFIED,
                "verified_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).eq("id", order.id).execute()
            
            if not update_response.data:
                return None
            
            # 创建核销记录
            verification_record = VerificationRecordCreate(
                order_id=order.id,
                merchant_id=order.merchant_id,
                store_id=order.store_id,
                staff_id=staff_id,
                staff_name=staff_name,
                verification_method="scan_qr"
            )
            
            await VerificationService.create_verification_record(verification_record)
            
            return OrderInDB(**update_response.data[0])
            
        except Exception as e:
            logger.error(f"二维码核销失败: {e}")
            return None
    
    @staticmethod
    async def batch_verify_orders(
        batch_request: BatchVerificationRequest
    ) -> Dict[str, Any]:
        """批量核销订单"""
        try:
            success_count = 0
            failed_orders = []
            
            for order_id in batch_request.order_ids:
                # 获取订单
                response = supabase.table("orders").select("*").eq("id", order_id).execute()
                
                if not response.data:
                    failed_orders.append({"order_id": order_id, "reason": "订单不存在"})
                    continue
                
                order_data = response.data[0]
                order = OrderInDB(**order_data)
                
                # 检查订单状态
                if order.status != OrderStatus.PENDING:
                    failed_orders.append({
                        "order_id": order_id, 
                        "reason": f"订单状态为{order.status}，无法核销"
                    })
                    continue
                
                # 更新订单状态
                update_response = supabase.table("orders").update({
                    "status": OrderStatus.VERIFIED,
                    "verified_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }).eq("id", order_id).execute()
                
                if update_response.data:
                    # 创建核销记录
                    verification_record = VerificationRecordCreate(
                        order_id=order_id,
                        merchant_id=order.merchant_id,
                        store_id=order.store_id,
                        staff_id=batch_request.staff_id,
                        staff_name=batch_request.staff_name,
                        verification_method="batch"
                    )
                    
                    await VerificationService.create_verification_record(verification_record)
                    success_count += 1
                else:
                    failed_orders.append({"order_id": order_id, "reason": "更新订单状态失败"})
            
            return {
                "success_count": success_count,
                "failed_orders": failed_orders,
                "total_processed": len(batch_request.order_ids)
            }
            
        except Exception as e:
            logger.error(f"批量核销失败: {e}")
            return {
                "success_count": 0,
                "failed_orders": [],
                "total_processed": 0,
                "error": str(e)
            }
    
    @staticmethod
    async def create_verification_record(record_data: VerificationRecordCreate) -> Optional[VerificationRecordInDB]:
        """创建核销记录"""
        try:
            record_dict = record_data.model_dump()
            record_dict["created_at"] = datetime.now().isoformat()
            
            response = supabase.table("verification_records").insert(record_dict).execute()
            
            if response.data:
                return VerificationRecordInDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建核销记录失败: {e}")
            return None
    
    @staticmethod
    async def get_verification_records(
        merchant_id: str,
        staff_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[VerificationRecordInDB], int]:
        """获取核销记录"""
        try:
            query = supabase.table("verification_records").select("*, orders(order_number, product_name, paid_amount)", count="exact").eq("merchant_id", merchant_id)
            
            if staff_id:
                query = query.eq("staff_id", staff_id)
            
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            start_index = (page - 1) * page_size
            response = query.order("created_at", desc=True).range(start_index, start_index + page_size - 1).execute()
            
            records = [VerificationRecordInDB(**item) for item in response.data]
            total_count = response.count or 0
            
            return records, total_count
            
        except Exception as e:
            logger.error(f"获取核销记录失败: {e}")
            return [], 0
    
    @staticmethod
    async def get_staff_verification_stats(merchant_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """获取员工核销统计"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 使用Supabase的rpc调用或直接查询
            response = supabase.table("verification_records").select(
                "staff_id, staff_name, count:id, orders(paid_amount)"
            ).eq("merchant_id", merchant_id).gte("created_at", start_date.isoformat()).execute()
            
            # 处理统计结果
            staff_stats = {}
            for record in response.data:
                staff_id = record["staff_id"]
                if staff_id not in staff_stats:
                    staff_stats[staff_id] = {
                        "staff_id": staff_id,
                        "staff_name": record["staff_name"],
                        "verification_count": 0,
                        "total_amount": 0
                    }
                
                staff_stats[staff_id]["verification_count"] += 1
                if record.get("orders") and isinstance(record["orders"], list) and len(record["orders"]) > 0:
                    staff_stats[staff_id]["total_amount"] += record["orders"][0].get("paid_amount", 0)
            
            return list(staff_stats.values())
            
        except Exception as e:
            logger.error(f"获取员工核销统计失败: {e}")
            return []

verification_service = VerificationService()