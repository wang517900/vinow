# -*- coding: utf-8 -*-
"""
Vinow 后端应用 
"""
import os
import time
import uvicorn
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

# 显式导入路由模块
from app.routers import product_router

# ---------------------------
# 加载环境变量（只加载一次）
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # fallback

# 启动时间，用于 uptime 统计
APP_START_TIME = datetime.now(timezone.utc)

# ---------------------------
# 应用生命周期
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时检查、日志与目录创建。"""
    startup_time = datetime.now(timezone.utc)
    print("🚀 启动 Vinow 后端服务器")
    print("📋 版本: v1.7.1 - 完整用户系统（优化版）")
    print("🔧 环境:", os.getenv("ENVIRONMENT", "development"))
    print("🌐 API文档: http://localhost:8000/docs")
    print("📊 健康检查: http://localhost:8000/health")
    print("=" * 50)

    # 验证关键环境变量（打印但不强制退出，以便测试）
    required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing_vars = [v for v in required_env_vars if not os.getenv(v)]
    if missing_vars:
        print("⚠️  警告: 以下环境变量未设置:", missing_vars)
    else:
        print("✅ 所有必需环境变量已配置")

    # 列出加载模块（方便日志）
    modules = [
        "v1.0.0 - 用户认证系统",
        "v1.1.0 - 用户资料管理",
        "v1.2.0 - 用户互动数据",
        "v1.3.0 - 订单中心",
        "v1.4.0 - 评价系统",
        "v1.5.0 - 数据分析",
        "v1.6.0 - 支付集成",
        "v1.7.0 - 高级功能",
        "v1.7.1 - 商家管理系统"
    ]
    print("✅ 已加载功能模块:")
    for m in modules:
        print("   ", m)

    # 创建必须目录（若不存在）
    required_dirs = [
        os.path.join(BASE_DIR, "uploads", "avatars"),
        os.path.join(BASE_DIR, "uploads", "reviews"),
        os.path.join(BASE_DIR, "uploads", "payments"),
        os.path.join(BASE_DIR, "logs"),
        os.path.join(BASE_DIR, "temp"),
        os.path.join(BASE_DIR, "uploads", "merchants"),
        os.path.join(BASE_DIR, "static"),
    ]
    for d in required_dirs:
        try:
            os.makedirs(d, exist_ok=True)
            print(f"📁 创建目录或已存在: {d}")
        except Exception as e:
            print(f"⚠️ 无法创建目录 {d}: {e}")

    print(f"⏰ 启动完成时间: {startup_time.isoformat()}")
    print("=" * 50)

    yield  # 应用运行时

    # 关闭时打印运行时长
    shutdown_time = datetime.now(timezone.utc)
    uptime = shutdown_time - startup_time
    print("🛑 应用关闭")
    print(f"⏰ 运行时长: {uptime}")
    print(f"📅 关闭时间: {shutdown_time.isoformat()}")

# ---------------------------
# 创建 FastAPI app
# ---------------------------
app = FastAPI(
    title="Vinow Backend API",
    description="越南本地生活平台 - 完整用户系统 v1.7.1 (优化版)",
    version="1.7.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ---------------------------
# CORS 中间件
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产请改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# 静态目录挂载（确保目录存在）
# ---------------------------
# 上面 lifespan 已确保 static/uploads 目录存在，防止挂载出错
try:
    app.mount("/uploads", StaticFiles(directory=os.path.join(BASE_DIR, "uploads")), name="uploads")
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
except Exception as e:
    # 仅记录，不阻止应用启动（方便本地调试）
    print(f"⚠️ 挂载静态目录失败: {e}")

# ---------------------------
# 动态注册路由模块（同时保留显式 product_router 注册）
# ---------------------------
def register_routes() -> bool:
    """
    尝试动态导入并注册预定义模块路径中的 router 对象。
    返回 True/False 表示必需模块是否全部加载成功。
    """
    modules = [
        # module_path, router_attr_name, module_display_name, required
        ("app.auth.router", "router", "认证系统", True),
        ("app.users.router", "router", "用户资料管理", True),
        ("app.interactions.router", "router", "用户互动数据", False),
        ("app.orders.router", "router", "订单中心", True),
        ("app.reviews.router", "router", "评价系统", False),
        ("app.analytics.router", "router", "数据分析", False),
        ("app.payment.router", "router", "支付集成", True),
        ("app.notifications.router", "router", "高级功能", False),
        # 这里仍然保留对 marketing_router 的尝试注册
        ("app.routers.marketing_router", "router", "商家管理系统", True),
        # 添加商品路由模块
        ("app.routers.product_router", "router", "商品管理系统", True),
    ]

    total = len(modules)
    success = 0
    required_success = 0
    required_total = sum(1 for _, _, _, r in modules if r)

    print("📡 开始注册路由模块...")
    for module_path, router_attr, display_name, required in modules:
        try:
            module = __import__(module_path, fromlist=[router_attr])
            router_obj = getattr(module, router_attr)
            app.include_router(router_obj)
            success += 1
            if required:
                required_success += 1
            status = "✅" if required else "☑️"
            print(f"   {status} {display_name} - 注册成功 ({module_path})")
        except ImportError as ie:
            msg = f"导入失败: {ie}"
            if required:
                print(f"   ❌ {display_name} - {msg}")
            else:
                print(f"   ⚠️  {display_name} - 可选模块导入失败: {msg}")
        except AttributeError as ae:
            msg = f"路由获取失败: {ae}"
            if required:
                print(f"   ❌ {display_name} - {msg}")
            else:
                print(f"   ⚠️  {display_name} - 可选模块路由获取失败: {msg}")
        except Exception as e:
            msg = f"注册失败: {e}"
            if required:
                print(f"   ❌ {display_name} - {msg}")
            else:
                print(f"   ⚠️  {display_name} - 可选模块注册失败: {msg}")

    print(f"📊 路由注册完成: 成功 {success}/{total} 个 (必需 {required_success}/{required_total})")
    if required_success < required_total:
        print("🚨 警告: 部分必需模块加载失败，应用可能无法正常工作")
        return False
    return True

# 先注册动态模块
routes_registered = register_routes()

# 显式注册顶部导入的 product_router（以避免遗漏）
try:
    # 检查是否已经注册了相同前缀的路由，避免重复注册
    product_router_registered = any(
        hasattr(route, 'path') and route.path.startswith('/api/products') 
        for route in app.routes
    )
    
    if not product_router_registered and hasattr(product_router, "router"):
        app.include_router(product_router.router, prefix="/api/products", tags=["商品管理"])
        print("   ✅ 显式注册 product_router 成功")
    else:
        print("   ℹ️  product_router 已经注册或不需要额外注册")
except Exception as e:
    print(f"   ⚠️ product_router 注册失败或已注册: {e}")

# ---------------------------
# 基础端点
# ---------------------------
@app.get("/", tags=["根目录"])
async def root():
    current_time = datetime.now(timezone.utc)
    uptime = current_time - APP_START_TIME
    return {
        "message": "Vinow Backend API",
        "version": "1.7.1",
        "status": "running" if routes_registered else "degraded",
        "description": "越南本地生活平台完整用户系统",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": current_time.isoformat(),
        "uptime_seconds": int(uptime.total_seconds()),
        "docs_url": "/docs",
        "health_check": "/health"
    }

@app.get("/health", tags=["健康检查"])
async def health_check():
    current_time = datetime.now(timezone.utc)
    uptime = current_time - APP_START_TIME
    health_status = {
        "status": "healthy",
        "timestamp": current_time.isoformat(),
        "version": "1.7.1",
        "uptime_seconds": int(uptime.total_seconds()),
        "services": {
            "api": "healthy",
            "database": "unknown",
            "routes": "healthy" if routes_registered else "degraded"
        },
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    if not routes_registered:
        health_status["status"] = "degraded"
        health_status["message"] = "部分路由模块加载失败"
    return health_status

@app.get("/api/version", tags=["API信息"])
async def api_version():
    current_time = datetime.now(timezone.utc)
    return {
        "current_version": "v1.7.1",
        "min_supported_version": "v1.0.0",
        "release_date": "2024-01-01",
        "changelog": {
            "v1.0.0": "用户认证基础版",
            "v1.1.0": "用户资料管理",
            "v1.2.0": "用户互动数据",
            "v1.3.0": "订单中心",
            "v1.4.0": "评价系统",
            "v1.5.0": "数据分析系统",
            "v1.6.0": "支付集成",
            "v1.7.0": "高级功能",
            "v1.7.1": "系统优化和稳定性改进，集成商家管理系统"
        },
        "timestamp": current_time.isoformat()
    }

# ---------------------------
# 开发调试端点（只在开发方便查看）
# ---------------------------
@app.get("/debug/routes", tags=["开发调试"])
async def debug_routes():
    current_time = datetime.now(timezone.utc)
    routes_info = []
    for route in app.routes:
        route_info = {
            "path": getattr(route, "path", None),
            "methods": getattr(route, "methods", None),
            "name": getattr(route, "name", None)
        }
        route_info = {k: v for k, v in route_info.items() if v is not None}
        if route_info:
            routes_info.append(route_info)
    return {"total_routes": len(routes_info), "timestamp": current_time.isoformat(), "routes": routes_info}

@app.get("/debug/config", tags=["开发调试"])
async def debug_config():
    current_time = datetime.now(timezone.utc)
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase_key_display = "未设置"
    if supabase_key:
        supabase_key_display = "已设置"
        if os.getenv("ENVIRONMENT") == "development":
            supabase_key_display += f" ({supabase_key[:10]}...)" if len(supabase_key) > 10 else f" ({supabase_key})"
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "supabase_url": os.getenv("SUPABASE_URL", "未设置"),
        "supabase_key": supabase_key_display,
        "cors_origins": ["*"],
        "static_files_mounted": True,
        "timestamp": current_time.isoformat(),
        "python_version": os.getenv("PYTHON_VERSION", "未知")
    }

@app.get("/debug/status", tags=["开发调试"])
async def debug_status():
    current_time = datetime.now(timezone.utc)
    uptime = current_time - APP_START_TIME
    return {
        "application": {
            "name": "Vinow Backend",
            "version": "1.7.1",
            "status": "running" if routes_registered else "degraded",
            "start_time": APP_START_TIME.isoformat(),
            "current_time": current_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime)
        },
        "system": {
            "routes_registered": routes_registered,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timezone": "UTC"
        },
        "timestamp": current_time.isoformat()
    }

# ---------------------------
# 异常处理
# ---------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    current_time = datetime.now(timezone.utc)
    detail = exc.detail if os.getenv("ENVIRONMENT") == "development" else "HTTP error"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.status_code,
            "message": str(detail),
            "path": request.url.path,
            "timestamp": current_time.isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    current_time = datetime.now(timezone.utc)
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "code": 422,
            "message": "请求参数验证失败",
            "errors": exc.errors(),
            "path": request.url.path,
            "timestamp": current_time.isoformat()
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    current_time = datetime.now(timezone.utc)
    detail = str(exc) if os.getenv("ENVIRONMENT") == "development" else "内部服务器错误"
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "code": 500,
            "message": "服务器内部错误",
            "detail": detail,
            "path": request.url.path,
            "timestamp": current_time.isoformat()
        }
    )

# ---------------------------
# 中间件 - 请求处理时间
# ---------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-API-Version"] = "v1.7.1"
    return response

# ---------------------------
# 应用启动（开发时运行该文件）
# ---------------------------
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_flag = os.getenv("ENVIRONMENT") == "development"

    print("🎯 启动配置:")
    print(f"   • 主机: {host}")
    print(f"   • 端口: {port}")
    print(f"   • 热重载: {reload_flag}")
    print(f"   • 环境: {os.getenv('ENVIRONMENT', 'development')}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_flag,
        log_level="info",
        access_log=True
    )



    # app/main.py订单系统
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import orders, verification, dashboard
from app.database import test_connection
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(orders.router, prefix=settings.API_V1_STR, tags=["orders"])
app.include_router(verification.router, prefix=settings.API_V1_STR, tags=["verification"])
app.include_router(dashboard.router, prefix=settings.API_V1_STR, tags=["dashboard"])

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动 {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # 测试数据库连接
    if await test_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接异常")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_check": "/health"
    }
商家系统内容营销
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


    # 更新 app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api import orders, verification, dashboard, refunds
from app.content_marketing import api as content_api  # 新增内容营销API
from app.database import test_connection
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME + " - 内容营销系统",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态文件目录
os.makedirs("app/static/uploads/content", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 包含API路由
app.include_router(orders.router, prefix=settings.API_V1_STR, tags=["orders"])
app.include_router(verification.router, prefix=settings.API_V1_STR, tags=["verification"])
app.include_router(dashboard.router, prefix=settings.API_V1_STR, tags=["dashboard"])
app.include_router(refunds.router, prefix=settings.API_V1_STR, tags=["refunds"])
app.include_router(content_api.router, prefix=settings.API_V1_STR, tags=["content_marketing"])  # 新增

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动 {settings.PROJECT_NAME} v{settings.VERSION} - 包含内容营销系统")
    
    # 测试数据库连接
    if await test_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接异常")

# 其余代码保持不变...

# app/content_marketing/services_enhanced.py
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.database import supabase
from app.content_marketing.models import (
    ContentInDB, ContentCreate, ContentUpdate, ContentStats,
    CollaborationInDB, CollaborationCreate, CollaborationStatus,
    CollaborationApplicationInDB, CollaborationApplicationCreate, ApplicationStatus,
    ContentMarketingDashboard, ContentType, ContentStatus
)
from app.core.exceptions import (
    ContentNotFoundException, CollaborationNotFoundException,
    PermissionDeniedException, ValidationException
)
from app.core.logging import BusinessLogger, AuditLogger
import logging
import uuid

logger = BusinessLogger("content_marketing")

class EnhancedContentMarketingService:
    """增强版内容营销服务（包含完整的错误处理和审计）"""
    
    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        self.audit_logger = AuditLogger()
    
    def _validate_merchant_access(self, resource_merchant_id: str, operation: str):
        """验证商家访问权限"""
        if resource_merchant_id != self.merchant_id:
            self.audit_logger.log_security_event(
                "UNAUTHORIZED_ACCESS",
                self.merchant_id,
                "unknown",
                {"attempted_access": resource_merchant_id, "operation": operation}
            )
            raise PermissionDeniedException(f"商家 {resource_merchant_id}")
    
    async def create_content(self, content_data: ContentCreate) -> Optional[ContentInDB]:
        """创建内容（增强版）"""
        try:
            logger.log_operation("CREATE_CONTENT", self.merchant_id, title=content_data.title)
            
            # 数据验证
            if content_data.content_type == ContentType.VIDEO and not content_data.video_url:
                raise ValidationException("video_url", "视频类型必须提供视频URL")
            
            if content_data.content_type == ContentType.IMAGE_TEXT and not content_data.image_urls:
                raise ValidationException("image_urls", "图文类型必须提供图片")
            
            content_dict = content_data.model_dump()
            content_dict["tracking_code"] = f"CONTENT_{uuid.uuid4()}"
            content_dict["created_at"] = datetime.now().isoformat()
            content_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_contents").insert(content_dict).execute()
            
            if response.data:
                content = ContentInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_content_operation(
                    "CREATED", self.merchant_id, content.id,
                    {"title": content.title, "type": content.content_type}
                )
                
                return content
            
            return None
            
        except ValidationException:
            raise
        except Exception as e:
            logger.log_error("CREATE_CONTENT", self.merchant_id, e, title=content_data.title)
            raise
    
    async def get_content(self, content_id: str) -> Optional[ContentInDB]:
        """获取内容详情（增强版）"""
        try:
            logger.log_operation("GET_CONTENT", self.merchant_id, content_id=content_id)
            
            response = supabase.table("merchant_orders.cm_contents").select("*").eq("id", content_id).execute()
            
            if not response.data:
                raise ContentNotFoundException(content_id)
            
            content = ContentInDB(**response.data[0])
            
            # 验证权限
            self._validate_merchant_access(content.merchant_id, "GET_CONTENT")
            
            return content
            
        except (ContentNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.log_error("GET_CONTENT", self.merchant_id, e, content_id=content_id)
            raise
    
    async def update_content(self, content_id: str, update_data: ContentUpdate) -> Optional[ContentInDB]:
        """更新内容（增强版）"""
        try:
            logger.log_operation("UPDATE_CONTENT", self.merchant_id, content_id=content_id)
            
            # 先获取现有内容验证权限
            existing_content = await self.get_content(content_id)
            if not existing_content:
                raise ContentNotFoundException(content_id)
            
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_contents").update(update_dict).eq("id", content_id).execute()
            
            if response.data:
                content = ContentInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_content_operation(
                    "UPDATED", self.merchant_id, content_id,
                    {"changes": list(update_dict.keys())}
                )
                
                return content
            
            return None
            
        except (ContentNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.log_error("UPDATE_CONTENT", self.merchant_id, e, content_id=content_id)
            raise
    
    async def create_collaboration(self, collaboration_data: CollaborationCreate) -> Optional[CollaborationInDB]:
        """创建合作任务（增强版）"""
        try:
            logger.log_operation("CREATE_COLLABORATION", self.merchant_id, title=collaboration_data.title)
            
            # 预算验证
            if collaboration_data.budget_amount and collaboration_data.budget_amount <= 0:
                raise ValidationException("budget_amount", "预算金额必须大于0")
            
            if collaboration_data.commission_rate and not (0 <= collaboration_data.commission_rate <= 100):
                raise ValidationException("commission_rate", "佣金比例必须在0-100之间")
            
            collaboration_dict = collaboration_data.model_dump()
            collaboration_dict["status"] = CollaborationStatus.RECRUITING
            collaboration_dict["created_at"] = datetime.now().isoformat()
            collaboration_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_collaborations").insert(collaboration_dict).execute()
            
            if response.data:
                collaboration = CollaborationInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_collaboration_operation(
                    "CREATED", self.merchant_id, collaboration.id,
                    {"title": collaboration.title, "budget": collaboration.budget_amount}
                )
                
                return collaboration
            
            return None
            
        except ValidationException:
            raise
        except Exception as e:
            logger.log_error("CREATE_COLLABORATION", self.merchant_id, e, title=collaboration_data.title)
            raise
    
    async def get_collaboration(self, collaboration_id: str) -> Optional[CollaborationInDB]:
        """获取合作任务详情（增强版）"""
        try:
            logger.log_operation("GET_COLLABORATION", self.merchant_id, collaboration_id=collaboration_id)
            
            response = supabase.table("merchant_orders.cm_collaborations").select("*").eq("id", collaboration_id).execute()
            
            if not response.data:
                raise CollaborationNotFoundException(collaboration_id)
            
            collaboration = CollaborationInDB(**response.data[0])
            
            # 验证权限
            self._validate_merchant_access(collaboration.merchant_id, "GET_COLLABORATION")
            
            return collaboration
            
        except (CollaborationNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.log_error("GET_COLLABORATION", self.merchant_id, e, collaboration_id=collaboration_id)
            raise
    
# 更新 app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api import orders, verification, dashboard, refunds
from app.content_marketing import api as content_api
from app.database import test_connection
from app.core.logging import setup_logging
from app.core.middleware import LoggingMiddleware, ErrorHandlingMiddleware, SecurityMiddleware
import logging
import os

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME + " - 内容营销系统",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(SecurityMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态文件目录
os.makedirs("app/static/uploads/content", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 包含API路由
app.include_router(orders.router, prefix=settings.API_V1_STR, tags=["orders"])
app.include_router(verification.router, prefix=settings.API_V1_STR, tags=["verification"])
app.include_router(dashboard.router, prefix=settings.API_V1_STR, tags=["dashboard"])
app.include_router(refunds.router, prefix=settings.API_V1_STR, tags=["refunds"])
app.include_router(content_api.router, prefix=settings.API_V1_STR, tags=["content_marketing"])

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动 {settings.PROJECT_NAME} v{settings.VERSION} - 包含完整的内容营销系统")
    
    # 测试数据库连接
    if await test_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接异常")
    
    # 记录启动完成
    audit_logger = logging.getLogger("audit")
    audit_logger.info("APPLICATION_STARTUP - 系统启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用程序关闭")
    audit_logger = logging.getLogger("audit")
    audit_logger.info("APPLICATION_SHUTDOWN - 系统正常关闭")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.PROJECT_NAME} - 内容营销系统",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_check": "/health"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy", 
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_config=None  # 使用自定义日志配置
    )

    商家板块5数据分析
    from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.middleware import LoggingMiddleware, SecurityHeadersMiddleware
from app.api.endpoints import health, dashboard, analytics
from app.services.supabase_client import SupabaseClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting Analytics Suite API")
    logger.info(f"Environment: {'development' if settings.DEBUG else 'production'}")
    
    # 初始化 Supabase 客户端
    try:
        supabase_client = SupabaseClient()
        # 测试数据库连接
        if await supabase_client.health_check():
            logger.info("Database connection established successfully")
        else:
            logger.error("Failed to establish database connection")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    yield  # 应用运行期间
    
    # 关闭时
    logger.info("Shutting down Analytics Suite API")

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    description="精简版数据分析功能套件 - 经营健康度仪表盘和智能分析",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 设置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# 包含路由
app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["health"]
)

app.include_router(
    dashboard.router,
    prefix="/api/v1",
    tags=["dashboard"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1",
    tags=["analytics"]
)

# 全局异常处理器
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return HTTPException(
        status_code=404,
        detail="Resource not found"
    )

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Analytics Suite API",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None
    }

@app.get("/api/v1")
async def api_root():
    """API 根端点"""
    return {
        "message": "Analytics Suite API v1",
        "endpoints": {
            "health": "/api/v1/health",
            "dashboard": "/api/v1/dashboard",
            "alerts": "/api/v1/alerts",
            "snapshot": "/api/v1/snapshot",
            "competitors": "/api/v1/competitors",
            "marketing_roi": "/api/v1/marketing/roi",
            "revenue_trends": "/api/v1/revenue/trends",
            "review_summary": "/api/v1/reviews/summary"
        }
    }

# 初始化日志
setup_logging()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

    商家系统6财务中心
    from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.jobs.scheduler import FinanceScheduler
from app.jobs.finance_jobs import finance_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("启动财务中心应用...")
    
    # 创建导出目录
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # 启动定时任务
    FinanceScheduler.start_scheduler()
    
    # 注册定时任务
    FinanceScheduler.add_daily_summary_job(finance_jobs.run_daily_summary)
    FinanceScheduler.add_settlement_job(finance_jobs.run_weekly_settlement)
    FinanceScheduler.add_reconciliation_job(finance_jobs.run_daily_reconciliation)
    FinanceScheduler.add_report_cleanup_job(finance_jobs.run_report_cleanup)
    
    yield
    
    # 关闭时执行
    print("关闭财务中心应用...")
    FinanceScheduler.shutdown_scheduler()


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="商户财务中心后端API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/exports", StaticFiles(directory=settings.upload_dir), name="exports")

# 注册API路由
app.include_router(api_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/info")
async def app_info():
    """应用信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production"
    }


