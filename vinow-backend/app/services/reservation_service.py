商户系统6财务中心
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging
import uuid

from app.database.supabase_client import db
from app.models.finance import (
    ReconciliationLog, ReconciliationStatus, ReconciliationResult,
    PaginatedResponse
)
from app.schemas.finance import ReconciliationHistoryParams
from app.core.exceptions import ReconciliationException

logger = logging.getLogger(__name__)


class ReconciliationService:
    """对账服务"""
    
    async def run_reconciliation(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date,
        force_reconcile: bool = False
    ) -> Optional[ReconciliationResult]:
        """执行对账"""
        try:
            logger.info(f"开始执行对账任务: 商户={merchant_id}, 日期范围={start_date}至{end_date}")
            
            # 检查是否已有对账记录
            if not force_reconcile:
                existing_log = await self._get_existing_reconciliation(
                    merchant_id, start_date, end_date
                )
                if existing_log:
                    logger.info(f"对账记录已存在: {existing_log.id}")
                    return await self._format_reconciliation_result(existing_log)
            
            # 获取平台数据
            platform_data = await self._get_platform_transactions(merchant_id, start_date, end_date)
            
            # 获取银行数据
            bank_data = await self._get_bank_transactions(merchant_id, start_date, end_date)
            
            # 执行对账比对
            reconciliation_result = await self._compare_transactions(
                platform_data, bank_data, merchant_id, start_date, end_date
            )
            
            # 保存对账记录
            reconciliation_log = await self._save_reconciliation_log(reconciliation_result)
            
            logger.info(f"对账完成: {reconciliation_log.id}")
            return await self._format_reconciliation_result(reconciliation_log)
            
        except ReconciliationException:
            raise
        except Exception as e:
            logger.error(f"执行对账失败: {str(e)}", exc_info=True)
            raise ReconciliationException("执行对账失败")
    
    async def get_reconciliation_history(
        self, 
        merchant_id: str,
        params: ReconciliationHistoryParams
    ) -> PaginatedResponse[ReconciliationResult]:
        """获取对账历史"""
        try:
            logger.info(f"获取商户 {merchant_id} 的对账历史记录")
            
            # 验证分页参数
            if params.limit > 100:
                raise ReconciliationException("单页查询数量不能超过100条")
            
            if params.limit <= 0 or params.offset < 0:
                raise ReconciliationException("分页参数无效")
            
            filters = {"merchant_id": merchant_id}
            
            # 添加日期范围过滤
            if params.start_date and params.end_date:
                filters["reconciliation_date"] = {
                    "gte": params.start_date.isoformat(),
                    "lte": params.end_date.isoformat()
                }
            
            # 添加状态过滤
            if params.status:
                filters["status"] = params.status.value
            
            logs = await db.execute_query(
                "finances_reconciliation_logs",
                filters=filters,
                order_by="reconciliation_date.desc",
                limit=params.limit,
                offset=params.offset
            )
            
            results = []
            for log in logs:
                results.append(await self._format_reconciliation_result(ReconciliationLog(**log)))
            
            # 获取总数
            total = await self._get_reconciliation_count(filters)
            
            logger.debug(f"成功获取到 {len(results)} 条对账历史记录")
            
            return PaginatedResponse.create(
                items=results,
                total=total,
                page=(params.offset // params.limit) + 1 if params.limit > 0 else 1,
                page_size=params.limit
            )
            
        except ReconciliationException:
            raise
        except Exception as e:
            logger.error(f"获取对账历史失败: {str(e)}", exc_info=True)
            raise ReconciliationException("获取对账历史失败")
    
    async def get_reconciliation_results(
        self, 
        merchant_id: str,
        reconciliation_id: str = None
    ) -> List[ReconciliationResult]:
        """获取对账结果"""
        try:
            logger.info(f"获取商户 {merchant_id} 的对账结果")
            
            filters = {"merchant_id": merchant_id}
            if reconciliation_id:
                filters["id"] = reconciliation_id
            
            logs = await db.execute_query(
                "finances_reconciliation_logs",
                filters=filters,
                order_by="reconciliation_date.desc",
                limit=10
            )
            
            results = []
            for log in logs:
                results.append(await self._format_reconciliation_result(ReconciliationLog(**log)))
            
            logger.debug(f"成功获取到 {len(results)} 条对账结果")
            
            return results
            
        except Exception as e:
            logger.error(f"获取对账结果失败: {str(e)}", exc_info=True)
            raise ReconciliationException("获取对账结果失败")
    
    async def submit_dispute(
        self,
        merchant_id: str,
        reconciliation_id: str,
        order_ids: List[str],
        dispute_reason: str,
        evidence: List[str] = None
    ) -> bool:
        """提交争议申请"""
        try:
            logger.info(f"商户 {merchant_id} 提交争议申请，对账ID: {reconciliation_id}")
            
            # 验证对账记录
            reconciliation_log = await self._get_reconciliation_log(reconciliation_id, merchant_id)
            if not reconciliation_log:
                raise ReconciliationException("对账记录不存在")
            
            if reconciliation_log.status != ReconciliationStatus.MISMATCHED:
                raise ReconciliationException("只有对账不一致的记录可以提交争议")
            
            # 验证订单是否属于对账记录
            valid_orders = await self._validate_dispute_orders(
                order_ids, reconciliation_log.mismatched_orders
            )
            
            if not valid_orders:
                raise ReconciliationException("争议订单不存在于对账记录中")
            
            # 创建争议记录
            dispute_id = await self._create_dispute_record(
                merchant_id,
                reconciliation_id,
                valid_orders,
                dispute_reason,
                evidence or []
            )
            
            # 更新对账记录中的已解决订单
            await self._update_resolved_orders(
                reconciliation_id, valid_orders
            )
            
            logger.info(f"争议申请提交成功: {dispute_id}")
            return True
            
        except ReconciliationException:
            raise
        except Exception as e:
            logger.error(f"提交争议申请失败: {str(e)}", exc_info=True)
            raise ReconciliationException("提交争议申请失败")
    
    async def _get_platform_transactions(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取平台交易数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的平台交易数据，日期范围: {start_date} 至 {end_date}")
            
            # 查询订单数据
            orders = await db.execute_query(
                "orders",
                filters={
                    "merchant_id": merchant_id,
                    "created_at": {
                        "gte": start_date.isoformat(),
                        "lte": end_date.isoformat()
                    },
                    "status": "completed"  # 只查询已完成的订单
                }
            )
            
            platform_transactions = []
            for order in orders:
                platform_transactions.append({
                    "order_id": order.get('order_no'),
                    "amount": Decimal(str(order.get('amount', 0))),
                    "transaction_time": datetime.fromisoformat(order.get('created_at')),
                    "payment_method": order.get('payment_method'),
                    "customer_info": order.get('customer_name')
                })
            
            logger.debug(f"获取到 {len(platform_transactions)} 条平台交易记录")
            
            return platform_transactions
            
        except Exception as e:
            logger.error(f"获取平台交易数据失败: {str(e)}", exc_info=True)
            return []
    
    async def _get_bank_transactions(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取银行交易数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的银行交易数据，日期范围: {start_date} 至 {end_date}")
            
            # 这里需要根据实际的银行接口或银行对账文件来获取数据
            # 暂时返回模拟数据
            
            # 模拟银行交易数据
            bank_transactions = [
                {
                    "transaction_id": "BANK001",
                    "amount": Decimal("1000000"),
                    "transaction_time": datetime.now(),
                    "reference_no": "ORDER001",
                    "bank_account": "VCB***6789"
                },
                {
                    "transaction_id": "BANK002", 
                    "amount": Decimal("500000"),
                    "transaction_time": datetime.now(),
                    "reference_no": "ORDER002",
                    "bank_account": "VCB***6789"
                }
            ]
            
            logger.debug(f"获取到 {len(bank_transactions)} 条银行交易记录")
            
            return bank_transactions
            
        except Exception as e:
            logger.error(f"获取银行交易数据失败: {str(e)}", exc_info=True)
            return []
    
    async def _compare_transactions(
        self,
        platform_data: List[Dict[str, Any]],
        bank_data: List[Dict[str, Any]],
        merchant_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """比对交易数据"""
        try:
            logger.info(f"开始比对交易数据，平台记录数: {len(platform_data)}, 银行记录数: {len(bank_data)}")
            
            # 计算平台总金额
            platform_total = sum(txn['amount'] for txn in platform_data)
            
            # 计算银行总金额
            bank_total = sum(txn['amount'] for txn in bank_data)
            
            # 计算差异
            difference = platform_total - bank_total
            
            # 查找不匹配的订单
            mismatched_orders = await self._find_mismatched_orders(platform_data, bank_data)
            
            # 确定对账状态
            status = await self._determine_reconciliation_status(
                difference, mismatched_orders
            )
            
            result = {
                "merchant_id": merchant_id,
                "reconciliation_date": date.today(),
                "start_date": start_date,
                "end_date": end_date,
                "platform_total": platform_total,
                "bank_total": bank_total,
                "difference": difference,
                "status": status,
                "mismatched_orders": mismatched_orders,
                "resolved_orders": [],
                "notes": f"自动对账 {start_date} 到 {end_date}",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            logger.info(f"交易比对完成: 状态={status.value}, 差异={difference}")
            
            return result
            
        except Exception as e:
            logger.error(f"比对交易数据失败: {str(e)}", exc_info=True)
            raise ReconciliationException("比对交易数据失败")
    
    async def _find_mismatched_orders(
        self,
        platform_data: List[Dict[str, Any]],
        bank_data: List[Dict[str, Any]]
    ) -> List[str]:
        """查找不匹配的订单"""
        try:
            logger.debug("开始查找不匹配的订单")
            
            mismatched_orders = []
            
            # 创建银行交易的映射（按参考号）
            bank_transactions_map = {}
            for txn in bank_data:
                ref_no = txn.get('reference_no')
                if ref_no:
                    bank_transactions_map[ref_no] = txn
            
            # 检查平台订单在银行数据中是否存在
            for platform_txn in platform_data:
                order_id = platform_txn['order_id']
                bank_txn = bank_transactions_map.get(order_id)
                
                if not bank_txn:
                    mismatched_orders.append(order_id)
                    logger.debug(f"订单 {order_id} 在银行数据中未找到")
                    continue
                
                # 检查金额是否匹配
                if platform_txn['amount'] != bank_txn['amount']:
                    mismatched_orders.append(order_id)
                    logger.debug(f"订单 {order_id} 金额不匹配: 平台={platform_txn['amount']}, 银行={bank_txn['amount']}")
            
            logger.debug(f"找到 {len(mismatched_orders)} 个不匹配的订单")
            
            return mismatched_orders
            
        except Exception as e:
            logger.error(f"查找不匹配订单失败: {str(e)}", exc_info=True)
            return []
    
    async def _determine_reconciliation_status(
        self,
        difference: Decimal,
        mismatched_orders: List[str]
    ) -> ReconciliationStatus:
        """确定对账状态"""
        if difference == 0 and not mismatched_orders:
            return ReconciliationStatus.MATCHED
        elif difference != 0 or mismatched_orders:
            return ReconciliationStatus.MISMATCHED
        else:
            return ReconciliationStatus.ERROR
    
    async def _save_reconciliation_log(self, data: Dict[str, Any]) -> ReconciliationLog:
        """保存对账日志"""
        try:
            logger.info("保存对账日志")
            
            reconciliation_log = ReconciliationLog(
                id=str(uuid.uuid4()),
                **data
            )
            
            await db.insert_data(
                "finances_reconciliation_logs",
                reconciliation_log.dict()
            )
            
            logger.info(f"对账日志保存成功: {reconciliation_log.id}")
            
            return reconciliation_log
            
        except Exception as e:
            logger.error(f"保存对账日志失败: {str(e)}", exc_info=True)
            raise ReconciliationException("保存对账日志失败")
    
    async def _format_reconciliation_result(
        self, 
        reconciliation_log: ReconciliationLog
    ) -> ReconciliationResult:
        """格式化对账结果"""
        logger.debug(f"格式化对账结果: {reconciliation_log.id}")
        
        return ReconciliationResult(
            reconciliation_id=reconciliation_log.id,
            status=reconciliation_log.status,
            platform_total=reconciliation_log.platform_total,
            bank_total=reconciliation_log.bank_total,
            difference=reconciliation_log.difference,
            mismatched_orders=reconciliation_log.mismatched_orders,
            reconciliation_date=reconciliation_log.created_at
        )
    
    async def _get_existing_reconciliation(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[ReconciliationLog]:
        """获取已存在的对账记录"""
        try:
            logger.debug(f"检查是否存在对账记录: 商户={merchant_id}, 日期范围={start_date}至{end_date}")
            
            records = await db.execute_query(
                "finances_reconciliation_logs",
                filters={
                    "merchant_id": merchant_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                limit=1
            )
            
            if records:
                reconciliation_log = ReconciliationLog(**records[0])
                logger.debug(f"找到已存在的对账记录: {reconciliation_log.id}")
                return reconciliation_log
            
            logger.debug("未找到已存在的对账记录")
            return None
            
        except Exception as e:
            logger.error(f"获取已存在的对账记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _get_reconciliation_log(
        self, 
        reconciliation_id: str, 
        merchant_id: str
    ) -> Optional[ReconciliationLog]:
        """获取对账记录"""
        try:
            logger.debug(f"获取对账记录: {reconciliation_id}")
            
            records = await db.execute_query(
                "finances_reconciliation_logs",
                filters={
                    "id": reconciliation_id,
                    "merchant_id": merchant_id
                },
                limit=1
            )
            
            if records:
                reconciliation_log = ReconciliationLog(**records[0])
                logger.debug(f"找到对账记录: {reconciliation_log.id}")
                return reconciliation_log
            
            logger.debug(f"未找到对账记录: {reconciliation_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取对账记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _validate_dispute_orders(
        self, 
        order_ids: List[str], 
        mismatched_orders: List[str]
    ) -> List[str]:
        """验证争议订单"""
        logger.debug(f"验证争议订单: {order_ids}")
        
        valid_orders = []
        for order_id in order_ids:
            if order_id in mismatched_orders:
                valid_orders.append(order_id)
        
        logger.debug(f"验证通过的争议订单: {valid_orders}")
        return valid_orders
    
    async def _create_dispute_record(
        self,
        merchant_id: str,
        reconciliation_id: str,
        order_ids: List[str],
        dispute_reason: str,
        evidence: List[str]
    ) -> str:
        """创建争议记录"""
        try:
            logger.info(f"创建争议记录: 商户={merchant_id}, 对账ID={reconciliation_id}")
            
            dispute_id = str(uuid.uuid4())
            
            dispute_data = {
                "id": dispute_id,
                "merchant_id": merchant_id,
                "reconciliation_id": reconciliation_id,
                "order_ids": order_ids,
                "dispute_reason": dispute_reason,
                "evidence": evidence,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 插入争议记录到数据库
            await db.insert_data("finances_dispute_records", dispute_data)
            
            logger.info(f"争议记录创建成功: {dispute_id}")
            
            return dispute_id
            
        except Exception as e:
            logger.error(f"创建争议记录失败: {str(e)}", exc_info=True)
            raise ReconciliationException("创建争议记录失败")
    
    async def _update_resolved_orders(
        self, 
        reconciliation_id: str, 
        resolved_orders: List[str]
    ):
        """更新已解决订单"""
        try:
            logger.info(f"更新对账记录 {reconciliation_id} 的已解决订单")
            
            # 获取当前对账记录
            records = await db.execute_query(
                "finances_reconciliation_logs",
                filters={"id": reconciliation_id},
                limit=1
            )
            
            if not records:
                logger.warning(f"未找到对账记录: {reconciliation_id}")
                return
            
            current_log = records[0]
            current_resolved = current_log.get('resolved_orders', [])
            
            # 合并已解决订单
            updated_resolved = list(set(current_resolved + resolved_orders))
            
            # 更新记录
            await db.update_data(
                "finances_reconciliation_logs",
                {
                    "resolved_orders": updated_resolved,
                    "updated_at": datetime.now().isoformat()
                },
                {"id": reconciliation_id}
            )
            
            logger.info(f"对账记录 {reconciliation_id} 的已解决订单更新成功")
            
        except Exception as e:
            logger.error(f"更新已解决订单失败: {str(e)}", exc_info=True)
            raise ReconciliationException("更新已解决订单失败")
    
    async def _get_reconciliation_count(self, filters: Dict[str, Any]) -> int:
        """获取对账记录总数"""
        try:
            logger.debug("查询对账记录总数")
            
            # 这里应该调用数据库的 COUNT 方法
            # 示例实现，实际应根据数据库客户端调整
            count = await db.execute_count("finances_reconciliation_logs", filters=filters)
            return count if count else 0
            
        except Exception as e:
            logger.error(f"获取对账记录总数失败: {str(e)}", exc_info=True)
            # 回退到原来的实现方式
            records = await db.execute_query("finances_reconciliation_logs", filters=filters)
            return len(records)