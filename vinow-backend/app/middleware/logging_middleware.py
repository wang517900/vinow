交易系统

import time
import json
import uuid
from typing import Callable, Awaitable, Optional, Dict, Any
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.utils.logger_api import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    记录所有HTTP请求的详细信息，包括请求参数、响应结果、处理时间等
    支持追踪ID，便于请求链路追踪和问题排查
    """
    
    def __init__(self, app, 
                 skip_paths: Optional[list] = None,
                 include_request_body: bool = False,
                 include_response_body: bool = False,
                 generate_trace_id: bool = True):
        """
        初始化日志中间件
        
        Args:
            app: ASGI应用
            skip_paths (list, optional): 需要跳过日志记录的路径列表
            include_request_body (bool): 是否记录请求体内容
            include_response_body (bool): 是否记录响应体内容
            generate_trace_id (bool): 是否生成追踪ID
        """
        super().__init__(app)
        
        # 配置选项
        self.skip_paths = set(skip_paths or [
            "/health",
            "/metrics",
            "/favicon.ico"
        ])
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.generate_trace_id = generate_trace_id
        
        logger.info(
            "logging_middleware_initialized",
            skip_paths=list(self.skip_paths),
            include_request_body=include_request_body,
            include_response_body=include_response_body
        )
    
    def _should_skip_logging(self, request: Request) -> bool:
        """
        判断是否应该跳过日志记录
        
        Args:
            request (Request): 请求对象
            
        Returns:
            bool: True表示跳过日志记录，False表示需要记录
        """
        path = request.url.path
        
        # 检查是否在跳过路径列表中
        if path in self.skip_paths:
            return True
            
        # 检查是否以跳过路径开头
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
                
        return False
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        获取客户端真实IP地址
        
        Args:
            request (Request): 请求对象
            
        Returns:
            str: 客户端IP地址
        """
        # 检查常见的代理头部
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
            
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
            
        cf_connecting_ip = request.headers.get("cf-connecting-ip")
        if cf_connecting_ip:
            return cf_connecting_ip
            
        # 回退到直接客户端IP
        if request.client:
            return request.client.host
            
        return None
    
    def _get_user_info(self, request: Request) -> Dict[str, Any]:
        """
        获取用户信息
        
        Args:
            request (Request): 请求对象
            
        Returns:
            dict: 用户信息字典
        """
        user_info = {}
        
        # 从请求状态中获取用户信息
        if hasattr(request.state, 'user') and request.state.user:
            user = request.state.user
            user_info["user_id"] = user.get("sub")
            user_info["user_type"] = user.get("type", "unknown")
            user_info["username"] = user.get("username")
            
        return user_info
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """
        获取请求体内容（如果需要记录）
        
        Args:
            request (Request): 请求对象
            
        Returns:
            str: 请求体内容（截断后的）
        """
        if not self.include_request_body:
            return None
            
        try:
            # 只记录特定类型的内容
            content_type = request.headers.get("content-type", "")
            if not any(ct in content_type for ct in ["application/json", "application/x-www-form-urlencoded"]):
                return f"[{content_type}]"
            
            # 获取请求体
            body = await request.body()
            if body:
                body_str = body.decode("utf-8")
                # 限制长度以避免日志过大
                if len(body_str) > 1000:
                    return body_str[:1000] + "...(truncated)"
                return body_str
            return ""
        except Exception as e:
            logger.warning("logging_middleware_body_read_error", error=str(e))
            return "[Error reading body]"
    
    def _get_request_headers(self, request: Request) -> Dict[str, str]:
        """
        获取请求头信息（敏感信息会被过滤）
        
        Args:
            request (Request): 请求对象
            
        Returns:
            dict: 过滤后的请求头信息
        """
        sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token"
        }
        
        headers = {}
        for key, value in request.headers.items():
            if key.lower() in sensitive_headers:
                headers[key] = "[REDACTED]"
            else:
                headers[key] = value
                
        return headers
    
    def _generate_trace_id(self) -> str:
        """
        生成追踪ID
        
        Returns:
            str: 追踪ID
        """
        return str(uuid.uuid4())
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> Response:
        """
        中间件核心处理逻辑
        
        Args:
            request (Request): 请求对象
            call_next (Callable): 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        # 检查是否需要跳过日志记录
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # 生成追踪ID
        trace_id = None
        if self.generate_trace_id:
            trace_id = self._generate_trace_id()
            # 将追踪ID添加到请求状态中
            request.state.trace_id = trace_id
        
        start_time = time.time()
        
        # 获取请求相关信息
        client_ip = self._get_client_ip(request)
        user_info = self._get_user_info(request)
        request_headers = self._get_request_headers(request) if logger.level <= 10 else {}  # 只在DEBUG级别记录headers
        
        # 获取请求体（如果配置了记录）
        request_body = None
        if self.include_request_body:
            request_body = await self._get_request_body(request)
        
        # 记录请求开始
        logger.info(
            "request_started",
            trace_id=trace_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
            content_length=request.headers.get("content-length"),
            user_info=user_info,
            headers=request_headers if request_headers else None,
            body=request_body
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 获取响应体（如果配置了记录）
            response_body = None
            if self.include_response_body and hasattr(response, 'body'):
                try:
                    # 注意：这可能不适用于所有类型的响应
                    if hasattr(response, 'body_iterator'):
                        # 对于流式响应，我们不能轻易读取body
                        response_body = "[Stream response]"
                    else:
                        response_body = getattr(response, 'body', b'')[:1000].decode('utf-8', errors='ignore')
                except Exception:
                    response_body = "[Error reading response body]"
            
            # 记录请求完成
            logger.info(
                "request_completed",
                trace_id=trace_id,
                method=request.method,
                url=str(request.url),
                path=request.url.path,
                status_code=response.status_code,
                process_time=round(process_time, 3),
                response_size=getattr(response, 'headers', {}).get('content-length'),
                user_info=user_info,
                body=response_body if response_body else None
            )
            
            # 添加追踪和性能相关headers
            if trace_id:
                response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Process-Time"] = str(round(process_time, 3))
            
            return response
            
        except RequestValidationError as e:
            process_time = time.time() - start_time
            
            # 记录请求验证错误
            logger.warning(
                "request_validation_error",
                trace_id=trace_id,
                method=request.method,
                url=str(request.url),
                path=request.url.path,
                error=str(e),
                errors=e.errors(),
                process_time=round(process_time, 3),
                user_info=user_info
            )
            
            # 重新抛出异常让FastAPI处理
            raise
            
        except StarletteHTTPException as e:
            process_time = time.time() - start_time
            
            # 记录HTTP异常
            logger.info(
                "request_http_exception",
                trace_id=trace_id,
                method=request.method,
                url=str(request.url),
                path=request.url.path,
                status_code=e.status_code,
                detail=str(e.detail) if hasattr(e, 'detail') else str(e),
                process_time=round(process_time, 3),
                user_info=user_info
            )
            
            # 重新抛出异常
            raise
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # 记录未预期的错误
            logger.error(
                "request_unexpected_error",
                trace_id=trace_id,
                method=request.method,
                url=str(request.url),
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                process_time=round(process_time, 3),
                user_info=user_info
            )
            
            # 重新抛出异常
            raise

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    
    为每个请求生成唯一的请求ID，并添加到响应头中
    便于请求追踪和日志关联
    """
    
    def __init__(self, app, header_name: str = "X-Request-ID"):
        """
        初始化请求ID中间件
        
        Args:
            app: ASGI应用
            header_name (str): 请求ID头名称
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> Response:
        """
        中间件核心处理逻辑
        
        Args:
            request (Request): 请求对象
            call_next (Callable): 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 将请求ID添加到请求状态中
        request.state.request_id = request_id
        
        # 处理请求
        response = await call_next(request)
        
        # 添加请求ID到响应头
        response.headers[self.header_name] = request_id
        
        return response

# 创建日志中间件的便捷函数
def create_logging_middleware(app,
                            skip_paths: Optional[list] = None,
                            include_request_body: bool = False,
                            include_response_body: bool = False,
                            generate_trace_id: bool = True) -> LoggingMiddleware:
    """
    创建日志中间件实例
    
    Args:
        app: ASGI应用
        skip_paths (list, optional): 需要跳过日志记录的路径列表
        include_request_body (bool): 是否记录请求体内容
        include_response_body (bool): 是否记录响应体内容
        generate_trace_id (bool): 是否生成追踪ID
        
    Returns:
        LoggingMiddleware: 日志中间件实例
        
    Example:
        >>> middleware = create_logging_middleware(
        ...     app,
        ...     skip_paths=["/health", "/metrics"],
        ...     include_request_body=True
        ... )
    """
    return LoggingMiddleware(
        app,
        skip_paths=skip_paths,
        include_request_body=include_request_body,
        include_response_body=include_response_body,
        generate_trace_id=generate_trace_id
    )