from datetime import datetime, timedelta 
from jose import JWTError, jwt 
from passlib.context import CryptContext 
from app.config import settings 
 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") 
 
def create_access_token(data: dict, expires_delta: timedelta = None): 
    to_encode = data.copy() 
    if expires_delta: 
        expire = datetime.utcnow() + expires_delta 
    else: 
        expire = datetime.utcnow() + timedelta(days=7) 
    to_encode.update({"exp": expire}) 
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM) 
 
def verify_password(plain_password: str, hashed_password: str) -
    return pwd_context.verify(plain_password, hashed_password) 
 
def get_password_hash(password: str) -
    return pwd_context.hash(password) 

商家板块5数据分析
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.core.config import settings
from app.core.logging import logger

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token 模型
class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    scopes: list = []

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    logger.info(f"Access token created for user: {data.get('sub', 'unknown')}")
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenData]:
    """验证 JWT token"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        scopes: list = payload.get("scopes", [])
        
        if username is None:
            return None
            
        return TokenData(username=username, user_id=user_id, scopes=scopes)
    except JWTError as e:
        logger.warning(f"JWT token verification failed: {str(e)}")
        return None

def validate_api_key(api_key: str) -> bool:
    """验证 API Key (简化版本，生产环境应该使用数据库验证)"""
    # 这里应该从数据库或环境变量验证 API Key
    valid_keys = ["your-api-key-1", "your-api-key-2"]
    return api_key in valid_keys

    商家板块6财务中心
    from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.exceptions import CredentialsException


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取当前商户信息"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        merchant_id: str = payload.get("sub")
        if merchant_id is None:
            raise CredentialsException()
        return {"merchant_id": merchant_id, "payload": payload}
    except JWTError:
        raise CredentialsException()


async def validate_merchant_access(
    merchant_id: str,
    current_merchant: dict = Depends(get_current_merchant)
) -> bool:
    """验证商户访问权限"""
    current_merchant_id = current_merchant["merchant_id"]
    if current_merchant_id != merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该商户数据"
        )
    return True

    商家板块6财务中心
    import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
from app.core.config import settings


class RateLimiter:
    """速率限制器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
    
    async def is_rate_limited(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """检查是否超过速率限制"""
        try:
            current = self.redis_client.get(key)
            if current and int(current) >= max_requests:
                return True
            
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key, 1)
            pipeline.expire(key, window_seconds)
            pipeline.execute()
            
            return False
        except Exception:
            # 如果Redis不可用，不进行限流
            return False


class SecurityAudit:
    """安全审计"""
    
    @staticmethod
    async def log_security_event(
        event_type: str,
        merchant_id: str,
        user_id: str,
        details: Dict[str, Any],
        risk_level: str = "low"
    ):
        """记录安全事件"""
        logger = logging.getLogger('security')
        logger.warning(
            f"Security event: {event_type} - "
            f"Merchant: {merchant_id} - "
            f"User: {user_id} - "
            f"Risk: {risk_level} - "
            f"Details: {details}"
        )
    
    @staticmethod
    async def log_sensitive_operation(
        operation: str,
        merchant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        changes: Dict[str, Any] = None
    ):
        """记录敏感操作"""
        logger = logging.getLogger('audit')
        log_data = {
            "operation": operation,
            "merchant_id": merchant_id,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "timestamp": datetime.now().isoformat(),
            "changes": changes or {}
        }
        logger.info(f"Sensitive operation: {log_data}")


class DataEncryption:
    """数据加密工具"""
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: str = None) -> str:
        """哈希敏感数据"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用HMAC-SHA256进行哈希
        hashed = hmac.new(
            salt.encode(), 
            data.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return f"{salt}${hashed}"
    
    @staticmethod
    def verify_hashed_data(data: str, hashed: str) -> bool:
        """验证哈希数据"""
        try:
            salt, expected_hash = hashed.split('$')
            computed_hash = hmac.new(
                salt.encode(), 
                data.encode(), 
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False


# 增强的认证依赖
security = HTTPBearer(auto_error=False)


async def get_current_merchant_enhanced(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """增强的获取当前商户信息"""
    from app.core.security import create_access_token, verify_password
    from app.core.exceptions import CredentialsException
    
    if not credentials:
        raise CredentialsException()
    
    try:
        # JWT令牌验证
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        merchant_id: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if merchant_id is None:
            raise CredentialsException()
        
        # 记录请求中的商户信息（用于日志）
        request.state.merchant_id = merchant_id
        request.state.user_id = user_id
        
        return {
            "merchant_id": merchant_id,
            "user_id": user_id,
            "payload": payload
        }
        
    except JWTError as e:
        # 记录认证失败事件
        await SecurityAudit.log_security_event(
            "authentication_failed",
            "unknown",
            "unknown",
            {"reason": str(e), "token": credentials.credentials[:20] + "..."},
            "medium"
        )
        raise CredentialsException()


async def rate_limit_check(
    request: Request,
    current_merchant: dict = Depends(get_current_merchant_enhanced)
):
    """速率限制检查"""
    rate_limiter = RateLimiter()
    
    # 基于商户ID的限流
    merchant_key = f"rate_limit:merchant:{current_merchant['merchant_id']}"
    ip_key = f"rate_limit:ip:{request.client.host}"
    
    # 商户级别限流：100请求/分钟
    if await rate_limiter.is_rate_limited(merchant_key, 100, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后重试"
        )
    
    # IP级别限流：1000请求/分钟
    if await rate_limiter.is_rate_limited(ip_key, 1000, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后重试"
        )
    
    return True


async def sensitive_operation_protection(
    operation: str,
    current_merchant: dict = Depends(get_current_merchant_enhanced),
    verification_code: str = None
):
    """敏感操作保护"""
    # 记录敏感操作
    await SecurityAudit.log_sensitive_operation(
        operation,
        current_merchant['merchant_id'],
        current_merchant['user_id'],
        "financial_operation",
        operation
    )
    
    # 对于高风险操作，需要额外的验证
    high_risk_operations = ['settlement_confirm', 'large_export', 'bank_account_change']
    
    if operation in high_risk_operations:
        if not verification_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此操作需要验证码"
            )
        
        # 这里可以添加验证码验证逻辑
        # ...
    
    return True

    内容系统
    import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import json

from app.config import settings
from app.utils.logger import logger

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Redis 客户端
redis_client = redis.Redis.from_url(settings.redis_url, password=settings.redis_password, decode_responses=True)

class SecurityManager:
    """安全管理器"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """解码令牌"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"Token decode failed: {e}")
            return None
    
    @staticmethod
    def add_to_blacklist(token: str, expire_minutes: int = 30) -> bool:
        """将令牌加入黑名单"""
        try:
            expires = timedelta(minutes=expire_minutes)
            redis_client.setex(f"blacklist:{token}", expires, "true")
            return True
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
            return False
    
    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """检查令牌是否在黑名单中"""
        try:
            return redis_client.exists(f"blacklist:{token}") == 1
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return