# 错误处理
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    return {"success": False, "message": "请求的资源不存在", "error_code": "NOT_FOUND"}


@app.exception_handler(500)
async def internal_exception_handler(request, exc):
    return {"success": False, "message": "服务器内部错误", "error_code": "INTERNAL_ERROR"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
    商家系统6财务中心
    from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, LoggingMiddleware
from app.core.error_handlers import setup_exception_handlers
from app.api.v1.api import api_router
from app.jobs.scheduler import FinanceScheduler
from app.jobs.finance_jobs import finance_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("启动财务中心应用...")
    
    # 设置日志
    setup_logging()
    
    # 创建导出目录
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # 启动定时任务
    FinanceScheduler.start_scheduler()
    
    # 注册定时任务
    FinanceScheduler.add_daily_summary_job(finance_jobs.run_daily_summary)
    FinanceScheduler.add_settlement_job(finance_jobs.run_weekly_settlement)
    FinanceScheduler.add_reconciliation_job(finance_jobs.run_daily_reconciliation)
    FinanceScheduler.add_report_cleanup_job(finance_jobs.run_report_cleanup)
    
    yield
    
    # 关闭时执行
    print("关闭财务中心应用...")
    FinanceScheduler.shutdown_scheduler()


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="商户财务中心后端API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 设置异常处理器
setup_exception_handlers(app)

# 挂载静态文件
app.mount("/exports", StaticFiles(directory=settings.upload_dir), name="exports")

# 注册API路由
app.include_router(api_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/info")
async def app_info():
    """应用信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
    商家系统7评价管理
    from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import reviews, statistics

app = FastAPI(
    title="商户评价管理系统",
    description="基于FastAPI和Supabase的商户评价管理后端系统",
    version="1.0.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(reviews.router)
app.include_router(statistics.router)

@app.get("/")
async def root():
    return {
        "message": "商户评价管理系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "服务运行正常"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
    
交易系统

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router
from app.utils.logger import logger
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    startup_time = time.time()
    logger.info("application_startup", time=startup_time)
    
    yield
    
    # 关闭时
    shutdown_time = time.time()
    logger.info("application_shutdown", time=shutdown_time, uptime=shutdown_time-startup_time)

# 创建FastAPI应用
app = FastAPI(
    title="Trade Platform API",
    description="电商交易平台核心API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0"
    }

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Trade Platform API",
        "version": "2.0.0",
        "docs": "/docs"
    }

# 注册API路由
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(
        "global_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "Internal server error",
            "detail": str(exc) if settings.debug else "An internal error occurred"
        }
    )

# 404处理
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "code": 404,
            "message": "Resource not found"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )


    内容系统

from fastapi import FastAPI, Depends, HTTPException, status, Request  # 导入FastAPI核心组件
from fastapi.middleware.cors import CORSMiddleware  # 导入CORS中间件
from fastapi.responses import JSONResponse  # 导入JSON响应
from fastapi.exceptions import RequestValidationError  # 导入请求验证异常
from contextlib import asynccontextmanager  # 导入异步上下文管理器
import time  # 导入时间模块
import logging  # 导入日志模块
from app.config import settings  # 导入应用配置
from app.database.connection import DatabaseManager, supabase  # 导入数据库连接
from app.routes import content_routes, review_routes, media_routes  # 导入路由模块
from app.utils.cache import initialize_cache, cache_manager  # 导入缓存工具
from app.utils.logger import setup_logging  # 导入日志配置
import uvicorn  # 导入UVicorn服务器

# 设置日志配置
setup_logging()

# 获取日志记录器
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器 - 处理启动和关闭事件
    
    Args:
        app: FastAPI应用实例
    """
    # 启动事件
    logger.info("应用启动中...")
    
    try:
        # 初始化缓存系统
        await initialize_cache()
        logger.info("缓存系统初始化完成")
        
        # 测试数据库连接
        db_health = await DatabaseManager.health_check()
        logger.info(f"数据库健康检查: {db_health}")
        
        # 测试缓存连接
        cache_health = await cache_manager.health_check()
        logger.info(f"缓存健康检查: {cache_health}")
        
        logger.info("应用启动完成")
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    
    # 应用运行中
    yield
    
    # 关闭事件
    logger.info("应用关闭中...")
    
    try:
        # 关闭数据库连接
        DatabaseManager.close_connections()
        logger.info("数据库连接已关闭")
        
        logger.info("应用关闭完成")
        
    except Exception as e:
        logger.error(f"应用关闭异常: {e}")

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,  # 项目名称
    description="越南本地团购平台内容管理系统API",  # 项目描述
    version=settings.APP_VERSION,  # 应用版本
    docs_url="/docs" if settings.DEBUG else None,  # 调试模式下开启文档
    redoc_url="/redoc" if settings.DEBUG else None,  # 调试模式下开启ReDoc
    openapi_url="/openapi.json" if settings.DEBUG else None,  # 调试模式下开启OpenAPI
    lifespan=lifespan  # 生命周期管理器
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # 允许的源
    allow_credentials=True,  # 允许凭据
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头
)

# 自定义异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    请求验证异常处理器
    
    Args:
        request: 请求对象
        exc: 验证异常
        
    Returns:
        JSON错误响应
    """
    # 记录验证错误
    logger.warning(f"请求验证失败: {exc.errors()}")
    
    # 返回统一的错误响应格式
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "请求数据验证失败",
            "error": {
                "code": "VALIDATION_ERROR",
                "details": exc.errors()
            },
            "data": None
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP异常处理器
    
    Args:
        request: 请求对象
        exc: HTTP异常
        
    Returns:
        JSON错误响应
    """
    # 记录HTTP异常
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
    
    # 返回统一的错误响应格式
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error": {
                "code": "HTTP_ERROR",
                "details": None
            },
            "data": None
        },
        headers=exc.headers
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    通用异常处理器
    
    Args:
        request: 请求对象
        exc: 异常
        
    Returns:
        JSON错误响应
    """
    # 记录异常详情
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    
    # 返回统一的错误响应格式
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "details": str(exc) if settings.DEBUG else None
            },
            "data": None
        }
    )

# 添加中间件：请求日志记录
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    请求日志记录中间件
    
    Args:
        request: 请求对象
        call_next: 下一个中间件或路由处理函数
        
    Returns:
        HTTP响应
    """
    # 记录请求开始时间
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"请求开始: {request.method} {request.url}")
    
    try:
        # 调用下一个中间件或路由处理函数
        response = await call_next(request)
        
        # 计算请求处理时间
        process_time = time.time() - start_time
        
        # 记录响应信息
        logger.info(f"请求完成: {request.method} {request.url} - 状态: {response.status_code} - 耗时: {process_time:.2f}s")
        
        # 添加处理时间到响应头
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        # 记录请求处理异常
        process_time = time.time() - start_time
        logger.error(f"请求异常: {request.method} {request.url} - 错误: {str(e)} - 耗时: {process_time:.2f}s")
        raise

