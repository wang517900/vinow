商家板块5数据分析
from fastapi import APIRouter, Depends, status
from app.core.logging import logger
from app.services.supabase_client import SupabaseClient
from app.api.dependencies import get_supabase_client

router = APIRouter()

@router.get("/health")
async def health_check(
    supabase: SupabaseClient = Depends(get_supabase_client)
):
    """健康检查端点"""
    try:
        # 检查数据库连接
        db_healthy = await supabase.health_check()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": "2024-01-15T10:30:00Z",  # 实际应该使用 datetime.now().isoformat()
            "version": "1.0.0",
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy"
            }
        }
        
        if db_healthy:
            logger.info("Health check passed")
            return health_status
        else:
            logger.error("Health check failed: Database connection issue")
            return health_status, status.HTTP_503_SERVICE_UNAVAILABLE
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": "2024-01-15T10:30:00Z",
            "error": str(e)
        }, status.HTTP_503_SERVICE_UNAVAILABLE

@router.get("/ready")
async def readiness_check():
    """就绪检查端点"""
    return {
        "status": "ready",
        "timestamp": "2024-01-15T10:30:00Z"
    }