内容板块-限流中间件
"""
速率限制中间件模块

本模块提供了基于令牌桶算法的速率限制中间件，用于防止API滥用和DDoS攻击。
主要功能包括：
1. 基于IP地址、用户ID或API密钥的限流
2. 多种限流策略配置
3. 详细的限流头信息返回
4. 异常情况下的优雅降级

支持的特性：
- 灵活的限流配置
- 多维度客户端标识
- 标准化的限流响应头
- 路径排除（无需限流的路径）
- 缓存驱动的计数器管理
"""

from typing import Callable, Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.cache_utils import cache_manager
import logging
import time

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = ['RateLimitMiddleware']


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件 - 防止API滥用和DDoS攻击
    """
    
    def __init__(self, app, limits: Optional[Dict[str, Any]] = None):
        """
        初始化限流中间件
        
        Args:
            app: FastAPI应用实例
            limits: 限流配置字典
        """
        # 调用父类初始化
        super().__init__(app)
        # 设置默认限流配置
        self.limits = limits or {
            "default": {"requests": 100, "window": 60},  # 默认：60秒内100次请求
            "auth": {"requests": 10, "window": 60},  # 认证相关：60秒内10次请求
            "upload": {"requests": 5, "window": 60},  # 文件上传：60秒内5次请求
            "api_key": {"requests": 1000, "window": 3600},  # API密钥：1小时内1000次请求
        }
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        处理请求分发
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            HTTP响应
            
        Raises:
            HTTPException: 限流超限时抛出429状态码
        """
        try:
            # 获取客户端标识符
            client_identifier = await self._get_client_identifier(request)
            
            # 获取请求的限流配置
            rate_limit_config = await self._get_rate_limit_config(request)
            
            # 检查是否应该跳过限流
            if await self._should_skip_rate_limit(request, client_identifier):
                # 跳过限流检查
                response = await call_next(request)
                return response
            
            # 检查速率限制
            rate_limit_result = await self._check_rate_limit(
                client_identifier, 
                rate_limit_config,
                request
            )
            
            if not rate_limit_result["allowed"]:
                # 超过速率限制，返回429太多请求
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "message": "请求频率过高",
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "details": f"请在 {rate_limit_result['reset_in']} 秒后重试"
                        },
                        "data": None
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_config["requests"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(rate_limit_result["reset_time"]),
                        "Retry-After": str(rate_limit_result["reset_in"])
                    }
                )
            
            # 在响应头中添加限流信息
            response = await call_next(request)
            
            # 添加限流头信息
            response.headers["X-RateLimit-Limit"] = str(rate_limit_config["requests"])
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
            response.headers["X-RateLimit-Reset"] = str(rate_limit_result["reset_time"])
            
            return response
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录限流中间件异常
            logger.error(f"限流中间件异常: {str(e)}", exc_info=True)
            # 在异常情况下，允许请求通过（避免因为限流系统故障导致服务不可用）
            return await call_next(request)
    
    async def _get_client_identifier(self, request: Request) -> str:
        """
        获取客户端标识符
        
        Args:
            request: 请求对象
            
        Returns:
            客户端标识符字符串
        """
        try:
            # 优先使用API密钥作为标识符
            api_key = request.headers.get("X-API-Key")
            if api_key:
                return f"api_key:{api_key}"
            
            # 其次使用用户ID作为标识符（如果已认证）
            if hasattr(request.state, "user") and request.state.user:
                user_id = request.state.user.get("user_id")
                if user_id:
                    return f"user:{user_id}"
            
            # 最后使用IP地址作为标识符
            client_ip = await self._get_client_ip(request)
            return f"ip:{client_ip}"
            
        except Exception as e:
            # 记录客户端标识符获取异常
            logger.error(f"客户端标识符获取异常: {str(e)}", exc_info=True)
            # 返回默认标识符
            return "unknown"
    
    async def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端IP地址
        
        Args:
            request: 请求对象
            
        Returns:
            客户端IP地址字符串
        """
        try:
            # 优先使用X-Real-IP头
            x_real_ip = request.headers.get("X-Real-IP")
            if x_real_ip:
                return x_real_ip
            
            # 其次使用X-Forwarded-For头的第一个IP
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                # 取第一个IP（客户端原始IP）
                client_ip = x_forwarded_for.split(",")[0].strip()
                return client_ip
            
            # 最后使用客户端主机
            if request.client and request.client.host:
                return request.client.host
            
            # 无法获取IP地址
            return "unknown"
            
        except Exception as e:
            # 记录客户端IP获取异常
            logger.error(f"客户端IP获取异常: {str(e)}", exc_info=True)
            return "unknown"
    
    async def _get_rate_limit_config(self, request: Request) -> Dict[str, Any]:
        """
        获取请求的限流配置
        
        Args:
            request: 请求对象
            
        Returns:
            限流配置字典
        """
        try:
            # 获取请求路径
            path = request.url.path
            
            # 根据路径选择限流配置
            if path.startswith("/api/v1/auth"):
                # 认证相关接口
                return self.limits.get("auth", self.limits["default"])
            elif path.startswith("/api/v1/media/upload"):
                # 文件上传接口
                return self.limits.get("upload", self.limits["default"])
            elif request.headers.get("X-API-Key"):
                # API密钥请求
                return self.limits.get("api_key", self.limits["default"])
            else:
                # 默认配置
                return self.limits.get("default", {"requests": 100, "window": 60})
                
        except Exception as e:
            # 记录限流配置获取异常
            logger.error(f"限流配置获取异常: {str(e)}", exc_info=True)
            # 返回默认配置
            return {"requests": 100, "window": 60}
    
    async def _should_skip_rate_limit(self, request: Request, client_identifier: str) -> bool:
        """
        检查是否应该跳过限流
        
        Args:
            request: 请求对象
            client_identifier: 客户端标识符
            
        Returns:
            是否跳过限流
        """
        try:
            # 获取请求路径
            path = request.url.path
            
            # 健康检查接口跳过限流
            if path == "/health":
                return True
            
            # API文档接口跳过限流
            if path in ["/docs", "/redoc", "/openapi.json"]:
                return True
            
            # 内部网络IP跳过限流（用于监控等）
            if client_identifier.startswith("ip:127.0.0.1") or client_identifier.startswith("ip:10.") or client_identifier.startswith("ip:192.168."):
                return True
            
            # 其他情况不跳过限流
            return False
            
        except Exception as e:
            # 记录跳过限流检查异常
            logger.error(f"跳过限流检查异常: {str(e)}", exc_info=True)
            # 在异常情况下，不跳过限流
            return False
    
    async def _check_rate_limit(self, client_identifier: str, config: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """
        检查速率限制
        
        Args:
            client_identifier: 客户端标识符
            config: 限流配置
            request: 请求对象
            
        Returns:
            限流检查结果字典
        """
        try:
            # 获取当前时间戳
            current_time = int(time.time())
            # 计算时间窗口开始时间
            window_start = current_time - config["window"]
            
            # 构建缓存键
            cache_key = f"rate_limit:{client_identifier}:{window_start}"
            
            # 获取当前窗口的请求计数
            current_count = await cache_manager.get(cache_key) or 0
            
            # 计算剩余请求次数
            remaining = max(0, config["requests"] - current_count - 1)
            
            # 检查是否超过限制
            if current_count >= config["requests"]:
                # 超过限制，计算重置时间
                reset_time = window_start + config["window"]
                reset_in = reset_time - current_time
                
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "reset_in": reset_in
                }
            
            # 增加请求计数
            new_count = current_count + 1
            await cache_manager.set(cache_key, new_count, expire=config["window"])
            
            # 计算重置时间
            reset_time = window_start + config["window"]
            reset_in = reset_time - current_time
            
            return {
                "allowed": True,
                "remaining": remaining,
                "reset_time": reset_time,
                "reset_in": reset_in
            }
            
        except Exception as e:
            # 记录限流检查异常
            logger.error(f"限流检查异常: {str(e)}", exc_info=True)
            # 在异常情况下，允许请求通过
            return {
                "allowed": True,
                "remaining": config["requests"],
                "reset_time": int(time.time()) + config["window"],
                "reset_in": config["window"]
            }
        
    内容模块-限流中间件

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