商户系统6财务中心
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging
import uuid
import os

from app.database.supabase_client import db
from app.models.finance import (
    ReportType, ReportExport, FinancialReportData, 
    ReportExportResponse, InvoiceRequest, InvoiceStatus
)
from app.schemas.finance import ReportExportRequest, ReportParams
from app.utils.date_utils import DateUtils
from app.utils.export_utils import ExportUtils
from app.core.exceptions import ReportException

logger = logging.getLogger(__name__)


class ReportService:
    """报表服务"""
    
    def __init__(self):
        self.export_utils = ExportUtils()
    
    async def generate_daily_report(
        self, 
        merchant_id: str, 
        report_date: date = None,
        include_details: bool = False
    ) -> FinancialReportData:
        """生成日报表"""
        try:
            logger.info(f"开始生成商户 {merchant_id} 的日报表，日期: {report_date}")
            
            if report_date is None:
                report_date = date.today()
            
            # 获取日报表数据
            report_data = await self._get_daily_report_data(merchant_id, report_date)
            
            # 如果需要包含明细，获取明细数据
            details = []
            if include_details:
                details = await self._get_daily_details(merchant_id, report_date)
            
            # 计算同比数据
            comparison_data = await self._calculate_daily_comparison(merchant_id, report_date)
            
            result = FinancialReportData(
                period=report_date.isoformat(),
                total_income=report_data['total_income'],
                total_orders=report_data['order_count'],
                avg_order_value=report_data['avg_order_value'],
                refund_rate=report_data['refund_rate'],
                platform_fee_rate=report_data['platform_fee_rate'],
                net_profit=report_data['net_income'],
                comparison_rate=comparison_data,
                details=details if include_details else None
            )
            
            logger.info(f"日报表生成完成: 总收入={report_data['total_income']}")
            
            return result
            
        except Exception as e:
            logger.error(f"生成日报表失败: {str(e)}", exc_info=True)
            raise ReportException("生成日报表失败")
    
    async def generate_weekly_report(
        self, 
        merchant_id: str, 
        start_date: date = None,
        end_date: date = None,
        include_details: bool = False
    ) -> FinancialReportData:
        """生成周报表"""
        try:
            logger.info(f"开始生成商户 {merchant_id} 的周报表")
            
            if start_date is None or end_date is None:
                start_date, end_date = DateUtils.get_week_range()
            
            # 获取周报表数据
            report_data = await self._get_weekly_report_data(merchant_id, start_date, end_date)
            
            # 计算环比数据
            comparison_data = await self._calculate_weekly_comparison(merchant_id, start_date, end_date)
            
            result = FinancialReportData(
                period=f"{start_date.isoformat()} 到 {end_date.isoformat()}",
                total_income=report_data['total_income'],
                total_orders=report_data['order_count'],
                avg_order_value=report_data['avg_order_value'],
                refund_rate=report_data['refund_rate'],
                platform_fee_rate=report_data['platform_fee_rate'],
                net_profit=report_data['net_income'],
                comparison_rate=comparison_data
            )
            
            logger.info(f"周报表生成完成: 总收入={report_data['total_income']}")
            
            return result
            
        except Exception as e:
            logger.error(f"生成周报表失败: {str(e)}", exc_info=True)
            raise ReportException("生成周报表失败")
    
    async def generate_monthly_report(
        self, 
        merchant_id: str, 
        report_month: date = None,
        include_details: bool = False
    ) -> FinancialReportData:
        """生成月报表"""
        try:
            logger.info(f"开始生成商户 {merchant_id} 的月报表")
            
            if report_month is None:
                report_month = date.today().replace(day=1)
            
            start_date, end_date = DateUtils.get_month_range(report_month)
            
            # 获取月报表数据
            report_data = await self._get_monthly_report_data(merchant_id, start_date, end_date)
            
            # 计算同比数据
            comparison_data = await self._calculate_monthly_comparison(merchant_id, report_month)
            
            result = FinancialReportData(
                period=report_month.strftime("%Y年%m月"),
                total_income=report_data['total_income'],
                total_orders=report_data['order_count'],
                avg_order_value=report_data['avg_order_value'],
                refund_rate=report_data['refund_rate'],
                platform_fee_rate=report_data['platform_fee_rate'],
                net_profit=report_data['net_income'],
                comparison_rate=comparison_data
            )
            
            logger.info(f"月报表生成完成: 总收入={report_data['total_income']}")
            
            return result
            
        except Exception as e:
            logger.error(f"生成月报表失败: {str(e)}", exc_info=True)
            raise ReportException("生成月报表失败")
    
    async def export_report(
        self, 
        merchant_id: str, 
        request: ReportExportRequest
    ) -> ReportExportResponse:
        """导出报表"""
        try:
            logger.info(f"开始导出商户 {merchant_id} 的报表，类型: {request.report_type}")
            
            # 生成报表数据
            report_data = await self._generate_report_data(merchant_id, request)
            
            if not report_data:
                raise ReportException("没有可导出的数据")
            
            # 生成文件名
            filename = self.export_utils.generate_filename(
                merchant_id, request.report_type, request.format
            )
            
            # 导出文件
            if request.format == "excel":
                filepath = self.export_utils.export_to_excel(report_data, filename)
            elif request.format == "csv":
                filepath = self.export_utils.export_to_csv(report_data, filename)
            else:
                raise ReportException(f"不支持的导出格式: {request.format}")
            
            # 创建导出记录
            export_record = await self._create_export_record(
                merchant_id, request, filename, filepath
            )
            
            # 生成文件URL
            file_url = self.export_utils.get_file_url(filename)
            
            response = ReportExportResponse(
                export_id=export_record.id,
                file_url=file_url,
                file_name=filename,
                file_size=export_record.file_size,
                expires_at=export_record.expires_at
            )
            
            logger.info(f"报表导出完成: 文件名={filename}")
            
            return response
            
        except ReportException:
            raise
        except Exception as e:
            logger.error(f"导出报表失败: {str(e)}", exc_info=True)
            raise ReportException("导出报表失败")
    
    async def get_export_history(
        self, 
        merchant_id: str, 
        limit: int = 10
    ) -> List[ReportExport]:
        """获取导出历史"""
        try:
            logger.info(f"获取商户 {merchant_id} 的报表导出历史")
            
            # 验证参数
            if limit > 100:
                raise ReportException("查询数量不能超过100条")
            
            if limit <= 0:
                raise ReportException("查询数量必须大于0")
            
            records = await db.execute_query(
                "finances_report_exports",
                filters={"merchant_id": merchant_id},
                order_by="created_at.desc",
                limit=limit
            )
            
            export_history = []
            for record in records:
                export_history.append(ReportExport(**record))
            
            logger.debug(f"获取到 {len(export_history)} 条导出记录")
            
            return export_history
            
        except ReportException:
            raise
        except Exception as e:
            logger.error(f"获取导出历史失败: {str(e)}", exc_info=True)
            raise ReportException("获取导出历史失败")
    
    async def _get_daily_report_data(
        self, 
        merchant_id: str, 
        report_date: date
    ) -> Dict[str, Any]:
        """获取日报表数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的日报表数据，日期: {report_date}")
            
            # 查询日汇总数据
            summary = await db.execute_query(
                "finances_daily_summary",
                filters={
                    "merchant_id": merchant_id,
                    "summary_date": report_date.isoformat()
                },
                limit=1
            )
            
            if summary:
                data = summary[0]
                total_income = Decimal(str(data.get('total_income', 0)))
                order_count = data.get('order_count', 0)
                platform_fee = Decimal(str(data.get('platform_fee', 0)))
                refund_amount = Decimal(str(data.get('refund_amount', 0)))
                
                # 计算平均订单价值
                avg_order_value = total_income / order_count if order_count > 0 else Decimal('0')
                
                # 计算退款率
                refund_rate = (refund_amount / total_income * 100) if total_income > 0 else 0
                
                # 计算平台费率
                platform_fee_rate = (platform_fee / total_income * 100) if total_income > 0 else 0
                
                # 计算净收入
                net_income = total_income - platform_fee - refund_amount
                
                result = {
                    'total_income': total_income,
                    'order_count': order_count,
                    'avg_order_value': avg_order_value,
                    'refund_rate': float(refund_rate),
                    'platform_fee_rate': float(platform_fee_rate),
                    'net_income': net_income
                }
                
                logger.debug(f"日报表数据获取完成: {result}")
                return result
            else:
                result = {
                    'total_income': Decimal('0'),
                    'order_count': 0,
                    'avg_order_value': Decimal('0'),
                    'refund_rate': 0.0,
                    'platform_fee_rate': 0.0,
                    'net_income': Decimal('0')
                }
                logger.debug("未找到日报表数据，返回默认值")
                return result
                
        except Exception as e:
            logger.error(f"获取日报表数据失败: {str(e)}", exc_info=True)
            return {
                'total_income': Decimal('0'),
                'order_count': 0,
                'avg_order_value': Decimal('0'),
                'refund_rate': 0.0,
                'platform_fee_rate': 0.0,
                'net_income': Decimal('0')
            }
    
    async def _get_weekly_report_data(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """获取周报表数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的周报表数据，日期范围: {start_date} 至 {end_date}")
            
            # 查询周期内的日汇总数据
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
            
            total_income = Decimal('0')
            total_orders = 0
            total_platform_fee = Decimal('0')
            total_refund_amount = Decimal('0')
            
            for summary in summaries:
                total_income += Decimal(str(summary.get('total_income', 0)))
                total_orders += summary.get('order_count', 0)
                total_platform_fee += Decimal(str(summary.get('platform_fee', 0)))
                total_refund_amount += Decimal(str(summary.get('refund_amount', 0)))
            
            # 计算各项指标
            avg_order_value = total_income / total_orders if total_orders > 0 else Decimal('0')
            refund_rate = (total_refund_amount / total_income * 100) if total_income > 0 else 0
            platform_fee_rate = (total_platform_fee / total_income * 100) if total_income > 0 else 0
            net_income = total_income - total_platform_fee - total_refund_amount
            
            result = {
                'total_income': total_income,
                'order_count': total_orders,
                'avg_order_value': avg_order_value,
                'refund_rate': float(refund_rate),
                'platform_fee_rate': float(platform_fee_rate),
                'net_income': net_income
            }
            
            logger.debug(f"周报表数据获取完成: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取周报表数据失败: {str(e)}", exc_info=True)
            return {
                'total_income': Decimal('0'),
                'order_count': 0,
                'avg_order_value': Decimal('0'),
                'refund_rate': 0.0,
                'platform_fee_rate': 0.0,
                'net_income': Decimal('0')
            }
    
    async def _get_monthly_report_data(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """获取月报表数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的月报表数据")
            
            # 月报表数据计算逻辑与周报表类似
            return await self._get_weekly_report_data(merchant_id, start_date, end_date)
            
        except Exception as e:
            logger.error(f"获取月报表数据失败: {str(e)}", exc_info=True)
            return {
                'total_income': Decimal('0'),
                'order_count': 0,
                'avg_order_value': Decimal('0'),
                'refund_rate': 0.0,
                'platform_fee_rate': 0.0,
                'net_income': Decimal('0')
            }
    
    async def _calculate_daily_comparison(self, merchant_id: str, report_date: date) -> float:
        """计算日报表对比数据"""
        try:
            logger.debug(f"计算商户 {merchant_id} 的日报表对比数据")
            
            # 获取昨日数据
            yesterday = report_date - timedelta(days=1)
            today_data = await self._get_daily_report_data(merchant_id, report_date)
            yesterday_data = await self._get_daily_report_data(merchant_id, yesterday)
            
            if yesterday_data['total_income'] > 0:
                growth_rate = (
                    (today_data['total_income'] - yesterday_data['total_income']) / 
                    yesterday_data['total_income'] * 100
                )
                result = float(round(growth_rate, 2))
                logger.debug(f"日报表对比数据计算完成: {result}%")
                return result
            
            logger.debug("昨日收入为0，无法计算增长率")
            return 0.0
            
        except Exception as e:
            logger.error(f"计算日报表对比数据失败: {str(e)}", exc_info=True)
            return 0.0
    
    async def _calculate_weekly_comparison(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> float:
        """计算周报表对比数据"""
        try:
            logger.debug(f"计算商户 {merchant_id} 的周报表对比数据")
            
            # 获取上周数据
            last_week_start = start_date - timedelta(days=7)
            last_week_end = end_date - timedelta(days=7)
            
            this_week_data = await self._get_weekly_report_data(merchant_id, start_date, end_date)
            last_week_data = await self._get_weekly_report_data(merchant_id, last_week_start, last_week_end)
            
            if last_week_data['total_income'] > 0:
                growth_rate = (
                    (this_week_data['total_income'] - last_week_data['total_income']) / 
                    last_week_data['total_income'] * 100
                )
                result = float(round(growth_rate, 2))
                logger.debug(f"周报表对比数据计算完成: {result}%")
                return result
            
            logger.debug("上周收入为0，无法计算增长率")
            return 0.0
            
        except Exception as e:
            logger.error(f"计算周报表对比数据失败: {str(e)}", exc_info=True)
            return 0.0
    
    async def _calculate_monthly_comparison(self, merchant_id: str, report_month: date) -> float:
        """计算月报表对比数据"""
        try:
            logger.debug(f"计算商户 {merchant_id} 的月报表对比数据")
            
            # 获取上月数据
            if report_month.month > 1:
                last_month = report_month.replace(month=report_month.month-1)
            else:
                last_month = report_month.replace(year=report_month.year-1, month=12)
            
            last_month_start, last_month_end = DateUtils.get_month_range(last_month)
            
            this_month_start, this_month_end = DateUtils.get_month_range(report_month)
            
            this_month_data = await self._get_monthly_report_data(merchant_id, this_month_start, this_month_end)
            last_month_data = await self._get_monthly_report_data(merchant_id, last_month_start, last_month_end)
            
            if last_month_data['total_income'] > 0:
                growth_rate = (
                    (this_month_data['total_income'] - last_month_data['total_income']) / 
                    last_month_data['total_income'] * 100
                )
                result = float(round(growth_rate, 2))
                logger.debug(f"月报表对比数据计算完成: {result}%")
                return result
            
            logger.debug("上月收入为0，无法计算增长率")
            return 0.0
            
        except Exception as e:
            logger.error(f"计算月报表对比数据失败: {str(e)}", exc_info=True)
            return 0.0
    
    async def _generate_report_data(
        self, 
        merchant_id: str, 
        request: ReportExportRequest
    ) -> List[Dict[str, Any]]:
        """生成报表数据"""
        try:
            logger.info(f"生成报表数据，类型: {request.report_type}")
            
            if request.report_type == ReportType.DAILY:
                report_date = request.start_date or date.today()
                report_data = await self.generate_daily_report(merchant_id, report_date, True)
            elif request.report_type == ReportType.WEEKLY:
                start_date = request.start_date or (date.today() - timedelta(days=7))
                end_date = request.end_date or date.today()
                report_data = await self.generate_weekly_report(merchant_id, start_date, end_date, True)
            elif request.report_type == ReportType.MONTHLY:
                report_month = request.start_date or date.today().replace(day=1)
                report_data = await self.generate_monthly_report(merchant_id, report_month, True)
            else:
                raise ReportException(f"不支持的报表类型: {request.report_type}")
            
            # 转换为导出格式
            export_data = [{
                '统计周期': report_data.period,
                '总收入': float(report_data.total_income),
                '总订单数': report_data.total_orders,
                '平均订单价值': float(report_data.avg_order_value),
                '退款率(%)': report_data.refund_rate,
                '平台费率(%)': report_data.platform_fee_rate,
                '净利润': float(report_data.net_profit),
                '增长率(%)': report_data.comparison_rate or 0
            }]
            
            # 添加明细数据
            if hasattr(report_data, 'details') and report_data.details:
                export_data.extend(report_data.details)
            
            logger.debug(f"报表数据生成完成，共 {len(export_data)} 条记录")
            
            return export_data
            
        except Exception as e:
            logger.error(f"生成报表数据失败: {str(e)}", exc_info=True)
            raise ReportException("生成报表数据失败")
    
    async def _create_export_record(
        self, 
        merchant_id: str, 
        request: ReportExportRequest, 
        filename: str, 
        filepath: str
    ) -> ReportExport:
        """创建导出记录"""
        try:
            logger.info(f"创建导出记录: {filename}")
            
            file_size = self.export_utils.calculate_file_size(filepath)
            expires_at = self.export_utils.get_expires_time()
            
            export_record = ReportExport(
                id=str(uuid.uuid4()),
                merchant_id=merchant_id,
                report_type=request.report_type,
                file_name=filename,
                file_path=filepath,
                file_size=file_size,
                export_format=request.format,
                start_date=request.start_date,
                end_date=request.end_date,
                expires_at=expires_at
            )
            
            await db.insert_data(
                "finances_report_exports",
                export_record.dict()
            )
            
            logger.info(f"导出记录创建成功: {export_record.id}")
            
            return export_record
            
        except Exception as e:
            logger.error(f"创建导出记录失败: {str(e)}", exc_info=True)
            raise ReportException("创建导出记录失败")
    
    async def _get_daily_details(self, merchant_id: str, report_date: date) -> List[Dict[str, Any]]:
        """获取日报表明细数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的日报表明细数据，日期: {report_date}")
            
            # 查询当天的订单明细
            orders = await db.execute_query(
                "orders",
                filters={
                    "merchant_id": merchant_id,
                    "created_at": {
                        "gte": report_date.isoformat(),
                        "lte": (report_date + timedelta(days=1)).isoformat()
                    }
                }
            )
            
            details = []
            for order in orders:
                details.append({
                    '订单号': order.get('order_no'),
                    '订单时间': order.get('created_at'),
                    '订单金额': float(Decimal(str(order.get('amount', 0)))),
                    '支付方式': order.get('payment_method'),
                    '订单状态': order.get('status'),
                    '客户名称': order.get('customer_name')
                })
            
            logger.debug(f"获取到 {len(details)} 条明细数据")
            
            return details
            
        except Exception as e:
            logger.error(f"获取日报表明细失败: {str(e)}", exc_info=True)
            return []