# 健康检查端点
@app.get("/health", tags=["health"])
async def health_check():
    """
    应用健康检查端点
    
    Returns:
        健康状态信息
    """
    try:
        # 检查数据库健康状态
        db_health = await DatabaseManager.health_check()
        
        # 检查缓存健康状态
        cache_health = await cache_manager.health_check()
        
        # 构建健康状态响应
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": db_health,
            "cache": cache_health
        }
        
        # 检查所有组件是否健康
        if (db_health.get("supabase") and db_health.get("redis") and 
            cache_health.get("status") == "healthy"):
            return {
                "success": True,
                "message": "服务运行正常",
                "data": health_status
            }
        else:
            # 如果有组件不健康，返回503状态
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "message": "服务部分组件异常",
                    "data": health_status
                }
            )
            
    except Exception as e:
        # 记录健康检查异常
        logger.error(f"健康检查异常: {str(e)}")
        
        # 返回服务不可用状态
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "message": "服务健康检查失败",
                "error": {
                    "code": "HEALTH_CHECK_FAILED",
                    "details": str(e) if settings.DEBUG else None
                },
                "data": None
            }
        )

# 根端点
@app.get("/", tags=["root"])
async def root():
    """
    应用根端点
    
    Returns:
        欢迎信息
    """
    return {
        "success": True,
        "message": f"欢迎使用 {settings.PROJECT_NAME} API",
        "data": {
            "name": settings.PROJECT_NAME,
            "version": settings.APP_VERSION,
            "description": "越南本地团购平台内容管理系统",
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs" if settings.DEBUG else None
        }
    }

