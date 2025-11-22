交易系统

import time
import json
from typing import Dict, Optional, Callable, Awaitable
from redis import asyncio as aioredis
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.config import settings
from app.utils.logger_api import logger

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件
    
    基于Redis实现的分布式限流中间件，支持多种限流策略
    包括固定窗口、滑动窗口和令牌桶算法
    """
    
    def __init__(self, app, 
                 redis_url: str = None,
                 default_limits: Optional[Dict] = None,
                 key_func: Optional[Callable] = None,
                 strategy: str = "fixed_window"):
        """
        初始化限流中间件
        
        Args:
            app: ASGI应用
            redis_url (str): Redis连接URL
            default_limits (Dict, optional): 默认限流规则
            key_func (Callable, optional): 获取限流key的函数
            strategy (str): 限流策略 ("fixed_window", "sliding_window", "token_bucket")
        """
        super().__init__(app)
        
        # Redis连接配置
        self.redis_url = redis_url or settings.redis_url
        self.redis_client = None
        
        # 默认限流规则 (每分钟请求数)
        self.default_limits = default_limits or {
            "anonymous": {"requests": 60, "window": 60},      # 匿名用户每分钟60次
            "authenticated": {"requests": 1000, "window": 60}, # 认证用户每分钟1000次
            "premium": {"requests": 5000, "window": 60}        # 高级用户每分钟5000次
        }
        
        # 获取限流key的函数
        self.key_func = key_func or self._default_key_func
        
        # 限流策略
        self.strategy = strategy
        
        # 存储路径特定的限流规则
        self.route_limits = {}
        
        logger.info(
            "rate_limit_middleware_initialized",
            strategy=strategy,
            default_limits=self.default_limits
        )
    
    async def init_redis(self):
        """初始化Redis连接"""
        if self.redis_client is None:
            try:
                self.redis_client = aioredis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("rate_limit_redis_connected", url=self.redis_url)
            except Exception as e:
                logger.error("rate_limit_redis_connection_failed", error=str(e))
                raise
    
    def _default_key_func(self, request: Request) -> str:
        """
        默认的限流key生成函数
        
        Args:
            request (Request): 请求对象
            
        Returns:
            str: 限流key
        """
        # 优先使用用户ID
        if hasattr(request.state, 'user') and request.state.user:
            user_id = request.state.user.get('sub')
            if user_id:
                user_type = request.state.user.get('type', 'authenticated')
                return f"user:{user_id}:{user_type}"
        
        # 使用IP地址
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}:anonymous"
    
    def set_route_limit(self, path: str, limit: int, window: int, 
                       method: Optional[str] = None):
        """
        设置特定路由的限流规则
        
        Args:
            path (str): 路径
            limit (int): 限制请求数
            window (int): 时间窗口(秒)
            method (str, optional): HTTP方法
        """
        route_key = f"{path}:{method}" if method else path
        self.route_limits[route_key] = {
            "limit": limit,
            "window": window
        }
        logger.info(
            "rate_limit_route_configured",
            path=path,
            method=method,
            limit=limit,
            window=window
        )
    
    def _get_route_key(self, request: Request) -> str:
        """
        获取路由key
        
        Args:
            request (Request): 请求对象
            
        Returns:
            str: 路由key
        """
        return f"{request.url.path}:{request.method}"
    
    async def _get_limit_config(self, request: Request) -> Dict:
        """
        获取限流配置
        
        Args:
            request (Request): 请求对象
            
        Returns:
            Dict: 限流配置
        """
        route_key = self._get_route_key(request)
        
        # 检查是否有路由特定的限流规则
        if route_key in self.route_limits:
            return self.route_limits[route_key]
        
        # 使用默认规则
        key = self.key_func(request)
        user_type = key.split(":")[-1] if ":" in key else "anonymous"
        
        return self.default_limits.get(user_type, self.default_limits["anonymous"])
    
    async def _fixed_window_strategy(self, key: str, limit: int, window: int) -> Dict:
        """
        固定窗口限流策略
        
        Args:
            key (str): 限流key
            limit (int): 限制数量
            window (int): 时间窗口
            
        Returns:
            Dict: 限流结果
        """
        redis_key = f"rate_limit:{key}:{int(time.time()) // window}"
        
        try:
            # 增加计数器
            current = await self.redis_client.incr(redis_key)
            
            # 设置过期时间
            if current == 1:
                await self.redis_client.expire(redis_key, window)
            
            # 检查是否超出限制
            allowed = current <= limit
            remaining = max(0, limit - current)
            
            return {
                "allowed": allowed,
                "remaining": remaining,
                "reset_time": (int(time.time()) // window + 1) * window,
                "current": current
            }
        except Exception as e:
            logger.error("rate_limit_fixed_window_error", error=str(e), key=key)
            # 发生错误时允许请求通过
            return {"allowed": True, "remaining": -1, "reset_time": 0, "current": 0}
    
    async def _sliding_window_strategy(self, key: str, limit: int, window: int) -> Dict:
        """
        滑动窗口限流策略
        
        Args:
            key (str): 限流key
            limit (int): 限制数量
            window (int): 时间窗口
            
        Returns:
            Dict: 限流结果
        """
        now = time.time()
        redis_key = f"rate_limit_sliding:{key}"
        
        try:
            # 清理过期的记录
            await self.redis_client.zremrangebyscore(redis_key, 0, now - window)
            
            # 获取当前窗口内的请求数
            current = await self.redis_client.zcard(redis_key)
            
            allowed = current < limit
            remaining = max(0, limit - current)
            
            if allowed:
                # 添加当前请求时间戳
                await self.redis_client.zadd(redis_key, {str(now): now})
                await self.redis_client.expire(redis_key, int(window) + 1)
            
            return {
                "allowed": allowed,
                "remaining": remaining,
                "reset_time": int(now + window),
                "current": current
            }
        except Exception as e:
            logger.error("rate_limit_sliding_window_error", error=str(e), key=key)
            # 发生错误时允许请求通过
            return {"allowed": True, "remaining": -1, "reset_time": 0, "current": 0}
    
    async def _check_rate_limit(self, request: Request) -> Dict:
        """
        检查限流
        
        Args:
            request (Request): 请求对象
            
        Returns:
            Dict: 限流检查结果
        """
        # 获取限流key
        key = self.key_func(request)
        
        # 获取限流配置
        config = await self._get_limit_config(request)
        limit = config["limit"]
        window = config["window"]
        
        # 根据策略执行限流检查
        if self.strategy == "sliding_window":
            result = await self._sliding_window_strategy(key, limit, window)
        else:  # 默认使用固定窗口
            result = await self._fixed_window_strategy(key, limit, window)
        
        # 添加额外信息
        result.update({
            "key": key,
            "limit": limit,
            "window": window
        })
        
        return result
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> JSONResponse:
        """
        中间件核心处理逻辑
        
        Args:
            request (Request): 请求对象
            call_next (Callable): 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        # 初始化Redis连接
        if self.redis_client is None:
            await self.init_redis()
        
        try:
            # 检查是否需要跳过限流
            if self._should_skip_rate_limit(request):
                return await call_next(request)
            
            # 执行限流检查
            rate_limit_result = await self._check_rate_limit(request)
            
            # 如果超出限制，返回429错误
            if not rate_limit_result["allowed"]:
                logger.warning(
                    "rate_limit_exceeded",
                    key=rate_limit_result["key"],
                    current=rate_limit_result["current"],
                    limit=rate_limit_result["limit"],
                    path=request.url.path
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {rate_limit_result['limit']} per {rate_limit_result['window']} seconds.",
                        "retry_after": rate_limit_result["reset_time"] - int(time.time())
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                        "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                        "X-RateLimit-Reset": str(rate_limit_result["reset_time"])
                    }
                )
            
            # 继续处理请求
            response = await call_next(request)
            
            # 添加限流相关headers
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(rate_limit_result["reset_time"])
            
            return response
            
        except Exception as e:
            logger.error("rate_limit_middleware_error", error=str(e))
            # 发生错误时允许请求通过
            return await call_next(request)
    
    def _should_skip_rate_limit(self, request: Request) -> bool:
        """
        判断是否应该跳过限流检查
        
        Args:
            request (Request): 请求对象
            
        Returns:
            bool: True表示跳过限流，False表示需要检查
        """
        # 跳过健康检查等系统路径
        skip_paths = ["/health", "/metrics", "/ping"]
        if request.url.path in skip_paths:
            return True
        
        # 跳过静态文件
        if request.url.path.startswith("/static/") or request.url.path.endswith((".css", ".js", ".png", ".jpg", ".ico")):
            return True
        
        return False

