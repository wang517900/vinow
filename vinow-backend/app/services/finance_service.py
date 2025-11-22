商户系统6财务中心
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import logging
import os

from app.database.supabase_client import db
from app.models.finance import FinanceDailySummary, DailyIncomeResponse, IncomeFlowItem
from app.schemas.finance import IncomeFlowParams, PaginatedResponse
from app.utils.date_utils import DateUtils
from app.core.exceptions import FinanceDataException

logger = logging.getLogger(__name__)


class FinanceService:
    """财务数据服务"""
    
    async def get_daily_income(
        self, 
        merchant_id: str, 
        target_date: date = None
    ) -> DailyIncomeResponse:
        """获取日收入数据"""
        try:
            if target_date is None:
                target_date = date.today()
            
            logger.info(f"开始获取商户 {merchant_id} 在 {target_date} 的日收入数据")
            
            # 查询日汇总数据
            summary_data = await self._get_daily_summary(merchant_id, target_date)
            
            if summary_data:
                # 计算昨日对比
                yesterday = target_date - timedelta(days=1)
                yesterday_data = await self._get_daily_summary(merchant_id, yesterday)
                
                comparison = None
                if yesterday_data and yesterday_data.total_income > 0:
                    growth_rate = (
                        (summary_data.total_income - yesterday_data.total_income) / 
                        yesterday_data.total_income * 100
                    )
                    comparison = float(round(growth_rate, 2))
                
                net_income = summary_data.total_income - summary_data.platform_fee
                
                logger.debug(f"成功获取到商户 {merchant_id} 的日收入数据: 总收入={summary_data.total_income}, 净收入={net_income}")
                
                return DailyIncomeResponse(
                    date=target_date,
                    total_income=summary_data.total_income,
                    order_count=summary_data.order_count,
                    successful_orders=summary_data.successful_orders,
                    coupon_deduction=summary_data.coupon_deduction,
                    platform_fee=summary_data.platform_fee,
                    net_income=net_income,
                    yesterday_comparison=comparison
                )
            else:
                # 如果没有汇总数据，返回空数据
                logger.info(f"商户 {merchant_id} 在 {target_date} 没有汇总数据")
                return DailyIncomeResponse(
                    date=target_date,
                    total_income=Decimal('0'),
                    order_count=0,
                    successful_orders=0,
                    coupon_deduction=Decimal('0'),
                    platform_fee=Decimal('0'),
                    net_income=Decimal('0'),
                    yesterday_comparison=None
                )
                
        except Exception as e:
            logger.error(f"获取日收入数据失败: {str(e)}", exc_info=True)
            raise FinanceDataException("获取日收入数据失败")
    
    async def get_income_flow(
        self, 
        merchant_id: str, 
        params: IncomeFlowParams
    ) -> PaginatedResponse[IncomeFlowItem]:
        """获取收入流水"""
        try:
            # 验证分页参数
            if params.limit > 100:
                raise FinanceDataException("单页查询数量不能超过100条")
            
            if params.limit <= 0 or params.offset < 0:
                raise FinanceDataException("分页参数无效")
            
            # 计算日期范围
            start_date, end_date = DateUtils.calculate_date_range(
                params.start_date, params.end_date
            )
            
            if not DateUtils.is_valid_date_range(start_date, end_date, max_days=30):
                raise FinanceDataException("查询日期范围不能超过30天")
            
            logger.info(f"获取商户 {merchant_id} 的收入流水，日期范围: {start_date} 至 {end_date}")
            
            # 构建查询条件
            filters = {
                "merchant_id": merchant_id,
                "order_time": {
                    "gte": start_date.isoformat(),
                    "lte": end_date.isoformat()
                }
            }
            
            # 添加其他过滤条件
            if params.payment_method:
                filters["payment_method"] = params.payment_method
            
            if params.order_status:
                filters["order_status"] = params.order_status
            
            # 执行查询（这里需要根据实际的订单表结构调整）
            orders = await db.execute_query(
                "orders",  # 假设订单表名为 orders
                filters=filters,
                order_by="order_time.desc",
                limit=params.limit,
                offset=params.offset
            )
            
            # 转换为收入流水项
            items = []
            for order in orders:
                items.append(IncomeFlowItem(
                    id=order.get('id'),
                    order_id=order.get('order_no'),
                    order_time=datetime.fromisoformat(order.get('created_at')),
                    amount=Decimal(str(order.get('amount', 0))),
                    payment_method=order.get('payment_method', ''),
                    order_status=order.get('status', ''),
                    customer_name=order.get('customer_name')
                ))
            
            # 获取总数（优化查询）
            total = await self._get_order_count(filters)
            
            page = (params.offset // params.limit) + 1 if params.limit > 0 else 1
            
            logger.debug(f"成功获取到 {len(items)} 条收入流水记录，总记录数: {total}")
            
            return PaginatedResponse.create(
                items=items,
                total=total,
                page=page,
                page_size=params.limit
            )
            
        except FinanceDataException:
            raise
        except Exception as e:
            logger.error(f"获取收入流水失败: {str(e)}", exc_info=True)
            raise FinanceDataException("获取收入流水失败")
    
    async def generate_daily_summary(
        self, 
        merchant_id: str, 
        summary_date: date
    ) -> Optional[FinanceDailySummary]:
        """生成日汇总数据"""
        try:
            logger.info(f"开始生成商户 {merchant_id} 在 {summary_date} 的日汇总数据")
            
            # 查询当天的订单数据
            orders = await self._get_daily_orders(merchant_id, summary_date)
            
            if not orders:
                logger.info(f"商户 {merchant_id} 在 {summary_date} 没有订单数据")
                return None
            
            # 计算汇总数据
            total_income = Decimal('0')
            order_count = len(orders)
            successful_orders = 0
            coupon_deduction = Decimal('0')
            platform_fee = Decimal('0')
            refund_amount = Decimal('0')
            
            # 从环境变量获取平台费率，默认为2%
            platform_fee_rate = Decimal(str(os.getenv('PLATFORM_FEE_RATE', '0.02')))
            
            for order in orders:
                order_status = order.get('status')
                amount = Decimal(str(order.get('amount', 0)))
                
                if order_status == 'completed':
                    total_income += amount
                    successful_orders += 1
                    
                    # 计算平台费用
                    platform_fee += amount * platform_fee_rate
                
                elif order_status == 'refunded':
                    refund_amount += amount
                
                # 计算优惠券抵扣
                coupon_amount = Decimal(str(order.get('coupon_amount', 0)))
                coupon_deduction += coupon_amount
            
            # 计算结算金额
            settlement_amount = total_income - platform_fee - refund_amount
            
            # 创建汇总数据对象
            summary_id = f"{merchant_id}_{summary_date.isoformat()}"
            
            summary = FinanceDailySummary(
                id=summary_id,
                merchant_id=merchant_id,
                summary_date=summary_date,
                total_income=total_income,
                order_count=order_count,
                successful_orders=successful_orders,
                failed_orders=order_count - successful_orders,
                coupon_deduction=coupon_deduction,
                platform_fee=platform_fee,
                settlement_amount=settlement_amount,
                refund_amount=refund_amount
            )
            
            logger.info(f"成功生成商户 {merchant_id} 的日汇总数据: 总收入={total_income}, 成功订单={successful_orders}")
            
            return summary
            
        except Exception as e:
            logger.error(f"生成日汇总数据失败: {str(e)}", exc_info=True)
            return None
    
    async def _get_daily_summary(
        self, 
        merchant_id: str, 
        target_date: date
    ) -> Optional[FinanceDailySummary]:
        """获取日汇总数据"""
        try:
            logger.debug(f"查询商户 {merchant_id} 在 {target_date} 的日汇总数据")
            
            data = await db.execute_query(
                "finances_daily_summary",
                filters={
                    "merchant_id": merchant_id,
                    "summary_date": target_date.isoformat()
                },
                limit=1
            )
            
            if data:
                logger.debug(f"找到商户 {merchant_id} 在 {target_date} 的日汇总数据")
                return FinanceDailySummary(**data[0])
            
            logger.debug(f"未找到商户 {merchant_id} 在 {target_date} 的日汇总数据")
            return None
            
        except Exception as e:
            logger.error(f"查询日汇总数据失败: {str(e)}", exc_info=True)
            return None
    
    async def _get_daily_orders(
        self, 
        merchant_id: str, 
        order_date: date
    ) -> List[Dict[str, Any]]:
        """获取日订单数据"""
        try:
            logger.debug(f"查询商户 {merchant_id} 在 {order_date} 的订单数据")
            
            start_datetime = datetime.combine(order_date, datetime.min.time())
            end_datetime = datetime.combine(order_date, datetime.max.time())
            
            orders = await db.execute_query(
                "orders",
                filters={
                    "merchant_id": merchant_id,
                    "created_at": {
                        "gte": start_datetime.isoformat(),
                        "lte": end_datetime.isoformat()
                    }
                }
            )
            
            logger.debug(f"查询到商户 {merchant_id} 在 {order_date} 的 {len(orders)} 条订单数据")
            
            return orders
            
        except Exception as e:
            logger.error(f"查询日订单数据失败: {str(e)}", exc_info=True)
            return []
    
    async def _get_order_count(self, filters: Dict[str, Any]) -> int:
        """获取订单总数（优化版本）"""
        try:
            # 这里应该调用数据库的 COUNT 方法而不是查询所有数据再计算长度
            # 示例实现，实际应根据数据库客户端调整
            count = await db.execute_count("orders", filters=filters)
            return count if count else 0
        except Exception as e:
            logger.error(f"获取订单总数失败: {str(e)}", exc_info=True)
            # 回退到原来的实现方式
            orders = await db.execute_query("orders", filters=filters)
            return len(orders)

        商家板块6财务中心增强
        from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import logging

from app.database.supabase_client import db
from app.models.finance import FinanceDailySummary, DailyIncomeResponse, IncomeFlowItem
from app.schemas.finance import IncomeFlowParams, PaginatedResponse
from app.utils.date_utils import DateUtils
from app.core.exceptions import FinanceDataException
from app.core.security_enhanced import SecurityAudit, rate_limit_check

logger = logging.getLogger(__name__)


class FinanceServiceEnhanced:
    """增强的财务数据服务"""
    
    async def get_daily_income(
        self, 
        merchant_id: str, 
        target_date: date = None,
        user_id: str = None
    ) -> DailyIncomeResponse:
        """获取日收入数据（增强版）"""
        try:
            logger.info(f"获取日收入数据 - 商户: {merchant_id}, 日期: {target_date}")
            
            if target_date is None:
                target_date = date.today()
            
            # 验证日期范围（不能查询未来日期）
            if target_date > date.today():
                raise FinanceDataException("不能查询未来日期的数据")
            
            # 查询日汇总数据
            summary_data = await self._get_daily_summary(merchant_id, target_date)
            
            if summary_data:
                # 记录数据访问
                await SecurityAudit.log_sensitive_operation(
                    "daily_income_query",
                    merchant_id,
                    user_id or "system",
                    "financial_data",
                    f"daily_summary_{target_date}",
                    {"date": target_date.isoformat()}
                )
                
                # 计算昨日对比
                yesterday = target_date - timedelta(days=1)
                yesterday_data = await self._get_daily_summary(merchant_id, yesterday)
                
                comparison = None
                if yesterday_data and yesterday_data.total_income > 0:
                    growth_rate = (
                        (summary_data.total_income - yesterday_data.total_income) / 
                        yesterday_data.total_income * 100
                    )
                    comparison = float(round(growth_rate, 2))
                
                response = DailyIncomeResponse(
                    date=target_date,
                    total_income=summary_data.total_income,
                    order_count=summary_data.order_count,
                    successful_orders=summary_data.successful_orders,
                    coupon_deduction=summary_data.coupon_deduction,
                    platform_fee=summary_data.platform_fee,
                    net_income=summary_data.total_income - summary_data.platform_fee,
                    yesterday_comparison=comparison
                )
                
                logger.info(f"日收入数据查询成功 - 商户: {merchant_id}, 总收入: {summary_data.total_income}")
                return response
            else:
                # 如果没有汇总数据，返回空数据
                logger.info(f"未找到日收入数据 - 商户: {merchant_id}, 日期: {target_date}")
                return DailyIncomeResponse(
                    date=target_date,
                    total_income=Decimal('0'),
                    order_count=0,
                    successful_orders=0,
                    coupon_deduction=Decimal('0'),
                    platform_fee=Decimal('0'),
                    net_income=Decimal('0'),
                    yesterday_comparison=None
                )
                
        except FinanceDataException:
            raise
        except Exception as e:
            logger.error(f"获取日收入数据失败 - 商户: {merchant_id}, 错误: {str(e)}", exc_info=True)
            
            # 记录安全事件
            await SecurityAudit.log_security_event(
                "data_access_error",
                merchant_id,
                user_id or "system",
                {"operation": "daily_income_query", "error": str(e)},
                "medium"
            )
            
            raise FinanceDataException("获取日收入数据失败")
    
    async def get_income_flow(
        self, 
        merchant_id: str, 
        params: IncomeFlowParams,
        user_id: str = None
    ) -> PaginatedResponse[IncomeFlowItem]:
        """获取收入流水（增强版）"""
        try:
            logger.info(f"获取收入流水 - 商户: {merchant_id}, 参数: {params.dict()}")
            
            # 计算日期范围
            start_date, end_date = DateUtils.calculate_date_range(
                params.start_date, params.end_date
            )
            
            if not DateUtils.is_valid_date_range(start_date, end_date, max_days=30):
                logger.warning(f"日期范围过大 - 商户: {merchant_id}, 开始: {start_date}, 结束: {end_date}")
                raise FinanceDataException("查询日期范围不能超过30天")
            
            # 记录数据访问
            await SecurityAudit.log_sensitive_operation(
                "income_flow_query",
                merchant_id,
                user_id or "system",
                "financial_data",
                f"income_flow_{start_date}_{end_date}",
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "filters": {
                        "payment_method": params.payment_method,
                        "order_status": params.order_status
                    }
                }
            )
            
            # 构建查询条件
            filters = {
                "merchant_id": merchant_id,
                "order_time": {
                    "gte": start_date.isoformat(),
                    "lte": end_date.isoformat()
                }
            }
            
            # 添加其他过滤条件
            if params.payment_method:
                filters["payment_method"] = params.payment_method
            
            if params.order_status:
                filters["order_status"] = params.order_status
            
            # 执行查询
            orders = await db.execute_query(
                "orders",
                filters=filters,
                order_by="order_time.desc",
                limit=params.limit,
                offset=params.offset
            )
            
            # 转换为收入流水项
            items = []
            for order in orders:
                items.append(IncomeFlowItem(
                    id=order.get('id'),
                    order_id=order.get('order_no'),
                    order_time=datetime.fromisoformat(order.get('created_at')),
                    amount=Decimal(str(order.get('amount', 0))),
                    payment_method=order.get('payment_method', ''),
                    order_status=order.get('status', ''),
                    customer_name=order.get('customer_name')
                ))
            
            # 获取总数
            total = len(await db.execute_query(
                "orders",
                filters=filters
            ))
            
            response = PaginatedResponse.create(
                items=items,
                total=total,
                page=(params.offset // params.limit) + 1,
                page_size=params.limit
            )
            
            logger.info(f"收入流水查询成功 - 商户: {merchant_id}, 记录数: {len(items)}")
            return response
            
        except FinanceDataException:
            raise
        except Exception as e:
            logger.error(f"获取收入流水失败 - 商户: {merchant_id}, 错误: {str(e)}", exc_info=True)
            
            # 记录安全事件
            await SecurityAudit.log_security_event(
                "data_access_error",
                merchant_id,
                user_id or "system",
                {"operation": "income_flow_query", "error": str(e)},
                "medium"
            )
            
            raise FinanceDataException("获取收入流水失败")
    
    # 其他方法也类似增强...