# 注册路由
app.include_router(content_routes.router, prefix=settings.API_V1_STR)  # 内容路由
app.include_router(review_routes.router, prefix=settings.API_V1_STR)  # 评价路由
app.include_router(media_routes.router, prefix=settings.API_V1_STR)   # 媒体上传路由

# 启动应用（仅在直接运行时执行）
if __name__ == "__main__":
    # 启动UVicorn服务器
    uvicorn.run(
        "main:app",  # 应用实例
        host="0.0.0.0",  # 监听地址
        port=8000,  # 监听端口
        reload=settings.DEBUG,  # 调试模式下自动重载
        log_level=settings.LOG_LEVEL.lower(),  # 日志级别
        access_log=True  # 启用访问日志
    )

    内容模块

import time
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple, Optional
import asyncio

from app.utils.cache import cache_redis
from app.utils.exceptions import RateLimitException
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(
        self,
        app,
        default_limit: int = settings.RATE_LIMIT_PER_MINUTE,
        window: int = 60,  # 时间窗口（秒）
        block_duration: int = 300  # 封禁持续时间（秒）
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.window = window
        self.block_duration = block_duration
        self.rate_limit_rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict[str, Tuple[int, int]]:
        """初始化限流规则"""
        return {
            "/api/v1/videos/upload": (10, 300),  # 上传接口：10次/5分钟
            "/api/v1/auth/login": (5, 60),       # 登录接口：5次/分钟
            "/api/v1/auth/register": (3, 300),   # 注册接口：3次/5分钟
            "/api/v1/comments": (30, 60),        # 评论接口：30次/分钟
            "/api/v1/likes": (60, 60),           # 点赞接口：60次/分钟
        }
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 获取客户端标识
        client_id = await self._get_client_identifier(request)
        
        # 检查是否被封禁
        if await self._is_client_blocked(client_id):
            raise RateLimitException("请求过于频繁，请稍后重试")
        
        # 获取路径特定的限流规则
        limit, window = self._get_rate_limit_for_path(request.url.path)
        
        # 检查速率限制
        if await self._is_rate_limited(client_id, request.url.path, limit, window):
            # 触发封禁
            await self._block_client(client_id)
            raise RateLimitException("请求过于频繁，账户已被临时封禁")
        
        # 处理请求
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            raise e
    
    async def _get_client_identifier(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用用户ID（如果已认证）
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.utils.security import verify_token
                token = auth_header.replace("Bearer ", "")
                payload = verify_token(token)
                if payload and payload.get("user_id"):
                    return f"user:{payload['user_id']}"
            except Exception:
                pass
        
        # 使用IP地址作为后备
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host
        
        return f"ip:{client_ip}"
    
    def _get_rate_limit_for_path(self, path: str) -> Tuple[int, int]:
        """获取路径的限流规则"""
        for rule_path, (limit, window) in self.rate_limit_rules.items():
            if path.startswith(rule_path):
                return limit, window
        
        return self.default_limit, self.window
    
    async def _is_rate_limited(self, client_id: str, path: str, limit: int, window: int) -> bool:
        """检查是否超过速率限制"""
        try:
            key = f"rate_limit:{client_id}:{path}"
            current = await cache_redis.get(key)
            
            if current is None:
                # 第一次请求
                await cache_redis.set(key, 1, window)
                return False
            
            current_count = int(current)
            if current_count >= limit:
                return True
            
            # 递增计数
            await cache_redis.incr(key)
            return False
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return False
    
    async def _is_client_blocked(self, client_id: str) -> bool:
        """检查客户端是否被封禁"""
        try:
            block_key = f"blocked:{client_id}"
            return await cache_redis.exists(block_key)
        except Exception as e:
            logger.error(f"Block check error: {str(e)}")
            return False
    
    async def _block_client(self, client_id: str):
        """封禁客户端"""
        try:
            block_key = f"blocked:{client_id}"
            await cache_redis.set(block_key, 1, self.block_duration)
            logger.warning(f"Client blocked: {client_id} for {self.block_duration} seconds")
        except Exception as e:
            logger.error(f"Block client error: {str(e)}")


class ConcurrentLimitMiddleware(BaseHTTPMiddleware):
    """并发限制中间件"""
    
    def __init__(self, app, max_concurrent: int = 100):
        super().__init__(app)
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 检查并发限制
        if self.active_requests >= self.max_concurrent:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "服务器繁忙，请稍后重试",
                    "error_code": "SERVER_BUSY"
                }
            )
        
        async with self.semaphore:
            self.active_requests += 1
            try:
                response = await call_next(request)
                return response
            finally:
                self.active_requests -= 1


        
        内容系统

    import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.core.middleware import setup_middlewares, LoggingMiddleware, SecurityHeadersMiddleware
