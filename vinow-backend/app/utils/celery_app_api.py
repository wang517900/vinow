交易系统

from celery import Celery
from celery.schedules import crontab
from kombu import Queue
import logging
import os
from typing import Dict, Any, Optional
from app.config import settings

# 配置Celery日志
logger = logging.getLogger(__name__)

def create_celery_app(config: Optional[Dict[str, Any]] = None) -> Celery:
    """
    创建并配置Celery应用实例
    
    Args:
        config (Dict[str, Any], optional): 额外的配置参数
        
    Returns:
        Celery: 配置好的Celery应用实例
        
    Example:
        >>> celery_app = create_celery_app()
        >>> celery_app.start()
    """
    try:
        # 创建Celery应用实例
        app = Celery(
            "trade_platform",
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend,
        )
        
        # 基础配置
        base_conf = {
            # 序列化配置
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            
            # 时区配置
            'timezone': 'Asia/Ho_Chi_Minh',
            'enable_utc': True,
            
            # 任务执行配置
            'task_track_started': True,
            'task_time_limit': 30 * 60,  # 30分钟任务超时
            'task_soft_time_limit': 25 * 60,  # 25分钟软超时
            'worker_max_tasks_per_child': 1000,  # 每个工作进程处理1000个任务后重启
            'worker_prefetch_multiplier': 1,  # 每次预取1个任务
            
            # 结果存储配置
            'result_expires': 7 * 24 * 60 * 60,  # 结果保存7天
            'result_extended': True,  # 扩展结果信息
            
            # 队列配置
            'task_default_queue': 'default',
            'task_routes': {
                'app.tasks.order_tasks.*': {'queue': 'orders'},
                'app.tasks.payment_tasks.*': {'queue': 'payments'},
                'app.tasks.settlement_tasks.*': {'queue': 'settlements'},
                'app.tasks.notification_tasks.*': {'queue': 'notifications'},
            },
            
            # 工作进程配置
            'worker_hijack_root_logger': False,  # 不劫持根日志记录器
            'worker_log_color': True,  # 启用彩色日志
        }
        
        # 更新配置
        app.conf.update(base_conf)
        
        # 应用额外配置（如果有）
        if config:
            app.conf.update(config)
        
        # 配置任务队列
        _configure_task_queues(app)
        
        # 配置定时任务
        _configure_beat_schedule(app)
        
        # 配置日志
        _configure_logging(app)
        
        logger.info("celery_app_created_successfully", extra={
            'broker_url': settings.celery_broker_url,
            'backend_url': settings.celery_result_backend
        })
        
        return app
        
    except Exception as e:
        logger.error(f"Failed to create Celery app: {str(e)}")
        raise

def _configure_task_queues(app: Celery) -> None:
    """
    配置任务队列
    
    Args:
        app (Celery): Celery应用实例
    """
    app.conf.task_queues = (
        Queue('default', routing_key='default'),
        Queue('orders', routing_key='orders'),
        Queue('payments', routing_key='payments'),
        Queue('settlements', routing_key='settlements'),
        Queue('notifications', routing_key='notifications'),
        Queue('high_priority', routing_key='high_priority'),
        Queue('low_priority', routing_key='low_priority'),
    )

