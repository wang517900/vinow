内容模块-celery任务配置
from celery import Celery  # 导入Celery
from app.config import settings  # 导入应用配置
import logging  # 导入日志模块

# 获取日志记录器
logger = logging.getLogger(__name__)

# 创建Celery应用实例
celery_app = Celery(
    "content_system",  # 应用名称
    broker=settings.CELERY_BROKER_URL,  # 消息代理URL
    backend=settings.CELERY_RESULT_BACKEND,  # 结果后端URL
    include=[  # 包含的任务模块
        "app.tasks.video_tasks",
        "app.tasks.moderation_tasks", 
        "app.tasks.analytics_tasks",
    ]
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",  # 任务序列化格式
    accept_content=["json"],  # 接受的内容类型
    result_serializer="json",  # 结果序列化格式
    timezone="Asia/Ho_Chi_Minh",  # 时区（越南）
    enable_utc=True,  # 启用UTC
    task_track_started=True,  # 跟踪任务开始
    task_time_limit=300,  # 任务时间限制（5分钟）
    task_soft_time_limit=250,  # 任务软时间限制
    worker_prefetch_multiplier=1,  # worker预取乘数
    worker_max_tasks_per_child=100,  # 每个worker子进程最大任务数
    broker_connection_retry_on_startup=True,  # 启动时重试broker连接
)

# 记录Celery应用启动
logger.info("Celery应用已配置")

# 导入任务模块（确保在Celery应用创建后导入）
from app.tasks import video_tasks, moderation_tasks, analytics_tasks  # noqa"""商家系统模块"""