from app.core.exceptions import VideoContentException
from app.utils.logger import logger
from app.api.v1.endpoints import users, content, recommendations, moderation, upload

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行的操作
    logger.info("🚀 视频内容系统启动中...")
    logger.info(f"📝 应用名称: {settings.app_name}")
    logger.info(f"🔧 环境: {'开发' if settings.debug else '生产'}")
    logger.info(f"🌐 服务地址: http://{settings.host}:{settings.port}")
    
    # 执行启动任务
    await startup_tasks()
    
    yield  # 应用运行期间
    
    # 关闭时执行的操作
    logger.info("🛑 视频内容系统关闭中...")
    await shutdown_tasks()

async def startup_tasks():
    """启动任务"""
    try:
        logger.info("执行启动任务...")
        
        # 初始化数据库连接
        from app.database.supabase_client import db_manager
        # 测试数据库连接
        test_connection = await db_manager.select("users", limit=1)
        logger.info("✅ 数据库连接测试成功")
        
        # 初始化Redis连接
        from app.core.security import redis_client
        redis_client.ping()
        logger.info("✅ Redis连接测试成功")
        
        # 创建必要的目录
        from app.services.file_service import FileService
        file_service = FileService()
        logger.info("✅ 文件存储目录初始化成功")
        
        # 启动后台任务（如定时清理）
        import asyncio
        asyncio.create_task(periodic_cleanup_tasks())
        
        logger.info("✅ 所有启动任务完成")
        
    except Exception as e:
        logger.error(f"启动任务失败: {str(e)}")
        raise

