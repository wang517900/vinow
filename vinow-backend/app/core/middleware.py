商家内容营销
# app/core/middleware.py
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from app.core.exceptions import BusinessException
from app.core.logging import BusinessLogger

logger = BusinessLogger("middleware")

class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求开始
        logger.log_operation(
            "REQUEST_START",
            merchant_id=request.headers.get("x-merchant-id", "unknown"),
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录请求完成
            logger.log_performance(
                "REQUEST_COMPLETE",
                process_time,
                merchant_id=request.headers.get("x-merchant-id", "unknown")
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            logger.log_error(
                "REQUEST_ERROR",
                merchant_id=request.headers.get("x-merchant-id", "unknown"),
                error=exc,
                method=request.method,
                path=request.url.path
            )
            raise exc

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
            
        except BusinessException as exc:
            # 业务异常
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "message": exc.detail,
                    "code": exc.code,
                    "data": exc.data
                }
            )
            
        except HTTPException as exc:
            # FastAPI HTTP异常
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "message": exc.detail,
                    "code": "HTTP_ERROR"
                }
            )
            
        except Exception as exc:
            # 未预期的异常
            logger.log_error(
                "UNEXPECTED_ERROR",
                merchant_id=request.headers.get("x-merchant-id", "unknown"),
                error=exc,
                method=request.method,
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "message": "服务器内部错误",
                    "code": "INTERNAL_SERVER_ERROR"
                }
            )

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 安全检查
        security_checks = self._perform_security_checks(request)
        if security_checks:
            return security_checks
            
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response
    
    def _perform_security_checks(self, request: Request) -> Response | None:
        """执行安全检查"""
        # 检查必要的头部
        merchant_id = request.headers.get("x-merchant-id")
        if not merchant_id and request.method != "OPTIONS":
            return JSONResponse(
                status_code=400,
                content={
                    "message": "缺少商家ID头部",
                    "code": "MISSING_MERCHANT_ID"
                }
            )
        
        # 检查内容类型（对于POST/PUT请求）
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=415,
                    content={
                        "message": "不支持的媒体类型",
                        "code": "UNSUPPORTED_MEDIA_TYPE"
                    }
                )
        
        return None


        商家板块5数据分析
        import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger
from app.core.config import settings

class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 记录请求开始时间
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录日志
        log_data = {
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "client_ip": request.client.host if request.client else "unknown"
        }
        
        # 根据状态码记录不同级别的日志
        if response.status_code >= 500:
            logger.error("HTTP request error", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("HTTP client error", extra=log_data)
        else:
            logger.info("HTTP request processed", extra=log_data)
        
        # 添加处理时间到响应头
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

        内容系统

        import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from app.config import settings
from app.utils.logger import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            f"Request started: {request.method} {request.url} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"Request completed: {request.method} {request.url} - "
                f"Status: {response.status_code} - "
                f"Duration: {process_time:.3f}s"
            )
            
            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url} - "
                f"Error: {str(e)} - Duration: {process_time:.3f}s"
            )
            raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 添加安全头
        security_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
            
        return response

def setup_cors_middleware(app):
    """设置 CORS 中间件"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def setup_middlewares(app):
    """设置所有中间件"""
    setup_cors_middleware(app)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)