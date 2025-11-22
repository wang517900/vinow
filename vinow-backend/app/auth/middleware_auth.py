交易系统

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import List, Optional, Dict, Any
import re
from app.utils.security_utils import verify_token
from app.utils.logger_api import logger

class JWTBearer(HTTPBearer):
    """
    JWT Bearer Token 认证类
    
    继承FastAPI的HTTPBearer类，提供JWT Token验证功能
    验证请求头中的Authorization字段，解析并验证JWT Token
    """
    
    def __init__(self, auto_error: bool = True):
        """
        初始化JWT认证器
        
        Args:
            auto_error (bool): 是否自动返回错误响应，默认为True
        """
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Dict[str, Any]:
        """
        调用认证器进行JWT验证
        
        Args:
            request (Request): FastAPI请求对象
            
        Returns:
            dict: JWT解码后的payload数据
            
        Raises:
            HTTPException: 当认证失败时抛出HTTP异常
            
        Example:
            >>> # 在路由中使用
            >>> @app.get("/protected")
            >>> async def protected_route(payload: dict = Depends(JWTBearer())):
            >>>     return {"user": payload}
        """
        try:
            # 调用父类的__call__方法获取凭证
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            
            if credentials:
                # 验证认证方案是否为Bearer
                if not credentials.scheme == "Bearer":
                    logger.warning(
                        "auth_invalid_scheme",
                        scheme=credentials.scheme,
                        path=request.url.path
                    )
                    raise HTTPException(
                        status_code=403, 
                        detail="Invalid authentication scheme. Must use Bearer token."
                    )
                
                # 验证并解析JWT token
                payload = verify_token(credentials.credentials)
                if not payload:
                    logger.warning(
                        "auth_invalid_token",
                        path=request.url.path
                    )
                    raise HTTPException(
                        status_code=403, 
                        detail="Invalid or expired token"
                    )
                
                # 记录成功的认证
                logger.info(
                    "auth_success",
                    user_id=payload.get("sub"),
                    path=request.url.path
                )
                
                return payload
            else:
                logger.warning(
                    "auth_missing_credentials",
                    path=request.url.path
                )
                raise HTTPException(
                    status_code=403, 
                    detail="Missing authorization credentials"
                )
                
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            logger.error(
                "auth_unexpected_error",
                error=str(e),
                path=request.url.path
            )
            raise HTTPException(
                status_code=500,
                detail="Internal authentication error"
            )

