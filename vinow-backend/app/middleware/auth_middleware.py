内容板块-认证中间件
"""
认证中间件模块

本模块提供了基于JWT令牌的认证中间件，用于处理API请求的身份验证和授权。
主要功能包括：
1. 请求认证检查
2. JWT令牌验证
3. 用户状态检查
4. 认证失败处理
5. 性能监控和日志记录

支持的特性：
- 路径排除（无需认证的路径）
- 用户状态缓存
- 详细的错误处理和日志记录
- 请求处理时间监控
"""

from typing import Callable, Optional, Dict, Any, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.security import verify_token
from app.utils.cache_utils import cache_manager
import logging
import time

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = ['AuthenticationMiddleware']


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    认证中间件 - 处理请求认证和授权
    """
    
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        """
        初始化认证中间件
        
        Args:
            app: FastAPI应用实例
            exclude_paths: 不需要认证的路径列表
        """
        # 调用父类初始化
        super().__init__(app)
        # 设置排除路径
        self.exclude_paths = exclude_paths or [
            "/health",  # 健康检查
            "/docs",  # API文档
            "/redoc",  # ReDoc文档
            "/openapi.json",  # OpenAPI规范
            "/favicon.ico",  # 网站图标
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        处理请求分发
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            HTTP响应
            
        Raises:
            HTTPException: 认证失败或服务器错误时抛出
        """
        # 记录请求开始时间
        start_time = time.time()
        
        try:
            # 检查请求路径是否在排除列表中
            if await self._should_skip_auth(request):
                # 跳过认证，直接调用下一个处理函数
                response = await call_next(request)
                return response
            
            # 执行认证检查
            auth_result = await self._authenticate_request(request)
            
            if not auth_result["authenticated"]:
                # 认证失败，返回401未授权
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "message": "认证失败",
                        "error": {
                            "code": "AUTHENTICATION_FAILED",
                            "details": auth_result.get("reason", "未知原因")
                        },
                        "data": None
                    }
                )
            
            # 认证成功，将用户信息添加到请求状态中
            request.state.user = auth_result["user"]
            
            # 调用下一个处理函数
            response = await call_next(request)
            
            # 计算请求处理时间
            process_time = time.time() - start_time
            
            # 记录认证成功的请求
            logger.info(
                f"认证请求处理完成: {request.method} {request.url} - "
                f"用户: {auth_result['user'].get('user_id')} - "
                f"状态: {response.status_code} - 耗时: {process_time:.2f}s"
            )
            
            return response
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录认证中间件异常
            logger.error(f"认证中间件异常: {str(e)}", exc_info=True)
            # 返回500内部服务器错误
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "服务器内部错误",
                    "error": {
                        "code": "MIDDLEWARE_ERROR",
                        "details": str(e)
                    },
                    "data": None
                }
            )
    
    async def _should_skip_auth(self, request: Request) -> bool:
        """
        检查是否应该跳过认证
        
        Args:
            request: 请求对象
            
        Returns:
            是否跳过认证
        """
        # 获取请求路径
        path = request.url.path
        
        # 检查路径是否在排除列表中
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        
        # 检查OPTIONS请求（预检请求）
        if request.method == "OPTIONS":
            return True
        
        return False
    
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """
        认证请求
        
        Args:
            request: 请求对象
            
        Returns:
            认证结果字典
        """
        try:
            # 从请求头获取Authorization头
            auth_header = request.headers.get("Authorization")
            
            # 检查Authorization头是否存在
            if not auth_header:
                return {
                    "authenticated": False,
                    "reason": "缺少Authorization头"
                }
            
            # 检查Authorization头格式（应该是Bearer token）
            if not auth_header.startswith("Bearer "):
                return {
                    "authenticated": False,
                    "reason": "无效的Authorization头格式"
                }
            
            # 提取令牌
            token = auth_header[7:]  # 移除"Bearer "前缀
            
            # 验证令牌
            payload = verify_token(token)
            
            # 检查令牌是否有效
            if not payload:
                return {
                    "authenticated": False,
                    "reason": "无效的认证令牌"
                }
            
            # 从令牌中提取用户信息
            user_id = payload.get("user_id")
            username = payload.get("username")
            email = payload.get("email")
            
            # 检查用户ID是否存在
            if not user_id:
                return {
                    "authenticated": False,
                    "reason": "令牌中缺少用户ID"
                }
            
            # 构建用户信息
            user_info = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "token": token
            }
            
            # 检查用户状态（这里可以添加更复杂的用户状态检查）
            is_active = await self._check_user_status(user_id)
            if not is_active:
                return {
                    "authenticated": False,
                    "reason": "用户账户已被禁用"
                }
            
            # 认证成功
            return {
                "authenticated": True,
                "user": user_info
            }
            
        except Exception as e:
            # 记录认证异常
            logger.error(f"请求认证异常: {str(e)}", exc_info=True)
            return {
                "authenticated": False,
                "reason": "认证过程发生异常"
            }
    
    async def _check_user_status(self, user_id: str) -> bool:
        """
        检查用户状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户是否活跃
        """
        try:
            # 这里应该实现实际的用户状态检查逻辑
            # 简化实现：从缓存或数据库检查用户状态
            
            # 尝试从缓存获取用户状态
            cache_key = f"user:{user_id}:status"
            cached_status = await cache_manager.get(cache_key)
            
            if cached_status is not None:
                # 使用缓存的状态
                return cached_status.get("is_active", True)
            
            # 如果缓存中没有，这里应该查询数据库
            # 简化实现：假设所有用户都是活跃的
            user_status = {"is_active": True}
            
            # 将用户状态缓存5分钟
            await cache_manager.set(cache_key, user_status, expire=300)
            
            # 返回用户状态
            return user_status.get("is_active", True)
            
        except Exception as e:
            # 记录用户状态检查异常
            logger.error(f"用户状态检查异常: {str(e)}", exc_info=True)
            # 在异常情况下，默认允许访问（避免因为状态检查失败导致服务不可用）
            return True

    内容模块-认证中间件

  import logging
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import time

