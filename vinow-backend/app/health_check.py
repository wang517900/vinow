内容模块-健康检查
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.session import get_db
from app.utils.cache import cache_redis
from app.schemas.response_schemas import HealthCheckResponse
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """综合健康检查"""
    services_status = {}
    
    # 检查数据库连接
    try:
        db.execute(text("SELECT 1"))
        services_status["database"] = "healthy"
    except Exception as e:
        services_status["database"] = f"unhealthy: {str(e)}"
    
    # 检查Redis连接
    try:
        if await cache_redis.ping():
            services_status["redis"] = "healthy"
        else:
            services_status["redis"] = "unhealthy"
    except Exception as e:
        services_status["redis"] = f"unhealthy: {str(e)}"
    
    # 检查存储服务
    try:
        # 这里可以添加存储服务的健康检查
        services_status["storage"] = "healthy"
    except Exception as e:
        services_status["storage"] = f"unhealthy: {str(e)}"
    
    # 确定整体状态
    overall_status = "healthy" if all(
        status == "healthy" for status in services_status.values()
    ) else "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services_status,
        version=settings.APP_VERSION
    )


@router.get("/health/readiness")
async def readiness_probe():
    """就绪探针"""
    return {"status": "ready"}


@router.get("/health/liveness")
async def liveness_probe():
    """存活探针"""
    return {"status": "alive"}