class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件
    
    处理所有请求的认证逻辑，可以选择性地跳过特定路径的认证
    将用户信息注入到请求状态中供后续处理使用
    """
    
    def __init__(self, app, skip_paths: Optional[List[str]] = None, 
                 skip_pattern: Optional[str] = None):
        """
        初始化认证中间件
        
        Args:
            app: ASGI应用
            skip_paths (List[str], optional): 需要跳过认证的路径列表
            skip_pattern (str, optional): 需要跳过认证的路径正则表达式
        """
        super().__init__(app)
        
        # 默认跳过认证的路径
        self.skip_paths = set(skip_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/api/v1/payments/callback/momo",
            "/api/v1/payments/callback/zalopay",
            "/api/v1/payments/callback/vnpay"
        ])
        
        # 跳过路径的正则表达式模式
        self.skip_pattern = re.compile(skip_pattern) if skip_pattern else None
        
        logger.info(
            "auth_middleware_initialized",
            skip_paths=list(self.skip_paths)
        )
    
    def _should_skip_auth(self, request: Request) -> bool:
        """
        判断是否应该跳过认证
        
        Args:
            request (Request): 请求对象
            
        Returns:
            bool: True表示跳过认证，False表示需要认证
        """
        path = request.url.path
        
        # 检查是否在跳过路径列表中
        if path in self.skip_paths:
            return True
            
        # 检查是否匹配跳过路径模式
        if self.skip_pattern and self.skip_pattern.match(path):
            return True
            
        # 检查是否以跳过路径开头
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
                
        return False
    
    async def dispatch(self, request: Request, call_next):
        """
        中间件核心处理逻辑
        
        Args:
            request (Request): 请求对象
            call_next: 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        try:
            # 检查是否需要跳过认证
            if self._should_skip_auth(request):
                logger.debug(
                    "auth_skipped",
                    path=request.url.path
                )
                return await call_next(request)
            
            # 初始化用户状态
            request.state.user = None
            
            # 从header获取token
            auth_header = request.headers.get("Authorization")
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]  # 移除 "Bearer " 前缀
                
                try:
                    # 验证JWT token
                    payload = verify_token(token)
                    
                    if payload:
                        # 将用户信息存储到请求状态中
                        request.state.user = payload
                        
                        logger.info(
                            "auth_user_authenticated",
                            user_id=payload.get("sub"),
                            path=request.url.path
                        )
                    else:
                        logger.warning(
                            "auth_token_invalid",
                            path=request.url.path
                        )
                        # 对于需要认证但token无效的请求，返回401
                        return JSONResponse(
                            status_code=401,
                            content={"detail": "Invalid or expired token"}
                        )
                        
                except Exception as e:
                    logger.error(
                        "auth_token_verification_error",
                        error=str(e),
                        path=request.url.path
                    )
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication error"}
                    )
                    
            else:
                # 没有提供认证信息
                logger.debug(
                    "auth_missing_header",
                    path=request.url.path
                )
                # 对于需要认证但没有提供token的请求，返回401
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing or invalid"}
                )
                
        except Exception as e:
            logger.error(
                "auth_middleware_error",
                error=str(e),
                path=request.url.path
            )
            # 中间件内部错误不应该阻止请求处理
            request.state.user = None
        
        # 继续处理请求
        response = await call_next(request)
        return response

class PermissionChecker:
    """
    权限检查器
    
    用于检查用户是否有执行特定操作的权限
    """
    
    @staticmethod
    def has_permission(user_payload: Dict[str, Any], required_permissions: List[str]) -> bool:
        """
        检查用户是否具有所需权限
        
        Args:
            user_payload (dict): 用户JWT payload
            required_permissions (List[str]): 所需权限列表
            
        Returns:
            bool: True表示有权限，False表示无权限
        """
        if not user_payload:
            return False
            
        # 从payload中获取用户权限
        user_permissions = user_payload.get("permissions", [])
        
        # 检查是否拥有所有必需权限
        return all(permission in user_permissions for permission in required_permissions)
    
    @staticmethod
    def require_permission(permissions: List[str]):
        """
        权限依赖注入装饰器
        
        Args:
            permissions (List[str]): 所需权限列表
            
        Returns:
            callable: 依赖注入函数
        """
        def permission_dependency(current_user: dict = Depends(JWTBearer())):
            if not PermissionChecker.has_permission(current_user, permissions):
                logger.warning(
                    "auth_permission_denied",
                    user_id=current_user.get("sub") if current_user else None,
                    required_permissions=permissions
                )
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
            return current_user
        return permission_dependency

# 创建全局认证中间件实例的工厂函数
def create_auth_middleware(app, 
                          skip_paths: Optional[List[str]] = None,
                          skip_pattern: Optional[str] = None) -> AuthMiddleware:
    """
    创建认证中间件实例
    
    Args:
        app: ASGI应用
        skip_paths (List[str], optional): 需要跳过认证的路径列表
        skip_pattern (str, optional): 需要跳过认证的路径正则表达式
        
    Returns:
        AuthMiddleware: 认证中间件实例
        
    Example:
        >>> middleware = create_auth_middleware(
        ...     app,
        ...     skip_paths=["/public", "/health"],
        ...     skip_pattern=r"^/api/v1/hooks/"
        ... )
    """
    return AuthMiddleware(
        app,
        skip_paths=skip_paths,
        skip_pattern=skip_pattern
    )

# 默认的JWT认证依赖
oauth2_scheme = JWTBearer()