from app.utils.security import verify_token
from app.utils.cache import cache_redis
from app.utils.exceptions import AuthenticationException, AuthorizationException

logger = logging.getLogger(__name__)


class JWTBearer(HTTPBearer):
    """JWT Bearer认证"""
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无效的认证方案"
                )
            
            token = credentials.credentials
            payload = await self.verify_jwt(token)
            
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无效或过期的令牌"
                )
            
            # 检查令牌是否在黑名单中
            if await self.is_token_blacklisted(token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="令牌已失效"
                )
            
            return payload
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="认证凭证无效"
            )
    
    async def verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = verify_token(token)
            if payload is None:
                return None
            
            # 检查令牌是否过期
            if payload.get("exp") and payload["exp"] < time.time():
                return None
            
            return payload
        except Exception as e:
            logger.error(f"JWT verification error: {str(e)}")
            return None
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        try:
            blacklist_key = f"token_blacklist:{token}"
            return await cache_redis.exists(blacklist_key)
        except Exception as e:
            logger.error(f"Token blacklist check error: {str(e)}")
            return False


async def get_current_user(request: Request) -> Dict[str, Any]:
    """获取当前用户"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationException("缺少认证令牌")
    
    token = auth_header.replace("Bearer ", "")
    payload = verify_token(token)
    
    if not payload:
        raise AuthenticationException("无效的认证令牌")
    
    user_id = payload.get("user_id")
    if not user_id:
        raise AuthenticationException("令牌中缺少用户信息")
    
    # 检查用户状态（这里可以添加更多用户状态检查）
    user_status = await get_user_status(user_id)
    if user_status != "active":
        raise AuthorizationException("用户账户不可用")
    
    return {
        "user_id": user_id,
        "role": payload.get("role", "user"),
        "email": payload.get("email"),
        "permissions": payload.get("permissions", [])
    }


async def get_user_status(user_id: str) -> str:
    """获取用户状态（简化实现）"""
    # 实际项目中应该从数据库查询用户状态
    try:
        user_key = f"user:{user_id}:status"
        status = await cache_redis.get(user_key)
        return status or "active"
    except Exception:
        return "active"


async def require_permission(required_permission: str):
    """权限检查装饰器"""
    async def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = current_user.get("permissions", [])
        user_role = current_user.get("role")
        
        # 管理员拥有所有权限
        if user_role == "admin":
            return current_user
        
        if required_permission not in user_permissions:
            raise AuthorizationException(f"缺少所需权限: {required_permission}")
        
        return current_user
    
    return permission_dependency


async def require_role(required_role: str):
    """角色检查装饰器"""
    async def role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role")
        
        if user_role != required_role:
            raise AuthorizationException(f"需要{required_role}角色")
        
        return current_user
    
    return role_dependency


# 全局认证实例
auth_scheme = JWTBearer()  