class TokenBucketRateLimiter:
    """
    令牌桶限流器
    
    实现令牌桶算法的限流器，支持突发流量处理
    """
    
    def __init__(self, redis_client, key: str, capacity: int, refill_rate: float):
        """
        初始化令牌桶
        
        Args:
            redis_client: Redis客户端
            key (str): 限流key
            capacity (int): 桶容量
            refill_rate (float): 令牌补充速率(每秒)
        """
        self.redis_client = redis_client
        self.key = key
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens_key = f"token_bucket:tokens:{key}"
        self.timestamp_key = f"token_bucket:timestamp:{key}"
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        消费令牌
        
        Args:
            tokens (int): 需要消费的令牌数
            
        Returns:
            bool: True表示有足够的令牌，False表示令牌不足
        """
        try:
            now = time.time()
            
            # 获取当前令牌数和上次更新时间
            pipe = self.redis_client.pipeline()
            pipe.get(self.tokens_key)
            pipe.get(self.timestamp_key)
            results = await pipe.execute()
            
            current_tokens = float(results[0]) if results[0] else self.capacity
            last_timestamp = float(results[1]) if results[1] else now
            
            # 计算新增的令牌数
            elapsed = now - last_timestamp
            new_tokens = elapsed * self.refill_rate
            current_tokens = min(self.capacity, current_tokens + new_tokens)
            
            # 尝试消费令牌
            if current_tokens >= tokens:
                current_tokens -= tokens
                allowed = True
            else:
                allowed = False
            
            # 更新Redis中的值
            pipe = self.redis_client.pipeline()
            pipe.set(self.tokens_key, current_tokens)
            pipe.set(self.timestamp_key, now)
            pipe.expire(self.tokens_key, 60)  # 1分钟过期
            pipe.expire(self.timestamp_key, 60)
            await pipe.execute()
            
            return allowed
            
        except Exception as e:
            logger.error("token_bucket_consume_error", error=str(e), key=self.key)
            # 出错时允许通过
            return True

# 创建限流中间件的便捷函数
def create_rate_limit_middleware(app, 
                               redis_url: str = None,
                               default_limits: Optional[Dict] = None,
                               strategy: str = "fixed_window") -> RateLimitMiddleware:
    """
    创建限流中间件实例
    
    Args:
        app: ASGI应用
        redis_url (str): Redis连接URL
        default_limits (Dict, optional): 默认限流规则
        strategy (str): 限流策略
        
    Returns:
        RateLimitMiddleware: 限流中间件实例
        
    Example:
        >>> middleware = create_rate_limit_middleware(
        ...     app,
        ...     default_limits={
        ...         "anonymous": {"requests": 100, "window": 60},
        ...         "authenticated": {"requests": 1000, "window": 60}
        ...     }
        ... )
    """
    return RateLimitMiddleware(
        app,
        redis_url=redis_url,
        default_limits=default_limits,
        strategy=strategy
    )