def _configure_beat_schedule(app: Celery) -> None:
    """
    配置定时任务调度
    
    Args:
        app (Celery): Celery应用实例
    """
    # 根据环境变量决定是否启用某些任务
    enable_settlement = os.getenv('ENABLE_SETTLEMENT_TASKS', 'true').lower() == 'true'
    enable_notifications = os.getenv('ENABLE_NOTIFICATION_TASKS', 'true').lower() == 'true'
    
    beat_schedule = {
        # 自动取消未支付订单
        'auto-cancel-unpaid-orders': {
            'task': 'app.tasks.order_tasks.auto_cancel_unpaid_orders',
            'schedule': 300.0,  # 每5分钟执行一次
            'options': {
                'queue': 'orders',
                'expires': 300,  # 任务5分钟后过期
            }
        },
        
        # 处理过期支付
        'process-expired-payments': {
            'task': 'app.tasks.payment_tasks.process_expired_payments',
            'schedule': 600.0,  # 每10分钟执行一次
            'options': {
                'queue': 'payments',
                'expires': 600,
            }
        },
        
        # 每小时清理过期任务结果
        'cleanup-expired-results': {
            'task': 'app.tasks.system_tasks.cleanup_expired_results',
            'schedule': 3600.0,  # 每小时执行一次
            'options': {
                'queue': 'default',
                'expires': 300,
            }
        },
        
        # 每天凌晨2点发送每日报告
        'send-daily-report': {
            'task': 'app.tasks.notification_tasks.send_daily_report',
            'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
            'options': {
                'queue': 'notifications',
                'expires': 3600,
            },
            'enabled': enable_notifications
        },
    }
    
    # 条件性添加结算任务
    if enable_settlement:
        beat_schedule.update({
            # 生成每日结算
            'generate-daily-settlement': {
                'task': 'app.tasks.settlement_tasks.generate_daily_settlement',
                'schedule': crontab(hour=1, minute=0),  # 每天凌晨1点
                'options': {
                    'queue': 'settlements',
                    'expires': 7200,  # 2小时后过期
                }
            },
            
            # 每周一凌晨3点生成周报
            'generate-weekly-settlement': {
                'task': 'app.tasks.settlement_tasks.generate_weekly_settlement',
                'schedule': crontab(hour=3, minute=0, day_of_week=1),  # 每周一凌晨3点
                'options': {
                    'queue': 'settlements',
                    'expires': 14400,  # 4小时后过期
                }
            },
        })
    
    app.conf.beat_schedule = beat_schedule

def _configure_logging(app: Celery) -> None:
    """
    配置Celery日志
    
    Args:
        app (Celery): Celery应用实例
    """
    # 配置日志格式
    app.conf.worker_log_format = (
        '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
    )
    app.conf.worker_task_log_format = (
        '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
    )

# 创建Celery应用实例
try:
    celery_app = create_celery_app()
    
    # 动态导入任务模块
    celery_app.autodiscover_tasks([
        "app.tasks.order_tasks",
        "app.tasks.payment_tasks",
        "app.tasks.settlement_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.system_tasks"
    ], related_name='tasks', force=True)
    
except Exception as e:
    logger.error(f"Failed to initialize Celery app: {str(e)}")
    raise

class CeleryTaskManager:
    """
    Celery任务管理器
    
    提供任务调度、监控和管理功能
    """
    
    def __init__(self, app: Celery):
        """
        初始化任务管理器
        
        Args:
            app (Celery): Celery应用实例
        """
        self.app = app
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id (str): 任务ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        try:
            result = self.app.AsyncResult(task_id)
            return {
                'task_id': task_id,
                'status': result.status,
                'result': result.result if result.ready() else None,
                'traceback': result.traceback if result.failed() else None
            }
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def revoke_task(self, task_id: str, terminate: bool = False) -> bool:
        """
        撤销任务
        
        Args:
            task_id (str): 任务ID
            terminate (bool): 是否强制终止正在执行的任务
            
        Returns:
            bool: 撤销是否成功
        """
        try:
            self.app.control.revoke(task_id, terminate=terminate)
            logger.info(f"Task revoked: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke task: {str(e)}")
            return False
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """
        获取活跃任务信息
        
        Returns:
            Dict[str, Any]: 活跃任务信息
        """
        try:
            inspect = self.app.control.inspect()
            return {
                'active': inspect.active(),
                'scheduled': inspect.scheduled(),
                'reserved': inspect.reserved()
            }
        except Exception as e:
            logger.error(f"Failed to get active tasks: {str(e)}")
            return {}

# 创建任务管理器实例
task_manager = CeleryTaskManager(celery_app) if 'celery_app' in globals() else None

# 为了向后兼容，保留直接访问celery_app的方式
def get_celery_app() -> Celery:
    """
    获取Celery应用实例（向后兼容）
    
    Returns:
        Celery: Celery应用实例
    """
    global celery_app
    if celery_app is None:
        celery_app = create_celery_app()
    return celery_app

# Celery应用健康检查
def check_celery_health() -> Dict[str, Any]:
    """
    检查Celery应用健康状态
    
    Returns:
        Dict[str, Any]: 健康检查结果
    """
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        return {
            'status': 'healthy' if stats else 'unhealthy',
            'workers': len(stats) if stats else 0,
            'stats': stats
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }