商家板块6财务中心
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class FinanceScheduler:
    """财务任务调度器"""
    
    _instance = None
    _scheduler = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FinanceScheduler, cls).__new__(cls)
            cls._scheduler = AsyncIOScheduler()
        return cls._instance
    
    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        """获取调度器实例"""
        if cls._scheduler is None:
            cls()
        return cls._scheduler
    
    @classmethod
    def start_scheduler(cls):
        """启动调度器"""
        try:
            scheduler = cls.get_scheduler()
            if not scheduler.running:
                scheduler.start()
                logger.info("财务任务调度器已启动")
                print("财务任务调度器已启动")
        except Exception as e:
            logger.error(f"启动财务任务调度器失败: {e}")
            raise
    
    @classmethod
    def shutdown_scheduler(cls):
        """关闭调度器"""
        try:
            scheduler = cls.get_scheduler()
            if scheduler.running:
                scheduler.shutdown()
                logger.info("财务任务调度器已关闭")
                print("财务任务调度器已关闭")
        except Exception as e:
            logger.error(f"关闭财务任务调度器失败: {e}")
            raise
    
    @classmethod
    def add_daily_summary_job(cls, job_func):
        """添加日汇总任务"""
        try:
            scheduler = cls.get_scheduler()
            # 每天凌晨1点执行
            trigger = CronTrigger(hour=1, minute=0)
            scheduler.add_job(
                job_func,
                trigger,
                id='daily_finance_summary',
                name='财务日汇总任务',
                replace_existing=True
            )
            logger.info("已添加财务日汇总任务")
        except Exception as e:
            logger.error(f"添加财务日汇总任务失败: {e}")
            raise
    
    @classmethod
    def add_settlement_job(cls, job_func):
        """添加结算任务"""
        try:
            scheduler = cls.get_scheduler()
            # 每周一凌晨2点执行（结算上周数据）
            trigger = CronTrigger(day_of_week=0, hour=2, minute=0)
            scheduler.add_job(
                job_func,
                trigger,
                id='weekly_settlement',
                name='周结算任务',
                replace_existing=True
            )
            logger.info("已添加周结算任务")
        except Exception as e:
            logger.error(f"添加周结算任务失败: {e}")
            raise
    
    @classmethod
    def add_reconciliation_job(cls, job_func):
        """添加对账任务"""
        try:
            scheduler = cls.get_scheduler()
            # 每天凌晨3点执行
            trigger = CronTrigger(hour=3, minute=0)
            scheduler.add_job(
                job_func,
                trigger,
                id='daily_reconciliation',
                name='日对账任务',
                replace_existing=True
            )
            logger.info("已添加日对账任务")
        except Exception as e:
            logger.error(f"添加日对账任务失败: {e}")
            raise
    
    @classmethod
    def add_report_cleanup_job(cls, job_func):
        """添加报表清理任务"""
        try:
            scheduler = cls.get_scheduler()
            # 每天凌晨4点执行
            trigger = CronTrigger(hour=4, minute=0)
            scheduler.add_job(
                job_func,
                trigger,
                id='report_cleanup',
                name='报表文件清理任务',
                replace_existing=True
            )
            logger.info("已添加报表文件清理任务")
        except Exception as e:
            logger.error(f"添加报表文件清理任务失败: {e}")
            raise
    
    @classmethod
    def remove_all_jobs(cls):
        """移除所有任务"""
        try:
            scheduler = cls.get_scheduler()
            scheduler.remove_all_jobs()
            logger.info("已移除所有调度任务")
        except Exception as e:
            logger.error(f"移除调度任务失败: {e}")
            raise
    
    @classmethod
    def get_jobs(cls):
        """获取所有调度任务"""
        try:
            scheduler = cls.get_scheduler()
            return scheduler.get_jobs()
        except Exception as e:
            logger.error(f"获取调度任务列表失败: {e}")
            raise