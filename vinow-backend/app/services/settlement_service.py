商户系统6财务中心
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging
import uuid

from app.database.supabase_client import db
from app.models.finance import (
    SettlementRecord, SettlementStatus, SettlementStatusResponse, 
    SettlementHistoryItem, NextSettlementEstimate
)
from app.schemas.finance import SettlementHistoryParams, PaginatedResponse
from app.utils.date_utils import DateUtils
from app.core.exceptions import SettlementException

logger = logging.getLogger(__name__)


class SettlementService:
    """结算管理服务"""
    
    async def get_settlement_status(self, merchant_id: str) -> SettlementStatusResponse:
        """获取结算状态"""
        try:
            logger.info(f"开始获取商户 {merchant_id} 的结算状态")
            
            # 获取已结算金额
            settled_amount = await self._get_settled_amount(merchant_id)
            
            # 获取待结算金额
            pending_amount = await self._get_pending_amount(merchant_id)
            
            # 获取下次结算信息
            next_settlement_days = await self._get_next_settlement_days()
            
            # 获取银行账户信息
            bank_account = await self._get_bank_account(merchant_id)
            
            # 获取最后结算日期
            last_settlement = await self._get_last_settlement(merchant_id)
            last_settlement_date = last_settlement.settlement_date if last_settlement else None
            
            response = SettlementStatusResponse(
                settled_amount=settled_amount,
                pending_amount=pending_amount,
                next_settlement_days=next_settlement_days,
                bank_account=bank_account,
                last_settlement_date=last_settlement_date
            )
            
            logger.debug(f"成功获取商户 {merchant_id} 的结算状态: "
                        f"已结算={settled_amount}, 待结算={pending_amount}")
            
            return response
            
        except Exception as e:
            logger.error(f"获取结算状态失败: {str(e)}", exc_info=True)
            raise SettlementException("获取结算状态失败")
    
    async def get_settlement_history(
        self, 
        merchant_id: str, 
        params: SettlementHistoryParams
    ) -> PaginatedResponse[SettlementHistoryItem]:
        """获取结算历史"""
        try:
            logger.info(f"开始获取商户 {merchant_id} 的结算历史记录")
            
            # 验证分页参数
            if params.limit > 100:
                raise SettlementException("单页查询数量不能超过100条")
            
            if params.limit <= 0 or params.offset < 0:
                raise SettlementException("分页参数无效")
            
            # 构建查询条件
            filters = {"merchant_id": merchant_id}
            
            # 添加日期范围过滤
            if params.start_date and params.end_date:
                start_date = DateUtils.format_date_for_query(params.start_date)
                end_date = DateUtils.format_date_for_query(params.end_date)
                
                if start_date and end_date:
                    filters["settlement_date"] = {
                        "gte": start_date.isoformat(),
                        "lte": end_date.isoformat()
                    }
            
            # 添加状态过滤
            if params.status:
                filters["status"] = params.status.value
            
            # 执行查询
            records = await db.execute_query(
                "finances_settlement_records",
                filters=filters,
                order_by="settlement_date.desc",
                limit=params.limit,
                offset=params.offset
            )
            
            # 转换为历史项
            history_items = []
            for record in records:
                history_items.append(SettlementHistoryItem(
                    id=record.get('id'),
                    settlement_no=record.get('settlement_no'),
                    settlement_date=date.fromisoformat(record.get('settlement_date')),
                    total_amount=Decimal(str(record.get('total_amount', 0))),
                    net_amount=Decimal(str(record.get('net_amount', 0))),
                    status=SettlementStatus(record.get('status')),
                    bank_name=record.get('bank_name', '')
                ))
            
            # 获取总数
            total = await self._get_settlement_count(filters)
            
            logger.debug(f"成功获取到 {len(history_items)} 条结算历史记录")
            
            return PaginatedResponse.create(
                items=history_items,
                total=total,
                page=(params.offset // params.limit) + 1 if params.limit > 0 else 1,
                page_size=params.limit
            )
            
        except SettlementException:
            raise
        except Exception as e:
            logger.error(f"获取结算历史失败: {str(e)}", exc_info=True)
            raise SettlementException("获取结算历史失败")
    
    async def verify_settlement(
        self, 
        merchant_id: str, 
        settlement_id: str, 
        verification_code: str = None
    ) -> bool:
        """确认结算"""
        try:
            logger.info(f"商户 {merchant_id} 开始确认结算 {settlement_id}")
            
            # 验证结算记录是否存在且属于该商户
            settlement = await self._get_settlement_record(settlement_id, merchant_id)
            if not settlement:
                raise SettlementException("结算记录不存在")
            
            if settlement.status != SettlementStatus.COMPLETED:
                raise SettlementException("只能确认已完成的结算")
            
            # 这里可以添加验证码验证逻辑
            if verification_code:
                # 验证验证码
                if not await self._verify_verification_code(merchant_id, verification_code):
                    raise SettlementException("验证码错误")
            
            # 更新结算记录为已确认（这里可以根据业务需求添加确认状态）
            # 暂时只记录确认日志
            
            logger.info(f"商户 {merchant_id} 成功确认结算 {settlement_id}")
            return True
            
        except SettlementException:
            raise
        except Exception as e:
            logger.error(f"确认结算失败: {str(e)}", exc_info=True)
            raise SettlementException("确认结算失败")
    
    async def get_next_settlement_estimate(self, merchant_id: str) -> NextSettlementEstimate:
        """获取下次结算预估"""
        try:
            logger.info(f"开始获取商户 {merchant_id} 的下次结算预估")
            
            # 计算下次结算日期（假设为每周一）
            today = date.today()
            days_until_monday = (7 - today.weekday()) % 7
            # 如果今天就是周一，则下次结算是下周
            if days_until_monday == 0:
                days_until_monday = 7
            next_settlement_date = today + timedelta(days=days_until_monday)
            
            # 获取待结算金额作为预估金额
            estimated_amount = await self._get_pending_amount(merchant_id)
            
            # 获取符合条件的订单数
            eligible_orders = await self._get_eligible_orders_count(merchant_id)
            
            estimate = NextSettlementEstimate(
                estimated_amount=estimated_amount,
                settlement_date=next_settlement_date,
                days_remaining=days_until_monday,
                eligible_orders=eligible_orders
            )
            
            logger.debug(f"下次结算预估: 日期={next_settlement_date}, 金额={estimated_amount}")
            
            return estimate
            
        except Exception as e:
            logger.error(f"获取下次结算预估失败: {str(e)}", exc_info=True)
            raise SettlementException("获取下次结算预估失败")
    
    async def process_settlement(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[SettlementRecord]:
        """处理结算"""
        try:
            logger.info(f"开始处理商户 {merchant_id} 的结算，日期范围: {start_date} 到 {end_date}")
            
            # 检查是否已有结算记录
            existing_settlement = await self._get_existing_settlement(
                merchant_id, start_date, end_date
            )
            
            if existing_settlement:
                logger.info(f"结算记录已存在: {existing_settlement.settlement_no}")
                return existing_settlement
            
            # 计算结算金额
            settlement_data = await self._calculate_settlement_amount(
                merchant_id, start_date, end_date
            )
            
            if settlement_data['total_amount'] <= 0:
                logger.info(f"商户 {merchant_id} 在 {start_date} 到 {end_date} 期间无结算金额")
                return None
            
            # 生成结算记录
            settlement_record = await self._create_settlement_record(
                merchant_id, start_date, end_date, settlement_data
            )
            
            # 这里可以添加实际的结算处理逻辑（如调用银行接口等）
            # 暂时模拟结算成功
            await self._update_settlement_status(
                settlement_record.id, SettlementStatus.COMPLETED
            )
            
            logger.info(f"结算处理成功: {settlement_record.settlement_no}")
            return settlement_record
            
        except Exception as e:
            logger.error(f"结算处理失败: {str(e)}", exc_info=True)
            # 更新结算状态为失败
            if 'settlement_record' in locals() and 'settlement_record' in locals():
                await self._update_settlement_status(
                    settlement_record.id, SettlementStatus.FAILED, str(e)
                )
            raise SettlementException("结算处理失败")
    
    async def _get_settled_amount(self, merchant_id: str) -> Decimal:
        """获取已结算金额"""
        try:
            logger.debug(f"查询商户 {merchant_id} 的已结算金额")
            
            records = await db.execute_query(
                "finances_settlement_records",
                filters={
                    "merchant_id": merchant_id,
                    "status": SettlementStatus.COMPLETED.value
                }
            )
            
            total_amount = Decimal('0')
            for record in records:
                total_amount += Decimal(str(record.get('net_amount', 0)))
            
            logger.debug(f"商户 {merchant_id} 的已结算金额: {total_amount}")
            
            return total_amount
            
        except Exception as e:
            logger.error(f"获取已结算金额失败: {str(e)}", exc_info=True)
            return Decimal('0')
    
    async def _get_pending_amount(self, merchant_id: str) -> Decimal:
        """获取待结算金额"""
        try:
            logger.debug(f"查询商户 {merchant_id} 的待结算金额")
            
            # 这里需要根据业务逻辑计算待结算金额
            # 暂时返回一个模拟值
            pending_amount = Decimal('1500000')
            
            logger.debug(f"商户 {merchant_id} 的待结算金额: {pending_amount}")
            
            return pending_amount
            
        except Exception as e:
            logger.error(f"获取待结算金额失败: {str(e)}", exc_info=True)
            return Decimal('0')
    
    async def _get_next_settlement_days(self) -> int:
        """获取下次结算天数"""
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        # 如果今天就是周一，则下次结算是下周
        if days_until_monday == 0:
            days_until_monday = 7
        return days_until_monday
    
    async def _get_bank_account(self, merchant_id: str) -> str:
        """获取银行账户"""
        try:
            logger.debug(f"查询商户 {merchant_id} 的银行账户信息")
            
            # 这里需要查询商户的银行账户信息
            # 暂时返回模拟数据
            bank_account = "Vietcombank ***6789"
            
            logger.debug(f"商户 {merchant_id} 的银行账户: {bank_account}")
            
            return bank_account
            
        except Exception as e:
            logger.error(f"获取银行账户失败: {str(e)}", exc_info=True)
            return "未设置"
    
    async def _get_last_settlement(self, merchant_id: str) -> Optional[SettlementRecord]:
        """获取最后结算记录"""
        try:
            logger.debug(f"查询商户 {merchant_id} 的最后结算记录")
            
            records = await db.execute_query(
                "finances_settlement_records",
                filters={
                    "merchant_id": merchant_id,
                    "status": SettlementStatus.COMPLETED.value
                },
                order_by="settlement_date.desc",
                limit=1
            )
            
            if records:
                settlement = SettlementRecord(**records[0])
                logger.debug(f"找到商户 {merchant_id} 的最后结算记录: {settlement.settlement_no}")
                return settlement
            
            logger.debug(f"未找到商户 {merchant_id} 的结算记录")
            return None
            
        except Exception as e:
            logger.error(f"获取最后结算记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _get_settlement_record(
        self, 
        settlement_id: str, 
        merchant_id: str
    ) -> Optional[SettlementRecord]:
        """获取结算记录"""
        try:
            logger.debug(f"查询结算记录: {settlement_id}")
            
            records = await db.execute_query(
                "finances_settlement_records",
                filters={
                    "id": settlement_id,
                    "merchant_id": merchant_id
                },
                limit=1
            )
            
            if records:
                settlement = SettlementRecord(**records[0])
                logger.debug(f"找到结算记录: {settlement.settlement_no}")
                return settlement
            
            logger.debug(f"未找到结算记录: {settlement_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取结算记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _verify_verification_code(self, merchant_id: str, code: str) -> bool:
        """验证验证码"""
        # 这里实现验证码验证逻辑
        # 暂时返回True
        logger.debug(f"验证商户 {merchant_id} 的验证码")
        return True
    
    async def _get_eligible_orders_count(self, merchant_id: str) -> int:
        """获取符合条件的订单数"""
        try:
            logger.debug(f"查询商户 {merchant_id} 的符合条件订单数")
            
            # 这里需要根据业务逻辑查询符合条件的订单
            # 暂时返回模拟数据
            order_count = 45
            
            logger.debug(f"商户 {merchant_id} 的符合条件订单数: {order_count}")
            
            return order_count
            
        except Exception as e:
            logger.error(f"获取符合条件的订单数失败: {str(e)}", exc_info=True)
            return 0
    
    async def _get_existing_settlement(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[SettlementRecord]:
        """获取已存在的结算记录"""
        try:
            logger.debug(f"检查是否存在重复的结算记录: 商户={merchant_id}, 日期范围={start_date}至{end_date}")
            
            records = await db.execute_query(
                "finances_settlement_records",
                filters={
                    "merchant_id": merchant_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                limit=1
            )
            
            if records:
                settlement = SettlementRecord(**records[0])
                logger.debug(f"找到已存在的结算记录: {settlement.settlement_no}")
                return settlement
            
            logger.debug("未找到已存在的结算记录")
            return None
            
        except Exception as e:
            logger.error(f"检查已存在结算记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _calculate_settlement_amount(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Decimal]:
        """计算结算金额"""
        try:
            logger.debug(f"计算商户 {merchant_id} 的结算金额，日期范围: {start_date} 至 {end_date}")
            
            # 查询期间的日汇总数据
            summaries = await db.execute_query(
                "finances_daily_summary",
                filters={
                    "merchant_id": merchant_id,
                    "summary_date": {
                        "gte": start_date.isoformat(),
                        "lte": end_date.isoformat()
                    }
                }
            )
            
            total_amount = Decimal('0')
            platform_fee = Decimal('0')
            refund_amount = Decimal('0')
            
            for summary in summaries:
                total_amount += Decimal(str(summary.get('settlement_amount', 0)))
                platform_fee += Decimal(str(summary.get('platform_fee', 0)))
                refund_amount += Decimal(str(summary.get('refund_amount', 0)))
            
            net_amount = total_amount - platform_fee - refund_amount
            
            calculation_result = {
                "total_amount": total_amount,
                "platform_fee": platform_fee,
                "refund_amount": refund_amount,
                "net_amount": net_amount
            }
            
            logger.debug(f"结算金额计算完成: {calculation_result}")
            
            return calculation_result
            
        except Exception as e:
            logger.error(f"计算结算金额失败: {str(e)}", exc_info=True)
            return {
                "total_amount": Decimal('0'),
                "platform_fee": Decimal('0'),
                "refund_amount": Decimal('0'),
                "net_amount": Decimal('0')
            }
    
    async def _create_settlement_record(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date, 
        settlement_data: Dict[str, Decimal]
    ) -> SettlementRecord:
        """创建结算记录"""
        try:
            logger.info(f"为商户 {merchant_id} 创建结算记录")
            
            settlement_no = f"STL{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
            
            settlement_record = SettlementRecord(
                id=str(uuid.uuid4()),
                merchant_id=merchant_id,
                settlement_no=settlement_no,
                settlement_date=date.today(),
                start_date=start_date,
                end_date=end_date,
                total_amount=settlement_data['total_amount'],
                platform_fee=settlement_data['platform_fee'],
                refund_amount=settlement_data.get('refund_amount', Decimal('0')),
                net_amount=settlement_data['net_amount'],
                bank_account=await self._get_bank_account(merchant_id),
                bank_name="Vietcombank",
                status=SettlementStatus.PROCESSING
            )
            
            # 保存到数据库
            await db.insert_data(
                "finances_settlement_records",
                settlement_record.dict()
            )
            
            logger.info(f"成功创建结算记录: {settlement_no}")
            
            return settlement_record
            
        except Exception as e:
            logger.error(f"创建结算记录失败: {str(e)}", exc_info=True)
            raise SettlementException("创建结算记录失败")
    
    async def _update_settlement_status(
        self, 
        settlement_id: str, 
        status: SettlementStatus, 
        failure_reason: str = None
    ):
        """更新结算状态"""
        try:
            logger.info(f"更新结算记录 {settlement_id} 的状态为 {status.value}")
            
            update_data = {
                "status": status.value,
                "updated_at": datetime.now().isoformat()
            }
            
            if status == SettlementStatus.COMPLETED:
                update_data["settled_at"] = datetime.now().isoformat()
            elif status == SettlementStatus.FAILED and failure_reason:
                update_data["failure_reason"] = failure_reason
            
            await db.update_data(
                "finances_settlement_records",
                update_data,
                {"id": settlement_id}
            )
            
            logger.info(f"成功更新结算记录 {settlement_id} 的状态")
            
        except Exception as e:
            logger.error(f"更新结算状态失败: {str(e)}", exc_info=True)
            raise SettlementException("更新结算状态失败")
    
    async def _get_settlement_count(self, filters: Dict[str, Any]) -> int:
        """获取结算记录总数"""
        try:
            logger.debug("查询结算记录总数")
            
            # 这里应该调用数据库的 COUNT 方法
            # 示例实现，实际应根据数据库客户端调整
            count = await db.execute_count("finances_settlement_records", filters=filters)
            return count if count else 0
            
        except Exception as e:
            logger.error(f"获取结算记录总数失败: {str(e)}", exc_info=True)
            # 回退到原来的实现方式
            records = await db.execute_query("finances_settlement_records", filters=filters)
            return len(records)