async def shutdown_tasks():
    """关闭任务"""
    try:
        logger.info("执行关闭任务...")
        
        # 关闭数据库连接
        logger.info("数据库连接已关闭")
        
        # 关闭Redis连接
        from app.core.security import redis_client
        redis_client.close()
        logger.info("Redis连接已关闭")
        
        logger.info("✅ 所有关闭任务完成")
        
    except Exception as e:
        logger.error(f"关闭任务失败: {str(e)}")

async def periodic_cleanup_tasks():
    """定期清理任务"""
    try:
        while True:
            # 每6小时执行一次清理
            await asyncio.sleep(6 * 60 * 60)  # 6小时
            
            logger.info("执行定期清理任务...")
            
            # 清理临时文件
            from app.services.file_service import FileService
            file_service = FileService()
            await file_service.cleanup_temp_files()
            
            # 清理过期的Redis键
            # 这里可以添加其他清理逻辑
            
            logger.info("定期清理任务完成")
            
    except Exception as e:
        logger.error(f"定期清理任务失败: {str(e)}")

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="视频内容系统 - 为越南本地团购平台提供智能视频内容管理",
    docs_url="/docs" if settings.debug else None,  # 生产环境关闭文档
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 全局异常处理器
@app.exception_handler(VideoContentException)
async def video_content_exception_handler(request: Request, exc: VideoContentException):
    """自定义异常处理器"""
    logger.error(f"自定义异常: {exc.detail} - URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理异常: {str(exc)} - URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "服务器内部错误",
            "path": str(request.url.path)
        }
    )

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# 包含API路由
app.include_router(users.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(moderation.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")

# 根路由
@app.get("/")
async def root():
    """根路由 - 返回应用信息"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        from app.database.supabase_client import db_manager
        await db_manager.select("users", limit=1)
        
        # 检查Redis连接
        from app.core.security import redis_client
        redis_client.ping()
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )

@app.get("/info")
async def app_info():
    """应用信息端点"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "features": {
            "content_management": True,
            "recommendation_engine": True,
            "moderation_system": True,
            "file_upload": True,
            "user_authentication": True
        }
    }

# 启动应用
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )