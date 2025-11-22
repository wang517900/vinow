商家系统6财务中心
from fastapi import APIRouter
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

from app.api import finance_api, settlement_api, reconciliation_api, reports_api

# 创建主API路由器
api_router = APIRouter(prefix="/api/merchant/v1")

# 注册所有业务路由
api_router.include_router(
    finance_api.router, 
    prefix="/finances",
    tags=["财务数据"]
)

api_router.include_router(
    settlement_api.router, 
    prefix="/finances/settlement",
    tags=["结算管理"]
)

api_router.include_router(
    reconciliation_api.router, 
    prefix="/finances/reconciliation",
    tags=["对账中心"]
)

api_router.include_router(
    reports_api.router, 
    prefix="/finances/reports",
    tags=["报表系统"]
)

# 健康检查端点
@api_router.get("/health", summary="健康检查", tags=["系统管理"])
async def health_check():
    """
    系统健康检查端点
    
    用于检查API服务是否正常运行
    """
    return {
        "status": "healthy",
        "message": "API服务运行正常",
        "version": "1.0.0"
    }

# 版本信息端点
@api_router.get("/version", summary="版本信息", tags=["系统管理"])
async def get_version():
    """
    获取API版本信息
    """
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_time": "2024-01-01T00:00:00Z",
        "environment": "production"
    }

# API文档自定义路由（可选）
@api_router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    自定义Swagger UI文档页面
    """
    return get_swagger_ui_html(
        openapi_url="/api/merchant/v1/openapi.json",
        title="商户财务系统API - Swagger UI",
        oauth2_redirect_url="/api/merchant/v1/docs/oauth2-redirect",
    )

@api_router.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect():
    """
    Swagger UI OAuth2重定向
    """
    return get_swagger_ui_oauth2_redirect_html()

@api_router.get("/redoc", include_in_schema=False)
async def redoc_html():
    """
    ReDoc文档页面
    """
    return get_redoc_html(
        openapi_url="/api/merchant/v1/openapi.json",
        title="商户财务系统API - ReDoc",
    )