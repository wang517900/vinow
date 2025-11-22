内容板块-Celery配置

from celery import Celery
from app.config import settings

# 创建Celery应用
celery_app = Celery(
    "content_management",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.video_tasks",
        "app.tasks.content_tasks"
    ]
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,
    task_routes={
        'app.tasks.video_tasks.*': {'queue': 'video_transcoding'},
        'app.tasks.content_tasks.*': {'queue': 'default'},
    },
    task_annotations={
        'app.tasks.video_tasks.process_video_transcoding': {'rate_limit': '10/m'},
    }
)