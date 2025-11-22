商家板块6财务中心
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import logging
import os

from app.database.supabase_client import db
from app.utils.date_utils import DateUtils
from app.models.finance import FinanceDailySummary, SettlementRecord, ReconciliationLog
from app.services.finance_service import FinanceService
from app.services.settlement_service import SettlementService
from app.services.reconciliation_service import ReconciliationService

# 配置日志
logger = logging.getLogger(__name__)


class FinanceJobs:
    """财务定时任务"""
    
    def __init__(self):
        self.finance_service = FinanceService()
        self.settlement_service = SettlementService()
        self.reconciliation_service = ReconciliationService()
    
    async def run_daily_summary(self):
        """执行日汇总任务"""
        try:
            logger.info("开始执行财务日汇总任务")
            
            # 获取昨天的日期
            yesterday = DateUtils.get_yesterday()
            
            # 获取所有商户ID（这里需要根据实际情况获取）
            merchants = await self._get_active_merchants()
            
            success_count = 0
            error_count = 0
            
            for merchant in merchants:
                try:
                    merchant_id = merchant['id']
                    
                    # 生成日汇总数据
                    summary_data = await self.finance_service.generate_daily_summary(
                        merchant_id, yesterday
                    )
                    
                    if summary_data:
                        # 保存到数据库
                        await db.insert_data(
                            "finances_daily_summary",
                            summary_data.dict()
                        )
                        success_count += 1
                        logger.info(f"商户 {merchant_id} 日汇总数据生成成功")
                    else:
                        error_count += 1
                        logger.warning(f"商户 {merchant_id} 日汇总数据生成失败")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"商户 {merchant_id} 日汇总任务执行失败: {str(e)}", exc_info=True)
            
            logger.info(f"日汇总任务完成: 成功 {success_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"日汇总任务执行失败: {str(e)}", exc_info=True)
            raise
    
    async def run_weekly_settlement(self):
        """执行周结算任务"""
        try:
            logger.info("开始执行周结算任务")
            
            # 获取上周日期范围
            today = date.today()
            last_week_start = today - timedelta(days=today.weekday() + 7)
            last_week_end = last_week_start + timedelta(days=6)
            
            merchants = await self._get_active_merchants()
            
            success_count = 0
            error_count = 0
            
            for merchant in merchants:
                try:
                    merchant_id = merchant['id']
                    
                    # 执行结算
                    settlement_result = await self.settlement_service.process_settlement(
                        merchant_id, last_week_start, last_week_end
                    )
                    
                    if settlement_result:
                        # 保存结算结果到数据库
                        await db.insert_data(
                            "finances_settlement_records",
                            settlement_result.dict() if hasattr(settlement_result, 'dict') else settlement_result
                        )
                        success_count += 1
                        logger.info(f"商户 {merchant_id} 周结算处理成功")
                    else:
                        error_count += 1
                        logger.warning(f"商户 {merchant_id} 周结算处理失败")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"商户 {merchant_id} 周结算任务执行失败: {str(e)}", exc_info=True)
            
            logger.info(f"周结算任务完成: 成功 {success_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"周结算任务执行失败: {str(e)}", exc_info=True)
            raise
    
    async def run_daily_reconciliation(self):
        """执行日对账任务"""
        try:
            logger.info("开始执行日对账任务")
            
            # 获取昨天的日期
            yesterday = DateUtils.get_yesterday()
            
            merchants = await self._get_active_merchants()
            
            success_count = 0
            error_count = 0
            
            for merchant in merchants:
                try:
                    merchant_id = merchant['id']
                    
                    # 执行对账
                    reconciliation_result = await self.reconciliation_service.run_reconciliation(
                        merchant_id, yesterday, yesterday
                    )
                    
                    if reconciliation_result:
                        # 保存对账结果到数据库
                        await db.insert_data(
                            "finances_reconciliation_logs",
                            reconciliation_result.dict() if hasattr(reconciliation_result, 'dict') else reconciliation_result
                        )
                        success_count += 1
                        logger.info(f"商户 {merchant_id} 日对账处理成功")
                    else:
                        error_count += 1
                        logger.warning(f"商户 {merchant_id} 日对账处理失败")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"商户 {merchant_id} 日对账任务执行失败: {str(e)}", exc_info=True)
            
            logger.info(f"日对账任务完成: 成功 {success_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"日对账任务执行失败: {str(e)}", exc_info=True)
            raise
    
    async def run_report_cleanup(self):
        """执行报表文件清理任务"""
        try:
            logger.info("开始执行报表文件清理任务")
            
            # 获取过期的报表导出记录
            expired_reports = await self._get_expired_reports()
            
            deleted_count = 0
            error_count = 0
            
            for report in expired_reports:
                try:
                    file_path = report.get('file_path') or report.get('file_url')
                    report_id = report.get('id')
                    
                    if not file_path:
                        logger.warning(f"报表记录 {report_id} 缺少文件路径信息")
                        error_count += 1
                        continue
                    
                    # 删除文件
                    if await self._delete_file(file_path):
                        # 删除数据库记录
                        await db.delete_data(
                            "finances_report_exports",
                            {"id": report_id}
                        )
                        deleted_count += 1
                        logger.info(f"成功清理报表文件: {file_path}")
                    else:
                        error_count += 1
                        logger.warning(f"清理报表文件失败: {file_path}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"删除报表文件失败 {report.get('id')}: {str(e)}", exc_info=True)
            
            logger.info(f"报表清理任务完成: 删除 {deleted_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"报表清理任务执行失败: {str(e)}", exc_info=True)
            raise
    
    async def _get_active_merchants(self) -> List[Dict[str, Any]]:
        """获取活跃商户列表"""
        try:
            # 实际实现应该从数据库获取活跃商户
            merchants = await db.execute_query(
                "merchants",
                filters={"status": "active"}
            )
            return merchants or []
        except Exception as e:
            logger.error(f"获取活跃商户列表失败: {str(e)}", exc_info=True)
            return []
    
    async def _get_expired_reports(self) -> List[Dict[str, Any]]:
        """获取过期的报表记录"""
        try:
            current_time = datetime.now().isoformat()
            reports = await db.execute_query(
                "finances_report_exports",
                filters={"expires_at": {"lt": current_time}}
            )
            return reports or []
        except Exception as e:
            logger.error(f"获取过期报表失败: {str(e)}", exc_info=True)
            return []
    
    async def _delete_file(self, file_path: str) -> bool:
        """删除文件"""
        try:
            # 如果是URL，则可能需要特殊处理
            if file_path.startswith(('http://', 'https://')):
                logger.info(f"跳过远程文件删除: {file_path}")
                return True
                
            # 处理本地文件
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"成功删除文件: {file_path}")
                return True
            else:
                logger.warning(f"文件不存在: {file_path}")
                return True  # 文件不存在也认为是"删除成功"
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {str(e)}", exc_info=True)
            return False


# 全局任务实例
finance_jobs = FinanceJobs()